"""Pre-flight gate.

Runs before any provisioning. Every check returns a human-readable
remediation; if any check fails, Start Lab is blocked and nothing touches
the student's project.
"""

from dataclasses import asdict, dataclass

from .fake_gcp import REQUIRED_APIS, FakeGCP


@dataclass
class Check:
    id: str
    name: str
    ok: bool
    remediation: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def run_preflight(gcp: FakeGCP, project_id: str, lab: dict) -> dict:
    proj = gcp.project(project_id)
    checks: list[Check] = []

    checks.append(Check(
        id="billing", name="Billing linked", ok=proj.billing_linked,
        remediation="" if proj.billing_linked else
        "Link a billing account to this project (Console → Billing → Link). "
        "The launch module itself runs on the always-free tier.",
    ))

    missing = REQUIRED_APIS - proj.enabled_apis
    checks.append(Check(
        id="apis", name="Required APIs enabled", ok=not missing,
        remediation="" if not missing else
        "Enable: " + ", ".join(sorted(missing)) +
        " (Console → APIs & Services → Enable).",
    ))

    blocking = proj.denied_org_policies & set(lab.get("required_policies", []))
    checks.append(Check(
        id="org_policy", name="No blocking org policies", ok=not blocking,
        remediation="" if not blocking else
        "Org policy blocks this lab: " + ", ".join(sorted(blocking)) +
        ". Corporate orgs usually deny this — use a personal project instead.",
    ))

    need = lab.get("quota_needed", {})
    short = {k: v for k, v in need.items() if proj.quotas.get(k, 0) < v}
    checks.append(Check(
        id="quota", name="Sufficient quota", ok=not short,
        remediation="" if not short else
        "Quota too low for: " + ", ".join(short) +
        ". Request an increase or use a fresh personal project.",
    ))

    estimate = float(lab.get("credit_estimate_usd", 0.0))
    checks.append(Check(
        id="credit", name=f"Credit estimate ${estimate:.2f}", ok=True,
        remediation="This module runs entirely on the always-free tier.",
    ))

    return {
        "ok": all(c.ok for c in checks),
        "checks": [c.to_dict() for c in checks],
        "credit_estimate_usd": estimate,
    }
