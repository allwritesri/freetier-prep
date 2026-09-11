"""Provisioning engines.

SimulatedProvisioner (dev): applies the lab's resource graph into fake GCP
and writes a terraform-state-shaped JSON document into the *student's*
state bucket — the platform never stores it. TerraformProvisioner (prod)
will shell out to real terraform; interface identical, wiring swap only.
"""

import time

from .fake_gcp import SESSION_LABEL, FakeGCP

STATE_KEY = "sessions/{session_id}/terraform.tfstate"


class Provisioner:
    def apply(self, project_id: str, session_id: str, bucket: str, lab: dict) -> dict:
        raise NotImplementedError  # pragma: no cover - interface

    def destroy(self, project_id: str, session_id: str, bucket: str) -> dict:
        raise NotImplementedError  # pragma: no cover - interface


class SimulatedProvisioner(Provisioner):
    def __init__(self, gcp: FakeGCP):
        self.gcp = gcp

    def _state_key(self, session_id: str) -> str:
        return STATE_KEY.format(session_id=session_id)

    def apply(self, project_id: str, session_id: str, bucket: str, lab: dict) -> dict:
        created = []
        for res in lab["base_resources"]:
            if self.gcp.get_resource(project_id, res["name"]) is not None:
                continue
            self.gcp.insert_resource(
                project_id, res["type"], res["name"],
                labels={SESSION_LABEL: session_id},
                config=dict(res["config"]),
            )
            created.append({"type": res["type"], "name": res["name"]})
        state = {
            "version": 4,
            "terraform_version": "simulated",
            "serial": 1,
            "lineage": session_id,
            "applied_at": time.time(),
            "resources": created,
        }
        self.gcp.write_object(project_id, bucket, self._state_key(session_id), state)
        return state

    def read_state(self, project_id: str, session_id: str, bucket: str) -> dict | None:
        return self.gcp.read_object(project_id, bucket, self._state_key(session_id))

    def destroy(self, project_id: str, session_id: str, bucket: str) -> dict:
        """State-driven destroy + label-scoped sweep of session leftovers.

        Raises on the first failed delete (caller owns retry/escalation).
        Returns {destroyed: [...], remaining: [...]} on convergence.
        """
        destroyed = []
        state = self.read_state(project_id, session_id, bucket) or {"resources": []}
        for res in state["resources"]:
            if self.gcp.get_resource(project_id, res["name"]) is not None:
                self.gcp.delete_resource(project_id, res["name"])  # may raise
                destroyed.append(res["name"])
        # Sweep anything else the session created (student task resources
        # carry the session label too). Label scope = blast-radius boundary.
        for res in self.gcp.list_resources(
            project_id, label=(SESSION_LABEL, session_id)
        ):
            self.gcp.delete_resource(project_id, res.name)  # may raise
            destroyed.append(res.name)
        remaining = [
            r.name for r in self.gcp.list_resources(
                project_id, label=(SESSION_LABEL, session_id)
            )
        ]
        self.gcp.write_object(
            project_id, bucket, self._state_key(session_id),
            {**state, "resources": [], "destroyed_at": time.time()},
        )
        return {"destroyed": destroyed, "remaining": remaining}

    def session_resource_manifest(
        self, project_id: str, session_id: str, bucket: str
    ) -> list[dict]:
        """What still exists for this session — for escalation notices."""
        live = self.gcp.list_resources(project_id, label=(SESSION_LABEL, session_id))
        return [r.to_dict() for r in live]


class TerraformProvisioner(Provisioner):
    """Production engine — real terraform apply/destroy. Not in MVP dev scope."""

    def apply(self, project_id, session_id, bucket, lab):
        raise NotImplementedError("real terraform is production-only")

    def destroy(self, project_id, session_id, bucket):
        raise NotImplementedError("real terraform is production-only")
