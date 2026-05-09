---
stepsCompleted:
  - step-01-init
  - step-01b-continue
  - step-02-discovery
  - step-02b-vision
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
