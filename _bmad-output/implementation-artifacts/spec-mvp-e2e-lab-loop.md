---
title: 'MVP E2E lab loop'
type: 'feature'
created: '2026-09-02'
status: 'draft'
context:
  - '{project-root}/_bmad-output/planning-artifacts/prd.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** freetier-prep has planning artifacts but zero code. The wedge claim (real-account labs with trustworthy auto-teardown) is unproven until the full loop runs end-to-end.

**Approach:** Build the MVP loop as a runnable Python app: connect a GCP project → pre-flight gate → provision the "Your first VPC" lab → 12 outcome-validated tasks → End Lab or TTL → state-driven teardown with zero-resource verification → Ed25519-signed transcript + Terraform artifact + public verify page. Dev mode runs against an in-process fake GCP so the loop works locally with no credentials; provisioner and connector are interfaces so real Terraform/WIF drop in later.

## Boundaries & Constraints

**Always:** Platform DB stores only the session manifest (user, project, session, state-bucket URI, TTL, status) — never Terraform state or resource IDs; state lives in the (fake) student bucket. Teardown must converge to zero session-labeled resources or escalate loudly — silence is unacceptable. All provisioned resources carry a `freetier-prep-session=<id>` label; teardown/sweep touches only labeled resources. Validators check outcomes (reachability, least-privilege, config-meets-requirement), never bare existence. One active session per project. Boring tech: FastAPI, SQLite (stdlib), Jinja2, pytest; one command to run, one to test.

**Ask First:** Adding any dependency beyond fastapi/uvicorn/pytest/httpx. Implementing the real TerraformProvisioner or real WIF connector (out of MVP dev scope — stubs only).

**Never:** No long-lived key handling anywhere, even simulated. No sandbox-lab mode. No payment/marketplace/multi-cloud code. No storing fake-GCP cloud state in the platform DB (it lives in the FakeGCP service, playing the student's account).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | connect → preflight pass → start → complete 12 tasks → End Lab | Zero session resources in fake GCP; signed transcript; artifact repo emitted; verify page returns valid | N/A |
| Pre-flight gate | Project with billing unlinked / API disabled / blocking org policy | Start blocked; per-check human-readable remediation; nothing provisions | Each failed check named |
| Walk-away TTL | Active session, clock passes TTL | Auto-teardown fires; zero-resource verification; notification recorded; progress preserved | Teardown retries then escalates |
| Resume | Torn-down session with saved progress | Re-provision; task progress restored at last validated task | N/A |
| Teardown failure | Poisoned resource delete fails | Retries, then escalation record + notification with resource manifest; force-sweep endpoint converges to zero | Session marked `teardown_failed`, never silently dropped |
| Validator reject | Task attempted with wrong outcome (e.g. SSH open to 0.0.0.0/0) | Check fails with outcome-based explanation; retry allowed | N/A |
| Verify tampered | Transcript payload altered | Verify page reports invalid signature | N/A |

</frozen-after-approval>

## Code Map

Greenfield — all files new, rooted at `app/`.

- `app/freetier_prep/main.py` -- FastAPI app factory, routes (connect, preflight, start, tasks, validate, end, resume, verify, ops), startup wiring
- `app/freetier_prep/config.py` -- env-driven settings (mode, db path, key path, TTL seconds)
- `app/freetier_prep/db.py` -- SQLite manifest store: users, sessions, task_progress, transcripts, notifications
- `app/freetier_prep/fake_gcp.py` -- simulated GCP: projects, resources w/ labels, org policies, billing flag, poison flags for failure injection; the "student's account + console API"
- `app/freetier_prep/connector.py` -- Connector interface; DevConnector (fake project grant); WIFConnector stub raising NotImplemented
- `app/freetier_prep/preflight.py` -- gate: billing linked, APIs enabled, org policy, quota, $0 credit estimate; returns per-check results
- `app/freetier_prep/provisioner.py` -- Provisioner interface; SimulatedProvisioner (applies lab resource graph into fake GCP, writes terraform-state-shaped JSON to fake student bucket); TerraformProvisioner stub
- `app/freetier_prep/labs/first_vpc.py` -- lab module: resource graph (VPC, subnet, firewall rules, e2-micro VM, IAP SSH), 12 task definitions with validator specs + HCL artifact template
- `app/freetier_prep/validators.py` -- outcome validators reading fake GCP (reachability, least-privilege, config-meets-requirement)
- `app/freetier_prep/teardown.py` -- state-driven destroy from student-bucket state, zero-resource verification by session label, retry → escalate, force-sweep
- `app/freetier_prep/ttl.py` -- TTL scheduler with injectable clock (tests advance time)
- `app/freetier_prep/signing.py` -- Ed25519 keypair (generated at var/keys on first run), canonical-JSON transcript sign/verify
- `app/freetier_prep/artifacts.py` -- emit Terraform repo (real HCL) + signed transcript JSON to `var/out/<user>/` (simulated GitHub)
- `app/freetier_prep/web/*.html` -- Jinja2: connect, dashboard, lab (tasks + validate buttons), verify page
- `app/tests/test_e2e_happy.py`, `test_e2e_walkaway_ttl.py`, `test_e2e_teardown_failure.py` -- E2E via in-process ASGI client
- `app/requirements.txt`, `app/run.sh`, `README.md` update -- one-command run (`./app/run.sh`) and test (`./app/run.sh test`)

## Tasks & Acceptance

**Execution:**
- [ ] `app/freetier_prep/{config,db,fake_gcp}.py` -- foundation: settings, manifest schema, fake GCP with labels/policies/poison -- everything else depends on these
- [ ] `app/freetier_prep/{connector,preflight}.py` -- dev connect + pre-flight gate returning named checks -- gate before any provisioning
- [ ] `app/freetier_prep/labs/first_vpc.py` -- resource graph + 12 tasks + HCL template -- single source of truth for module content
- [ ] `app/freetier_prep/{provisioner,validators}.py` -- simulated apply writing state to student bucket; outcome validators -- core loop mechanics
- [ ] `app/freetier_prep/{teardown,ttl}.py` -- destroy-from-state, zero-verify, retry/escalate/force-sweep, injectable-clock TTL -- the zero-surprise-bill engine
- [ ] `app/freetier_prep/{signing,artifacts}.py` -- Ed25519 transcript + Terraform repo emission -- the credential
- [ ] `app/freetier_prep/main.py` + `web/` -- routes + minimal UI wiring the loop -- makes it runnable/demoable
- [ ] `app/tests/*` -- three E2E tests covering matrix rows -- proof the loop works
- [ ] `app/run.sh`, `app/requirements.txt`, `README.md` -- one-command run/test + quickstart docs

**Acceptance Criteria:**
- Given a fresh clone with Python 3.11, when `./app/run.sh test` runs, then all E2E tests pass with no network access or credentials.
- Given `./app/run.sh`, when a browser hits `/`, then the full loop (connect → start → validate tasks → end → verify transcript link) is completable by hand in dev mode.
- Given any completed-or-torn-down session, when the platform DB is inspected, then it contains manifest rows only — no Terraform state, no resource IDs.
- Given a teardown that cannot converge, when retries exhaust, then a notification + escalation record exists and `/ops` shows the session as `teardown_failed` with its resource manifest.

## Design Notes

Interfaces (`Connector`, `Provisioner`) isolate everything that touches real GCP; dev mode binds Dev/Simulated impls, so swapping in WIF + real Terraform later changes wiring, not the loop. FakeGCP is deliberately a standalone service object with its own store — it *is* the student's account, keeping the platform-side "no state" rule honest even in dev. TTL uses an injectable clock so E2E tests advance time instead of sleeping. Transcript signature binds the platform's attestation (user, module, task outcomes, date) and only references the artifact repo — verification never depends on student-owned mutable files.

## Verification

**Commands:**
- `cd app && ./run.sh test` -- expected: pytest green, 3 E2E files, exit 0
- `cd app && ./run.sh` -- expected: uvicorn serves on :8000; manual loop completable

**Manual checks (if no CLI):**
- `var/out/<user>/` contains `main.tf` + `transcript.json` after a completed lab; `/verify/<id>` shows valid; tampering the JSON flips it to invalid.
