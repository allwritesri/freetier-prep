"""Account connectors.

The Connector interface isolates everything that touches real GCP auth.
Dev mode binds DevConnector (fake project grant). Production will bind
WIFConnector — Workload Identity Federation with short-lived OIDC tokens,
never long-lived keys.
"""

from dataclasses import dataclass

from .fake_gcp import FakeGCP


@dataclass
class Grant:
    project_id: str
    state_bucket: str
    expires_in_seconds: int


class Connector:
    def connect(self, user_email: str) -> Grant:  # pragma: no cover - interface
        raise NotImplementedError


class DevConnector(Connector):
    """Simulates the one-time setup: project grant + state bucket creation."""

    def __init__(self, gcp: FakeGCP):
        self.gcp = gcp

    def connect(self, user_email: str) -> Grant:
        slug = user_email.split("@")[0].replace(".", "-")
        project_id = f"dev-project-{slug}"
        self.gcp.ensure_project(project_id)
        bucket = f"freetier-prep-{slug}-state"
        self.gcp.ensure_bucket(project_id, bucket)
        return Grant(project_id=project_id, state_bucket=bucket,
                     expires_in_seconds=12 * 3600)


class AdcConnector(Connector):
    """Own-account mode: the operator's own project via Application Default
    Credentials. No WIF ceremony needed — you are connecting to yourself,
    with short-lived local credentials and no key files."""

    def __init__(self, gcp, project_id: str, state_bucket: str | None = None):
        self.gcp = gcp  # RealGCP
        self.project_id = project_id
        self.state_bucket = state_bucket or f"freetier-prep-state-{project_id}"

    def connect(self, user_email: str) -> Grant:
        self.gcp.ensure_bucket(self.project_id, self.state_bucket)
        return Grant(project_id=self.project_id, state_bucket=self.state_bucket,
                     expires_in_seconds=3600)


class WIFConnector(Connector):
    """Hosted-platform connector — Workload Identity Federation for OTHER
    people's accounts. Not in MVP scope; AdcConnector covers own-account."""

    def connect(self, user_email: str) -> Grant:
        raise NotImplementedError(
            "WIF connector is for the hosted platform; use FTP_MODE=real "
            "(own account via ADC) or FTP_MODE=dev"
        )
