---
title: "Product Brief: freetier-prep"
status: "draft"
created: "2026-04-25T04:49:23Z"
updated: "2026-04-25T04:49:23Z"
inputs:
  - "user conversation transcript (bmad-product-brief skill, 2026-04-25)"
  - "web research synthesis (Stage 2 contextual discovery)"
---

# Product Brief: freetier-prep

## Executive Summary

**freetier-prep is the missing third leg of cloud certification training: real, hands-on labs that run inside the learner's own AWS account, paired with auto-teardown so they never get a surprise bill.**

Cloud cert-prep candidates today have two options, and both are broken. They can watch videos and grind practice exams (theory-heavy, doesn't transfer to the job) — or they can pay for sandbox lab platforms (KodeKloud, A Cloud Guru, Whizlabs) that hand them a vendor-managed playground that vanishes when they log out. Neither builds the muscle memory the AWS console actually demands of someone on day one of a cloud job. Meanwhile, learners who *do* try to lab in their own AWS account get burned: they forget a NAT Gateway running, wake up to a $200 bill, and quit.

freetier-prep solves both halves in one product. A learner connects their AWS account once via a scoped, time-limited role. They pick a cert track (SAA, DVA, SOA, SAP). For each lab module, the platform provisions real infrastructure into *their* account, walks them through 10–12 hands-on tasks against that real infra, and auto-tears everything down on completion or cancel — with hard cost caps as a backstop. The result: portfolio-grade muscle memory on the same console they'll use at work, on the free tier (or a few dollars of credits), with the safety net of guaranteed cleanup. The 12-month north star is concrete: **our students land cloud jobs at 2x the rate of theory-only courses.**

## The Problem

Cloud cert-prep is a $16–18B global market growing 12–14% annually, and the dominant playbook still doesn't work. Three pain points keep recurring across r/AWSCertifications, G2, and Trustpilot:

1. **"Sandbox labs don't transfer to my real job."** ACG, Pluralsight, KodeKloud, and Qwiklabs all run their hands-on portion inside their own managed accounts. Learners get a guided UI that doesn't match production AWS — no real IAM boundaries, no real billing console, no real CloudWatch noise, no real region switching. They pass the cert, start the job, and freeze the first time they open a real account.

2. **"Lab content is shallow and the validators are broken."** Forum sentiment on existing lab platforms is consistently that tasks are "next-next-finish" — they verify a resource exists but not whether the learner actually understood what they built. Outdated content (Whizlabs especially) and inconsistent grading erode trust.

3. **"I'm scared to lab in my own account."** This is the most-cited barrier on r/aws. Learners *want* real-account practice — they know it's the muscle memory that matters — but a single forgotten NAT Gateway, RDS instance, or EKS cluster can mean a $200–$5,000 surprise bill. The recent AWS Free Tier overhaul (July 2025, credit-based, 6-month window) made this worse, not better: people are now confused about *what's actually free*.

The status quo cost: motivated learners pick cert-prep platforms that produce paper credentials but not job readiness. Hiring managers in 2024–2025 increasingly demand "show me you've actually built it" — GitHub repos, Terraform portfolios, real console screenshots — and the existing training stack does not produce that.

## The Solution

**A guided cloud lab platform that runs in your own AWS account, safely.**

The student experience is a tight loop:

1. **One-time setup**: Connect AWS account via a scoped IAM role (no long-lived keys, no root credentials, transparent Terraform showing exactly what we provision)
2. **Pick a cert track**: AWS Solutions Architect Associate is the launch track; Developer, SysOps, and Solutions Architect Professional follow
3. **Start a lab**: Click "Start Lab." Platform provisions real infrastructure into the student's account in 30–90 seconds. Pre-flight cost estimate is shown upfront.
4. **Do the work**: Walk through 10–12 hands-on tasks in the student's actual AWS console + CLI. Each task validates against real-world outcomes (not just "resource exists").
5. **End cleanly**: Click "End Lab" — or walk away and the auto-teardown timer fires. Hard cost cap kicks in if anything goes wrong. Student leaves with a real CloudFormation/Terraform artifact in their own account history they can show on a portfolio.

Trust + cost-safety isn't a footnote — it's a feature surface: scoped roles, pre-flight cost estimates, hard caps, guaranteed teardown, and (over time) an insurance-style guarantee that the platform covers any runaway charges caused by a teardown failure.

## What Makes This Different

| | Sandbox lab platforms (KodeKloud, ACG, Pluralsight, Qwiklabs) | DIY in your own account | **freetier-prep** |
|---|---|---|---|
| Real cloud console muscle memory | ❌ vendor sandbox | ✅ | ✅ |
| Auto-teardown / cost safety | ✅ (their account) | ❌ | ✅ |
| Guided 10–12 task structure | ✅ (often shallow) | ❌ | ✅ |
| Validation depth | Shallow (resource-exists) | None | **Outcome-based** |
| Portfolio artifact in your account | ❌ | ✅ | ✅ |

The defensible angle isn't BYOC alone — KodeKloud or ACG could ship that in a quarter if they wanted. The moats build over time:

1. **Validation engine that correlates with job-readiness, not exam pattern-matching.** This is the v2+ flywheel: every cohort of students that lands jobs validates which task designs predict workplace performance, sharpening the validator over time. Competitors with sandbox-only telemetry can't see this signal.
2. **Cost-safety primitives as a brand asset.** Being publicly known as "the only place you can lab in your own AWS account without fear" is a moat against incumbents adding BYOC as a feature — they'd have to earn the trust we earn from day one.
3. **The marketplace flywheel (v2).** Once first-party tracks prove the experience, opening the platform to independent instructors with a validity-score gate creates the only Udemy-equivalent for cloud labs. Indie Hackers / Twitter chatter is clear: this whitespace exists.

## Who This Serves

**Primary user (MVP launch): the AWS cert-prep candidate.**

Think: a 24–35-year-old self-taught developer or career-changer studying for AWS Solutions Architect Associate. They've already bought a Stephane Maarek Udemy course and a TutorialsDojo practice exam set. They're 4–8 weeks from their exam date. They feel theory-rich and hands-on-poor. They've heard "you should lab in your own AWS account" but don't trust themselves not to leave a $0.05/hour resource running for a month.

**Their "aha moment":** They click "Start Lab," watch real EC2 instances appear in their own AWS console, work through the lab, click "End Lab," refresh the console, and see *zero resources*. They realize they can finally practice for real, safely.

**Secondary user (v2): the indie cloud instructor.** Someone who already produces cert content (YouTube, blogs, Udemy) and wants a marketplace to publish hands-on labs alongside their videos. They're served when the v2 instructor side ships.

## Success Criteria

**12-month outcome metrics (in priority order):**

1. **The North Star: 2x cloud-job placement rate vs theory-only courses.** Measured by surveying users 3 and 6 months post-lab completion. Self-reported, augmented by LinkedIn signal where consented.
2. **Module completion rate ≥ 60%.** Cert-prep platforms typically see 15–25% completion; we should beat this materially because the product is more engaging.
3. **Zero cost-runaway incidents.** Not "low" — zero. One $5,000 surprise bill in a public forum is a brand-killer.
4. **Net Promoter Score ≥ 60** for the cohort that completes a full cert track.

**12-month leading indicators:**

- 5,000+ AWS accounts connected
- 1,000+ paid cert-track purchases ($5,000–$10,000 monthly revenue ceiling at $5–$10 per track)
- ≥ 40% of paid users referred by a previous user

## Scope

**In for MVP (curated, first-party, AWS-only):**

- Student-side product only — no instructor authoring, no marketplace
- AWS cloud only (single cert-track at launch: Solutions Architect Associate)
- 1 cert track × 8–12 lab modules × 10–12 tasks each
- AWS account connection via scoped IAM role + OIDC
- Provision / validate / teardown engine (Terraform-based, IaC artifacts visible to user)
- Hard cost cap + auto-teardown timer + pre-flight cost estimate
- Free tier at MVP launch (no payment infra)
- Manual support channel for cost-runaway incidents (no automation needed at this volume)

**Explicitly out for MVP (becomes v2+):**

- Instructor authoring + upload tooling
- Marketplace, ratings, reviews, search
- Validity-score auto-validation engine for instructor-uploaded content
- Multi-cloud (Azure, GCP)
- Additional cert tracks beyond SAA
- Paid plans, billing, subscription, rev-share infrastructure
- Insurance-style cost guarantees (manually handled at MVP volume)
- Enterprise / team accounts
- Mobile app

**The discipline rule for a solo founder:** if it isn't required to prove the wedge claim — *"hands-on labs in your own AWS account, safely, that build job-readiness for the SAA cert"* — it does not belong in MVP.

## Vision (2–3 years)

The 24-month picture, if the wedge proves out:

- **Year 1**: Free MVP → ~5K connected accounts on SAA track → first paid cert-track ships at $5–$10 → kill or double down based on completion + job-placement signal.
- **Year 2**: All four AWS associate + professional tracks live. Instructor authoring beta opens — the first 10–20 community instructors join with curated onboarding. Validity-score engine ships and becomes the marketplace's quality gate.
- **Year 3**: Open marketplace at scale. Multi-cloud (Azure, then GCP). The product becomes *"the Udemy of cloud labs"* — the default place independent cloud instructors publish, and the default place cert-prep candidates go for hands-on practice.

The eventual platform vision is Udemy-shaped, but the path there runs through being undeniably the best place to prep for a single cert in a single cloud first. That sequencing is what makes this realistic for a solo founder: prove the experience before opening the platform.
