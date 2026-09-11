"""Teardown engine: converge to zero or escalate loudly.

Retry the state-driven destroy up to N times; on success verify zero
session-labeled resources and notify the student with the destroyed-
resource manifest. On exhaustion: mark teardown_failed, record an
escalation with the live resource manifest, notify. Force-sweep is the
operator's convergence hammer (still label-scoped).
"""

import json

from .db import Database
from .fake_gcp import SESSION_LABEL


def teardown_session(
    db: Database, gcp, provisioner, session, reason: str, max_retries: int = 3,
) -> dict:
    sid = session["id"]
    db.set_session_status(sid, "ending")
    last_error = None
    for _attempt in range(max_retries):
        try:
            report = provisioner.destroy(
                session["project_id"], sid, _bucket(session)
            )
            if report["remaining"]:
                last_error = f"resources remain: {report['remaining']}"
                continue
            db.set_session_status(sid, "torn_down")
            db.notify(
                session["user_id"], "teardown",
                f"Lab session ended ({reason}). Destroyed: "
                f"{', '.join(report['destroyed']) or 'nothing left to destroy'}. "
                "Verified: 0 session resources remaining. Your progress is saved.",
            )
            return {"ok": True, "report": report}
        except Exception as exc:  # any failed delete/subprocess is retryable
            last_error = str(exc)[:500]

    manifest = provisioner.session_resource_manifest(
        session["project_id"], sid, _bucket(session)
    )
    db.set_session_status(sid, "teardown_failed")
    db.record_escalation(sid, f"{reason}: {last_error}", json.dumps(manifest))
    db.notify(
        session["user_id"], "escalation",
        f"Teardown could not complete ({last_error}). These resources may still "
        f"exist in your project: {[m['name'] for m in manifest]}. "
        "You can delete them from your console (they carry the label "
        f"{SESSION_LABEL}={sid}); support has been alerted.",
    )
    return {"ok": False, "error": last_error, "manifest": manifest}


def force_sweep(db: Database, gcp, provisioner, session) -> dict:
    """Operator hammer: converge to zero inside the blast-radius boundary
    (session label in dev; the lab-known name set in real mode)."""
    sid = session["id"]
    project_id = session["project_id"]
    if hasattr(gcp, "heal_delete"):  # dev/fake: label-scoped
        for res in gcp.list_resources(project_id, label=(SESSION_LABEL, sid)):
            gcp.heal_delete(project_id, res.name)
            gcp.delete_resource(project_id, res.name)
        remaining = [r.name for r in gcp.list_resources(
            project_id, label=(SESSION_LABEL, sid))]
    else:  # real: name-scoped sweep + survey
        gcp.sweep_lab_resources()
        remaining = [r["name"] for r in gcp.lab_resource_survey()]
    if remaining:
        return {"ok": False, "remaining": remaining}
    db.set_session_status(sid, "torn_down")
    db.resolve_escalations(sid)
    db.notify(
        session["user_id"], "teardown",
        "Support completed cleanup: all lab resources removed. "
        "Verified: 0 session resources remaining.",
    )
    return {"ok": True, "remaining": []}


def _bucket(session) -> str:
    # state_bucket_uri is stored as gs://<bucket>
    return session["state_bucket_uri"].removeprefix("gs://")
