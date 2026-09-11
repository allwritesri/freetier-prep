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

## Own-account mode: run against YOUR real GCP project

Real mode provisions **real infrastructure with real Terraform** into your
own project, using your local Application Default Credentials — no key
files, no WIF ceremony needed when you operate the app yourself.

**Prerequisites** (on your machine):

1. `gcloud auth application-default login`
2. `terraform` installed (first `terraform init` downloads the Google
   provider, so the machine needs registry.terraform.io access)
3. A personal project with billing linked and APIs enabled:
   `gcloud services enable compute.googleapis.com iam.googleapis.com storage.googleapis.com`

**Run:**

```bash
FTP_MODE=real FTP_PROJECT=<your-project-id> ./app/run.sh
```

What changes vs dev mode:

- Pre-flight really checks billing, enabled APIs, and the terraform binary
  before anything provisions.
- Start Lab runs `terraform apply` of the base module (custom VPC, subnet,
  e2-micro VM, and the deliberately over-permissive firewall rule). State
  goes to `gs://freetier-prep-state-<project>/sessions/<id>/` in **your**
  bucket (override with `FTP_STATE_BUCKET`).
- The "do it (dev)" buttons disappear — you do the tasks in your **real
  GCP console**, then hit validate; validators read your project's live
  firewall rules, subnets, IAM policy, bucket config.
- End Lab / TTL runs `terraform destroy`, then sweeps any surviving
  lab-created resources and surveys for zero. In real GCP,
  networks/firewalls can't carry labels, so the sweep boundary is the
  lab's fixed `ftp-lab-*` name set — it never touches anything else.

**First-run safety checklist** (the product's own zero-surprise-bill bar):

- Use a personal project, not your employer's org (org policies commonly
  block pieces of this, and the pre-flight will tell you).
- Set a budget alert on the project first
  (Billing → Budgets & alerts → $1 threshold is fine).
- The module is sized for the always-free tier (e2-micro, no external
  services), but watch the first full Start → End cycle to completion and
  confirm the console shows zero `ftp-lab-*` resources at the end.
- If teardown ever fails, `/ops` shows the escalation with the exact
  resource manifest and a force-sweep button; everything is also
  deletable by hand — every resource starts with `ftp-lab-`.

Real mode has not been exercised against live GCP from CI — the loop
logic is E2E-tested in dev mode, HCL parses clean, and the REST reads are
best-effort verified. Treat your first run as a supervised one.
