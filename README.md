# freetier-prep

Hands-on cloud cert-prep labs that run in the **student's own GCP account**,
with state-driven Terraform teardown, outcome-based task validation, and a
signed Terraform portfolio artifact. See
`_bmad-output/planning-artifacts/` for the product brief and PRD.

## Run the MVP loop locally (dev mode)

Dev mode runs the entire loop against an in-process fake GCP — no
credentials, no network:

```bash
./app/run.sh          # serve on http://localhost:8000
./app/run.sh test     # run the E2E test suite
```

Then in the browser: connect with any email → pre-flight checks → Start Lab
→ work the 12 tasks (each has a dev-mode "do it" button that performs the
console action, and a "validate" button that runs the outcome validator) →
End Lab → watch resources drop to zero → follow the transcript link to the
public verify page. Artifacts land in `app/var/out/<user>/first-vpc/`.

## What's real vs simulated in dev mode

| Piece | Dev mode |
|---|---|
| Provisioning / teardown engine, TTL timer, escalation, force-sweep | Real code paths |
| Outcome validators (reachability, least-privilege, config) | Real, run against fake GCP |
| Ed25519 transcript signing + verify endpoint | Real cryptography |
| Terraform HCL artifact | Real HCL, emitted to the artifact repo |
| GCP itself | `fake_gcp.py` simulates projects, resources, org policies, billing |
| Account connection | `DevConnector`; production `WIFConnector` (Workload Identity Federation) is stubbed |
| terraform binary | Not required; `SimulatedProvisioner` writes terraform-state-shaped JSON into the (fake) student bucket |

Trust rules hold even in dev: the platform DB stores only the session
manifest — Terraform state lives in the student's bucket, and teardown only
ever touches resources labeled `freetier-prep-session=<id>`.
