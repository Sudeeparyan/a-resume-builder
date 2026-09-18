#!/usr/bin/env python3
"""Shared chat interface for the React dashboard's SQLite state."""
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "backend/scripts")]
from career import Workspace
from backend.services.workspace_v2 import CareerServices
from backend.services.agents import AgentRunner


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "instructions",
            "send-instruction",
            "agent-control",
            "score",
            "stale-drafts",
            "recompile",
            "summary",
            "goals",
            "profile",
            "mail",
            "runs",
            "export",
            "save-profile",
            "remove-profile",
            "confirm-mail",
            "run",
            "excluded",
            "restore-excluded",
            "sponsor-check",
            "check-reapply",
            "age",
        ],
    )
    parser.add_argument("--file", type=Path)
    parser.add_argument("--id")
    parser.add_argument("--job-id")
    parser.add_argument('--message')
    parser.add_argument('--revision', type=int)
    parser.add_argument("--kind", choices=["research", "resume_advisor", "email", "discovery", "resume_build", "resume_match", "instruction_interpret", "study_plan"])
    parser.add_argument("--preset", choices=["default", "balanced_five", "portals"], default="default",
                        help="discovery mix: portals reads tracked career pages with no AI call")
    parser.add_argument("--company")
    parser.add_argument("--title")
    parser.add_argument("--url", default="")
    args = parser.parse_args()
    s = CareerServices(Workspace(ROOT))
    if args.command in {'instructions', 'send-instruction', 'agent-control', 'score', 'stale-drafts', 'recompile'}:
        from backend.services.resume_studio import ResumeStudio
        from backend.services.instruction_tracker import InstructionTracker
        from backend.services.agent_cache import AgentCache
        studio = ResumeStudio(s)
        tracker = InstructionTracker(s, studio)
        if args.command == 'instructions': result = tracker.history(args.job_id)
        elif args.command == 'send-instruction':
            if not args.message: parser.error('--message is required')
            result = tracker.send(args.message, args.job_id, args.revision, args.id)
        elif args.command == 'score': result = studio.score(args.job_id)
        elif args.command == 'stale-drafts': result = studio.stale_drafts()
        elif args.command == 'recompile':
            result = studio.recompile_stale(
                [args.job_id] if args.job_id else None,
                lambda target: print('compiling ' + target['job_id'] + ' r' + str(target['revision']) + ' (' + target['reason'] + ')', file=sys.stderr, flush=True),
            )
        else: result = {'budget': AgentCache(s).stats(), 'runs': s.runs()}
    elif args.command == "save-profile":
        if not args.file:
            parser.error("--file is required")
        result = s.save_knowledge(json.loads(args.file.read_text()), args.id)
    elif args.command == "remove-profile":
        result = s.delete_knowledge(args.id)
    elif args.command == "confirm-mail":
        result = s.resolve_mail(args.id, args.job_id)
    elif args.command == "run":
        if not args.kind:
            parser.error("--kind is required")
        runner = AgentRunner(s)
        from backend.services.resume_studio import ResumeStudio
        runner.studio = ResumeStudio(s)
        result = runner.enqueue(args.kind, args.job_id, preset=args.preset)
        print(json.dumps(result), flush=True)
        runner.pool.shutdown(wait=True)
        result = s.runs()[0]
    elif args.command == "excluded":
        result = s.excluded()
    elif args.command == "restore-excluded":
        if not args.id:
            parser.error("--id is required")
        result = s.restore_excluded(args.id)
    elif args.command == "sponsor-check":
        # The gate on one posting: --company plus the JD in --file. Nothing is saved.
        if not (args.company and args.file):
            parser.error("--company and --file are required")
        from backend.services import sponsorship
        result = sponsorship.evaluate(args.company, args.file.read_text(), args.url).as_dict()
    elif args.command == "check-reapply":
        if not (args.company and args.title):
            parser.error("--company and --title are required")
        from backend.services import reapply
        result = reapply.check(args.company, args.title, s.reapply_memory(), s.excluded(), s.w.profile())
    elif args.command == "age":
        result = {"ghosted": s.age_applications()}
    elif args.command == "profile":
        result = s.knowledge()
    elif args.command == "export":
        s.export_profile()
        s.w.export_tracking()
        s.export_state()
        result = {"exported": True}
    else:
        result = getattr(s, args.command)()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
