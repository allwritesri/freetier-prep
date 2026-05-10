---
stepsCompleted:
  - step-01-init
  - step-01b-continue
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
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
