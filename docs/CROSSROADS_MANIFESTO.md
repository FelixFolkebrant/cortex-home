# Crossroads Manifesto

This manifesto defines the ideas behind the Crossroads workflow. The goal is high AI-assisted velocity while keeping the human in the loop for decisions that need taste, judgment, or long-term ownership.

This file is the highest-level source of truth for the workflow. Operational docs and templates should follow it.

# 1. Problem Definition

## 1.1 - AI Velocity

People often fall into one of two modes: fully trusting AI to make every decision, or reading every generated line in detail. The first mode removes human taste. The second mode removes most of the velocity gain.

Crossroads exists to keep AI moving quickly while directing human attention to the decisions that actually need it.

## 1.2 - Overplanning

Planning too far ahead can block momentum. Defining every feature, stack detail, and scalability concern up front kills creativity and is usually impossible. Some dots only connect in hindsight.

The process should be quick to start, then grow through gradual decisions. AI should not guess on hard-to-reverse choices that the user will later need to unwind.

## 1.3 - Losing Direction

Too little planning lets AI make too many tasteless choices and makes it unclear what should happen next. During development, the question "what are we doing next?" should always have an answer.

## 1.4 - Human Attention

Human attention is valuable. If something has too much detail, poor hierarchy, or unclear presentation, it will be skimmed. Skimming is not bad when the document is designed for it.

Documentation should make the important parts easy to find, especially the choices that need taste.

# 2. Solution - Gradual Definition

## 2.1 - Start With `IDEA.md`

`docs/project/IDEA.md` is the entry point for a project. The user describes the product in simple terms, including user flows, constraints, and any module or tech stack preferences they already have.

The goal is not a complete specification. The goal is enough shared context to start building and planning narrow slices.

## 2.2 - Taste

The human acts as the source of taste. Gradual definition transfers that taste into the project through accepted decisions, patterns, and style choices.

Taste is often easier to judge from a concrete proposal than from an open question. Prefer statements with motivation and alternatives over broad questions.

The more expensive a decision is to reverse, especially after future work depends on it, the more human acceptance it needs.

## 2.3 - Scaffolding And Plumbing

Decisions move top down. Do not decide everything immediately, but do decide choices that would cause heavy rewrites later.

Good example:

> We will use React and Tailwind. Auth will be handled by a third-party provider.

Reason: changing the application framework or styling system later can cause broad rewrites. Auth can also be expensive to retrofit if data ownership and access boundaries depend on it.

Bad example:

> We will use a specific graph component for a small feature planned far in the future.

Reason: this is a local implementation choice that can wait.

Plumbing connects modules through a narrow slice. The goal is not to define every schema. The goal is to define how schemas are defined and prove one hello-world shape flows end to end.

Instead of building the full backend before the frontend, build one backend endpoint and one frontend view that proves the connection. Then widen from there, prioritizing hard-to-reverse decisions and turning repeated choices into accepted patterns.

## 2.4 - Heatmap

The heatmap tells reviewers where judgment matters. Heat is not severity. Definitions live in `docs/project/HEATMAP.md`.

Repeated Hot decisions should become accepted patterns in `docs/project/PATTERNS.md`. Repeated Stylistic choices should become accepted style in `docs/project/STYLE.md`.

## 2.5 - Roadmaps And Planpoints

Planning also follows gradual definition. A plan gains detail as work gets closer.

`docs/project/ROADMAP.md` gives direction. It tracks upcoming Planpoints, deferred decisions, and broad Crossroads.

A Planpoint is a vertical slice above issue work. It decides the hard-to-reverse choices needed before its issues start. The file is named `docs/planpoints/PP-<n>.md`.

Issue-level choices belong in `docs/wip/GH-<n>-PLAN.md`, unless they become hard to reverse and need to be raised to the Planpoint.

Example Hot decisions at issue level:
- Add a third-party graph component for this feature?
- Separate builder and listing UI?

Example Crossroads at Planpoint level:
- Relational database vs NoSQL database.
- Third-party, self-hosted, or in-memory storage.
- React vs Next.js.

# Workflow

## Plan Work

1. Create or update `docs/project/IDEA.md`.
2. Create or update `docs/project/ROADMAP.md`.
3. Accept the roadmap.
4. Create `docs/planpoints/PP-<n>.md`.
5. Accept the Planpoint.

## Issue Work

1. Create `docs/wip/GH-<n>-PLAN.md`.
2. Check out the issue branch.
3. Make changes with atomic commits.
4. Keep `docs/wip/GH-<n>.md` updated as the issue record.

## Review Process

1. Review into `docs/wip/GH-<n>-REVIEW.md`.
2. Accept the review.
3. Fix accepted findings with fixup commits.
4. Review the fixup commits.
5. Update `docs/wip/GH-<n>.md` and check off `docs/wip/GH-<n>-REVIEW.md`.
6. Rebase after accepted fixes.
7. Repeat the review process until done.

## Finishing

1. Push the branch and create a PR.
2. Run CI and manual review when needed.
3. After approval and merge, remove WIP documents.
4. Move `docs/wip/GH-<n>.md` to `docs/issues/GH-<n>.md`.

# Document Roles

## `docs/project/IDEA.md`

Defines the idea, stack preferences, user flows, and constraints. It can be updated later when new product context appears.

## `docs/project/ROADMAP.md`

Sets direction and lists Planpoints. The roadmap stays loose so it can change as the project learns.

## `docs/planpoints/PP-<n>.md`

Defines one vertical slice. It makes the Crossroad decisions that need to happen before issue work starts.

## `docs/wip/GH-<n>-PLAN.md`

Plans one issue. It states what will be implemented, what is deferred, acceptance criteria, tasks, and issue-level Hot or Stylistic choices.

## `docs/wip/GH-<n>-REVIEW.md`

Records review findings by severity and heat. Findings are marked as fixed, deferred, accepted, or open.

## `docs/wip/GH-<n>.md` And `docs/issues/GH-<n>.md`

The final issue record. It is the only issue-level artifact that persists after merge, so it should summarize what changed, what was confirmed, and which decisions matter later.
