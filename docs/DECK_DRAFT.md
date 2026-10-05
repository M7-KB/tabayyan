# Tabayyan (تبيّن): deck draft

Draft text, one short section per slide. Placeholders in **[brackets]** stay until the eval and the live demo fill them. Source of truth for claims: SPEC.md §1, §5, §6, §8 and §10 decisions 30–31.

## 1. Problem

A user hears or reads a religious claim and needs to know whether an approved source supports it, and which source that is. This tool answers only from approved sources and shows them on every card. It does not claim how other tools perform.

## 2. Solution

Tabayyan checks religious claims in Arabic text, and later links and short audio. It returns one evidence card per claim. Each card has exactly one state:

- **SUPPORTED:** a verbatim quote from an approved source (the local corpus, or an approved-source result returned in the same request), with its visible source.
- **DISPUTED:** the positions and their sources, with no ranking.
- **CANNOT_CONFIRM:** an explicit abstention, a referral to an official fatwa body, and a ready question for the user to ask.

Every card ends with two lines on how to verify it yourself.

## 3. How it works

1. The user pastes Arabic text.
2. The model extracts the claims. The user confirms or edits them.
3. The model classifies each claim's content level (A to D). Level D (personal fatwa, judging people or groups, private disputes) gets general information and a referral only.
4. Retrieval runs against the approved corpus (the Qur'an, KFC Hafs v30) and allowlisted connectors (HadeethEnc).
5. Code gates check every quote verbatim against the source record or the same request's results. Failed quotes are dropped and the state is recomputed.
6. The result cards render. Scripture text and the generated explanation are separate fields and separate UI blocks.

## 4. Added value

- **Closed corpus, not open search.** Evidence comes only from approved sources, named on every card.
- **Abstention is designed.** When the corpus does not hold the evidence, the tool says so and refers the user. It does not guess.
- **Verbatim by code.** Quote checks run in code, not in the prompt.
- **Arabic-first, RTL.** The product UI is in Arabic. Each result view carries the notice that this is an AI tool and not a fatwa.
- **Private by design.** No accounts and no stored queries. No secrets in the repo.

## 5. Techniques

- Python FastAPI API. React and Vite RTL web app. Render (API) and Cloudflare Pages (web).
- Model-based claim extraction and level classification, with strict JSON-schema outputs.
- Lexical retrieval over the private, checksummed Qur'an artifact (SHA-256 checked at startup, fail closed).
- Scripture-span detector: a verbatim veto first, then near-miss checks, so a misquote is not confirmed.
- Eval harness over the 12-case brief test set and the 18 public safety cases. The red-team set and the corpus-free **control** arm are planned and pending; their reports do not exist yet. The control arm, when run, is for comparison only and is never shown to users.

## 6. Results

Placeholders until the eval runs. Do not fill these with estimates.

- Classification accuracy: **[pending eval]**
- Abstention precision and recall: **[pending eval]**
- Unmatched or unsourced quotes: **[pending eval]**
- Control arm (plain model, same prompts, no corpus): fabricated-source rate **[pending eval]**, correct-abstention rate **[pending eval]**
- Live demo check, four chips reviewed by Nami: **[pending]**

## 7. Known limits

- **Dorar is disabled.** The Render smoke call returned HTTP 403 with no JSON. Hadith comes from HadeethEnc only. Until a HadeethEnc result returns, hadith claims abstain with a referral.
- **No Sharia specialist on this project.** Content decisions are the owner's. The source and review record is in SOURCES.md and the README.
- **Links and audio** are P1 and ship only if stable. Images are P2.

## 8. Roadmap (continuation plan)

Not built in this submission. All of these run on the same verification engine:

- A public API for other sites.
- Instagram DMs.
- A browser extension.
- Platform share-to-app.
- A WhatsApp tipline.
- Matching a repeated viral claim to an earlier result.

No public-comment automation.
