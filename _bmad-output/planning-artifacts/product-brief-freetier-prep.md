---
title: "Product Brief: freetier-prep"
status: "complete"
created: "2026-04-25T04:49:23Z"
updated: "2026-04-25T06:00:00Z"
inputs:
  - "user conversation transcript (bmad-product-brief skill, 2026-04-25)"
  - "web research synthesis (Stage 2 contextual discovery)"
  - "review subagent findings (skeptic, opportunity, cost-safety/trust viability)"
companion: "product-brief-freetier-prep-distillate.md"
---

# Product Brief: freetier-prep

> **Outcome promise (north star):** *Our students land cloud jobs at 2x the rate of theory-only courses.*

## Executive Summary

**freetier-prep is the missing third leg of cloud certification training: real, hands-on labs that run inside the learner's own Google Cloud account, with auto-teardown so practice doesn't turn into a forgotten cluster.**

Cloud cert-prep candidates today choose between two broken options. They watch videos and grind practice exams (theory-heavy, doesn't transfer to the job) — or they pay for sandbox lab platforms (Qwiklabs / Google Cloud Skills Boost, KodeKloud, A Cloud Guru) that hand them a vendor-managed playground that vanishes when they log out. Neither builds the muscle memory the real GCP console actually demands of someone on day one of a cloud job. The learners who *do* try to lab in their own account get stuck on setup pain, leak resources, and quit.

freetier-prep solves this with a tight loop: connect a GCP account once via short-lived Workload Identity Federation tokens (no long-lived keys, ever); pick a lab; the platform provisions real infrastructure into *your* account in under 60 seconds; you complete 10-12 outcome-validated tasks against that real infra; you click End Lab — or walk away — and our auto-teardown engine cleans everything up. You leave with a real Terraform artifact and console history of what you built.

The launch hypothesis is deliberately narrow: **one lab module, end-to-end, for the GCP Associate Cloud Engineer track, free for the student to use.** If the loop earns trust on one module, we expand to a full curriculum. If it doesn't, we kill it cheap.

## The Problem

Cloud cert-prep is a $16-18B global market growing 12-14% annually. The dominant playbook produces paper credentials but not job readiness. Three pain points keep recurring across r/googlecloud, r/devops, G2 and Trustpilot:

1. **"Sandbox labs don't transfer to my real job."** Qwiklabs, KodeKloud, ACG all run their hands-on portion inside their own managed environments. Learners get a guided UI that doesn't match production GCP — no real IAM boundaries, no real billing console, no real CloudShell context. They pass the cert, start the job, and freeze the first time they open their employer's actual console.

2. **"Lab content is shallow and the validators are broken."** Forum sentiment on existing platforms is consistently that tasks are "next-next-finish" — they verify a resource exists but not whether the learner understood what they built. Outdated content and inconsistent grading erode trust.

3. **"Setting up my own GCP account from scratch is friction I never get past."** Learners want real-account practice but service account setup, Workload Identity, gcloud config, project structure, billing alerts, IAM bindings — the *meta-work* — eats their study time before they touch a single service. Most quit during setup.

The status quo cost is real: hiring managers in 2024-2025 increasingly demand "show me you've actually built it" — Terraform repos, real console screenshots, project history. Theory-only courses do not produce that. Sandbox labs do not produce that. The training stack is structurally misaligned with what employers reward.

## The Solution

**A guided cloud lab platform that runs inside your own GCP account, safely.**

The student experience:

1. **One-time setup (under 5 minutes).** Connect GCP via Workload Identity Federation. The platform requests a scoped, short-lived OIDC role — credentials expire in 1-12 hours and are never stored in our database. The exact IAM bindings we request are public, in a GitHub repo we link from the connect screen.
2. **Pick a lab.** Launch curriculum: GCP Associate Cloud Engineer (ACE).
3. **Click Start.** The platform provisions real infrastructure into your project in 30-60 seconds. A pre-flight credit estimate is shown upfront — for the launch module, that's $0.
4. **Do the work.** Walk through 10-12 hands-on tasks in your actual GCP console + gcloud CLI. Each task validates against real-world outcomes — not just "resource exists" but "service is reachable from the right network, IAM is least-privilege, the configuration meets the stated requirement."
5. **End cleanly.** Click End Lab — or walk away and the auto-teardown engine fires on a hard timer. The infra is destroyed; you keep the Terraform artifact in your GitHub.

Auto-teardown is not a marketing claim — it's load-bearing infrastructure. Built first, before any lab content, validated against the nastiest known delete-failure modes (orphaned disks, dependent IAM bindings, hung deletions). The student stays responsible for monitoring their own bill — we don't sell insurance, but we engineer for the leak never to happen.

## What Makes This Different

| | Sandbox labs (Qwiklabs, KodeKloud, ACG) | DIY in your own account | **freetier-prep** |
|---|---|---|---|
| Real cloud console muscle memory | ❌ vendor sandbox | ✅ | ✅ |
| Auto-teardown / no leaked infra | ✅ (their account) | ❌ | ✅ |
| Guided 10-12 task structure | ✅ (often shallow) | ❌ | ✅ |
| Validation depth | "Resource exists" | None | **Outcome-based** |
| Portfolio artifact in your account | ❌ | ✅ | ✅ + signed transcript |

Three compounding moats build over time:

1. **Outcome-based validation that correlates with job-readiness.** Every cohort of students who land jobs validates which task designs predict workplace performance. Sandbox-only competitors can't see this signal — they instrument exam pass rates; we instrument career outcomes.
2. **Signed portfolio artifacts.** Each completed lab generates a cryptographically signed transcript plus a Terraform repo committed to the student's GitHub. Hiring managers can verify in 10 seconds that this candidate actually shipped real infrastructure on their own account. We become not just a study tool but a *credential* in the hiring market.
3. **Structural gross-margin advantage.** Students bring the compute. Our gross margin is structurally ~95%+ — we never pay for sandbox infrastructure. Competitors burning cash on managed environments cannot match our pricing flexibility long-term.

## Who This Serves

**Primary user (MVP launch): the GCP Associate Cloud Engineer candidate.** A 24-35-year-old self-taught developer or career-changer. Often has prior AWS or Azure exposure but is going for GCP because their target employer runs on it. They've watched a Coursera or YouTube ACE course and have practice-exam fatigue. They're 4-8 weeks from their exam date. They feel theory-rich and hands-on-poor.

**Their "aha moment":** They click Start Lab, watch real Compute Engine instances appear in their own GCP console, work through the lab, click End Lab, refresh the console, and see *zero resources*. They realize they can finally practice for real, safely.

**Secondary user (v2-v3): the indie cloud instructor.** Someone who already produces cert content (YouTube, blogs, Udemy) and wants a marketplace to publish hands-on labs alongside their videos. Served when the marketplace ships post-MVP.

## Success Criteria

**12-month outcome metrics (in priority order):**

1. **The North Star: 2x cloud-job placement rate vs. theory-only courses.** Measured by surveying users 3 and 6 months post-lab completion against a control group from common theory-only ACE courses (self-reported, augmented by LinkedIn signal where consented).
2. **Module completion rate ≥ 60%.** Cert-prep platforms typically see 15-25% completion; we should beat this materially because the loop is engaging.
3. **Zero teardown-failure incidents resulting in surprise bills.** Not "low" — zero. Achieved via the dual-channel teardown engine (in-band Terraform destroy + out-of-band sweeper + budget action kill-switch as belt-and-suspenders).
4. **Net Promoter Score ≥ 60** for the cohort that completes the launch module.

**12-month leading indicators:**

- 2,000+ GCP accounts connected
- 500+ launch-module completions
- ≥ 40% of users referred by a previous user

**Near-term proxy metric for the North Star (since job-placement signal takes 6-12 months):** completion of an interview-style mock-scenario walkthrough at the end of each cert track. Correlates with workplace performance more reliably than exam pass rate.

## Scope

**In for MVP (single module, GCP-only, free service):**

- Student-side product only — no instructor authoring, no marketplace
- Google Cloud Platform only — single cert track at launch (Associate Cloud Engineer)
- **One lab module**: *"Your first VPC — networks, instances, and secure SSH"* (10-12 outcome-validated tasks, runs entirely on GCP always-free tier)
- GCP account connection via Workload Identity Federation (short-lived OIDC tokens, never long-lived keys)
- Provisioning engine (Terraform) + outcome-validation engine + dual-channel auto-teardown engine
- Pre-flight credit estimate shown to user
- Signed completion transcript + auto-commit Terraform artifact to student's GitHub
- Free at MVP launch (no payment infrastructure)
- Manual support channel for incidents

**Explicitly out for MVP (becomes v2+):**

- Additional lab modules (modules 2-N follow only if module 1 proves the loop)
- Instructor authoring + marketplace + ratings + reviews
- Multi-cloud (AWS, Azure)
- Additional cert tracks (Professional Cloud Architect, AWS Solutions Architect Associate, Azure Administrator)
- Paid plans, billing, subscription, rev-share infrastructure
- Enterprise / team accounts
- Mobile app
- Validity-score engine for instructor-uploaded content
- Cost-overage refund/insurance program

**The discipline rule:** if it isn't required to validate the wedge claim — *"one real-account hands-on GCP lab that ACE candidates trust enough to grant a Workload Identity binding to"* — it does not belong in MVP.

## Vision (2-3 years)

The 24-month picture, gated on the launch module proving the loop:

- **Months 1-3**: Teardown engine + connector + launch module ship. Free MVP. Goal: validate setup → completion → teardown loop with the first 200 users.
- **Months 3-9**: If loop validates, expand to 8-12 modules covering the full ACE blueprint. Begin North Star measurement cohort. First paid track ships at $5-10/track once content depth justifies it.
- **Months 9-18**: Add Professional Cloud Architect track. Begin AWS expansion (a separate launch with the now-proven engine, addressing the larger cert market). Open instructor authoring beta — first 10-20 community instructors, curated onboarding, validity-score gate.
- **Months 18-36**: Open marketplace at scale. Multi-cloud (AWS, Azure). Hiring-side flywheel: companies subscribe to verify candidate signed transcripts. The product becomes *"the Udemy of cloud labs and the de facto verifiable hands-on credential for cloud hiring."*

The eventual platform vision is two-sided and cross-cloud. The path there runs through being undeniably the best place to prep for one cert in one cloud first. That sequencing is what makes this realistic for a lean team.

## Strategic Bets Worth Naming

Three bets the brief is making that compound if they hit:

1. **Hiring-market accountability becomes a category.** "Cert-prep platforms compete on hours watched" → "freetier-prep competes on jobs landed." If the North Star metric proves out, the company stops being a study tool and becomes infrastructure for the cloud hiring market.
2. **The cost-safety engine is a product, not just a feature.** The Terraform-orchestrated teardown engine + budget guardrails could be licensed to bootcamps, universities, and enterprise L&D programs as a standalone primitive. Reserved as a v3 wedge.
3. **AWS partnership window is real but time-limited (post-July-2025 AWS Free Tier overhaul).** When AWS expansion ships in v2, the AWS-credit-anxiety story is still fresh enough to support a co-marketing motion. Decision point: month 9-12.
