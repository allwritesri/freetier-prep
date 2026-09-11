"""Real GCP client for own-account mode.

Auth: Application Default Credentials (`gcloud auth application-default
login`) — short-lived local user credentials, no key files, honest to the
product's no-long-lived-keys rule for the self-hosted case.

Read surface mirrors FakeGCP exactly where validators/preflight touch it
(get_resource → normalized Resource, ssh_open_to_internet, iap_ssh_allowed,
roles_of, list_resources for firewalls), so validators.py runs unchanged.

Blast radius: GCP networks/subnets/firewalls don't support labels, so in
real mode the lab's fixed name set (labs/first_vpc.REAL_RESOURCE_INDEX)
is the sweep boundary — survey and delete touch only those names.
"""

import httpx

from .fake_gcp import Resource
from .labs.first_vpc import REAL_RESOURCE_INDEX, REAL_SWEEP_ORDER

COMPUTE = "https://compute.googleapis.com/compute/v1"
STORAGE = "https://storage.googleapis.com/storage/v1"
CRM = "https://cloudresourcemanager.googleapis.com/v1"
BILLING = "https://cloudbilling.googleapis.com/v1"
SERVICEUSAGE = "https://serviceusage.googleapis.com/v1"

REQUIRED_APIS = {"compute.googleapis.com", "iam.googleapis.com",
                 "storage.googleapis.com"}


class RealGCP:
    def __init__(self, project_id: str):
        import google.auth
        import google.auth.transport.requests

        self.project_id = project_id
        self._creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"])
        self._auth_request = google.auth.transport.requests.Request()
        self._http = httpx.Client(timeout=30)

    # -- plumbing ----------------------------------------------------------
    def _token(self) -> str:
        if not self._creds.valid:
            self._creds.refresh(self._auth_request)
        return self._creds.token

    def _call(self, method: str, url: str, ok404: bool = False, **kw):
        r = self._http.request(
            method, url,
            headers={"Authorization": f"Bearer {self._token()}"}, **kw)
        if r.status_code == 404 and ok404:
            return None
        r.raise_for_status()
        return r.json() if r.content else {}

    def _bucket_name(self, name: str, entry: dict) -> str:
        return f"{name}-{self.project_id}" if entry.get("name_suffix_project") \
            else name

    # -- normalized reads (validator surface) --------------------------------
    def get_resource(self, project_id: str, name: str) -> Resource | None:
        entry = REAL_RESOURCE_INDEX.get(name)
        if entry is None:
            return None
        api = entry["api"]
        p = self.project_id
        if api == "network":
            d = self._call("GET", f"{COMPUTE}/projects/{p}/global/networks/{name}",
                           ok404=True)
            if d is None:
                return None
            return Resource(d["id"], "compute.network", name, {}, {
                "auto_create_subnetworks": d.get("autoCreateSubnetworks", False)})
        if api == "subnetwork":
            region = entry["region"]
            d = self._call(
                "GET",
                f"{COMPUTE}/projects/{p}/regions/{region}/subnetworks/{name}",
                ok404=True)
            if d is None:
                return None
            return Resource(d["id"], "compute.subnetwork", name, {}, {
                "cidr": d.get("ipCidrRange"),
                "region": region,
                "network": d.get("network", "").rsplit("/", 1)[-1],
                "private_google_access": d.get("privateIpGoogleAccess", False)})
        if api == "instance":
            zone = entry["zone"]
            d = self._call(
                "GET", f"{COMPUTE}/projects/{p}/zones/{zone}/instances/{name}",
                ok404=True)
            if d is None:
                return None
            nic = (d.get("networkInterfaces") or [{}])[0]
            return Resource(d["id"], "compute.instance", name, {}, {
                "machine_type": d.get("machineType", "").rsplit("/", 1)[-1],
                "tags": (d.get("tags") or {}).get("items", []),
                "labels": d.get("labels", {}),
                "internal_ip": nic.get("networkIP")})
        if api == "firewall":
            d = self._fw_get(name)
            return self._fw_to_resource(d) if d else None
        if api == "bucket":
            b = self._bucket_name(name, entry)
            d = self._call("GET", f"{STORAGE}/b/{b}", ok404=True)
            if d is None:
                return None
            ubla = ((d.get("iamConfiguration") or {})
                    .get("uniformBucketLevelAccess") or {})
            return Resource(d.get("id", b), "storage.bucket", name, {}, {
                "uniform_access": ubla.get("enabled", False),
                "location": d.get("location")})
        if api == "address":
            region = entry["region"]
            d = self._call(
                "GET", f"{COMPUTE}/projects/{p}/regions/{region}/addresses/{name}",
                ok404=True)
            if d is None:
                return None
            return Resource(d["id"], "compute.address", name, {}, {
                "address": d.get("address")})
        return None

    def _fw_get(self, name: str) -> dict | None:
        return self._call(
            "GET",
            f"{COMPUTE}/projects/{self.project_id}/global/firewalls/{name}",
            ok404=True)

    def _fw_to_resource(self, d: dict) -> Resource:
        allowed = d.get("allowed")
        ports: list[str] = []
        if allowed:
            for a in allowed:
                if "ports" in a:
                    ports.extend(a["ports"])
                elif a.get("IPProtocol") in ("all", "tcp"):
                    ports = ["all"]
                    break
        return Resource(d.get("id", d["name"]), "compute.firewall", d["name"], {}, {
            "network": d.get("network", "").rsplit("/", 1)[-1],
            "action": "allow" if allowed else "deny",
            "source_ranges": d.get("sourceRanges", []),
            "ports": ports or ["all"],
            "target_tags": d.get("targetTags", [])})

    def _fw_list(self, network: str) -> list[Resource]:
        d = self._call(
            "GET", f"{COMPUTE}/projects/{self.project_id}/global/firewalls")
        out = []
        for item in d.get("items", []):
            res = self._fw_to_resource(item)
            if res.config["network"] == network:
                out.append(res)
        return out

    def list_resources(self, project_id: str, label=None, type_glob=None):
        # Only firewall listing is used by validators (no_allow_all).
        if type_glob == "compute.firewall":
            d = self._call(
                "GET", f"{COMPUTE}/projects/{self.project_id}/global/firewalls")
            return [self._fw_to_resource(i) for i in d.get("items", [])]
        raise NotImplementedError("real mode lists only firewalls")

    def ssh_open_to_internet(self, project_id, network, tag) -> bool:
        for fw in self._fw_list(network):
            c = fw.config
            if (c["action"] == "allow" and "0.0.0.0/0" in c["source_ranges"]
                    and ("22" in c["ports"] or c["ports"] == ["all"])
                    and (not c["target_tags"] or tag in c["target_tags"])):
                return True
        return False

    def iap_ssh_allowed(self, project_id, network, tag) -> bool:
        for fw in self._fw_list(network):
            c = fw.config
            if (c["action"] == "allow"
                    and "35.235.240.0/20" in c["source_ranges"]
                    and "22" in c["ports"]
                    and (not c["target_tags"] or tag in c["target_tags"])):
                return True
        return False

    def roles_of(self, project_id: str, member: str) -> set[str]:
        d = self._call(
            "POST", f"{CRM}/projects/{self.project_id}:getIamPolicy", json={})
        out: set[str] = set()
        for b in d.get("bindings", []):
            for m in b.get("members", []):
                if m.split(":", 1)[-1] == member:
                    out.add(b["role"])
        return out

    # -- preflight surface ---------------------------------------------------
    def billing_linked(self) -> bool:
        d = self._call(
            "GET", f"{BILLING}/projects/{self.project_id}/billingInfo")
        return bool(d.get("billingEnabled"))

    def enabled_apis(self) -> set[str]:
        enabled: set[str] = set()
        url = (f"{SERVICEUSAGE}/projects/{self.project_id}/services"
               "?filter=state:ENABLED&pageSize=200")
        while url:
            d = self._call("GET", url)
            for s in d.get("services", []):
                enabled.add(s.get("config", {}).get("name")
                            or s.get("name", "").rsplit("/", 1)[-1])
            token = d.get("nextPageToken")
            url = (f"{SERVICEUSAGE}/projects/{self.project_id}/services"
                   f"?filter=state:ENABLED&pageSize=200&pageToken={token}"
                   ) if token else None
        return enabled

    def ensure_bucket(self, project_id: str, bucket: str) -> None:
        if self._call("GET", f"{STORAGE}/b/{bucket}", ok404=True) is None:
            self._call("POST", f"{STORAGE}/b?project={self.project_id}",
                       json={"name": bucket, "location": "US",
                             "iamConfiguration": {
                                 "uniformBucketLevelAccess": {"enabled": True}},
                             "lifecycle": {"rule": [{
                                 "action": {"type": "Delete"},
                                 "condition": {"age": 30}}]}})

    # -- survey + sweep (teardown surface; name-scoped) ----------------------
    def lab_resource_survey(self) -> list[dict]:
        """Which lab-known resources currently exist. The manifest source."""
        out = []
        for name in REAL_RESOURCE_INDEX:
            res = self.get_resource(self.project_id, name)
            if res is not None:
                out.append(res.to_dict())
        return out

    def delete_lab_resource(self, name: str) -> None:
        entry = REAL_RESOURCE_INDEX[name]
        api, p = entry["api"], self.project_id
        if api == "network":
            self._call("DELETE", f"{COMPUTE}/projects/{p}/global/networks/{name}",
                       ok404=True)
        elif api == "subnetwork":
            self._call("DELETE", f"{COMPUTE}/projects/{p}/regions/"
                       f"{entry['region']}/subnetworks/{name}", ok404=True)
        elif api == "instance":
            self._call("DELETE", f"{COMPUTE}/projects/{p}/zones/"
                       f"{entry['zone']}/instances/{name}", ok404=True)
        elif api == "firewall":
            self._call("DELETE", f"{COMPUTE}/projects/{p}/global/firewalls/{name}",
                       ok404=True)
        elif api == "bucket":
            self._call("DELETE", f"{STORAGE}/b/{self._bucket_name(name, entry)}",
                       ok404=True)
        elif api == "address":
            self._call("DELETE", f"{COMPUTE}/projects/{p}/regions/"
                       f"{entry['region']}/addresses/{name}", ok404=True)

    def sweep_lab_resources(self) -> list[str]:
        """Delete every surviving lab-known resource, dependents first."""
        deleted = []
        for name in REAL_SWEEP_ORDER:
            if self.get_resource(self.project_id, name) is not None:
                self.delete_lab_resource(name)
                deleted.append(name)
        return deleted
