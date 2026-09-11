"""Simulated GCP for dev mode.

FakeGCP plays the *student's* cloud account: projects, resources with
labels, org policies, billing, buckets. It owns its own store so the
platform-side "manifest only, never state" rule stays honest even in dev.
Tests use poison flags to inject delete failures.
"""

import fnmatch
import json
from dataclasses import dataclass, field

SESSION_LABEL = "freetier-prep-session"

REQUIRED_APIS = {"compute.googleapis.com", "iam.googleapis.com", "storage.googleapis.com"}


class GcpError(Exception):
    pass


class DeletePoisoned(GcpError):
    pass


@dataclass
class Resource:
    id: str
    type: str          # e.g. compute.network, compute.subnetwork, compute.firewall,
                       # compute.instance, storage.bucket, compute.address
    name: str
    labels: dict = field(default_factory=dict)
    config: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "type": self.type, "name": self.name,
            "labels": dict(self.labels), "config": dict(self.config),
        }


@dataclass
class Project:
    project_id: str
    billing_linked: bool = True
    enabled_apis: set = field(default_factory=lambda: set(REQUIRED_APIS))
    denied_org_policies: set = field(default_factory=set)
    quotas: dict = field(default_factory=lambda: {"e2-micro": 4})
    credit_remaining_usd: float = 300.0
    resources: dict = field(default_factory=dict)      # name -> Resource
    buckets: dict = field(default_factory=dict)        # bucket -> {object: str}
    iam_bindings: dict = field(default_factory=dict)   # member -> set(roles)
    poisoned_deletes: set = field(default_factory=set)  # resource names


class FakeGCP:
    def __init__(self):
        self.projects: dict[str, Project] = {}
        self._id_seq = 0

    # -- projects ----------------------------------------------------------
    def ensure_project(self, project_id: str) -> Project:
        if project_id not in self.projects:
            self.projects[project_id] = Project(project_id=project_id)
        return self.projects[project_id]

    def project(self, project_id: str) -> Project:
        if project_id not in self.projects:
            raise GcpError(f"project {project_id} not found")
        return self.projects[project_id]

    # -- resources ---------------------------------------------------------
    def insert_resource(
        self, project_id: str, type: str, name: str,
        labels: dict | None = None, config: dict | None = None,
    ) -> Resource:
        proj = self.project(project_id)
        if name in proj.resources:
            raise GcpError(f"resource {name} already exists")
        self._id_seq += 1
        res = Resource(
            id=f"res-{self._id_seq}", type=type, name=name,
            labels=labels or {}, config=config or {},
        )
        proj.resources[name] = res
        return res

    def get_resource(self, project_id: str, name: str) -> Resource | None:
        return self.project(project_id).resources.get(name)

    def update_resource(self, project_id: str, name: str, **config) -> Resource:
        res = self.project(project_id).resources.get(name)
        if res is None:
            raise GcpError(f"resource {name} not found")
        res.config.update(config)
        return res

    def delete_resource(self, project_id: str, name: str) -> None:
        proj = self.project(project_id)
        if name in proj.poisoned_deletes:
            raise DeletePoisoned(f"delete of {name} failed (injected)")
        proj.resources.pop(name, None)

    def list_resources(
        self, project_id: str, label: tuple[str, str] | None = None,
        type_glob: str | None = None,
    ) -> list[Resource]:
        out = []
        for res in self.project(project_id).resources.values():
            if label and res.labels.get(label[0]) != label[1]:
                continue
            if type_glob and not fnmatch.fnmatch(res.type, type_glob):
                continue
            out.append(res)
        return out

    # -- failure injection (tests only) -------------------------------------
    def poison_delete(self, project_id: str, name: str) -> None:
        self.project(project_id).poisoned_deletes.add(name)

    def heal_delete(self, project_id: str, name: str) -> None:
        self.project(project_id).poisoned_deletes.discard(name)

    # -- buckets (student's state bucket lives here) -------------------------
    def ensure_bucket(self, project_id: str, bucket: str) -> None:
        self.project(project_id).buckets.setdefault(bucket, {})

    def write_object(self, project_id: str, bucket: str, key: str, data: dict) -> None:
        self.ensure_bucket(project_id, bucket)
        self.project(project_id).buckets[bucket][key] = json.dumps(data)

    def read_object(self, project_id: str, bucket: str, key: str) -> dict | None:
        raw = self.project(project_id).buckets.get(bucket, {}).get(key)
        return json.loads(raw) if raw is not None else None

    def delete_object(self, project_id: str, bucket: str, key: str) -> None:
        self.project(project_id).buckets.get(bucket, {}).pop(key, None)

    # -- IAM ----------------------------------------------------------------
    def bind_role(self, project_id: str, member: str, role: str) -> None:
        self.project(project_id).iam_bindings.setdefault(member, set()).add(role)

    def unbind_role(self, project_id: str, member: str, role: str) -> None:
        self.project(project_id).iam_bindings.get(member, set()).discard(role)

    def roles_of(self, project_id: str, member: str) -> set[str]:
        return set(self.project(project_id).iam_bindings.get(member, set()))

    # -- network semantics (validators' reachability model) ------------------
    def _firewalls(self, project_id: str, network: str) -> list[Resource]:
        return [
            r for r in self.list_resources(project_id, type_glob="compute.firewall")
            if r.config.get("network") == network
        ]

    def ssh_open_to_internet(self, project_id: str, network: str, tag: str) -> bool:
        """True if any firewall allows tcp:22 from 0.0.0.0/0 reaching `tag`."""
        for fw in self._firewalls(project_id, network):
            c = fw.config
            if c.get("action") != "allow":
                continue
            if "0.0.0.0/0" not in c.get("source_ranges", []):
                continue
            if "22" not in c.get("ports", []) and c.get("ports") != ["all"]:
                continue
            targets = c.get("target_tags")
            if not targets or tag in targets:
                return True
        return False

    def iap_ssh_allowed(self, project_id: str, network: str, tag: str) -> bool:
        """True if a firewall allows tcp:22 from IAP range 35.235.240.0/20 to `tag`."""
        for fw in self._firewalls(project_id, network):
            c = fw.config
            if (
                c.get("action") == "allow"
                and "35.235.240.0/20" in c.get("source_ranges", [])
                and "22" in c.get("ports", [])
                and (not c.get("target_tags") or tag in c.get("target_tags", []))
            ):
                return True
        return False
