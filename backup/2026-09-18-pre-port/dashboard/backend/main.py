"""
The app.

Serves the API and the built React frontend from one process on one port, so
starting the whole thing is a single command and there is nothing to configure.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import db, paths, scheduler, settings
from .api.routes import router
from .services import sponsor_index, workspace_sync

log = logging.getLogger("dashboard")


@asynccontextmanager
async def lifespan(app: FastAPI):
    paths.ensure_dirs()
    db.init()

    # The tracker file has never been written; create the header so she can open
    # it in Excel, and age any application that has gone quiet for 21 days.
    try:
        workspace_sync.bootstrap_tracker()
        ghosted = workspace_sync.age_applications()
        if ghosted:
            log.info("marked %d silent applications as ghosted", ghosted)
    except Exception as exc:  # noqa: BLE001
        log.warning("tracker bootstrap skipped: %s", exc)

    # Index the 83,624-row sponsor CSV in the background: a first boot must not
    # look frozen while it builds.
    async def build_index() -> None:
        try:
            res = await asyncio.to_thread(sponsor_index.build)
            log.info("sponsor index: %s (%s rows)", res["reason"], res["rows"])
        except Exception as exc:  # noqa: BLE001
            log.warning("sponsor index unavailable: %s", exc)

    task = asyncio.create_task(build_index())

    # The morning brief. Only ticks while the app is open; cli.py prints the
    # Task Scheduler command for a genuinely unattended run.
    scheduler.start()

    yield

    task.cancel()
    await scheduler.stop()


app = FastAPI(
    title="Career Dashboard",
    description="Job finder and resume builder for one person.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


# Registered after the real routes, so they always win. Without this, a request
# to an /api path that does not exist falls through to the single-page-app
# catch-all, which is GET-only -- and a POST then surfaces as "405 Method Not
# Allowed" rather than "no such endpoint", which is a confusing thing to debug.
@app.api_route(
    "/api/{rest:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    include_in_schema=False,
)
async def api_not_found(rest: str):
    return JSONResponse(
        status_code=404, content={"detail": f"No such API endpoint: /api/{rest}"}
    )


@app.exception_handler(Exception)
async def unhandled(request, exc: Exception):
    """Never show a stack trace to someone who is not a developer."""
    log.exception("unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Something went wrong on the server.",
            "detail": f"{type(exc).__name__}: {exc}",
            "path": str(request.url.path),
        },
    )


# The built frontend, if it has been built. Mounted last so /api wins.
if paths.FRONTEND_DIST.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(paths.FRONTEND_DIST / "assets")),
        name="assets",
    )

    @app.get("/{full_path:path}")
    async def spa(full_path: str):
        # An /api path that reaches here is a route that does not exist. Serving
        # index.html for it makes a missing endpoint look like a 405 on the
        # wrong method, which is a genuinely confusing thing to debug.
        if full_path.startswith("api/"):
            return JSONResponse(
                status_code=404,
                content={"detail": f"No such API endpoint: /{full_path}"},
            )
        candidate = paths.FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(paths.FRONTEND_DIST / "index.html")

else:

    @app.get("/")
    async def not_built():
        return JSONResponse({
            "message": (
                "The API is running, but the web page has not been built yet. "
                "Run: cd dashboard/frontend && npm install && npm run build"
            ),
            "api_docs": "/docs",
            "health": "/api/health",
        })
