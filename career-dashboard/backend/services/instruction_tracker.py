"""Durable chat above profile and resume editing. Explicit commands cost no AI."""
import re
import uuid
from backend.services.resume_layout import set_density


class InstructionTracker:
    def __init__(self, service, studio):
        self.s, self.w, self.studio = service, service.w, studio
        with self.w.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS instruction_messages(id TEXT PRIMARY KEY,job_id TEXT REFERENCES jobs(id),message TEXT NOT NULL,response TEXT NOT NULL,state TEXT NOT NULL,created_at TEXT NOT NULL);
            ''')

    def history(self, job_id=None):
        with self.w.connect() as db:
            return [dict(r) for r in db.execute('SELECT * FROM instruction_messages WHERE job_id IS NULL OR job_id=? ORDER BY created_at,rowid', (job_id,))]

    def send(self, message, job_id=None, revision=None, request_id=None):
        message = message.strip()
        if not message or len(message) > 10000:
            raise ValueError('Enter 1–10,000 characters')
        key = request_id or uuid.uuid4().hex
        if len(key) > 100:
            raise ValueError('Invalid message ID')
        if job_id:
            self.w.get_job(job_id)
        with self.studio.lock:
            with self.w.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                old = db.execute('SELECT * FROM instruction_messages WHERE id=?', (key,)).fetchone()
                if old:
                    if old['message'] != message or old['job_id'] != job_id:
                        raise ValueError('Message ID already belongs to another request')
                    return dict(old)
                db.execute('INSERT INTO instruction_messages VALUES(?,?,?,?,?,?)',
                           (key, job_id, message, 'Processing this instruction.', 'processing', self.s.now()))
            state, response = 'needs_clarification', 'Saved your full request. It has not changed resume wording. Use “skills: …” (Languages line), “skills data: …”, “skills ml: …”, “skills cloud: …”, “coursework: …”, “project: ID”, “second project: ID”, “font: 10.5”, “experience: …”, or “note: …” for a precise update.'
            field = re.fullmatch(r'(?:set\s+)?(skills(?:\s+(?:languages|data|ml|cloud))?|coursework)\s*:\s*([\s\S]+)', message, re.I)
            project = re.fullmatch(r'(second project|project)\s*:\s*([\w:-]+)', message, re.I)
            font = re.fullmatch(r'(?:set\s+)?(?:font|font size|body font)\s*:?\s*(auto|\d+(?:\.\d+)?)\s*(?:pt)?', message, re.I)
            note = re.fullmatch(r'(experience|note)\s*:\s*([\s\S]+)', message, re.I)
            if field or project or font:
                if not job_id or revision is None:
                    response = 'Saved your request. Select a job and open its draft to apply this resume instruction.'
                else:
                    try:
                        if field:
                            target = re.sub(r'\s+', ' ', field[1].lower())
                            # Annie's template has four skill lines and a coursework line; it has no summary section.
                            macro = {'skills': 'SkillsLanguages', 'coursework': 'Coursework',
                                     'skills languages': 'SkillsLanguages', 'skills data': 'SkillsData', 'skills ml': 'SkillsML',
                                     'skills cloud': 'SkillsCloud'}[target]
                            draft = self.studio.save(job_id, revision, fields={macro: field[2]})
                        elif project:
                            draft = self.studio.save(job_id, revision, **{('second_project_id' if project[1].lower().startswith('second') else 'project_id'): project[2]})
                        else:
                            size = None if font[1].lower() == 'auto' else float(font[1])
                            if size is not None and not 10 <= size <= 11:
                                raise ValueError('Body font must stay between 10 and 11pt: a one-page resume is fitted by trimming content, never by shrinking text')
                            current = self.studio.get(job_id)
                            draft = self.studio.save(job_id, revision, source=set_density(current['source'], size) if size is not None else current['source'])
                            with self.w.connect() as db:
                                self.s.set_pref('resume_font:' + job_id, size, db)
                        state, response = 'applied', f"Applied to saved draft version {draft['revision']}. Build & score to refresh its PDF. This instruction and its outcome are retained."
                    except ValueError as exc:
                        state, response = 'needs_attention', 'Request saved; not applied: ' + str(exc)
            elif note:
                entry = self.s.save_knowledge({'kind': 'experience' if note[1].lower() == 'experience' else 'fact',
                    'title': ('Experience correction' if note[1].lower() == 'experience' else 'Chat profile note'),
                    'summary': note[2], 'data': {'origin': 'instruction_chat', 'message_id': key, 'job_id': job_id}})
                state, response = 'pending_evidence', 'Saved in Profile (' + entry['id'] + '). The profile agent sees your wording; canonical evidence must be reconciled before new resume generation.'
            elif re.fullmatch(r'(help|what can you do)\??', message, re.I):
                state, response = 'answered', 'I retain every message. Precise commands: skills: Python, SQL, C# (Languages line); skills data: …; skills ml: …; skills cloud: …; coursework: …; project: PROJ-ID (signature); second project: PROJ-ID (supporting); font: 10.5 (10–11pt, or auto); experience: roles and dates; note: any profile fact. Resume instructions apply to the selected job. Profile notes apply globally. Unknown requests stay visible until clarified; no AI is used.'
            with self.w.connect() as db:
                db.execute('UPDATE instruction_messages SET response=?,state=? WHERE id=?', (response, state, key))
                self.w.record_event(db, 'instruction_recorded', job_id, message_id=key, state=state)
            self.w.export_tracking()
            return next(m for m in self.history(job_id) if m['id'] == key)
