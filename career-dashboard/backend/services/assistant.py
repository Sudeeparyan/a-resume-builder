"""One chat for the whole workspace, run by an agent with every feature as a tool.

Two kinds of message, in this order:

1. The deterministic paths, which need no model and never guess: a pasted job
   description (with its link) goes through the sponsorship gate and
   never-re-apply, opens the Resume Studio draft, fits one US Letter page and
   scores it; a posting link is fetched first; a handful of exact shortcuts
   ("find jobs", "status", "applied to X", "open X", "excluded") map straight
   to a service call, and "applied" always waits for her yes.

2. Everything else goes to the agent loop. The `workspace_agent` specialist
   sees the workspace snapshot, the tool catalogue (services/assistant_tools.py)
   and the task so far, and returns one decision per turn: call a tool, ask
   her something, or reply. The loop runs the tool, records it as a step the
   page shows live, appends the result and asks again, until the agent replies
   or the turn budget runs out. A tool marked `confirm` (marking applied,
   changing the profile or goals, removing a job) pauses the loop until she
   says yes; the answer resumes the same task.

The model runs on whatever is ready on this Mac — Claude Code, Codex or a
keyed provider — through the same tier preferences as the other specialists.
Work happens on one worker thread; the page polls the message row.
"""

from __future__ import annotations

import json
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta

from backend.services.assistant_tools import Toolbox, brief_job, phrase_gaps, resume_card  # noqa: F401 - phrase_gaps is re-exported for tests

URL = re.compile(r"https?://[^\s<>()\"'\]]+")
JD_MARKERS = re.compile(
    r"\b(responsibilit\w*|qualifications?|requirements?|what you(?:'|’)?ll (?:do|bring)|what you will do|"
    r"about (?:the|this) (?:role|job|team|position|opportunity)|we(?:'|’)?re looking for|we are looking for|"
    r"you will|experience (?:with|in)|bachelor(?:'|’)?s?|master(?:'|’)?s?|degree|preferred|nice to have|"
    r"must have|minimum qualifications|basic qualifications|salary|compensation|benefits|"
    r"equal opportunity|job description|skills|apply)\b",
    re.I,
)
ROLE_WORDS = re.compile(
    r"\b(engineer(?:ing)?|developer|analyst|scientist|intern(?:ship)?|programmer|specialist|associate|"
    r"researcher|consultant|technician|sde|swe|data|software|embedded|automation|machine learning|ml|ai)\b",
    re.I,
)
LABELLED = {
    "company": re.compile(r"^(?:company|employer|organization|organisation)\s*[:\-–]\s*(.+?)\s*$", re.I | re.M),
    "title": re.compile(r"^(?:job title|title|role|position)\s*[:\-–]\s*(.+?)\s*$", re.I | re.M),
    "location": re.compile(r"^(?:location|based in|office|work location)\s*[:\-–]\s*(.+?)\s*$", re.I | re.M),
}
NAMED_AFTER = re.compile(r"\b(?i:at|join|joining|about)\s+([A-Z][\w&.'’-]+(?:\s+[A-Z][\w&.'’-]+){0,2})(?=\s*(?:$|[.,!;:)]|\n))", re.M)
STOP_WORDS = {"the", "our", "a", "an", "this", "that", "you", "your", "we", "us", "least", "home", "work", "scale", "all", "every",
              "python", "java", "sql", "aws", "azure", "gcp", "kafka", "flink", "airflow", "spark", "linux", "git"}
ABOUT_COMPANY = re.compile(r"^about\s+(?!the\b|this\b|us\b|you\b)([A-Z][\w&.'’\- ]{1,60}?)\s*:?\s*$", re.M)
LOCATION_LINE = re.compile(
    r"^(?:remote(?: \(us\))?|hybrid|[A-Z][\w.' ]+,\s*[A-Z]{2}(?:\s*\(?(?:remote|hybrid|on-?site)\)?)?)\s*$", re.I | re.M
)
YES = re.compile(r"(yes|y|yes please|confirm|correct|do it|ok|okay|sure|go ahead|proceed)\.?!?", re.I)
NO = re.compile(r"(no|n|nope|not yet|skip|cancel|don'?t)\.?", re.I)
CONJUNCTION = re.compile(r"\b(and|then|also)\b", re.I)

HELP = (
    "Paste a job description here (with its link) and I run the sponsorship gate, save it, build the "
    "one-page resume and hand you the PDF.\n\n"
    "Ask for anything else in plain words and I do it with the same tools the tabs use, for example:\n"
    "- *research Snowflake and then write the study plan*\n"
    "- *which saved jobs still have no resume? build them*\n"
    "- *I finished the AWS Data Engineer course* (goes to your Profile for review)\n"
    "- *change the Acme resume summary to lead with streaming pipelines*\n"
    "- *what did I apply to this week?* · *set my weekly target to 12*\n\n"
    "Anything hard to undo — marking a job applied, changing your profile or goals, removing a job — "
    "waits for your *yes*. Nothing is ever submitted for you.\n"
    "Shortcuts: **find jobs** · **status** · **open <company>** · **applied to <company> on YYYY-MM-DD** · **excluded**"
)

STEP_ORDER = ("Reading the posting", "Sponsorship gate and never-re-apply", "Opening the draft",
              "Fitting one US Letter page", "Scoring against the posting")
STEP_AGENTS = ("assistant", "sponsorship", "resume", "resume", "resume_match")

# The agent loop: how many model decisions one message may take, how much of a
# tool result the model sees, and how many results stay whole in the transcript.
MAX_TURNS = 14
RESULT_CHARS = 3500
FULL_RESULTS_KEPT = 8


def looks_like_posting(text: str) -> bool:
    """A pasted description: long, and it talks the way postings talk."""
    if re.match(r"^\s*(?:jd|job|posting|job description)\s*:", text, re.I):
        return True
    if len(text) < 300:
        return False
    return len(set(m.group(0).casefold() for m in JD_MARKERS.finditer(text))) >= 3


def parse_posting_fields(text: str, labelled_only: bool = False) -> dict:
    """Cheap, no-AI extraction: labelled lines, an 'About X' heading, a title-shaped first line."""
    found = {}
    for key, pattern in LABELLED.items():
        match = pattern.search(text)
        if match and len(match[1]) <= 120:
            found[key] = match[1].strip()
    if labelled_only:
        return found
    if "company" not in found:
        about = ABOUT_COMPANY.search(text)
        if about:
            found["company"] = about[1].strip()
    if "company" not in found:
        # "Build your future at Snowflake", "Join Acme Analytics": an employer named early and
        # repeated later. One mention is a guess; the chat asks rather than guessing.
        for candidate in NAMED_AFTER.findall(text[:800]):
            name = candidate.strip().rstrip(".,")
            if name and name.split()[0].casefold() not in STOP_WORDS and text.count(name) >= 2:
                found["company"] = name
                break
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if "title" not in found and lines:
        first = re.sub(r"^(?:jd|job|posting|job description)\s*:\s*", "", lines[0], flags=re.I)
        if 3 <= len(first) <= 90 and ROLE_WORDS.search(first) and not first.endswith((".", ":")) and not URL.search(first):
            found["title"] = first
    if "location" not in found:
        for line in lines[:12]:
            if len(line) <= 60 and LOCATION_LINE.match(line):
                found["location"] = line
                break
    link = URL.search(text)
    if link:
        found["url"] = link.group(0).rstrip(".,;:)")
    return found


def _strip_link(text: str) -> str:
    return URL.sub("", text).strip()


def _trim(value, limit: int) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[:limit] + f"… (+{len(text) - limit:,} chars)"


class Assistant:
    def __init__(self, service, studio, runner, quality=None, background=True, tools=None):
        from backend.job_quality import JobQualityService

        self.s, self.w, self.studio, self.runner = service, service.w, studio, runner
        self.quality = quality or JobQualityService(service)
        self.tools = tools or Toolbox(service, studio, runner, self.quality)
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="career-assistant") if background else None
        with self.w.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS assistant_messages(id TEXT PRIMARY KEY, message TEXT NOT NULL, response TEXT NOT NULL, state TEXT NOT NULL, steps TEXT NOT NULL DEFAULT '[]', data TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            ''')
            db.execute("UPDATE assistant_messages SET state='failed',response=?,updated_at=? WHERE state='processing'",
                       ("The app stopped before this finished. Send it again.", self.s.now()))

    # ---- Storage -------------------------------------------------------------
    @staticmethod
    def _decode(row) -> dict:
        return {**dict(row), "steps": json.loads(row["steps"]), "data": json.loads(row["data"])}

    def get(self, id: str) -> dict:
        with self.w.connect() as db:
            row = db.execute("SELECT * FROM assistant_messages WHERE id=?", (id,)).fetchone()
        if not row:
            raise ValueError("Message not found")
        return self._decode(row)

    def history(self, limit: int = 60) -> list:
        with self.w.connect() as db:
            rows = db.execute("SELECT * FROM assistant_messages ORDER BY created_at DESC, rowid DESC LIMIT ?", (limit,)).fetchall()
        return [self._decode(r) for r in reversed(rows)]

    def agents(self) -> list:
        """The agent registry with what the chat can reach: every tool names the agent it runs on."""
        from backend.services.workspace_v2 import AGENTS

        reach: dict[str, list] = {}
        for tool in self.tools.tools.values():
            reach.setdefault(tool.agent, []).append(tool.label)
        # The gates and Studio run inside the paste path; the runnable agents (and the hiring
        # review and profile comparison a research run chains) start through run_agent.
        from backend.services.assistant_tools import RUNNABLE_AGENTS

        for agent in STEP_AGENTS + ("reapply", "hiring", "match") + tuple(RUNNABLE_AGENTS):
            reach.setdefault("resume" if agent == "resume_build" else agent, [])
        return [{"id": a["id"], "name": a["name"], "does": a["does"], "implementation": a["implementation"],
                 "linked": a["id"] in reach, "tools": reach.get(a["id"], [])} for a in AGENTS]

    def overview(self) -> dict:
        from backend.ai import any_provider_configured, engine

        messages = self.history()
        return {
            "messages": messages,
            "pending": self.s.pref("assistant_pending"),
            "busy": any(m["state"] == "processing" for m in messages),
            "ai_configured": any_provider_configured(self.w.root),
            "engine": engine(self.s),
            "agents": self.agents(),
            "capabilities": self.tools.capabilities(),
        }

    def _write(self, id: str, *, state=None, response=None, steps=None, data=None):
        sets, values = ["updated_at=?"], [self.s.now()]
        for column, value in (("state", state), ("response", response)):
            if value is not None:
                sets.append(column + "=?")
                values.append(value)
        for column, value in (("steps", steps), ("data", data)):
            if value is not None:
                sets.append(column + "=?")
                values.append(json.dumps(value, ensure_ascii=False, default=str))
        with self.w.connect() as db:
            db.execute("UPDATE assistant_messages SET " + ",".join(sets) + " WHERE id=?", (*values, id))

    # ---- Entry point ---------------------------------------------------------
    def send(self, message: str, request_id: str | None = None) -> dict:
        message = message.strip()
        if not message or len(message) > 120_000:
            raise ValueError("Enter 1–120,000 characters")
        key = request_id or uuid.uuid4().hex
        if len(key) > 100:
            raise ValueError("Invalid message ID")
        stamp = self.s.now()
        with self.w.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT * FROM assistant_messages WHERE id=?", (key,)).fetchone()
            if old:
                if old["message"] != message:
                    raise ValueError("Message ID already belongs to another request")
                return self._decode(old)
            db.execute("INSERT INTO assistant_messages VALUES(?,?,?,?,?,?,?,?)",
                       (key, message, "Working on it.", "processing", "[]", "{}", stamp, stamp))
        if self.pool:
            self.pool.submit(self._process, key)
        else:
            self._process(key)
        return self.get(key)

    def _process(self, id: str) -> None:
        row = self.get(id)
        try:
            state, response, data = self._handle(id, row["message"])
        except ValueError as error:
            state, response, data = "failed", str(error), {}
        except Exception as error:  # noqa: BLE001 - the row must never stay "processing"
            state, response, data = "failed", "Something went wrong: " + type(error).__name__ + ": " + str(error)[:500], {}
        steps = self.get(id)["steps"]
        for step in steps:
            if step["state"] == "running":
                step["state"] = "failed" if state == "failed" else "done"
        self._write(id, state=state, response=response, steps=steps, data=data)
        with self.w.connect() as db:
            self.w.record_event(db, "assistant_replied", data.get("job_id") if isinstance(data, dict) else None,
                                message_id=id, state=state, intent=(data or {}).get("intent"))
        try:
            self.s.sync_projections()
        except Exception:  # noqa: BLE001 - projections are a convenience; the reply is already saved
            pass

    # ---- Steps ---------------------------------------------------------------
    def _step(self, id: str, label: str, state: str = "running", detail: str = "", agent: str = "assistant", **extra) -> None:
        steps = self.get(id)["steps"]
        for step in steps:
            if step["state"] == "running":
                step["state"] = "done"
        steps.append({"at": self.s.now(), "label": label, "state": state, "detail": detail, "agent": agent, **extra})
        self._write(id, steps=steps)

    def _finish_step(self, id: str, state: str = "done", detail: str | None = None, **extra) -> None:
        steps = self.get(id)["steps"]
        if steps:
            steps[-1]["state"] = state
            if detail is not None:
                steps[-1]["detail"] = detail
            steps[-1].update(extra)
        self._write(id, steps=steps)

    def _relabel_step(self, id: str, label: str, detail: str = "", agent: str | None = None) -> None:
        steps = self.get(id)["steps"]
        if steps and steps[-1]["state"] == "running":
            steps[-1].update({"label": label, "detail": detail, **({"agent": agent} if agent else {})})
            self._write(id, steps=steps)

    # ---- Routing -------------------------------------------------------------
    def _handle(self, id: str, message: str):
        text = message.strip()
        low = text.casefold()
        if re.fullmatch(r"(help|what can you do|\?)\??", low):
            return "done", HELP, {"intent": "help"}
        if re.fullmatch(r"(cancel|never ?mind|stop|forget it|start over)\.?", low):
            self.s.set_pref("assistant_pending", None)
            return "done", "Cleared. Paste a posting or ask me anything.", {"intent": "cancel"}

        pending = self.s.pref("assistant_pending")
        if pending:
            resolved = self._resume_pending(id, pending, text)
            if resolved is not None:
                return resolved

        if looks_like_posting(text):
            return self._prepare_posting(id, text)
        lone = URL.fullmatch(text.rstrip(".,;)")) or (URL.search(text) and len(_strip_link(text)) < 40)
        if lone:
            return self._from_link(id, URL.search(text).group(0).rstrip(".,;:)"))

        # Exact shortcuts: instant, no model, and "applied" always waits for her yes.
        # A request with "and"/"then" in it is a task for the agent, not a shortcut.
        if re.fullmatch(r"(find|search|look for|discover|hunt)( me)?( some| new| more)? (jobs?|roles?|postings?|openings?)( for (me|my profile|today))?\.?", low) \
                or re.fullmatch(r"(daily search|run (the )?search|search)\.?", low):
            return self._discover(id)
        if re.fullmatch(r"(status|summary|progress|pipeline|where (are|am) (we|i)|what(’|')?s (next|new|going on)|how am i doing)\??\.?", low):
            return "done", self._status(), {"intent": "status", "suggestions": ["find jobs", "which saved jobs still have no resume? build them"]}
        if re.fullmatch(r"(excluded( roles| postings)?|what was excluded)\??", low):
            return "done", self._excluded(), {"intent": "excluded"}
        match = re.fullmatch(r"(?:write |make |create )?(?:a |the )?study[- ]plan(?: for)?\s+([^,;]+?)\.?", text, re.I)
        if match and not CONJUNCTION.search(match[1]):
            return self._run_for_job(id, "study_plan", match[1])
        match = re.fullmatch(r"(?:run |do )?(?:company )?(?:research|hiring review|company & hiring review)(?: for| on)?\s+([^,;]+?)\.?", text, re.I)
        if match and not CONJUNCTION.search(match[1]):
            return self._run_for_job(id, "research", match[1])
        match = re.fullmatch(
            r"(?:i (?:have |just |’ve |'ve )?)?(?:applied|submitted(?: my application)?|sent(?: my application| it)?)"
            r"(?: to| for| at)?\s+([^,;]+?)(?:\s+(?:on|today|yesterday)\b\s*(.*?))?\.?",
            text, re.I)
        if match and not CONJUNCTION.search(match[1]):
            when = (match[2] or "").strip()
            phrase = match[0].casefold()
            if "today" in phrase and not when:
                when = self.s.today()
            elif "yesterday" in phrase and not when:
                when = (date.fromisoformat(self.s.today()) - timedelta(days=1)).isoformat()
            return self._propose_applied(id, match[1], when)
        match = re.fullmatch(r"(?:open|show|show me|go to|resume for|the resume for)\s+([^,;]+?)\.?", text, re.I)
        if match and not re.search(r"\b(and|then|also|jobs?|resumes?|profile|questions?|runs?|agents?|status|pending|entries)\b", match[1], re.I):
            return self._open(id, match[1])
        return self._agent(id, text)

    # ---- Pending questions ---------------------------------------------------
    def _resume_pending(self, id, pending, text):
        """Continue a flow that stopped to ask something. None means the message is unrelated."""
        kind = pending.get("kind")
        link = URL.search(text)
        if kind == "posting_link":
            if link and len(_strip_link(text)) < 200:
                self.s.set_pref("assistant_pending", None)
                return self._prepare_posting(id, pending["description"], url=link.group(0).rstrip(".,;:)"), fields=pending.get("fields"))
            if looks_like_posting(text):
                return None  # a new posting replaces the old question
            return "needs_input", "I still need the link to that posting so it can be saved and never applied to twice. Paste the URL, or say *cancel*.", {"intent": "posting_link"}
        if kind == "posting_fields":
            parts = [p.strip() for p in re.split(r"\s*[|;]\s*|\s*\n\s*", text) if p.strip()]
            fields = dict(pending.get("fields") or {})
            labelled = parse_posting_fields(text, labelled_only=True)
            for key in ("company", "title", "location"):
                if labelled.get(key):
                    fields[key] = labelled[key]
            missing = [k for k in ("company", "title", "location") if not fields.get(k)]
            if not any(labelled.get(k) for k in ("company", "title", "location")) and len(parts) >= 1 and len(parts) <= 3 and not looks_like_posting(text):
                for key, value in zip(missing, parts):
                    fields[key] = value
            if all(fields.get(k) for k in ("company", "title")):
                self.s.set_pref("assistant_pending", None)
                fields.setdefault("location", "United States")
                return self._prepare_posting(id, pending["description"], url=pending.get("url"), fields=fields)
            if looks_like_posting(text):
                return None
            return "needs_input", "Reply with **Company | Job title | Location** for that posting (for example *Snowflake | Software Engineer | Menlo Park, CA*), or say *cancel*.", {"intent": "posting_fields"}
        if kind == "confirm_applied":
            if YES.fullmatch(text):
                self.s.set_pref("assistant_pending", None)
                job = self.w.update_job(pending["job_id"], "applied", None, pending["date"])
                self.w.export_tracking()
                return "done", (f"Recorded: **{job['company']} — {job['title']}** applied on {pending['date']}. "
                                "If they go quiet for 21 days it will show as ghosted; a reply or a status change takes it out."), \
                    {"intent": "mark_applied", "job_id": job["id"]}
            if NO.fullmatch(text):
                self.s.set_pref("assistant_pending", None)
                return "done", "Not recorded. Tell me when it is sent.", {"intent": "mark_applied_cancelled"}
            return None
        if kind == "choose_job":
            choice = re.fullmatch(r"\s*(\d{1,2})\s*\.?", text)
            candidates = pending.get("candidates") or []
            picked = None
            if choice and 1 <= int(choice[1]) <= len(candidates):
                picked = candidates[int(choice[1]) - 1]
            else:
                matches = [c for c in candidates if self._job_matches(c, text)]
                picked = matches[0] if len(matches) == 1 else None
            if picked:
                self.s.set_pref("assistant_pending", None)
                return self._dispatch_job_intent(id, pending["intent"], picked, pending.get("extra") or {})
            return None
        if kind == "agent":
            # The agent asked her something; her answer continues the same task.
            self.s.set_pref("assistant_pending", None)
            if looks_like_posting(text):
                return None
            return self._agent(id, text, transcript=pending.get("transcript") or [])
        if kind == "confirm_tool":
            self.s.set_pref("assistant_pending", None)
            transcript = list(pending.get("transcript") or [])
            tool = self.tools.get(pending["tool"])
            arguments = pending.get("arguments") or {}
            if YES.fullmatch(text):
                self._step(id, tool.label, detail="Confirmed by her", agent=tool.agent)
                transcript.append(self._run_tool(id, tool, arguments))
                return self._agent(id, None, transcript=transcript)
            if NO.fullmatch(text):
                transcript.append({"role": "tool", "tool": tool.name, "declined": True,
                                   "note": "She said no. Do not run it; tell her what was left undone and reply."})
                return self._agent(id, None, transcript=transcript)
            transcript.append({"role": "tool", "tool": tool.name, "declined": True,
                               "note": "She did not confirm; her next message follows. Treat it as her answer."})
            return self._agent(id, text, transcript=transcript)
        return None

    # ---- Paste a posting -> resume --------------------------------------------
    def _from_link(self, id, url):
        self._step(id, "Fetching the posting page", agent="discovery")
        page = self.quality.fetcher(url)
        text = (page or {}).get("text") or ""
        if len(text) < 300:
            self._finish_step(id, "failed", "The page did not return readable text (status " + str((page or {}).get("status")) + ")")
            self.s.set_pref("assistant_pending", None)
            return "needs_input", ("I could not read that page (a login wall or a script-only page, most likely). "
                                   "Paste the job description text here and I will use this link for it."), \
                {"intent": "posting_link_unreadable", "url": url}
        self._finish_step(id, "done", f"{len(text):,} characters of page text")
        return self._prepare_posting(id, text[:100_000], url=url)

    def _extract_fields(self, id, text, url, fields):
        """Heuristics first (free), then the cheap parser for what is still missing, both grounded in the text."""
        from backend.ai import any_provider_configured, team_for

        found = {**parse_posting_fields(text), **{k: v for k, v in (fields or {}).items() if v}}
        if url:
            found["url"] = url
        missing = [k for k in ("company", "title", "location") if not found.get(k)]
        note = ""
        if missing and any_provider_configured(self.w.root):
            try:
                parsed = team_for(self.s).run("posting_parser", {"posting_text": text[:20_000]})
                lowered = text.casefold()
                for key in missing:
                    value = (getattr(parsed, key, "") or "").strip()
                    # Grounding: a value the text does not contain is a guess, and a guess is dropped.
                    if value and value.casefold() in lowered:
                        found[key] = value
                if not found.get("url") and parsed.url and parsed.url in text:
                    found["url"] = parsed.url
            except Exception as error:  # noqa: BLE001 - no key, no network, bad output: the chat asks instead
                note = "(The posting parser could not run: " + str(error).rstrip(".") + ".)"
        return found, note

    def _prepare_posting(self, id, text, url=None, fields=None):
        text = re.sub(r"^\s*(?:jd|job|posting|job description)\s*:\s*", "", text, flags=re.I).strip()
        self._step(id, STEP_ORDER[0], agent=STEP_AGENTS[0])
        found, note = self._extract_fields(id, text, url, fields)
        if not found.get("url"):
            self._finish_step(id, "done", "No link in the text")
            self.s.set_pref("assistant_pending", {"kind": "posting_link", "description": text, "fields": found, "asked_at": self.s.now()})
            return "needs_input", ("I have the description" + (f" for **{found['company']} — {found['title']}**" if found.get("company") and found.get("title") else "") +
                                   ". Paste the posting link too, so the job is saved under its own URL and never applied to twice."), \
                {"intent": "posting_link", "fields": found}
        if not found.get("company") or not found.get("title"):
            self._finish_step(id, "done", "Employer or title not stated in the text")
            self.s.set_pref("assistant_pending", {"kind": "posting_fields", "description": text, "url": found["url"], "fields": found, "asked_at": self.s.now()})
            known = ", ".join(f"{k}: {found[k]}" for k in ("company", "title", "location") if found.get(k))
            return "needs_input", ("I could not find the employer or the job title in the text" + (f" (I have {known})" if known else "") +
                                   ". Reply with **Company | Job title | Location**." + (" " + note if note else "")), \
                {"intent": "posting_fields", "fields": found}
        found.setdefault("location", "United States")
        self._finish_step(id, "done", f"{found['company']} — {found['title']} · {found['location']}")

        self._step(id, STEP_ORDER[1], agent=STEP_AGENTS[1])
        saved = self.tools.save_posting(found["company"], found["title"], found["url"], text, found["location"])
        if saved.get("excluded"):
            self._finish_step(id, "failed", saved["reason"])
            return "done", (f"Not saved. The posting says **“{saved['sentence']}”** — {saved['reason']}. "
                            "It is listed under Excluded roles on the Dashboard; if that reading is wrong, restore it there and paste it again."), \
                {"intent": "posting_excluded", "excluded_id": saved.get("excluded_id"), "sentence": saved["sentence"]}
        if saved.get("blocked"):
            self._finish_step(id, "failed", saved["rule"])
            return "done", "Not saved: " + saved["note"], {"intent": "posting_blocked", "rule": saved["rule"]}
        job = self.w.get_job(saved["job"]["id"])
        tier = job.get("sponsor_tier") or "C"
        tier_label = saved["job"]["sponsor_note"]
        self._finish_step(id, "done", saved["summary"])
        warnings = list(saved["warnings"])

        self._step(id, STEP_ORDER[2], agent=STEP_AGENTS[2])
        if self.s.profile_dirty():
            self._finish_step(id, "failed", "Profile has unreviewed edits")
            return "done", (f"**{job['company']} — {job['title']}** is saved (tier {tier}), but the Profile has unreviewed edits, "
                            "so no new draft can start until they are reconciled with the evidence registry. Open Profile, confirm the pending entries, then say *open "
                            + job["company"] + "* and I will build the resume."), \
                {"intent": "posting_saved_profile_dirty", "job_id": job["id"], "warnings": warnings,
                 "suggestions": ["show my pending profile entries", "open " + job["company"]]}
        draft = self.studio.open(job["id"])
        self._finish_step(id, "done", f"Draft version {draft['revision']} · signature project: {draft['fields'].get('SelectedProjectTitle') or '—'}")

        self._step(id, STEP_ORDER[3], agent=STEP_AGENTS[3])
        fitted = self.studio.fit(job["id"], draft["revision"])
        card = resume_card(job, draft, fitted)
        page = card["page"]
        fill = page["fill_percent"] if page["fill_percent"] is not None else "?"
        self._finish_step(id, "done", f"{page['count'] or 1} page · {fill}% filled · {page['font_pt']}pt" + (" · cut: " + ", ".join(page["cuts"]) if page["cuts"] else ""))

        self._step(id, STEP_ORDER[4], agent=STEP_AGENTS[4])
        match = fitted.get("match") or {}
        self._finish_step(id, "done" if match else "failed",
                          (f"JD coverage {card['coverage']} · ATS readiness {card['ats']}" if match else "Score unavailable; the page is fitted and saved"))

        lines = [f"**{job['company']} — {job['title']}** is saved (sponsorship tier {tier}" + (f": {tier_label}" if tier_label else "") + ")."]
        signature = card["signature_project"] or "the signature project"
        lines.append(f"The resume is fitted to one US Letter page at {page['font_pt']}pt ({fill}% filled), "
                     f"leading with **{signature}**" + (f", after cutting the {' and the '.join(page['cuts'])}." if page["cuts"] else "."))
        if match:
            lines.append(f"JD term coverage {card['coverage']} · ATS readiness {card['ats']}." + (f" Requirements the evidence does not cover: {', '.join(card['gaps'])}." if card["gaps"] else ""))
        for warning in warnings:
            lines.append("⚠ " + warning)
        lines.append("Download the PDF, look at the page once, apply through the posting link, then tell me *applied to " + job["company"] + "*. "
                     "A visual review is still pending on the Studio side; nothing here has been submitted.")
        data = {**card, "warnings": warnings + card["warnings"], "duplicate": bool(saved.get("duplicate"))}
        return "done", "\n".join(lines), data

    # ---- Shortcuts ---------------------------------------------------------------
    def _discover(self, id):
        preset = (self.s.pref("discovery_preferences", {}) or {}).get("preset", "default")
        self._step(id, "Starting job discovery (" + preset + ")", agent="discovery")
        try:
            run = self.runner.enqueue("discovery", None, *self.tools._engine_for("discovery"), preset)
        except ValueError as error:
            self._finish_step(id, "failed", str(error))
            return "done", str(error), {"intent": "discovery_refused"}
        self._finish_step(id, "done", "Run " + run["id"][:8] + (" was already running" if run.get("existing") else " queued"), run_id=run["id"])
        return "done", ("Job discovery is running with the *" + preset + "* mix. Every lead passes the sponsorship gate and the never-re-apply check "
                        "before it is saved; watch the Agents rail or ask me *status* in a few minutes."), \
            {"intent": "discovery", "run_id": run["id"], "suggestions": ["status"]}

    def _status(self):
        summary = self.s.summary()
        goals = summary["goals"]
        jobs = summary["jobs"]
        counts = summary["counts"]
        lines = [f"This week: {goals['week_completed']} of {goals['current_week_target']} applications; today {goals['today_completed']} of {goals['today_target']} ({goals['remaining_today']} left)."]
        lines.append(f"Saved jobs {counts['saved']} · applied {counts['applied']} · interviews {counts['interviews']} · offers {counts['offers']} · ghosted {counts['ghosted']} · excluded {counts['excluded']}.")
        ready = [j for j in jobs if j["status"] in {"saved", "prepared"}]
        if ready:
            lines.append("Resumes waiting to be sent: " + "; ".join(f"**{j['company']} — {j['title']}** (tier {j.get('sponsor_tier') or 'C'})" for j in ready[:8]) + ".")
        active = [r for r in summary["runs"] if r["state"] in {"queued", "running"}]
        if active:
            lines.append("Working now: " + ", ".join(r["kind"] + ((" — " + ((r.get("result") or {}).get("stage") or "")) if r.get("result") else "") for r in active) + ".")
        if summary["profile_dirty"]:
            lines.append("⚠ The Profile has unreviewed edits; new drafts wait until they are reconciled.")
        return "\n".join(lines)

    def _excluded(self):
        rows = self.s.excluded()
        if not rows:
            return "Nothing has been excluded."
        lines = [f"{len(rows)} postings were cut by the sponsorship gate. Most recent:"]
        for row in rows[:10]:
            lines.append(f"- **{row['company']} — {row['title']}**: “{row['sentence']}” ({row['reason_label']})")
        lines.append("Restore any wrong call from Dashboard → Excluded roles, or tell me which one was read wrongly.")
        return "\n".join(lines)

    def _job_matches(self, job, text):
        low = text.casefold()
        company = job["company"].casefold()
        if job["id"].casefold() == low or company in low or low in company:
            return True
        words = [w for w in re.findall(r"[a-z0-9+#]+", low) if len(w) > 2]
        return bool(words) and all(w in company + " " + job["title"].casefold() for w in words)

    def _find_jobs(self, phrase):
        jobs = sorted((j for j in self.w.jobs() if not j.get("deleted_at")), key=lambda j: (j["company"].casefold(), j["title"].casefold()))
        exact = [j for j in jobs if j["id"] == phrase.strip()]
        if exact:
            return exact
        return [j for j in jobs if self._job_matches(j, phrase.strip())]

    def _run_for_job(self, id, kind, phrase):
        found = self._find_jobs(phrase)
        if len(found) == 1:
            return self._dispatch_job_intent(id, kind, found[0], {})
        if not found:
            # Not a saved job by that name ("research the newest one"): the agent works out what she meant.
            return self._agent(id, self.get(id)["message"])
        return self._ask_which(id, kind, found, phrase, {})

    def _ask_which(self, id, intent, found, phrase, extra):
        if not found:
            jobs = [j for j in self.w.jobs() if not j.get("deleted_at")][:10]
            listing = "; ".join(f"**{j['company']} — {j['title']}**" for j in jobs) or "none saved yet"
            return "done", f"I can't find a saved job matching “{phrase}”. Saved: {listing}.", {"intent": intent + "_not_found"}
        self.s.set_pref("assistant_pending", {"kind": "choose_job", "intent": intent, "candidates": [{"id": j["id"], "company": j["company"], "title": j["title"]} for j in found], "extra": extra, "asked_at": self.s.now()})
        options = "\n".join(f"{n}. {j['company']} — {j['title']}" for n, j in enumerate(found, 1))
        return "needs_input", "Which posting?\n" + options + "\nReply with the number.", {"intent": intent + "_choose", "candidates": [j["id"] for j in found]}

    def _dispatch_job_intent(self, id, intent, job, extra):
        job = self.w.get_job(job["id"])
        if intent == "mark_applied":
            return self._confirm_applied(job, extra.get("date"))
        if intent == "open":
            return self._open_reply(job)
        label = {"study_plan": "Writing the study plan", "research": "Company research and hiring review"}.get(intent, intent)
        self._step(id, label + " for " + job["company"], agent=intent)
        try:
            run = self.runner.enqueue(intent, job["id"], *self.tools._engine_for(intent))
        except ValueError as error:
            self._finish_step(id, "failed", str(error))
            return "done", str(error), {"intent": intent + "_refused", "job_id": job["id"]}
        self._finish_step(id, "done", "Run " + run["id"][:8] + (" was already running" if run.get("existing") else " queued"), run_id=run["id"])
        if intent == "study_plan":
            text = (f"Writing the study plan for **{job['company']} — {job['title']}** from the honest gaps. Everything in it is a skill she does not have yet: "
                    "it never goes on the resume until it is learned and written into her profile. It lands in the application folder; watch the Agents rail.")
        else:
            text = f"Researching **{job['company']}** and running the independent hiring review (it never sees her profile). Results appear on the job's card when done."
        return "done", text, {"intent": intent, "job_id": job["id"], "run_id": run["id"], "suggestions": ["status", f"open {job['company']}"]}

    def _propose_applied(self, id, phrase, when):
        when = when.strip()
        if when:
            try:
                when = datetime.strptime(when[:10], "%Y-%m-%d").date().isoformat()
            except ValueError:
                return "done", "Give the date as YYYY-MM-DD, for example *applied to Snowflake on 2026-09-19*.", {"intent": "mark_applied_bad_date"}
        found = self._find_jobs(phrase)
        if len(found) == 1:
            return self._confirm_applied(self.w.get_job(found[0]["id"]), when)
        if not found:
            return self._agent(id, self.get(id)["message"])
        return self._ask_which(id, "mark_applied", found, phrase, {"date": when})

    def _confirm_applied(self, job, when):
        when = when or self.s.today()
        self.s.set_pref("assistant_pending", {"kind": "confirm_applied", "job_id": job["id"], "date": when, "asked_at": self.s.now()})
        return "needs_input", f"Record **{job['company']} — {job['title']}** as applied on {when}? Reply *yes* to confirm (I only record what you have actually sent).", \
            {"intent": "confirm_applied", "job_id": job["id"], "date": when, "suggestions": ["yes", "no"]}

    def _open(self, id, phrase):
        found = self._find_jobs(phrase)
        if len(found) == 1:
            return self._open_reply(self.w.get_job(found[0]["id"]))
        if not found:
            return self._agent(id, self.get(id)["message"])
        return self._ask_which(id, "open", found, phrase, {})

    def _open_reply(self, job):
        try:
            draft = self.studio.get(job["id"])
        except ValueError:
            return "done", f"**{job['company']} — {job['title']}** · status {job['status']}. No resume draft yet; say *build the resume for {job['company']}* to start one.", \
                {"intent": "open", "job_id": job["id"], "company": job["company"], "title": job["title"], "posting_url": job["url"],
                 "tier": job.get("sponsor_tier") or "C", "suggestions": [f"build the resume for {job['company']}"]}
        data = resume_card(job, draft)
        text = f"**{job['company']} — {job['title']}** · status {job['status']} · draft version {draft['revision']}" + (" with a current PDF." if data.get("pdf") else "; the PDF is not built for this version yet.")
        return "done", text, data

    # ---- The agent loop ------------------------------------------------------------
    def _snapshot(self) -> dict:
        summary = self.s.summary()
        goals = summary["goals"]
        return {
            "today": self.s.today(),
            "goals": {k: goals[k] for k in ("weekly_target", "current_week_target", "week_completed", "today_target", "today_completed", "remaining_today")},
            "counts": summary["counts"],
            "jobs": [{k: v for k, v in brief_job(j).items() if k in {"id", "company", "title", "status", "sponsor_tier", "application_date", "has_resume_folder"}}
                     for j in summary["jobs"][:40]],
            "active_runs": [{"run_id": r["id"], "kind": r["kind"], "job_id": r["job_id"], "stage": (r.get("result") or {}).get("stage")}
                            for r in summary["runs"] if r["state"] in {"queued", "running"}],
            "profile_has_unreviewed_edits": summary["profile_dirty"],
            "pending_profile_entries": len(self.s.pending_knowledge()),
            "excluded_count": len(summary["excluded_jobs"]),
        }

    def _payload(self, id, transcript, turn_no) -> dict:
        recent = [{"you": m["message"][:500], "assistant": m["response"][:500]} for m in self.history(8) if m["id"] != id][-5:]
        # Older tool results shrink to their summary so the transcript stays within budget.
        results = [i for i, entry in enumerate(transcript) if entry.get("role") == "tool" and "result" in entry]
        keep = set(results[-FULL_RESULTS_KEPT:])
        task = []
        for index, entry in enumerate(transcript):
            if entry.get("role") == "tool" and "result" in entry and index not in keep:
                entry = {"role": "tool", "tool": entry["tool"], "summary": entry.get("summary", ""), "result": "(omitted: older result)"}
            task.append({k: v for k, v in entry.items() if k != "card"})
        return {
            "workspace": self._snapshot(),
            "tools": self.tools.catalogue(),
            "recent_conversation": recent,
            "task": task,
            "turns": {"used": turn_no, "max": MAX_TURNS},
        }

    def _run_tool(self, id, tool, arguments) -> dict:
        """Run one tool inside the current step; the transcript entry is the return value."""
        try:
            result = tool.handler(**arguments)
        except ValueError as error:
            self._finish_step(id, "failed", str(error))
            return {"role": "tool", "tool": tool.name, "arguments": arguments, "error": str(error)}
        except Exception as error:  # noqa: BLE001 - a broken tool is a failed step, never a stuck message
            detail = type(error).__name__ + ": " + str(error)[:300]
            self._finish_step(id, "failed", detail)
            return {"role": "tool", "tool": tool.name, "arguments": arguments, "error": detail}
        summary = str(result.get("summary") or "done")
        self._finish_step(id, "done", summary, **{k: result[k] for k in ("run_id", "agent") if result.get(k)})
        shown = {k: v for k, v in result.items() if k != "card"}
        text = json.dumps(shown, ensure_ascii=False, default=str)
        entry = {"role": "tool", "tool": tool.name, "arguments": arguments, "summary": summary,
                 "result": shown if len(text) <= RESULT_CHARS else _trim(text, RESULT_CHARS)}
        if result.get("card"):
            entry["card"] = result["card"]
        return entry

    def _agent(self, id, text, transcript=None):
        from backend.ai import any_provider_configured, team_for
        from backend.ai.agents.graph import AgentError

        if not any_provider_configured(self.w.root):
            return "done", ("No AI runtime is set up, so I can only run the exact commands. Install Claude Code or the ChatGPT app "
                            "(Codex), or add a provider key in Settings, and I can do the rest.\n\n" + HELP), {"intent": "answer_unavailable"}
        transcript = list(transcript or [])
        if text is not None:
            transcript.append({"role": "user", "content": text})
        team = team_for(self.s)
        data: dict = {"intent": "agent"}
        for entry in transcript:
            if entry.get("card"):
                data.update(entry["card"])
        used = sum(1 for e in transcript if e.get("role") == "tool")
        for turn_no in range(used, used + MAX_TURNS):
            self._step(id, "Thinking", agent="assistant")
            try:
                turn = team.run("workspace_agent", self._payload(id, transcript, turn_no))
            except (AgentError, ValueError) as error:
                self._finish_step(id, "failed", str(error)[:300])
                return "failed", ("I could not reach the AI runtime, so nothing more was changed. " + str(error).rstrip(".")
                                  + ". The exact commands (say *help*) still work without it."), {**data, "intent": "agent_failed"}
            thought = " ".join(turn.thought.split())[:200]
            suggestions = [s.strip() for s in turn.suggestions if isinstance(s, str) and 0 < len(s.strip()) <= 80][:4]
            if turn.action == "reply":
                self._finish_step(id, "done", thought)
                return "done", turn.reply.strip() or "Done.", {**data, "suggestions": suggestions}
            if turn.action == "ask":
                self._finish_step(id, "done", thought)
                question = turn.reply.strip() or "What would you like me to do?"
                self.s.set_pref("assistant_pending", {"kind": "agent", "transcript": transcript + [{"role": "assistant", "asked": question}], "asked_at": self.s.now()})
                return "needs_input", question, {**data, "intent": "agent_question", "suggestions": suggestions}
            try:
                tool = self.tools.get(turn.tool)
                arguments = self.tools.coerce(tool, json.loads(turn.arguments or "{}"))
            except (ValueError, json.JSONDecodeError) as error:
                self._finish_step(id, "failed", str(error)[:200])
                transcript.append({"role": "tool", "tool": turn.tool, "error": str(error)[:400]})
                continue
            if tool.confirm:
                self._finish_step(id, "done", thought)
                self.s.set_pref("assistant_pending", {"kind": "confirm_tool", "tool": tool.name, "arguments": arguments,
                                                      "transcript": transcript, "asked_at": self.s.now()})
                lead = turn.reply.strip()
                question = (lead + "\n\n" if lead else "") + f"Ready to: {self.tools.describe(tool.name, arguments)}. Reply *yes* to go ahead or *no* to skip it."
                return "needs_input", question, {**data, "intent": "confirm_tool", "tool": tool.name, "arguments": arguments, "suggestions": ["yes", "no"]}
            self._relabel_step(id, tool.label, thought, agent=tool.agent)
            entry = self._run_tool(id, tool, arguments)
            transcript.append(entry)
            if entry.get("card"):
                data.update(entry["card"])
        return "failed", (f"I stopped after {MAX_TURNS} steps without finishing. What was done is listed above; "
                          "tell me how to continue, or split the request."), {**data, "intent": "agent_exhausted"}
