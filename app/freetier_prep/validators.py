"""Outcome validators.

Validators read the (fake) student project and check *outcomes* —
reachability, least-privilege, configuration-meets-requirement — never
bare resource existence. Each failure returns the task's outcome-based
explanation so a rejection teaches instead of stonewalling.
"""

from .fake_gcp import FakeGCP


def _fail(spec: dict, detail: str = "") -> dict:
    msg = spec.get("explain", "Check failed.")
    if detail:
        msg = f"{msg} ({detail})"
    return {"ok": False, "explanation": msg}


def _ok() -> dict:
    return {"ok": True, "explanation": "Validated."}


def validate(gcp: FakeGCP, project_id: str, spec: dict) -> dict:
    kind = spec["kind"]

    if kind == "config":
        res = gcp.get_resource(project_id, spec["resource"])
        if res is None:
            return _fail(spec, f"{spec['resource']} not found")
        for key, want in spec["expect"].items():
            if res.config.get(key) != want:
                return _fail(spec, f"{key}={res.config.get(key)!r}, expected {want!r}")
        return _ok()

    if kind == "config_contains":
        res = gcp.get_resource(project_id, spec["resource"])
        if res is None:
            return _fail(spec, f"{spec['resource']} not found")
        if spec["value"] not in (res.config.get(spec["field"]) or []):
            return _fail(spec, f"{spec['field']} missing {spec['value']!r}")
        return _ok()

    if kind == "config_label":
        res = gcp.get_resource(project_id, spec["resource"])
        if res is None:
            return _fail(spec, f"{spec['resource']} not found")
        labels = res.config.get("labels") or {}
        if labels.get(spec["label"]) != spec["value"]:
            return _fail(spec, f"label {spec['label']} is {labels.get(spec['label'])!r}")
        return _ok()

    if kind == "iap_ssh":
        if not gcp.iap_ssh_allowed(project_id, spec["network"], spec["tag"]):
            return _fail(spec)
        return _ok()

    if kind == "no_public_ssh":
        if gcp.ssh_open_to_internet(project_id, spec["network"], spec["tag"]):
            return _fail(spec)
        return _ok()

    if kind == "iap_only_ssh":
        iap = gcp.iap_ssh_allowed(project_id, spec["network"], spec["tag"])
        public = gcp.ssh_open_to_internet(project_id, spec["network"], spec["tag"])
        if not iap:
            return _fail(spec, "IAP path not reachable")
        if public:
            return _fail(spec, "still reachable from public internet")
        return _ok()

    if kind == "iam_least_priv":
        roles = gcp.roles_of(project_id, spec["member"])
        if spec["required"] not in roles:
            return _fail(spec, f"{spec['required']} not granted")
        broad = roles & set(spec.get("forbidden", []))
        if broad:
            return _fail(spec, "over-broad grant: " + ", ".join(sorted(broad)))
        return _ok()

    if kind == "static_ip":
        addr = gcp.get_resource(project_id, spec["address_name"])
        if addr is None or addr.config.get("address") != spec["ip"]:
            return _fail(spec, f"address {spec['address_name']} missing or wrong IP")
        vm = gcp.get_resource(project_id, spec["vm"])
        if vm is None or vm.config.get("internal_ip") != spec["ip"]:
            return _fail(spec, "VM does not use the reserved address")
        return _ok()

    if kind == "no_allow_all":
        for fw in gcp.list_resources(project_id, type_glob="compute.firewall"):
            c = fw.config
            if (
                c.get("network") == spec["network"]
                and c.get("action") == "allow"
                and "0.0.0.0/0" in c.get("source_ranges", [])
                and c.get("ports") == ["all"]
            ):
                return _fail(spec, f"rule {fw.name} still allows all")
        return _ok()

    raise ValueError(f"unknown validator kind: {kind}")


def apply_simulation(gcp: FakeGCP, project_id: str, session_id: str, sim: dict) -> None:
    """Perform the 'student did it in the console' mutation for a task.

    Resources the student creates during the lab are stamped with the
    session label: they belong to the lab session, so teardown can sweep
    them to zero while still touching *only* session-labeled infra
    (blast-radius rule). Anything pre-existing in the project is untouched.
    """
    from .fake_gcp import SESSION_LABEL

    if sim.get("noop"):
        return
    if "create" in sim:
        c = sim["create"]
        if gcp.get_resource(project_id, c["name"]) is None:
            gcp.insert_resource(project_id, c["type"], c["name"],
                                labels={SESSION_LABEL: session_id},
                                config=dict(c["config"]))
        return
    if "update" in sim:
        gcp.update_resource(project_id, sim["update"]["resource"],
                            **sim["update"]["config"])
        return
    if "update_label" in sim:
        u = sim["update_label"]
        res = gcp.get_resource(project_id, u["resource"])
        labels = dict(res.config.get("labels") or {})
        labels[u["label"]] = u["value"]
        gcp.update_resource(project_id, u["resource"], labels=labels)
        return
    if "delete" in sim:
        gcp.delete_resource(project_id, sim["delete"]["resource"])
        return
    if "iam" in sim:
        gcp.bind_role(project_id, sim["iam"]["member"], sim["iam"]["role"])
        return
    if "static_ip" in sim:
        s = sim["static_ip"]
        if gcp.get_resource(project_id, s["address_name"]) is None:
            gcp.insert_resource(project_id, "compute.address", s["address_name"],
                                labels={SESSION_LABEL: session_id},
                                config={"address": s["ip"], "subnet": s["subnet"]})
        gcp.update_resource(project_id, s["vm"], internal_ip=s["ip"])
        return
    raise ValueError(f"unknown simulation: {sim}")
