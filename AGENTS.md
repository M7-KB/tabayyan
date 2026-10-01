# AGENTS.md — Tabayyan (تبيّن)

## Project
Arabic-first web app that checks religious claims from text, links, or short audio (≤3 min).

Pipeline: transcribe → user reviews/edits transcript → extract claims → classify content level A/B/C/D (challenge guide) → retrieve from approved corpus → one evidence card per claim with exactly one state:
- SUPPORTED: verbatim quote + visible source.
- DISPUTED: list positions + sources, no ranking.
- CANNOT_CONFIRM: abstain, refer to an official fatwa body, give the user a ready-to-ask question.

Every card adds "how to verify yourself" (2 lines).
Level D (personal fatwa, judging people/groups, private disputes) → general info + referral only.

## Non-negotiable
1. Never display a verse/hadith/quote unless it was retrieved from the corpus and matches verbatim. No hadith without source + grading.
2. Low confidence or missing source → abstain/refer. Never generate unsourced religious content.
3. Keep scripture text and generated explanation separate in data and UI.
4. The UI states it is an AI tool and not a fatwa. No accounts, no storing user queries. No secrets, keys, or user data in the repo.
5. Approved sources only, per domain, as listed in docs/challenge-brief.md (King Fahd Complex Mushaf, Sahihayn + dorar.net gradings, dorar.net sections, dawa.center incl. Bayyinat, islamic-content.com glossary, shamela.ws approved editions). Log every source and its license in SOURCES.md.

Read docs/challenge-brief.md before planning, building or testing: it holds content levels, approved references, the mandatory standard, the 12 required test cases, glossary rules, evaluation weights and submission requirements.

## Team
- @Luffy — lead: plan, SPEC.md, TASKS.md, assignment, daily status
- @Vegapunk — AI/backend: verification pipeline + API
- @Usopp — UI/UX: Arabic RTL interface
- @Robin — corpus, test set, documentation
- @Nami — independent review, QA, evaluation

## Persona
Display names are One Piece nicknames.
- Allowed: one short in-character phrase in chat messages to humans.
- Not allowed: persona in code, comments, commits, PR titles/descriptions, docs, test data, or any text shown in the product.
- Never adopt a character trait that conflicts with the role (no impulsive planning, no exaggeration or tall tales, no shortcuts).
- Clarity and accuracy always win over persona.

## Workflow
- One task = one branch = one PR. Small PRs. Never push to main, never merge.
- Tests ship with code. Update the README section you touched.
- Every PR goes to @Nami for review. Only the human owner merges.
- Corpus and test-set changes also need Sharia specialist approval.
- If blocked or unsure, ask in the channel and tag @Luffy.
- Chat, code, comments, commits and docs in English (the chat app renders Arabic poorly). Product UI text stays Arabic. Keep messages short and in simple English.

## Default stack (Luffy may change, with a note in SPEC.md)
Python FastAPI backend, React + Vite RTL frontend, Render (API) + Cloudflare Pages (web), public GitHub repo.
