"""Manual probe for the compile service. Run: python dashboard/tests/probe_compile.py"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend import paths  # noqa: E402
from backend.services import tectonic as T  # noqa: E402

TEX = paths.read_text(paths.OUTPUT / "Annie_Manoharan_USC_01" / "resume.tex")
END = "\\end{document}"


async def main() -> None:
    print("engine:", T.engine_status()["engine"])

    t0 = time.time()
    r = await T.compile_tex(TEX, mode="ship", resume_id="p_ok", return_pdf=False)
    print(f"SHIP     {time.time()-t0:5.2f}s ok={r.ok} pages={r.pages} chars={r.text_chars}")

    bad = TEX.replace(END, "\\resumeItm{oops}\n" + END)
    assert "\\resumeItm{oops}" in bad, "the broken macro was not inserted"
    r2 = await T.compile_tex(bad, mode="draft", resume_id="p_bad", return_pdf=False)
    print(f"BROKEN   ok={r2.ok} (want False)")
    for p in r2.problems[:5]:
        print(f"         [{p['severity']}] {p['kind']} line={p['line']}: {p['message'][:70]}")
    if not r2.problems:
        print("         log tail:")
        for line in r2.log_tail.splitlines()[-12:]:
            print("           ", line)


if __name__ == "__main__":
    asyncio.run(main())
