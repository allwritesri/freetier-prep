---
stepsCompleted:
  - step-01-init
  - step-01b-continue
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
  - step-03-success
inputDocuments:
  - _bmad-output/planning-artifacts/product-brief-freetier-prep.md
  - _bmad-output/planning-artifacts/product-brief-freetier-prep-distillate.md
workflowType: 'prd'
documentCounts:
  briefs: 2
  research: 0
  brainstorming: 0
  projectDocs: 0
projectType: greenfield
classification:
  projectType: developer_tool
  domain: edtech
  complexity: high
  projectContext: greenfield
  rationale: >-
    Party-mode roundtable converged on developer_tool over web_app/saas_b2b.
    JTBD is producing a verifiable Terraform portfolio artifact plus cloud
    reps that get the student hired (developer outcome). Multi-surface
    product (web app + GCP console + CLI + GitHub). Edtech retained as
    secondary tag for GTM clarity and outcome-language in stories;
    edtech-regulatory weight (FERPA/COPPA) intentionally excluded — ICP
    is adult learners. Complexity high, re-scoped from "trust + cost-safety
    + cloud orchestration" to adversarial blast-radius management in
    someone else's cloud account, idempotent state reconciliation under
    a <60s provisioning budget, with a signed-artifact supply chain.
customRequiredSections:
  - id: cross_account_trust_and_blast_radius_spec
    purpose: WIF trust policy, exact IAM scopes, threat model, revoke path
  - id: cost_safety_and_teardown_convergence
    purpose: Cost ceilings, idempotent teardown, orphan detection, partial-failure handling
  - id: provisioning_slo_and_validation_harness
    purpose: <60s provisioning budget decomposed, outcome-validation contract per task, artifact signing/provenance
  - id: state_ownership_and_portability
    purpose: State in student's GCS bucket, lock-in/portability story, deletion-mid-lab handling
---

# Product Requirements Document - freetier-prep

**Author:** Root
**Date:** 2026-04-29

## Executive Summary

freetier-prep is a hands-on cloud cert-prep platform that runs real lab infrastructure inside the **student's own GCP account**, with state-driven Terraform teardown that leaves the account empty and the student's GitHub holding a signed Terraform portfolio they actually own. The MVP is a single Associate Cloud Engineer (ACE) lab module — *"Your first VPC: networks, instances, and secure SSH"* — provisioned via Workload Identity Federation in under 60 seconds, validated against outcome-based checks (not "resource exists"), and torn down on End Lab or hard timer.

The cloud cert-prep stack is structurally misaligned with what hiring managers reward in 2025. Theory courses produce paper credentials. Sandbox labs (Qwiklabs, KodeKloud, A Cloud Guru) produce vendor-managed playgrounds that vanish on logout. Hiring managers want *"show me you've actually built it"* — Terraform repos, real console history, evidence of cloud judgment in a real account. No incumbent product makes that easy; learners who try BYOC on their own quit during setup. freetier-prep closes the loop with three load-bearing capabilities — federated trust without long-lived keys, dual-channel auto-teardown, and outcome-validated tasks — so the student finishes with the artifact employers actually look at.

**Primary user (MVP):** the GCP ACE candidate — a 24-35-year-old self-taught developer or career-changer, often with prior AWS/Azure exposure, 4-8 weeks from exam date, theory-rich and hands-on-poor. **North Star:** 2x cloud-job placement rate vs. theory-only ACE courses (12-month measurement). The 24-month arc gates each stage on the prior step earning trust: launch module → full ACE track → AWS expansion + instructor-authoring beta → cross-cloud marketplace + hiring-side flywheel where employers verify signed transcripts. The downstream destination is *credentialing infrastructure for cloud hiring*; the discipline rule is shipping one trust-earning lab first.

### What Makes This Special

The product is structurally different from sandbox-lab incumbents along three dimensions, each compounding into a moat:

1. **BYOC is the wedge.** Real GCP console, real `gcloud`, real IAM boundaries, real billing context — the muscle memory transfers to day one of the cloud job. Every incumbent runs hands-on in their own sandbox; Qwiklabs (Google's first-party) won't ship BYOC because it cannibalizes their managed-environment economics. WIF/OIDC maturity has only recently made BYOC technically feasible without long-lived service-account keys, which is the structural reason no third-party BYOC GCP cert-prep exists today.

2. **The artifact is the credential.** Each completed lab auto-commits a Terraform repo to the student's GitHub plus a cryptographically signed completion transcript. Hiring managers verify in 10 seconds that the candidate shipped real infrastructure on a real account. The product stops being a study tool and becomes a verifiable hiring credential — a category bet adjacent to Sigstore-style provenance and Triplebyte-style screening, not Coursera.

3. **Trust posture is a product feature, not a footnote.** Public IAM bindings repo, no long-lived keys ever, scoped per-module least-privilege, Terraform state in the *student's* GCS bucket (not platform-side). These positioning assets earn the right to ask for a WIF binding into a billing account. The dual-channel teardown engine — state-driven `terraform destroy` is the canonical mechanism at MVP — is engineered for zero-leak ("we engineer for the leak never to happen") and is built first, before any lab content.

**Core insight:** the cert-prep stack's structural failure isn't content quality, it's artifact production. Theory-only and sandbox-only both produce credentials that don't transfer. BYOC plus engineered cost-safety is the only configuration that closes the loop — and it's the configuration the dominant incumbent structurally won't ship.

**Aha moment:** Click Start → real GCE instances appear in the student's own GCP console in <60s → 10-12 outcome-validated tasks against real infra → click End Lab → refresh the console → zero resources → check GitHub → signed Terraform repo waiting. They've done real work, safely, with proof.

**Structural margin advantage:** ~95%+ gross margin because students bring the compute. Competitors burning cash on managed sandboxes cannot match the pricing flexibility long-term.

## Project Classification

| Dimension | Value | Notes |
|---|---|---|
| **Project Type** | `developer_tool` (primary) | JTBD = produce a verifiable Terraform portfolio artifact + cloud reps that get the student hired. Multi-surface product spanning a thin web control plane, the student's GCP console, `gcloud`/CloudShell, and GitHub. The web app is the orchestrator, not the product. |
| **Domain** | `edtech` (secondary) | Retained for go-to-market clarity, learner-language in copy, and outcome-vocabulary in stories ("task validated" not "endpoint returns 200"). Edtech-regulatory weight (FERPA, COPPA) intentionally excluded — ICP is adult learners, no K-12 surface. |
| **Complexity** | `high` | Driver is not edtech-regulatory but adversarial blast-radius management in someone else's cloud account: idempotent state reconciliation, federated trust scoping, signed-artifact supply chain, all under a <60s provisioning budget and a zero-tolerance teardown SLO. |
| **Project Context** | `greenfield` | No existing system, no migration burden, scope discipline is the binding constraint (solo founder, AI-assisted dev). |

**Custom required PRD sections** (grafted onto the developer_tool template because the vanilla template assumes vendor-owned state and locally-installed surface area):

1. **Cross-Account Trust & Blast-Radius Spec** — WIF trust policy, exact IAM scopes requested in the student's project, what the platform *cannot* do by construction, audit log surface, revoke path, and threat model (compromised platform credential, malicious lab module, mid-run revocation).
2. **Cost-Safety & Teardown Convergence** — per-lab cost ceiling, budget-alert wiring into the student's project, idle detection, teardown idempotency and convergence guarantees, orphaned-resource detection, partial-failure handling. *Zero* teardown-failure-resulting-in-surprise-bill incidents is a North Star input, not a stretch goal.
3. **Provisioning SLO & Validation Harness** — <60s cold-start budget decomposed (auth, plan, apply, validate), the per-task outcome-validation contract (reachability, least-privilege IAM, configuration-meets-requirement — not just resource existence), retry/idempotency on provisioning, failure taxonomy.
4. **State Ownership & Portability** — state lives in `gs://freetier-prep-<student-uuid>-state/sessions/<session-id>/terraform.tfstate` in the *student's* project, with versioning, encryption at rest, optional CMEK, and 30-day lifecycle cleanup. Lock-in/portability story, deletion-mid-lab handling, recovery from corrupt state.

## Success Criteria

### User Success

A student who completes the MVP module experiences three measurable wins, in this order:

1. **First-time setup converts.** They finish the WIF connection ceremony and arrive at the lab launch screen **in under 5 minutes**, without dropping off. The brief identifies setup friction as the failure mode that kills DIY-in-own-account learners; this is the highest-leverage funnel point at MVP.
2. **They produce real artifacts they can show an employer.** At lab end, the Terraform repo and signed transcript land in their GitHub. ≥95% of completions produce a clean repo (no commit failure, no push failure, signature verifies) — provisional engineering target, to be firmed at NFR definition.
3. **They feel safe doing it.** Zero surprise-bill incidents in the first 200 completions. The End Lab → "zero resources" verification holds without manual support intervention.

The emotional success moment is the brief's **aha**: refresh the GCP console post-teardown → zero resources → refresh GitHub → signed Terraform repo waiting. That sequence is what we instrument; if it doesn't happen, nothing else matters.

### Business Success

**North Star: 2x cloud-job placement rate vs. theory-only ACE courses** at 12 months. Measured by surveying users 3 and 6 months post-completion against a control cohort from common theory-only ACE courses (self-reported, augmented by LinkedIn signal where consented).

**Why this metric, not the obvious alternatives:**

- *Exam pass rate* — every incumbent instruments this; correlates poorly with workplace performance; doesn't distinguish freetier-prep from sandbox labs.
- *Hours watched* — theory-course metric; adopting it loses the category bet.
- *Module completion rate* — leading indicator, not North Star (see below).

**Near-term proxy** (because job-placement signal lags 6–12 months): completion of an **end-of-track interview-style mock-scenario walkthrough**. Correlates with workplace performance more reliably than pass rate. Ships once ≥3 modules exist.

**12-month operational metrics:**

| Metric | Target | Industry baseline |
|---|---|---|
| Module completion rate | ≥ 60% | 15–25% |
| Teardown-failure incidents resulting in surprise bills | **0** (not "low") | n/a — competitors don't expose users to this |
| NPS (launch-module cohort) | ≥ 60 | n/a |

**12-month leading indicators:** 2,000+ GCP accounts connected; 500+ launch-module completions; ≥40% of users acquired via referral.

### Technical Success

The four grafted PRD sections (cross-account trust, cost-safety/teardown, provisioning SLO, state ownership) earn their keep here. Technical success isn't parallel to user/business success — it gates them.

| Capability | Success criterion | Why it matters |
|---|---|---|
| **Provisioning SLO** | p95 cold-start (auth → plan → apply → "ready") **< 60s**; p99 < 90s | Sub-minute is the brief's commitment; over-budget kills the wedge |
| **Teardown convergence** | **Zero** resource-leak incidents resulting in surprise bills; idempotent + resumable; orphan detection on every End Lab | Single failure mode that kills word-of-mouth and the company |
| **Trust posture** | Zero long-lived service-account keys; WIF tokens expire ≤12h; per-module IAM bindings public in linked GitHub repo | Earns the right to ask for a binding into a billing account |
| **Validation depth** | 100% of MVP tasks validate against outcome-based checks (reachability / least-privilege / configuration-meets-requirement) — not "resource exists" | Differentiates from sandbox-incumbent shallow validators |
| **Artifact integrity** | 100% of completions emit signed transcript + Terraform repo to student's GitHub; signature verifiable by hiring manager in <10s | The credential is the moat; signature failure breaks the category bet |

### Measurable Outcomes

Single-line targets, by horizon:

- **3-month (post-MVP launch):** 200 unique GCP accounts connected; 100 launch-module completions; 0 surprise-bill incidents; teardown loop validated under failure injection.
- **6-month:** 1,000 connections; 250 completions; ≥40% completion rate (en route to ≥60%); first signed-transcript verification by an external hiring manager.
- **12-month:** 2,000+ connections; 500+ completions; ≥60% completion rate; NPS ≥60; North Star measurement cohort started; ≥40% referral acquisition.

## Product Scope

### MVP - Minimum Viable Product

The discipline rule from the brief: *if it isn't required to validate the wedge claim — "one real-account hands-on GCP lab that ACE candidates trust enough to grant a Workload Identity binding to" — it does not belong in MVP.*

**In:**

- One lab module: *"Your first VPC: networks, instances, and secure SSH"* (10–12 outcome-validated tasks, runs entirely on GCP always-free tier)
- GCP-only, ACE track only
- Workload Identity Federation account connection (short-lived OIDC tokens, never long-lived keys)
- Provisioning engine (Terraform-based control plane)
- Outcome-validation engine (per-task validators run from platform against student's project via OIDC token)
- State-driven Terraform teardown (canonical mechanism; sweeper deferred entirely from MVP)
- Pre-flight credit estimate displayed before lab start
- Signed completion transcript + auto-commit Terraform artifact to student's GitHub
- Free service (no payment infrastructure)
- Manual support channel for incidents
- Public GitHub repo of the exact IAM bindings the platform requests

**Out** (deferred to v2 or explicitly rejected):

- Additional lab modules (ship only if module 1 proves the loop)
- Instructor authoring + marketplace + ratings + reviews
- Multi-cloud (AWS, Azure)
- Additional cert tracks (PCA, AWS SAA, Azure Admin)
- Paid plans, billing, subscription, rev-share infrastructure
- Enterprise / team accounts
- Mobile app
- Validity-score engine for instructor-uploaded content
- Cost-overage refund / insurance program (rejected — engineered for, not promised)
- Sweeper as primary teardown (rejected — state-driven destroy is canonical)
- Storing Terraform state platform-side (rejected — state lives in student's bucket; trust positioning)

### Growth Features (Post-MVP)

Gated on the MVP loop validating.

**Months 3–9:**

- Expand to 8–12 modules covering the full ACE blueprint
- Begin North Star measurement cohort (job-placement survey infrastructure)
- First paid track at $5–10 per cert track once content depth justifies it
- End-of-track interview-style mock-scenario walkthrough (near-term North Star proxy)

**Months 9–18:**

- Professional Cloud Architect (PCA) track
- Begin AWS expansion (separate launch with proven engine; AWS-credit-anxiety story still fresh post-July-2025 Free Tier overhaul)
- Instructor authoring beta — first 10–20 curated community instructors, validity-score gate

### Vision (Future)

18–36 months:

- Open marketplace at scale (instructor labs alongside videos, rev-share)
- Multi-cloud parity (AWS, Azure)
- Hiring-side flywheel: companies subscribe to verify candidate signed transcripts; product becomes infrastructure for cloud hiring rather than a study tool
- Cost-safety engine licensable as a B2B2C primitive to bootcamps, universities, enterprise L&D (v3+ wedge)
- Positioning destination: *"the Udemy of cloud labs and the de facto verifiable hands-on credential for cloud hiring"*
