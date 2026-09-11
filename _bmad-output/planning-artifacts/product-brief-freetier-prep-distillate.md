---
title: "Product Brief Distillate: freetier-prep"
type: llm-distillate
source: "product-brief-freetier-prep.md"
created: "2026-04-25T06:00:00Z"
purpose: "Token-efficient context for downstream PRD and architecture creation"
---

# Product Brief Distillate — freetier-prep

Companion to the executive brief. Captures everything surfaced during discovery that didn't fit the 1-2 page format but is needed for PRD and architecture work.

## Core Wedge (one sentence)

Hands-on cloud cert-prep labs that run in the **student's own GCP account** with **state-driven Terraform teardown** — every lab leaves the student with a real Terraform repo and signed completion transcript on their GitHub.

## Personas

### Primary (MVP): GCP Associate Cloud Engineer (ACE) candidate
- 24-35yo self-taught dev or career-changer
- Often has prior AWS/Azure exposure; switching to GCP because target employer runs on GCP
- 4-8 weeks from exam date; theory-rich, hands-on-poor
- Has practice-exam fatigue; bought Coursera or YouTube ACE content
- Aha moment: real GCE instances appear in their own console, then disappear cleanly on teardown
- Will pay $5-10 for full cert track post-MVP (price floor; needs willingness-to-pay validation)

### Secondary (v2-v3): indie cloud instructor
- Already produces cert content (YouTube, blogs, Udemy)
- Wants a marketplace to publish hands-on labs alongside videos
- Earns rev-share when their modules get consumed
- Served when the marketplace ships post-MVP

## Scope Signals (in/out/maybe)

### In MVP (Phase 0)
- Single lab module: *"Your first VPC — networks, instances, and secure SSH"*
- 10-12 outcome-validated tasks
- GCP only, ACE track only
- Workload Identity Federation account connection
- Provisioning + Terraform-state-driven teardown
- Pre-flight credit estimate display
- Auto-commit Terraform artifact to student's GitHub
- Signed completion transcript
- Free service (no payment infra)

### Deferred to v2 (gated on MVP loop validating)
- Full ACE module set (8-12 modules)
- Paid plans ($5-10 per cert track)
- Beginning AWS expansion (separate launch with proven engine)
- Professional Cloud Architect (PCA) track
- Instructor authoring beta (10-20 curated indie creators)
- Validity-score engine for instructor-uploaded labs

### Deferred to v3+
- Open marketplace at scale
- Multi-cloud (AWS, Azure)
- Hiring-side flywheel (companies subscribe to verify candidate transcripts)
- Cost-safety engine as standalone licensable primitive (B2B2C: bootcamps, universities, enterprise L&D)

### Explicitly out of scope (reject if re-proposed)
- Sandbox-only labs (defeats the wedge — same as KodeKloud/ACG/Qwiklabs)
- Long-lived service-account keys / access keys (security regression; ICP is taught not to share keys)
- Insurance / SLO / cost-overage refund program (founder doesn't want liability; engineering rigor instead of marketing promise)
- Cost-safety primitives marketed as guarantees (engineered for, not promised)
- Cloud Practitioner (CCP) as launch cert (was considered when restricted to free-tier-only services; rejected because $300 GCP credit covers ACE-level paid services)
- Mobile app at MVP
- Enterprise / team accounts at MVP
- Storing Terraform state on platform side (rejected: trust-positioning conflict; state lives in student's bucket)
- Sweeper as primary teardown (rejected: state-driven destroy is canonical; sweeper deferred entirely from MVP)

## Technical Context

### Cloud + cert
- **Cloud**: GCP at launch. AWS deferred to v2.
- **Cert track**: Associate Cloud Engineer (ACE).
- **Free-tier envelope**: $300 / 90-day GCP credit + always-free tier (e2-micro, 5GB Cloud Storage, Cloud Run free tier, etc.). Sufficient for full ACE curriculum even with paid services included.
- **Edge case**: returning GCP users may have $0 credit. Pre-flight credit check at onboarding surfaces this transparently; not a blocker, just a UX flag.

### Trust & onboarding
- **Account connection**: Workload Identity Federation. Short-lived OIDC tokens (1-12 hour expiry). Never long-lived keys, never service-account-key JSON files.
- **IAM transparency**: exact bindings the platform requests are public in a GitHub repo, linked from the connect screen.
- **Per-module least privilege**: bindings scoped per-lab, not a single standing role.

### State management
- **State backend**: GCS bucket in the **student's** GCP project (not platform side). Pattern: `gs://freetier-prep-<student-uuid>-state/sessions/<session-id>/terraform.tfstate`
- **Bucket lifecycle**: created once on first-time setup. Persists across sessions. Versioning enabled. Encryption at rest, with student-controllable CMEK option. Lifecycle rules to clean up state files for torn-down sessions after 30 days.
- **Platform side stores only**: session manifest = `{user_id, project_id, session_id, state_bucket_uri, lab_template_id, ttl, status}`. No Terraform state, no resource IDs, no IPs.

### Provisioning + teardown
- **Provisioning**: Terraform applied from platform control plane using the OIDC token. State written to student's bucket. Resources tagged `freetier-prep-session=<id>` (cheap, useful for billing analytics; not used by sweeper at MVP).
- **Teardown**: `terraform destroy` against the state in the student's bucket. State-driven, single mechanism.
- **No sweeper at MVP**: deferred. Manual support handles edge cases (revoked role mid-session, state corruption, partial failures).
- **Provisioning target**: < 60 seconds end-to-end for the launch module.

### Validation
- **Outcome-based, not resource-existence-based.** Examples of validation logic:
  - "Service is reachable from the correct network"
  - "IAM bindings are least-privilege (no overly-broad roles granted)"
  - "Configuration meets the stated requirement (e.g., firewall rule rejects external SSH but allows IAP-tunneled SSH)"
- Each task has its own validator. Validators run in the platform control plane against the student's project via the OIDC token.

### Engineering capacity assumption
- AI-assisted development (Claude Code + BMAD methodology). Solo founder. Build-order priority: teardown engine first, then one module wired through, then expand.

## Competitive Intelligence (preserve from research)

### Direct competitors
- **Qwiklabs / Google Cloud Skills Boost**: Google-owned, dominant first-party for GCP labs. Sandboxed (their accounts), no BYOC. The incumbent for GCP cert-prep labs specifically.
- **KodeKloud**: Browser-based hands-on labs. GCP content present but sandboxed. Forum sentiment: stale labs, broken validators, "next-next-finish" tasks.
- **A Cloud Guru / Pluralsight**: GCP content present, sandboxed, criticized as "too hand-held," doesn't transfer to real-job IAM/networking realities.
- **Whizlabs**: GCP cert content; reviews cite outdated content and shallow validation.
- **Instruqt**: Authoring + delivery for vendor DevRel teams. Sells to enterprises/vendors, not individual cert learners. Sandboxed.

### Adjacent / non-competitive
- AWS Skill Builder Builder Labs (AWS first-party, AWS only, doesn't apply to GCP launch)
- LocalStack (simulator, not real cloud)
- Coursera / Udemy hands-on (sandboxed, vendor-managed)

### Why no third-party BYOC GCP cert-prep platform exists today
- GCP cert volume is ~1/5 to 1/10 of AWS volume → less attractive to incumbents
- Qwiklabs has Google distribution → kills third-party economics in sandboxed segment
- BYOC requires solving cost-safety + trust onboarding, which has been hard until OIDC/WIF maturity
- **This is the wedge**: BYOC is now technically feasible, and the dominant player (Qwiklabs) doesn't do it

## Market Context

- Cloud cert-prep market: ~$16-18B globally, ~12-14% CAGR per Gartner / HolonIQ (2024)
- Pluralsight 2024 State of Cloud: 75% of leaders cite cloud skills gap as a primary blocker, up from 66% in 2023
- AWS, Azure, GCP cert volumes growing double-digits annually into 2025
- Coursera / Udemy 2024 earnings: hands-on / lab-based learning called out as fastest-growing segment
- 2024-2025 hiring trend: employers demanding "show me you've actually built it" — GitHub repos, Terraform portfolios, real console screenshots — over cert paper

## Strategic Bets (from Stage 4 elevation, named in brief)

1. **Hiring-market accountability becomes a category.** Theory courses sell hours watched; freetier-prep sells jobs landed. North Star measurable; if it proves out, the company stops being a study tool and becomes infrastructure for cloud hiring.
2. **Cost-safety engine is a future product, not just a feature.** The Terraform orchestration + budget guardrails could be licensed standalone to bootcamps, universities, enterprise L&D. v3+ wedge.
3. **AWS partnership window is real but time-limited.** July 2025 AWS Free Tier overhaul created confusion freetier-prep solves. Co-marketing motion reachable with traction. Decision point: month 9-12 of v2 AWS launch.

## Strategic Opportunities Considered but Parked (not in brief)

- **Cert-prep creator partnerships** (Maarek, Cantrill, TutorialsDojo): bundle hands-on layer with their existing content, rev-share. Distribution channel worth pursuing post-MVP.
- **Bootcamp / university B2B2C** licensing of the cost-safety engine: separate motion, defer until v2+.
- **AWS Marketplace SaaS Contract listing**: trust signal, AWS billing integration. Reachable post-AWS-expansion.
- **Read-only "Lab 0"** (observe a pre-built reference architecture before connecting provisioning role): considered as Decision 2 option, not adopted because student is willing to grant the role; revisit if MVP onboarding conversion is poor.

## Open Questions Requiring PRD/Architecture Resolution

- Exact IAM bindings for the cross-account role — needs publishable spec
- North Star measurement protocol — survey cadence, control cohort definition, LinkedIn integration scope
- Lab template format / DSL (instructor authoring deferred to v2, but the format choice constrains v1 lab definition)
- Validation engine design — how generic is it? Can it grow without per-lab custom code?
- Validity-score engine for v2 — methodology, ML / heuristics / human review
- Pricing willingness-to-pay validation method (smoke-test landing page? actual launch at $5 vs $10?)
- Pre-MVP smoke-test for landing→connect funnel (skeptic recommended; founder may or may not adopt)
- AWS expansion timing and architectural deltas (Workload Identity → IAM cross-account role; GCS state → S3 state)
- Cert-prep partnerships — outreach plan, rev-share terms

## Success Metrics (from brief, restated for downstream use)

### North Star (12 months)
- 2x cloud-job placement rate vs. theory-only courses (control: common ACE Coursera/YouTube cohorts)

### Operational metrics (12 months)
- Module completion rate ≥ 60% (industry baseline: 15-25%)
- Zero teardown-failure incidents resulting in surprise bills
- NPS ≥ 60 for cohort completing the launch module

### Leading indicators (12 months)
- 2,000+ GCP accounts connected
- 500+ launch-module completions
- ≥ 40% of users referred by previous user

### Near-term proxy for North Star (job-placement signal lags 6-12 months)
- Completion rate of an interview-style mock-scenario walkthrough at end of cert track

## Founder Context (not in brief)

- **Solo founder**, AI-assisted development capacity (Claude Code + BMAD)
- **Existing audience / training brand**: not yet established (greenfield product)
- **Funding**: bootstrapped at MVP stage
- **Pacing implication**: scope discipline is the binding constraint; one module at MVP is non-negotiable

## Brand / Voice Notes

- **Honest over aspirational**: "we engineer for the leak never to happen" is preferred to "guaranteed no surprise bills"
- **Trust-as-feature**: public IAM repo, no long-lived keys, state in student's bucket — these are positioning assets, not engineering footnotes
- **Outcome-anchored**: "students land cloud jobs" is the headline frame, not "students pass exams"
