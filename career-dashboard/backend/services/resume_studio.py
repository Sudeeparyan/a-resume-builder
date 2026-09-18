"""Job-specific editable drafts, version history and deterministic profile capture."""
from __future__ import annotations
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import threading
import yaml
from pathlib import Path
from pypdf import PdfReader
from career import atomic_write, company_key, safe_child, tex_escape
from validate_resume import extract_zero_argument_macros, inspect_pdf, evidence_ids_from_source
from backend.services.resume_layout import ranked_source, set_density, measure_pages


LEGACY_PROJECT_SECTION = re.compile(r'\\section\{(?:Selected|Academic) Projects?\}')


def project_registry(evidence):
    return {p.get('id'): p for p in evidence.get('projects', []) if isinstance(p, dict)}


EMPTY_ITEM_BLOCK = re.compile(
    r'\n?\s*\\begin\{(resumeitems|itemize)\}\s*(?:%[^\n]*\n\s*)*\\end\{\1\}[ \t]*\n?'
)


def drop_empty_item_blocks(source):
    """Remove bullet lists left empty by an earlier content migration.

    LaTeX raises "perhaps a missing \\item" on an empty itemize, which made one
    saved draft uncompilable after its academic bullets were removed.
    """
    return EMPTY_ITEM_BLOCK.sub('\n', source)


ROLE_HEADING_BODY = "  \\textit{#3} \\hfill \\textit{#4}\\vspace{3pt}"
ROLE_HEADING_FIX = (
    "  \\settowidth{\\roleheadingright}{\\textit{#4}}%\n"
    "  \\parbox[t]{\\dimexpr\\linewidth-\\roleheadingright-1em\\relax}{\\raggedright\\textit{#3}}%\n"
    "  \\hfill\\parbox[t]{\\roleheadingright}{\\raggedleft\\textit{#4}}\\vspace{3pt}"
)


def upgrade_role_heading(source):
    """Keep the right-hand location on the heading line when the qualification wraps.

    The old macro put #3 and #4 in one paragraph, so a long degree line pushed the
    location onto its own line and split 'Honours (1:1)'. Giving each its own column
    lets #3 wrap while #4 stays right-aligned at the top.
    """
    if ROLE_HEADING_BODY not in source or "\\roleheadingright" in source:
        return source
    source = source.replace(ROLE_HEADING_BODY, ROLE_HEADING_FIX, 1)
    return source.replace(
        "\\newcommand{\\roleheading}[4]{%",
        "\\newlength{\\roleheadingright}\n\\newcommand{\\roleheading}[4]{%",
        1,
    )


def rename_projects_section(source):
    """Fold legacy Selected/Academic Project headings into the single Projects section."""
    if LEGACY_PROJECT_SECTION.search(source) and '\\section{Projects}' in source:
        # Renaming here would create a second Projects section; leave it for manual review.
        return source
    return LEGACY_PROJECT_SECTION.sub(r'\\section{Projects}', source)


def plain(text):
    for before, after in [(r'\textbar{}', '|'), (r'\textbackslash{}', '\\'),
                          (r'\textasciitilde{}', '~'), (r'\textasciicircum{}', '^')]:
        text = text.replace(before, after)
    return re.sub(r'\\([&%$#_{}])', r'\1', text).strip()


def replace_macro(source, name, value):
    if name == 'CoreSkills':
        from backend.resume_rules import canonicalize_skill_list
        value = canonicalize_skill_list(value)
    old = extract_zero_argument_macros(source).get(name)
    if old is None:
        raise ValueError('Template field is missing: ' + name + '. Use the source editor to restore it.')
    prefix = re.search(r'\\newcommand\{\\' + re.escape(name) + r'\}\s*\{', source)
    start = prefix.end()
    return source[:start] + tex_escape(value.replace('\n', ' ')) + source[start + len(old):]


class ResumeStudio:
    def __init__(self, service):
        self.s, self.w = service, service.w
        self.lock = threading.RLock()
        with self.w.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS studio_drafts(job_id TEXT PRIMARY KEY REFERENCES jobs(id), source TEXT NOT NULL, revision INTEGER NOT NULL, folder TEXT NOT NULL, updated_at TEXT NOT NULL, profile_revision TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS studio_versions(job_id TEXT NOT NULL REFERENCES jobs(id), revision INTEGER NOT NULL, source TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(job_id,revision));
            CREATE TABLE IF NOT EXISTS resume_scores(job_id TEXT NOT NULL REFERENCES jobs(id), revision INTEGER NOT NULL, source_sha256 TEXT NOT NULL, pdf_sha256 TEXT NOT NULL, jd_sha256 TEXT NOT NULL, result TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(job_id,revision,jd_sha256,pdf_sha256));
            CREATE TABLE IF NOT EXISTS studio_captures(job_id TEXT NOT NULL REFERENCES jobs(id), fingerprint TEXT NOT NULL, knowledge_id TEXT NOT NULL REFERENCES knowledge(id), PRIMARY KEY(job_id,fingerprint));
            ''')

    def stale_drafts(self):
        """Drafts whose compiled PDF no longer matches the saved source."""
        stale = []
        with self.w.connect() as db:
            rows = db.execute('SELECT job_id FROM studio_drafts ORDER BY job_id').fetchall()
        for row in rows:
            draft = self.get(row['job_id'])
            preview = draft.get('preview')
            if not preview or not preview.get('current') or preview.get('revision') != draft['revision']:
                stale.append({'job_id': row['job_id'], 'revision': draft['revision'],
                              'reason': 'never compiled' if not preview else 'compiled from an older source'})
        return stale

    def recompile_stale(self, job_ids=None, on_progress=None):
        """Rebuild the PDF for every draft whose source changed after its last compile.

        migrate_current_drafts rewrites saved LaTeX without compiling, which leaves the
        stored PDF showing the superseded wording and hides the PDF download. This
        reconciles the artifacts with the source; it never edits the source itself.
        """
        targets = [d for d in self.stale_drafts() if job_ids is None or d['job_id'] in set(job_ids)]
        rebuilt, failed = [], []
        for target in targets:
            if on_progress:
                on_progress(target)
            try:
                draft = self.preview(target['job_id'], target['revision'])
                rebuilt.append({'job_id': target['job_id'], 'revision': target['revision'],
                                'pages': (draft.get('preview') or {}).get('page_count')})
            except Exception as error:
                failed.append({'job_id': target['job_id'], 'revision': target['revision'], 'error': str(error)[:500]})
        return {'checked': len(targets), 'rebuilt': rebuilt, 'failed': failed}

    def open(self, job_id):
        with self.lock:
            job = self.w.get_job(job_id)
            with self.w.connect() as db:
                row = db.execute('SELECT * FROM studio_drafts WHERE job_id=?', (job_id,)).fetchone()
            if not row:
                if self.s.profile_dirty():
                    raise ValueError('Profile edits need evidence reconciliation before creating a new resume. Open Profile and confirm the pending entries; existing Studio drafts remain editable.')
                if not job['folder']:
                    self.w.prepare(job_id)
                folder = self.w.current_folder(job_id)
                source = (folder / 'resume.tex').read_text()
                # Preserve existing prepared wording. Only a newly prepared draft gets skill ordering.
                if not job['folder']:
                    macros = extract_zero_argument_macros(source)
                    jd = (job['title'] + ' ' + job['description']).casefold()
                    for name, value in macros.items():
                        if name.startswith('Skills') or name == 'CoreSkills':
                            separator = '; ' if '; ' in value else ', '
                            skills = plain(value).split(separator)
                            skills.sort(key=lambda skill: skill.casefold() not in jd)
                            source = replace_macro(source, name, separator.join(skills))
                mapping_file = folder / 'evidence-map.yml'
                draft_profile_revision = (yaml.safe_load(mapping_file.read_text()) or {}).get('candidate_revision', self.w.evidence()['candidate_revision']) if mapping_file.exists() else self.w.evidence()['candidate_revision']
                studio_folder = folder / 'studio'
                studio_folder.mkdir(exist_ok=True)
                stamp = self.s.now()
                with self.w.connect() as db:
                    db.execute('INSERT INTO studio_drafts VALUES(?,?,?,?,?,?)', (job_id, source, 1, str(studio_folder.relative_to(self.w.root)), stamp, draft_profile_revision))
                    db.execute('INSERT INTO studio_versions VALUES(?,?,?,?)', (job_id, 1, source, stamp))
                    self.w.record_event(db, 'studio_opened', job_id, revision=1)
                self.w.export_tracking()
            return self.get(job_id)

    def get(self, job_id):
        with self.w.connect() as db:
            row = db.execute('SELECT * FROM studio_drafts WHERE job_id=?', (job_id,)).fetchone()
            if not row:
                raise ValueError('Open Resume Studio for this job first')
            versions = [dict(r) for r in db.execute('SELECT revision,created_at FROM studio_versions WHERE job_id=? ORDER BY revision DESC', (job_id,))]
            captures = [dict(r) for r in db.execute('SELECT DISTINCT k.id,k.kind,k.title,k.review_state,k.deleted FROM studio_captures c JOIN knowledge k ON k.id=c.knowledge_id WHERE c.job_id=?', (job_id,))]
        result = dict(row)
        folder = safe_child(self.w.root / 'data/output', str(Path(row['folder']).relative_to('data/output')))
        atomic_write(folder / 'resume.tex', row['source'])
        preview_file = folder / 'preview.json'
        preview = json.loads(preview_file.read_text()) if preview_file.exists() else None
        if preview:
            preview['current'] = preview['source_sha256'] == hashlib.sha256(row['source'].encode()).hexdigest()
        fields = {k: plain(v) for k, v in extract_zero_argument_macros(row['source']).items() if k in {'ResumeSummary', 'CoreSkills'} or k.startswith(('SelectedProject', 'SecondProject'))}
        warnings = []
        if self.s.profile_dirty():
            warnings.append('Profile has unreviewed changes. Reconcile evidence before releasing this resume; this saved draft may contain older wording.')
        if row['profile_revision'] != self.w.evidence()['candidate_revision']:
            warnings.append('This draft was started with an older evidence revision. Review it against the current profile.')
        if not fields.get('SelectedProjectTitle') or not fields.get('SelectedProjectBulletOne'):
            warnings.append('Your selected project is missing. Add a project before exporting your application resume.')
        if preview and preview.get('layout') and not preview['layout']['full_pages']:
            warnings.append('The preview is not exactly one full page. Use Fit to one page to rank supported content and trim in the documented order.')
        warnings.append('Draft only: wording, evidence, one-page layout and visual review must pass before release.')
        if not fields.get('SecondProjectID') or not fields.get('SecondProjectTitle') or not fields.get('SecondProjectBulletOne'):
            warnings.append('A supporting project is required alongside the signature project. Sync profile & rank projects, or select a second registered project.')
        active_projects = {i['id'] for i in self.s.knowledge() if i['kind'] == 'project' and i['review_state'] == 'registered'}
        with self.w.connect() as db:
            score_row = db.execute('SELECT * FROM resume_scores WHERE job_id=? ORDER BY created_at DESC,rowid DESC LIMIT 1', (job_id,)).fetchone()
        match = None
        preview_pdf = safe_child(self.w.root / 'data/output', preview['path'] + '/resume.pdf') if preview else None
        current_pdf_hash = hashlib.sha256(preview_pdf.read_bytes()).hexdigest() if preview_pdf and preview_pdf.exists() else None
        if score_row:
            match = {**json.loads(score_row['result']), 'revision': score_row['revision'], 'created_at': score_row['created_at'],
                     'current': score_row['source_sha256'] == hashlib.sha256(row['source'].encode()).hexdigest()
                     and score_row['jd_sha256'] == hashlib.sha256(self.w.get_job(job_id)['description'].encode()).hexdigest()
                     and score_row['pdf_sha256'] == current_pdf_hash}
        library = self.s.knowledge()
        ranked = self.w.rank_projects(self.w.get_job(job_id)['description'])
        ranks = {p['id']: (index + 1, p) for index, p in enumerate(ranked)}
        projects = []
        for item in library:
            if item['kind'] != 'project':
                continue
            rank, known = ranks.get(item['id'], (None, {}))
            projects.append({'id': item['id'], 'title': item['title'], 'rank': rank if item['review_state'] == 'registered' else None,
                             'review_state': item['review_state'], 'eligible': item['id'] in active_projects and bool(known),
                             'score': known.get('match_count'), 'reason': known.get('matched_terms', [])})
        projects.sort(key=lambda p: (p['rank'] is None, p['rank'] or 999, p['title']))
        return {**result, 'fields': fields, 'match': match, 'project_library': projects, 'preview': preview, 'versions': versions,
                'captures': captures, 'warnings': warnings, 'file_root': str(folder.relative_to(self.w.root / 'data/output')),
                'projects': [p for p in self.w.rank_projects(self.w.get_job(job_id)['description']) if p['id'] in active_projects]}

    def capture(self, db, job_id, kind, title, summary):
        title, summary = title.strip()[:250], summary.strip()[:30000]
        if not title:
            return
        fingerprint = hashlib.sha256((kind + '\n' + title.casefold() + '\n' + summary).encode()).hexdigest()
        if db.execute('SELECT 1 FROM studio_captures WHERE job_id=? AND fingerprint=?', (job_id, fingerprint)).fetchone():
            return
        # Reuse an exact entry across jobs; never resurrect a deleted profile entry.
        old = db.execute('SELECT id,deleted FROM knowledge WHERE kind=? AND lower(title)=lower(?) AND summary=?', (kind, title, summary)).fetchone()
        if old and old['deleted']:
            return
        related = db.execute("SELECT * FROM knowledge WHERE kind=? AND lower(title)=lower(?) AND source=?", (kind, title, 'User edit in Resume Studio for job ' + job_id)).fetchone()
        if not old and related and not related['deleted']:
            db.execute("UPDATE knowledge SET summary=?,revision=revision+1,review_state='user_updated',updated_at=? WHERE id=?", (summary, self.s.now(), related['id']))
            self.w.record_event(db, 'profile_entry_saved', job_id, entry_id=related['id'], before=dict(related), summary=summary, origin='resume_studio')
            old = related
        key = old['id'] if old else 'studio:' + fingerprint[:24]
        if not old:
            db.execute('INSERT INTO knowledge VALUES(?,?,?,?,?,?,?,?,?,?)', (key, kind, title, summary,
                json.dumps({'origin': 'resume_studio', 'job_id': job_id, 'user_supplied': True}),
                'User edit in Resume Studio for job ' + job_id, 1, 0, 'user_updated', self.s.now()))
            self.w.record_event(db, 'profile_entry_saved', job_id, entry_id=key, origin='resume_studio', kind=kind)
        db.execute('INSERT OR IGNORE INTO studio_captures VALUES(?,?,?)', (job_id, fingerprint, key))

    def track(self, db, job_id, before, after):
        if 'SecondProjectTitle' in after:
            # Reuse the first-slot tracker on a document containing only second-slot definitions.
            def second_only(text):
                return '\n'.join(line for line in text.splitlines() if 'SecondProject' in line).replace('SecondProject', 'SelectedProject')
            self.track(db, job_id, second_only(before), second_only(after))
        old, new = extract_zero_argument_macros(before), extract_zero_argument_macros(after)
        keys = ['SelectedProjectTitle', 'SelectedProjectContext', 'SelectedProjectBulletOne', 'SelectedProjectBulletTwo', 'SelectedProjectBulletThree']
        if any(old.get(k) != new.get(k) for k in keys) and new.get('SelectedProjectTitle'):
            title = plain(new['SelectedProjectTitle'])
            summary = '\n'.join(plain(new[k]) for k in keys[1:] if new.get(k))
            registered = any(p.get('resume_content', {}).get('title') == title and
                             '\n'.join([p['resume_content'].get('context', ''), *p['resume_content'].get('bullets', [])]) == summary
                             for p in self.w.evidence()['projects'])
            if not registered:
                self.capture(db, job_id, 'project', title, summary)
        def skills(source, macros):
            text = ';'.join(plain(v) for k, v in macros.items() if k.startswith('Skills') or k == 'CoreSkills')
            section = source.split(r'\section{Technical Skills}')
            if len(section) > 1:
                body = section[1].split(r'\section{')[0].split(r'\end{document}')[0]
                for line in body.splitlines():
                    if line.strip().startswith(r'\textbf{') and not line.strip().startswith(r'\textbf{Languages'):
                        text += ';' + re.sub(r'\\\\\[.*?\]', '', line.split('}', 1)[-1])
            from backend.resume_rules import parse_skills
            return {s: s.casefold() for s in parse_skills(plain(text))}
        previous = set(skills(before, old).values())
        known = ' '.join(r['title'] + ' ' + r['summary'] for r in db.execute("SELECT title,summary FROM knowledge WHERE kind='skill' AND deleted=0")).casefold()
        for skill, normalized in skills(after, new).items():
            if normalized not in previous and not re.search(r'(?<!\w)' + re.escape(normalized) + r'(?!\w)', known):
                self.capture(db, job_id, 'skill', skill, skill)

    def save(self, job_id, revision, source=None, fields=None, project_id=None, restore_revision=None, second_project_id=None):
        with self.lock, self.w.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM studio_drafts WHERE job_id=?', (job_id,)).fetchone()
            if not row or row['revision'] != revision:
                raise ValueError('This resume changed elsewhere. Copy your edits, then reload before saving.')
            before = row['source']
            if restore_revision is not None:
                version = db.execute('SELECT source FROM studio_versions WHERE job_id=? AND revision=?', (job_id, restore_revision)).fetchone()
                if not version:
                    raise ValueError('Saved version not found')
                source = version['source']
            source = before if source is None else source
            for name, value in (fields or {}).items():
                if name not in {'ResumeSummary', 'CoreSkills', 'Coursework'} and not name.startswith(('SelectedProject', 'SecondProject', 'Skills')):
                    raise ValueError('Unknown resume field')
                source = replace_macro(source, name, value)
            if project_id or second_project_id:
                from backend.services.resume_projects import install_project
                active = {i['id']: i for i in self.s.knowledge()}
                for chosen, second in [(project_id, False), (second_project_id, True)]:
                    if not chosen:
                        continue
                    project = next((p for p in self.w.rank_projects('') if p['id'] == chosen), None)
                    if not project or chosen not in active or active[chosen]['review_state'] != 'registered':
                        raise ValueError('Choose an active registered project. Edited projects need evidence review.')
                    if not second and project_registry(self.w.evidence()).get(chosen, {}).get('signature_eligible') is False:
                        raise ValueError(f'{chosen} is registered as a supporting project only and cannot lead Projects.')
                    other = extract_zero_argument_macros(source).get('SelectedProjectID' if second else 'SecondProjectID')
                    if other == chosen:
                        raise ValueError('Choose two distinct projects')
                    if not second:
                        # One signature project per company: another company's signature may only be a supporting project here.
                        mine = company_key(db.execute('SELECT company FROM jobs WHERE id=?', (job_id,)).fetchone()[0])
                        owner = db.execute('SELECT company_key FROM signature_assignments WHERE project_id=? AND company_key<>?', (chosen, mine)).fetchone()
                        if owner:
                            raise ValueError(f'{chosen} is already the signature project for another company ({owner[0]}). A signature project is never reused across companies; use it as the supporting project instead.')
                    source = install_project(source, project, second)
            if extract_zero_argument_macros(before).get('SelectedProjectID') != extract_zero_argument_macros(source).get('SelectedProjectID'):
                source = re.sub(r'% STUDIO_PROJECT_SKILLS\n% EVIDENCE:[^\n]+\n[^\n]+\n', '', source)
            if not source.strip() or len(source) > 150000:
                raise ValueError('Resume source must contain 1–150,000 characters')
            if source != before:
                if restore_revision is None:
                    self.track(db, job_id, before, source)
                stamp = self.s.now()
                db.execute('UPDATE studio_drafts SET source=?,revision=revision+1,updated_at=? WHERE job_id=?', (source, stamp, job_id))
                db.execute('INSERT INTO studio_versions VALUES(?,?,?,?)', (job_id, revision + 1, source, stamp))
                signature = extract_zero_argument_macros(source).get('SelectedProjectID')
                if signature and signature != extract_zero_argument_macros(before).get('SelectedProjectID'):
                    db.execute('INSERT OR REPLACE INTO signature_assignments(company_key, project_id, job_id, assigned_at) VALUES(?,?,?,?)',
                               (company_key(db.execute('SELECT company FROM jobs WHERE id=?', (job_id,)).fetchone()[0]), signature, job_id, stamp))
                self.w.record_event(db, 'studio_saved', job_id, revision=revision + 1, restored_from=restore_revision)
        self.s.export_profile()
        self.w.export_tracking()
        return self.get(job_id)

    def write_review_sources(self, target, source, job_id):
        """Keep each preview's JD and claim references aligned without claiming a review."""
        original = self.w.current_folder(job_id)
        mapping_path = original / 'evidence-map.yml'
        mapping = yaml.safe_load(mapping_path.read_text()) if mapping_path.exists() else {}
        snapshot = original / 'job-description.md'
        if snapshot.exists():
            shutil.copy2(snapshot, target / 'job-description.md')
            mapping['job_snapshot_sha256'] = hashlib.sha256(snapshot.read_bytes()).hexdigest()
        errors = []
        ids = evidence_ids_from_source(source, self.w.evidence(), errors)
        mapping.update(job_id=job_id, resume_claim_ids=sorted(ids),
                       selected_project_id=extract_zero_argument_macros(source).get('SelectedProjectID'),
                       selected_project_ids=[extract_zero_argument_macros(source).get(k) for k in ('SelectedProjectID', 'SecondProjectID') if extract_zero_argument_macros(source).get(k)],
                       candidate_revision=self.w.evidence()['candidate_revision'],
                       studio_review_required=True, source_evidence_errors=errors)
        atomic_write(target / 'resume.tex', source)
        atomic_write(target / 'evidence-map.yml', yaml.safe_dump(mapping, sort_keys=False))

    def preview(self, job_id, revision):
        with self.lock:
            draft = self.get(job_id)
            if draft['revision'] != revision:
                raise ValueError('Save or reload the current resume before compiling.')
            executable = shutil.which('tectonic')
            if not executable:
                raise ValueError('PDF compiler is unavailable. Your draft is saved; restart with Start Dashboard.command.')
            folder = safe_child(self.w.root / 'data/output', draft['file_root'])
            with tempfile.TemporaryDirectory(prefix='studio-preview-') as temp:
                build = Path(temp)
                (build / 'resume.tex').write_text(draft['source'])
                try:
                    run = subprocess.run([executable, '--untrusted', '--outdir', str(build), 'resume.tex'], cwd=build, capture_output=True, text=True, timeout=90)
                except subprocess.TimeoutExpired:
                    raise ValueError('Preview timed out. Your source is saved; check it for loops or very large content.') from None
                if run.returncode or not (build / 'resume.pdf').exists():
                    raise ValueError('Preview could not compile. Your edits are saved.\n' + (run.stderr + run.stdout)[-3500:])
                if len(PdfReader(str(build / 'resume.pdf')).pages) > 10:
                    raise ValueError('Preview exceeds ten pages. Reduce the content before compiling again.')
                report = inspect_pdf(build / 'resume.pdf', build / 'pages')
                target = folder / ('preview-' + str(revision))
                target.mkdir(exist_ok=True)
                self.write_review_sources(target, draft['source'], job_id)
                shutil.copy2(build / 'resume.pdf', target / 'resume.pdf')
                for page in (build / 'pages').glob('*.png'):
                    shutil.copy2(page, target / page.name)
                metadata = {'revision': revision, 'source_sha256': hashlib.sha256(draft['source'].encode()).hexdigest(), 'page_count': report['page_count'], 'created_at': self.s.now(), 'path': str(target.relative_to(self.w.root / 'data/output')), 'review_required': True, 'layout': measure_pages(build / 'resume.pdf', build / 'pages')}
                atomic_write(folder / 'preview.json', json.dumps(metadata))
            self.score(job_id)
            return self.get(job_id)


    def fit(self, job_id, revision):
        """Commit a ranked version that fills exactly one page, measured on the compiled PDF.

        Font goes from the contract maximum down to its minimum (never lower); if the
        page still overflows, content is cut in the order profile.yml documents, one
        registered construct at a time. Nothing is ever added that is not registered.
        """
        from backend.resume_contract import load_contract
        from backend.services.resume_projects import install_project
        contract = load_contract()
        with self.lock:
            draft = self.get(job_id)
            if draft['revision'] != revision:
                raise ValueError('This resume changed elsewhere. Reload before fitting the page.')
            if self.s.profile_dirty() or draft['profile_revision'] != self.w.evidence()['candidate_revision']:
                raise ValueError('Reconcile your Profile edits with the evidence registry before ranking content. You can still edit and preview the saved draft.')
            base_source = draft['source']
            if not extract_zero_argument_macros(base_source).get('SecondProjectID'):
                choices = [p for p in draft['projects'] if p['id'] != draft['fields'].get('SelectedProjectID')]
                if not choices:
                    raise ValueError('A signature project and one supporting project are required')
                base_source = install_project(base_source, choices[0], second=True)
            source, ranking = ranked_source(base_source, self.w.get_job(job_id), self.w.evidence(), self.s.knowledge(), self.w.profile())
            executable = shutil.which('tectonic')
            if not executable:
                raise ValueError('PDF compiler is unavailable. Restart with Start Dashboard.command.')
            folder = safe_child(self.w.root / 'data/output', draft['file_root'])
            fixed_font = self.s.pref('resume_font:' + job_id)
            points = [fixed_font] if fixed_font else [contract.max_body_pt, round((contract.max_body_pt + contract.min_body_pt) / 2, 2), contract.min_body_pt]
            cuts_applied = []
            best = None
            with tempfile.TemporaryDirectory(prefix='studio-fit-') as temp:
                attempt = 0
                while attempt < 12 and best is None:
                    for point in points:
                        build = Path(temp) / str(attempt)
                        build.mkdir()
                        attempt += 1
                        candidate = set_density(source, point)
                        (build / 'resume.tex').write_text(candidate)
                        try:
                            result = subprocess.run([executable, '--untrusted', '--outdir', str(build), 'resume.tex'], cwd=build, capture_output=True, text=True, timeout=90)
                        except subprocess.TimeoutExpired:
                            raise ValueError('Page fitting timed out. Your previous draft remains unchanged.') from None
                        if result.returncode or not (build / 'resume.pdf').exists():
                            raise ValueError('Could not compile the ranked draft. Your previous version is preserved.\n' + (result.stderr + result.stdout)[-2000:])
                        page_count = len(PdfReader(str(build / 'resume.pdf')).pages)
                        if page_count > contract.pages:
                            continue  # try a smaller allowed font, then cut content
                        inspect_pdf(build / 'resume.pdf', build / 'pages')
                        layout = measure_pages(build / 'resume.pdf', build / 'pages')
                        if layout['full_pages'] or page_count == contract.pages:
                            best = (build, candidate, layout, round(float(point), 2))
                            break
                    if best is None:
                        # Every allowed font overflowed: cut the next construct in the documented order.
                        cut_source, label = self._cut_next(source, cuts_applied)
                        if cut_source is None:
                            raise ValueError('The content could not fit one page at ' + f'{contract.min_body_pt:g}' + 'pt even after the documented cuts (' + '; '.join(cuts_applied) + '). Your draft is unchanged. Shorten custom text, then try again.')
                        source = cut_source
                        cuts_applied.append(label)
                if best is None:
                    raise ValueError('Page fitting stopped after 12 compiles. Your draft is unchanged.')
                build, candidate, layout, body_pt = best
                stamp = self.s.now()
                new_revision = revision + 1 if candidate != draft['source'] else revision
                with self.w.connect() as db:
                    db.execute('BEGIN IMMEDIATE')
                    current = db.execute('SELECT revision FROM studio_drafts WHERE job_id=?', (job_id,)).fetchone()
                    if current[0] != revision:
                        raise ValueError('This resume changed elsewhere during fitting. Reload before retrying.')
                    if new_revision != revision:
                        # Registry-derived reordering and cuts are not new user claims: do not feed the profile tracker.
                        db.execute('UPDATE studio_drafts SET source=?,revision=?,updated_at=? WHERE job_id=?', (candidate, new_revision, stamp, job_id))
                        db.execute('INSERT INTO studio_versions VALUES(?,?,?,?)', (job_id, new_revision, candidate, stamp))
                    self.w.record_event(db, 'studio_fitted_one_page', job_id, revision=new_revision, body_font_pt=body_pt, page_fill=[p['fill_percent'] for p in layout['pages']], section_order=ranking['section_order'], cuts=cuts_applied)
                target = folder / ('preview-' + str(new_revision))
                target.mkdir(exist_ok=True)
                self.write_review_sources(target, candidate, job_id)
                shutil.copy2(build / 'resume.pdf', target / 'resume.pdf')
                for page in (build / 'pages').glob('*.png'):
                    shutil.copy2(page, target / page.name)
                metadata = {'revision': new_revision, 'source_sha256': hashlib.sha256(candidate.encode()).hexdigest(), 'page_count': layout['page_count'], 'created_at': stamp, 'path': str(target.relative_to(self.w.root / 'data/output')), 'review_required': True, 'layout': layout, 'ranking': {**ranking, 'cuts': cuts_applied}, 'body_font_pt': body_pt}
                atomic_write(folder / 'preview.json', json.dumps(metadata, indent=2))
                atomic_write(target / 'layout-review.json', json.dumps(metadata, indent=2))
                atomic_write(target / 'resume.tex', candidate)
            self.w.export_tracking()
            self.score(job_id)
            return self.get(job_id)

    # Kept for callers that still say "fill"; the contract decides the page count.
    fill = fit

    # The documented cut order (profile.yml resume_contract.cut_order), one step per call.
    CUT_STEPS = (
        ('supporting project third bullet', r'(?m)^\s*% EVIDENCE: [^\n]+\n\s*\\item \\SecondProjectBulletThree\n'),
        ('last bullet of the oldest role', None),
        ('coursework line', r'(?m)^% EVIDENCE: [^\n]+\n\\textbf\{Coursework:\}[^\n]*\n'),
        ('second degree', None),
    )

    def _cut_next(self, source, applied):
        """Apply the first not-yet-applied cut that changes the source. Returns (source, label) or (None, None)."""
        for label, pattern in self.CUT_STEPS:
            if label in applied:
                continue
            if pattern:
                new = re.sub(pattern, '', source, count=1)
                if label == 'supporting project third bullet':
                    new = re.sub(r'(?m)^% EVIDENCE: [^\n]+\n\\newcommand\{\\SecondProjectBulletThree\}\{[^\n]*\}\n', '', new, count=1)
            elif label == 'last bullet of the oldest role':
                new = self._drop_last_bullet_of_oldest_role(source)
            else:
                new = self._drop_second_degree(source)
            if new != source:
                return new, label
            applied.append(label)
        return None, None

    @staticmethod
    def _drop_second_degree(source):
        """Remove the last degree heading in Education when more than one is printed."""
        edu = re.search(r'\\section\{Education\}[\s\S]*?(?=\\section\{|\\end\{document\})', source)
        if not edu:
            return source
        headings = list(re.finditer(r'(?m)^% EVIDENCE: [^\n]+\n\\roleheading\{[^\n]*\n\n?', edu[0]))
        if len(headings) < 2:
            return source
        last = headings[-1]
        new_edu = edu[0][:last.start()] + edu[0][last.end():]
        return source[:edu.start()] + new_edu + source[edu.end():]

    @staticmethod
    def _drop_last_bullet_of_oldest_role(source):
        """Remove the final bullet of the last role in Professional Experience (roles are chronological, newest first)."""
        exp = re.search(r'\\section\{Professional Experience\}[\s\S]*?(?=\\section\{|\\end\{document\})', source)
        if not exp:
            return source
        blocks = list(re.finditer(r'\\begin\{resumeitems\}([\s\S]*?)\\end\{resumeitems\}', exp[0]))
        for block in reversed(blocks):
            items = list(re.finditer(r'(?m)^\s*% EVIDENCE: [^\n]+\n\s*\\item [^\n]+\n', block[1]))
            if len(items) >= 2:
                last = items[-1]
                body = block[1][:last.start()] + block[1][last.end():]
                new_block = '\\begin{resumeitems}' + body + '\\end{resumeitems}'
                new_exp = exp[0][:block.start()] + new_block + exp[0][block.end():]
                return source[:exp.start()] + new_exp + source[exp.end():]
        return source

    def match_input(self, job_id):
        """Allow-listed snapshot from the actual current PDF, never candidate context."""
        draft = self.get(job_id)
        preview = draft['preview']
        if not preview or not preview['current'] or preview['revision'] != draft['revision']:
            raise ValueError('Build the current saved resume before scoring')
        pdf = safe_child(self.w.root / 'data/output', preview['path'] + '/resume.pdf')
        text = '\n'.join(p.extract_text() or '' for p in PdfReader(str(pdf)).pages)
        jd = self.w.get_job(job_id)['description']
        return {'resume_text': text, 'job_description': jd, 'revision': draft['revision'],
                'source_sha256': hashlib.sha256(draft['source'].encode()).hexdigest(),
                'pdf_sha256': hashlib.sha256(pdf.read_bytes()).hexdigest(),
                'jd_sha256': hashlib.sha256(jd.encode()).hexdigest()}

    def score(self, job_id):
        from backend.assessment import AssessmentService, SCORING_VERSION
        with self.lock:
            payload = self.match_input(job_id)
            with self.w.connect() as db:
                old = db.execute('SELECT details FROM resume_assessments WHERE job_id=? AND draft_revision=? AND jd_hash=? AND pdf_hash=? AND scoring_version=?',
                                 (job_id, payload['revision'], payload['jd_sha256'], payload['pdf_sha256'], SCORING_VERSION)).fetchone()
                if old:
                    return {**json.loads(old[0]), 'cached': True}
            draft = self.get(job_id)
            result = AssessmentService(self.s).run(job_id, payload, draft['source'])
            with self.w.connect() as db:
                db.execute('INSERT INTO resume_scores VALUES(?,?,?,?,?,?,?)',
                           (job_id, payload['revision'], payload['source_sha256'], payload['pdf_sha256'], payload['jd_sha256'], json.dumps(result), self.s.now()))
                self.w.record_event(db, 'resume_scored', job_id, revision=payload['revision'], ats_readiness=result['ats_readiness']['score'], resume_coverage=result['resume_coverage']['score'])
            self.w.export_tracking()
            return {**result, 'cached': False}

    def assessment(self, job_id):
        draft = self.get(job_id)
        preview = draft.get('preview')
        if not preview or not preview.get('current') or preview.get('revision') != draft['revision']:
            return {'current': False, 'stale': True, 'message': 'Build the current revision to calculate assessments.'}
        result = self.score(job_id)
        return {**result, 'current': True, 'stale': False, 'revision': draft['revision']}

    def download(self, job_id, format):
        if format not in {'pdf', 'tex'}:
            raise ValueError('Choose pdf or tex')
        draft = self.get(job_id)
        job = self.w.get_job(job_id)
        preview = draft.get('preview')
        if format == 'pdf':
            if not preview or not preview.get('current') or preview.get('revision') != draft['revision']:
                raise ValueError('PDF download is available only for the current successfully compiled revision')
            path = safe_child(self.w.root / 'data/output', preview['path'] + '/resume.pdf')
        else:
            folder = safe_child(self.w.root / 'data/output', draft['file_root'])
            path = folder / 'resume.tex'
            atomic_write(path, draft['source'])
        slug = re.sub(r'[^a-z0-9]+', '-', (job['company'] + '-' + job['title']).casefold()).strip('-')
        return path, f'{slug}-resume-v{draft["revision"]}.{format}'

    def sync_profile(self, job_id, revision):
        """Re-rank the signature and supporting project slots from the registry as a new version."""
        from backend.services.resume_projects import install_project
        with self.lock:
            draft = self.get(job_id)
            if draft['revision'] != revision:
                raise ValueError('This resume changed elsewhere. Reload before syncing')
            if self.s.profile_dirty():
                raise ValueError('Reconcile pending Profile edits before syncing the resume')
            ranked = draft['projects']
            if len(ranked) < 2:
                raise ValueError('Two active registered projects are required')
            # The signature slot follows the one-per-company rule; the supporting slot takes the next best project.
            job = self.w.get_job(job_id)
            signature = self.w.choose_signature_project(job, ranked, [])
            first = next(p for p in ranked if p['id'] == signature)
            supporting = next(p for p in ranked if p['id'] != signature)
            source = draft['source']
            source = install_project(source, first)
            source = install_project(source, supporting, second=True)
            # Registry-derived updates are not new user claims, so bypass capture.
            stamp = self.s.now()
            with self.w.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                current = db.execute('SELECT revision FROM studio_drafts WHERE job_id=?', (job_id,)).fetchone()
                if current[0] != revision:
                    raise ValueError('This resume changed elsewhere. Reload before syncing')
                db.execute('UPDATE studio_drafts SET source=?,revision=revision+1,profile_revision=?,updated_at=? WHERE job_id=?',
                           (source, self.w.evidence()['candidate_revision'], stamp, job_id))
                db.execute('INSERT INTO studio_versions VALUES(?,?,?,?)', (job_id, revision+1, source, stamp))
                db.execute('INSERT OR REPLACE INTO signature_assignments(company_key, project_id, job_id, assigned_at) VALUES(?,?,?,?)',
                           (company_key(job['company']), signature, job_id, stamp))
                self.w.record_event(db, 'studio_profile_synced', job_id, revision=revision+1,
                                    profile_revision=self.w.evidence()['candidate_revision'], projects=[signature, supporting['id']])
            self.w.export_tracking()
            return self.get(job_id)
