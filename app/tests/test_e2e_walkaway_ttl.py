"""Walk-away path: TTL hard-timer tears down unattended sessions, verifies
zero, notifies, preserves progress; resume restores validated tasks."""

from conftest import TTL, connect, start_lab

from freetier_prep.fake_gcp import SESSION_LABEL


def test_walkaway_ttl_teardown_and_resume(env):
    app, client, clock = env
    info = connect(client, "dev@example.com")
    project = info["project_id"]
    sid = start_lab(client)["id"]

    # Student does the first 3 tasks, then walks away (kid woke up).
    for tid in ["t01", "t02", "t03"]:
        client.post(f"/api/session/{sid}/task/{tid}/simulate")
        assert client.post(
            f"/api/session/{sid}/task/{tid}/validate").json()["ok"]

    clock.advance(TTL + 1)
    results = app.state.scheduler.check_expired()
    assert len(results) == 1 and results[0]["result"]["ok"]

    # Zero resources, session closed, student notified with the manifest.
    assert app.state.gcp.list_resources(project, label=(SESSION_LABEL, sid)) == []
    assert app.state.db.get_session(sid)["status"] == "torn_down"
    notes = client.get("/api/notifications").json()
    assert any("TTL expired" in n["message"] and "0 session resources"
               in n["message"] for n in notes)

    # Progress survived teardown; resume restores it in a fresh session.
    new = client.post("/api/resume", json={"lab_id": "first-vpc"}).json()["session"]
    assert new["id"] != sid and new["status"] == "active"
    view = client.get(f"/api/session/{new['id']}").json()
    validated = {t["id"] for t in view["tasks"] if t["validated"]}
    assert validated == {"t01", "t02", "t03"}
