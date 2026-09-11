"""Teardown-failure path: injected delete failure exhausts retries,
escalates with a resource manifest, notifies the student with a self-rescue
path, and force-sweep converges to zero. Silence is unacceptable."""

import json

from conftest import connect, start_lab

from freetier_prep.fake_gcp import SESSION_LABEL


def test_teardown_failure_escalates_then_force_sweep_converges(env):
    app, client, clock = env
    info = connect(client, "dev@example.com")
    project = info["project_id"]
    sid = start_lab(client)["id"]

    app.state.gcp.poison_delete(project, "ftp-lab-vm")

    out = client.post(f"/api/session/{sid}/end").json()
    assert out["teardown"]["ok"] is False
    assert app.state.db.get_session(sid)["status"] == "teardown_failed"

    # Escalation carries the live resource manifest.
    escalations = client.get("/api/ops").json()["escalations"]
    assert len(escalations) == 1 and not escalations[0]["resolved"]
    manifest = json.loads(escalations[0]["resource_manifest"])
    assert any(m["name"] == "ftp-lab-vm" for m in manifest)

    # Student is told what may still exist and how to self-rescue.
    notes = client.get("/api/notifications").json()
    esc = [n for n in notes if n["kind"] == "escalation"]
    assert esc and "ftp-lab-vm" in esc[0]["message"]
    assert SESSION_LABEL in esc[0]["message"]

    # Operator force-sweep converges to zero and resolves the escalation.
    swept = client.post(f"/api/ops/force-sweep/{sid}").json()
    assert swept["ok"] and swept["remaining"] == []
    assert app.state.gcp.list_resources(project, label=(SESSION_LABEL, sid)) == []
    assert app.state.db.get_session(sid)["status"] == "torn_down"
    assert all(e["resolved"] for e in client.get("/api/ops").json()["escalations"])
