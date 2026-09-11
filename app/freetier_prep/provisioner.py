"""Provisioning engines.

SimulatedProvisioner (dev): applies the lab's resource graph into fake GCP
and writes a terraform-state-shaped JSON document into the *student's*
state bucket — the platform never stores it. TerraformProvisioner (prod)
will shell out to real terraform; interface identical, wiring swap only.
"""

import subprocess
import time
from pathlib import Path

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
    """Own-account mode: real terraform apply/destroy against the user's
    project, state in their GCS bucket (backend gcs, prefix sessions/<id>).

    Destroy is state-driven (canonical), then sweeps surviving lab-known
    names (student task resources created outside terraform), then surveys
    for zero. Any subprocess failure raises — teardown.py owns retries.
    """

    def __init__(self, gcp, workdir_root, terraform_bin: str = "terraform"):
        self.gcp = gcp  # RealGCP
        self.workdir_root = Path(workdir_root)
        self.tf = terraform_bin

    def _workdir(self, session_id: str, bucket: str, lab: dict | None) -> Path:
        wd = self.workdir_root / session_id
        wd.mkdir(parents=True, exist_ok=True)
        if lab is not None:
            (wd / "main.tf").write_text(lab["hcl_base"])
        (wd / "backend.tf").write_text(
            'terraform {\n  backend "gcs" {\n'
            f'    bucket = "{bucket}"\n'
            f'    prefix = "sessions/{session_id}"\n'
            "  }\n}\n")
        (wd / "terraform.tfvars").write_text(
            f'project = "{self.gcp.project_id}"\n')
        return wd

    def _run(self, wd: Path, *args: str) -> str:
        proc = subprocess.run(
            [self.tf, *args], cwd=wd, capture_output=True, text=True,
            timeout=1800)
        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout)[-2000:]
            raise RuntimeError(f"terraform {args[0]} failed: {tail}")
        return proc.stdout

    def apply(self, project_id: str, session_id: str, bucket: str, lab: dict) -> dict:
        wd = self._workdir(session_id, bucket, lab)
        self._run(wd, "init", "-input=false", "-no-color")
        self._run(wd, "apply", "-input=false", "-auto-approve", "-no-color")
        return {"resources": self.gcp.lab_resource_survey()}

    def destroy(self, project_id: str, session_id: str, bucket: str) -> dict:
        from .labs import LABS

        wd = self.workdir_root / session_id
        if not (wd / "main.tf").exists():
            # e.g. TTL fired after a restart — regenerate the module files
            wd = self._workdir(session_id, bucket, LABS["first-vpc"])
            self._run(wd, "init", "-input=false", "-no-color")
        self._run(wd, "destroy", "-input=false", "-auto-approve", "-no-color")
        swept = self.gcp.sweep_lab_resources()
        remaining = [r["name"] for r in self.gcp.lab_resource_survey()]
        return {"destroyed": swept or ["(terraform state)"],
                "remaining": remaining}

    def session_resource_manifest(self, project_id, session_id, bucket):
        return self.gcp.lab_resource_survey()
