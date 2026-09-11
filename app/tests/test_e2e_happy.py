"""Happy path: connect → preflight → provision → validate → teardown →
signed transcript. Plus: outcome-validator reject, manifest-only DB rule,
tamper detection."""

import json

from conftest import complete_all_tasks, connect, start_lab

from freetier_prep.fake_gcp import SESSION_LABEL


def test_full_happy_path(env):
    app, client, clock = env
    info = connect(client)
    project = info["project_id"]

    pf = client.get("/api/preflight").json()
    assert pf["ok"] and pf["credit_estimate_usd"] == 0.0

    session = start_lab(client)
    sid = session["id"]

    # Real (fake-)infra appeared in the student's project, session-labeled.
    live = app.state.gcp.list_resources(project, label=(SESSION_LABEL, sid))
    assert {r.name for r in live} >= {"ftp-lab-net", "ftp-lab-subnet",
                                      "ftp-lab-vm", "ftp-lab-allow-all"}

    # Outcome validator rejects before the fix, with a teaching explanation.
    r = client.post(f"/api/session/{sid}/task/t05/validate").json()
    assert not r["ok"] and "0.0.0.0/0" in r["explanation"]

    complete_all_tasks(client, sid)

    out = client.post(f"/api/session/{sid}/end").json()
    assert out["teardown"]["ok"]
    assert out["teardown"]["report"]["remaining"] == []
    assert app.state.gcp.list_resources(project, label=(SESSION_LABEL, sid)) == []
    assert app.state.db.get_session(sid)["status"] == "torn_down"

    # Signed transcript verifies; artifact repo emitted with real HCL.
    tid = out["artifact"]["transcript_id"]
    v = client.get(f"/api/verify/{tid}").json()
    assert v["valid"] and len(v["payload"]["tasks"]) == 12
    repo = out["artifact"]["repo_path"]
    hcl = open(f"{repo}/main.tf").read()
    assert "google_compute_network" in hcl

    # Trust rule: platform DB is manifest-only — no state, no resource IDs.
    cols = [c[1] for c in app.state.db.conn.execute(
        "PRAGMA table_info(sessions)")]
    assert set(cols) == {"id", "user_id", "project_id", "lab_id",
                         "state_bucket_uri", "ttl_deadline", "status",
                         "created_at", "updated_at"}
    # Terraform state lives in the student's bucket, not the platform.
    state = app.state.provisioner.read_state(
        project, sid, info["state_bucket"])
    assert state is not None and state["resources"] == []


def test_tampered_transcript_is_invalid(env):
    app, client, clock = env
    connect(client)
    sid = start_lab(client)["id"]
    complete_all_tasks(client, sid)
    tid = client.post(f"/api/session/{sid}/end").json()["artifact"]["transcript_id"]

    row = app.state.db.get_transcript(tid)
    doctored = json.loads(row["payload"])
    doctored["user_email"] = "attacker@example.com"
    app.state.db.conn.execute(
        "UPDATE transcripts SET payload = ? WHERE id = ?",
        (json.dumps(doctored, sort_keys=True, separators=(",", ":")), tid))
    app.state.db.conn.commit()

    assert client.get(f"/api/verify/{tid}").json()["valid"] is False
