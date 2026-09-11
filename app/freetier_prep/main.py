"""FastAPI control plane wiring the MVP loop.

JSON API under /api/* (used by the E2E tests) plus thin server-rendered
HTML pages over the same logic so the loop is completable by hand in a
browser. Identity is a dev-mode cookie set at connect time.
"""

import asyncio
import contextlib
import json
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .artifacts import emit_artifacts
from .config import Settings
from .connector import AdcConnector, DevConnector
from .db import Database
from .fake_gcp import FakeGCP, SESSION_LABEL
from .labs import LABS
from .preflight import run_preflight, run_preflight_real
from .provisioner import SimulatedProvisioner, TerraformProvisioner
from .signing import TranscriptSigner
from .teardown import force_sweep, teardown_session
from .ttl import Clock, FakeClock, TTLScheduler
from .validators import apply_simulation, validate

TEMPLATES_DIR = Path(__file__).parent / "web"


def create_app(settings: Settings | None = None, clock: Clock | None = None) -> FastAPI:
    settings = settings or Settings()
    settings.ensure_dirs()
    clock = clock or Clock()

    db = Database(settings.db_path)
    if settings.mode == "real":
        if not settings.project_id:
            raise RuntimeError(
                "FTP_MODE=real requires FTP_PROJECT=<your-gcp-project-id> "
                "(and `gcloud auth application-default login` beforehand)")
        from .real_gcp import RealGCP

        gcp = RealGCP(settings.project_id)
        provisioner = TerraformProvisioner(
            gcp, settings.tf_dir, settings.terraform_bin)
        connector = AdcConnector(gcp, settings.project_id,
                                 settings.state_bucket or None)
    else:
        gcp = FakeGCP()
        provisioner = SimulatedProvisioner(gcp)
        connector = DevConnector(gcp)
    scheduler = TTLScheduler(db, gcp, provisioner, clock,
                             max_retries=settings.teardown_max_retries)

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI):
        task = None
        if not isinstance(clock, FakeClock):  # tests drive the scheduler directly
            async def ttl_loop():
                while True:
                    await asyncio.sleep(settings.ttl_check_interval)
                    # real mode runs terraform subprocesses — keep them off
                    # the event loop
                    await asyncio.to_thread(scheduler.check_expired)
            task = asyncio.create_task(ttl_loop())
        yield
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    app = FastAPI(title="freetier-prep", lifespan=lifespan)
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    # exposed for tests
    app.state.settings = settings
    app.state.db = db
    app.state.gcp = gcp
    app.state.provisioner = provisioner
    app.state.scheduler = scheduler
    app.state.clock = clock
    app.state.connector = connector
    app.state.signer = TranscriptSigner(settings.keys_dir)

    def preflight_for(user, lab) -> dict:
        if settings.mode == "real":
            return run_preflight_real(gcp, lab, settings.terraform_bin)
        return run_preflight(gcp, user["project_id"], lab)

    # -- helpers -----------------------------------------------------------
    def current_user(request: Request):
        uid = request.cookies.get("ftp_user")
        return db.get_user(uid) if uid else None

    def require_user(request: Request):
        user = current_user(request)
        if user is None:
            raise HTTPException(401, "connect an account first")
        return user

    def owned_session(request: Request, session_id: str):
        user = require_user(request)
        session = db.get_session(session_id)
        if session is None or session["user_id"] != user["id"]:
            raise HTTPException(404, "session not found")
        return user, session

    def do_connect(email: str) -> dict:
        grant = app.state.connector.connect(email)
        user = db.upsert_user(email, grant.project_id)
        return {"user_id": user["id"], "project_id": grant.project_id,
                "state_bucket": grant.state_bucket,
                "grant_expires_in": grant.expires_in_seconds}

    def do_start(user, lab_id: str) -> dict:
        lab = LABS.get(lab_id)
        if lab is None:
            raise HTTPException(404, f"unknown lab {lab_id}")
        pf = preflight_for(user, lab)
        if not pf["ok"]:
            raise HTTPException(412, detail={"preflight": pf})
        if db.active_session_for_project(user["project_id"]):
            raise HTTPException(
                409, "a lab is already running in this project — end or resume it")
        if settings.mode == "real":
            bucket = app.state.connector.state_bucket
        else:
            bucket = (f"freetier-prep-"
                      f"{user['email'].split('@')[0].split('.')[0]}-state")
        gcp.ensure_bucket(user["project_id"], bucket)
        session = db.create_session(
            user["id"], user["project_id"], lab_id, f"gs://{bucket}",
            ttl_deadline=clock.now() + settings.ttl_seconds,
        )
        provisioner.apply(user["project_id"], session["id"], bucket, lab)
        return {"session": dict(session)}

    def session_view(user, session) -> dict:
        lab = LABS[session["lab_id"]]
        done = db.validated_tasks(user["id"], session["lab_id"])
        return {
            "session": dict(session),
            "lab": {"id": lab["id"], "title": lab["title"]},
            "tasks": [
                {"id": t["id"], "title": t["title"],
                 "instructions": t["instructions"],
                 "validated": t["id"] in done}
                for t in lab["tasks"]
            ],
            "all_validated": len(done) == len(lab["tasks"]),
        }

    def do_end(user, session) -> dict:
        lab = LABS[session["lab_id"]]
        result = teardown_session(db, gcp, provisioner, session, reason="End Lab",
                                  max_retries=settings.teardown_max_retries)
        out: dict = {"teardown": result}
        done = db.validated_tasks(user["id"], session["lab_id"])
        if result["ok"] and len(done) == len(lab["tasks"]):
            task_results = [{"task_id": t["id"], "title": t["title"],
                             "outcome": "validated"} for t in lab["tasks"]]
            out["artifact"] = emit_artifacts(
                db, app.state.signer, settings.out_dir, user, lab, task_results)
        return out

    # -- JSON API ----------------------------------------------------------
    @app.post("/api/connect")
    async def api_connect(body: dict):
        email = body.get("email", "").strip()
        if not email:
            raise HTTPException(422, "email required")
        info = do_connect(email)
        resp = JSONResponse(info)
        resp.set_cookie("ftp_user", info["user_id"], httponly=True)
        return resp

    @app.get("/api/preflight")
    async def api_preflight(request: Request, lab_id: str = "first-vpc"):
        user = require_user(request)
        return preflight_for(user, LABS[lab_id])

    @app.post("/api/start")
    async def api_start(request: Request, body: dict):
        user = require_user(request)
        return do_start(user, body.get("lab_id", "first-vpc"))

    @app.get("/api/session/{session_id}")
    async def api_session(request: Request, session_id: str):
        user, session = owned_session(request, session_id)
        return session_view(user, session)

    @app.post("/api/session/{session_id}/task/{task_id}/validate")
    async def api_validate(request: Request, session_id: str, task_id: str):
        user, session = owned_session(request, session_id)
        if session["status"] != "active":
            raise HTTPException(409, "session is not active")
        lab = LABS[session["lab_id"]]
        task = next((t for t in lab["tasks"] if t["id"] == task_id), None)
        if task is None:
            raise HTTPException(404, "unknown task")
        result = validate(gcp, session["project_id"], task["validator"])
        if result["ok"]:
            db.mark_task_validated(user["id"], session["lab_id"], task_id)
        return result

    @app.post("/api/session/{session_id}/task/{task_id}/simulate")
    async def api_simulate(request: Request, session_id: str, task_id: str):
        if settings.mode == "real":
            raise HTTPException(
                403, "simulate is dev-mode only — in real mode, do the task "
                     "in your actual GCP console, then hit validate")
        _user, session = owned_session(request, session_id)
        if session["status"] != "active":
            raise HTTPException(409, "session is not active")
        lab = LABS[session["lab_id"]]
        task = next((t for t in lab["tasks"] if t["id"] == task_id), None)
        if task is None:
            raise HTTPException(404, "unknown task")
        apply_simulation(gcp, session["project_id"], session_id, task["simulate"])
        return {"ok": True}

    @app.post("/api/session/{session_id}/end")
    async def api_end(request: Request, session_id: str):
        user, session = owned_session(request, session_id)
        if session["status"] not in ("active", "teardown_failed"):
            raise HTTPException(409, f"session is {session['status']}")
        return do_end(user, session)

    @app.post("/api/resume")
    async def api_resume(request: Request, body: dict):
        user = require_user(request)
        return do_start(user, body.get("lab_id", "first-vpc"))

    @app.get("/api/notifications")
    async def api_notifications(request: Request):
        user = require_user(request)
        return [dict(n) for n in db.notifications_for(user["id"])]

    @app.get("/api/verify/{transcript_id}")
    async def api_verify(transcript_id: str):
        row = db.get_transcript(transcript_id)
        if row is None:
            raise HTTPException(404, "transcript not found")
        valid = app.state.signer.verify(row["payload"], row["signature"])
        return {"transcript_id": transcript_id, "valid": valid,
                "payload": json.loads(row["payload"]) if valid else None}

    @app.get("/api/ops")
    async def api_ops():
        return {
            "sessions": [dict(s) for s in db.all_sessions()],
            "escalations": [dict(e) for e in db.escalations()],
        }

    @app.post("/api/ops/force-sweep/{session_id}")
    async def api_force_sweep(session_id: str):
        session = db.get_session(session_id)
        if session is None:
            raise HTTPException(404, "session not found")
        return force_sweep(db, gcp, provisioner, session)

    @app.get("/health")
    async def health():
        return {"ok": True, "mode": settings.mode}

    # -- HTML pages --------------------------------------------------------
    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        user = current_user(request)
        ctx: dict = {"user": user, "labs": LABS.values(),
                     "mode": settings.mode}
        if user:
            ctx["preflight"] = preflight_for(user, LABS["first-vpc"])
            sessions = [s for s in db.all_sessions()
                        if s["user_id"] == user["id"]]
            ctx["sessions"] = sessions
            ctx["active"] = next(
                (s for s in sessions if s["status"] == "active"), None)
            ctx["notifications"] = db.notifications_for(user["id"])[:5]
        return templates.TemplateResponse(request, "dashboard.html", ctx)

    @app.post("/connect")
    async def form_connect(email: str = Form(...)):
        info = do_connect(email)
        resp = RedirectResponse("/", status_code=303)
        resp.set_cookie("ftp_user", info["user_id"], httponly=True)
        return resp

    @app.post("/start")
    async def form_start(request: Request, lab_id: str = Form("first-vpc")):
        user = require_user(request)
        out = do_start(user, lab_id)
        return RedirectResponse(f"/lab/{out['session']['id']}", status_code=303)

    @app.get("/lab/{session_id}", response_class=HTMLResponse)
    async def lab_page(request: Request, session_id: str):
        user, session = owned_session(request, session_id)
        view = session_view(user, session)
        if settings.mode == "real":
            live = [r["name"] for r in gcp.lab_resource_survey()]
        else:
            live = [r.name for r in gcp.list_resources(
                session["project_id"], label=(SESSION_LABEL, session_id))]
        return templates.TemplateResponse(request, "lab.html", {
            "user": user, **view, "mode": settings.mode,
            "live_resources": live,
        })

    @app.post("/lab/{session_id}/task/{task_id}/{action}")
    async def form_task(request: Request, session_id: str, task_id: str,
                        action: str):
        if action == "simulate":
            await api_simulate(request, session_id, task_id)
        elif action == "validate":
            await api_validate(request, session_id, task_id)
        else:
            raise HTTPException(404)
        return RedirectResponse(f"/lab/{session_id}", status_code=303)

    @app.post("/lab/{session_id}/end")
    async def form_end(request: Request, session_id: str):
        user, session = owned_session(request, session_id)
        out = do_end(user, session)
        if "artifact" in out:
            return RedirectResponse(
                out["artifact"]["verify_url"], status_code=303)
        return RedirectResponse("/", status_code=303)

    @app.get("/verify/{transcript_id}", response_class=HTMLResponse)
    async def verify_page(request: Request, transcript_id: str):
        row = db.get_transcript(transcript_id)
        valid = bool(row) and app.state.signer.verify(
            row["payload"], row["signature"])
        payload = json.loads(row["payload"]) if (row and valid) else None
        return templates.TemplateResponse(request, "verify.html", {
            "transcript_id": transcript_id,
            "valid": valid, "payload": payload, "found": row is not None,
        })

    @app.get("/ops", response_class=HTMLResponse)
    async def ops_page(request: Request):
        return templates.TemplateResponse(request, "ops.html", {
            "sessions": db.all_sessions(),
            "escalations": db.escalations(),
        })

    return app


app = create_app()
