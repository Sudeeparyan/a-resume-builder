"""Persistent AI stage cache and a shared daily call budget (not token estimates)."""
import hashlib
import json
import threading
import uuid
from datetime import datetime, timezone

CACHE_VERSION = 'career-workers-v1'


class AgentCache:
    def __init__(self, service):
        self.s, self.w = service, service.w
        self.lock = threading.RLock()
        with self.w.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS ai_cache(key TEXT PRIMARY KEY, result TEXT NOT NULL, created_at TEXT NOT NULL, web INTEGER NOT NULL, hits INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS ai_calls(id TEXT PRIMARY KEY, cache_key TEXT NOT NULL, day TEXT NOT NULL, state TEXT NOT NULL, created_at TEXT NOT NULL, error TEXT);
            ''')

    def settings(self):
        return self.s.pref('ai_policy', {'daily_call_limit': 6})

    def configure(self, limit):
        if not isinstance(limit, int) or not 0 <= limit <= 50:
            raise ValueError('Daily AI call limit must be between 0 and 50')
        with self.w.connect() as db:
            self.s.set_pref('ai_policy', {'daily_call_limit': limit}, db)
            self.w.record_event(db, 'ai_policy_updated', daily_call_limit=limit)
        self.w.export_tracking()
        return self.stats()

    def stats(self):
        with self.w.connect() as db:
            used = db.execute('SELECT COUNT(*) FROM ai_calls WHERE day=?', (self.s.today(),)).fetchone()[0]
            cache = db.execute('SELECT COUNT(*), COALESCE(SUM(hits),0) FROM ai_cache').fetchone()
        return {**self.settings(), 'calls_today': used, 'cached_results': cache[0], 'cache_hits': cache[1],
                'remaining_calls': max(0, self.settings()['daily_call_limit'] - used),
                'note': 'Counts local AI invocations, including failures; actual credits and tokens vary.'}

    def execute(self, invoke, prompt, schema, *, cacheable=True, **options):
        key = hashlib.sha256(json.dumps([CACHE_VERSION, prompt, schema, options], sort_keys=True).encode()).hexdigest()
        with self.lock:
            # Reserve before invoking: concurrent workers cannot overspend the shared limit.
            with self.w.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                old = db.execute('SELECT * FROM ai_cache WHERE key=?', (key,)).fetchone() if cacheable else None
                if old:
                    age = (datetime.now(timezone.utc) - datetime.fromisoformat(old['created_at'])).total_seconds()
                    if not old['web'] or age < 7 * 86400:
                        db.execute('UPDATE ai_cache SET hits=hits+1 WHERE key=?', (key,))
                        return json.loads(old['result'])
                used = db.execute('SELECT COUNT(*) FROM ai_calls WHERE day=?', (self.s.today(),)).fetchone()[0]
                policy = db.execute("SELECT value FROM preferences WHERE key='ai_policy'").fetchone()
                limit = json.loads(policy[0])['daily_call_limit'] if policy else 6
                if used >= limit:
                    raise ValueError('Daily AI call budget reached. Saved results remain available. Raise the limit in Agent control or retry tomorrow.')
                call_id = uuid.uuid4().hex
                provider = options.get('provider', 'codex')
                model = options.get('model', 'codex-runtime')
                action = options.get('action', 'unknown')
                db.execute(
                    """INSERT INTO ai_calls(id,cache_key,day,state,created_at,error,provider,model,action,cache_version)
                    VALUES(?,?,?,?,?,NULL,?,?,?,?)""",
                    (call_id, key, self.s.today(), 'running', self.s.now(), provider, model, action, CACHE_VERSION),
                )
            try:
                result = invoke(prompt, schema, **options)
                # Only complete, schema-shaped reports can become reusable results.
                if not isinstance(result, dict) or any(k not in result for k in schema.get('required', [])):
                    raise ValueError('AI returned an incomplete structured result')
                encoded = json.dumps(result, ensure_ascii=False)
                with self.w.connect() as db:
                    db.execute("UPDATE ai_calls SET state='completed' WHERE id=?", (call_id,))
                    if cacheable:
                        db.execute('INSERT INTO ai_cache VALUES(?,?,?,?,0) ON CONFLICT(key) DO UPDATE SET result=excluded.result,created_at=excluded.created_at',
                                   (key, encoded, self.s.now(), int(options.get('web', True))))
                return result
            except Exception as exc:
                with self.w.connect() as db:
                    db.execute("UPDATE ai_calls SET state='failed',error=? WHERE id=?", (str(exc)[:1000], call_id))
                raise
