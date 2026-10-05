# Source and licence register

P-03 source register, status checked 2026-10-03 against the evidence recorded below and [docs/DOWNLOAD_MANIFEST.md](docs/DOWNLOAD_MANIFEST.md). Content approval comes from [docs/challenge-brief.md](docs/challenge-brief.md). Acquisition steps belong to P-04. This register does not build a corpus. **The dated owner decision below permits challenge-app ingestion for three selected sources, with redistribution prohibited. Raw files and built corpus never enter the public repo. Machine-readable gates record this scoped permission; public distribution remains disabled.**

## Current source status

Each line covers source readiness, not approval in the challenge brief. `confirmed` requires
written permission on file for the exact item/edition and intended use, with an evidence path
and permitted scope recorded here. `pending` means that evidence review is incomplete;
`needs owner action` identifies a missing selection, file or permission the owner must supply.
The historical statuses below describe evidence still needed per item. The later
owner decision overrides ingestion restrictions for kfc-mushaf, sahih-bukhari and
dorar-hadith within the challenge app only; redistribution is prohibited.
Other permissions and specialist review remain pending.

- `kfc-mushaf` — **needs owner action**: supply exact Hafs Smart package terms or written permission covering ingestion and public application display/redistribution; the general policy below is insufficient.
- `sahih-bukhari` — **needs owner action**: supply edition-specific permission, selected source files and matching Dorar grading records; the Shamela book card establishes no licence grant.
- `sahih-muslim` — **needs owner action**: supply edition-specific permission, selected source files and matching Dorar grading records; the Shamela book card establishes no licence grant.
- `dorar-hadith` — **needs owner action**: supply permission for the selected grading records and their exact saved references; the rights-reserved footer establishes no dataset grant.
- `jamhara-glossary` — **needs owner action**: supply permission for public application use and selected Arabic/English term files; the personal-use policy does not establish that scope.
- `bayyinat` — **needs owner action**: supply the selected PDF and its terms or written permission for excerpts and application display; catalogue evidence is insufficient.
- `approved-quran-translation` — **needs owner action**: select translator, edition and exact file, and supply its licence evidence; no translation artifact is selected.
- `dorar-tafsir` — **needs owner action**: supply selected files and written permission for ingestion and public application display/redistribution; no grant is recorded below.
- `dorar-aqeeda` — **needs owner action**: supply selected files and written permission for ingestion and public application display/redistribution; no grant is recorded below.
- `dorar-fiqh` — **needs owner action**: supply selected files and written permission for ingestion and public application display/redistribution; no grant is recorded below.
- `dorar-history` — **needs owner action**: supply selected files and written permission for ingestion and public application display/redistribution; no grant is recorded below.
- `dawa-other` — **needs owner action**: select exact items and supply their files and item-specific permission; a domain entry is not clearance.
- `jamhara-dawah` — **needs owner action**: select exact items and supply their files and permission for public application use; the personal-use policy is insufficient.

The machine-readable fields confirm challenge-app ingestion for the three sources covered by
the dated owner decision. Redistribution stays disabled. Other entries remain `pending`.
A readiness status does not change those gates or substitute
for Sharia specialist review. Use-only permission, if supplied, must record its exact scope;
whether public verbatim display is permitted remains an owner/organizer decision.

## Partner approval for challenge use (2026-10-03)

The owner reports that the organizers replied: the sources are approved by the
challenge partner and may be used within the challenge scope. Evidence: the
owner-provided organizer-reply report dated 2026-10-03; the correspondence remains
with the owner.
This records the owner's report of the reply, not an independently inspected copy
of the organizers' correspondence or an item-specific licence document.

**Partner approval: use within the challenge. Redistribution licence: needs owner
action.** Public redistribution in the repository was not addressed. The owner is
asking a follow-up; until answered, no full third-party text goes into the public
repository. Raw files, derived excerpts/indexes and public verbatim display still
require their applicable scope to be recorded per item.
**Superseded by the dated owner ingestion decision below:** the earlier statement that
all machine-readable licence fields remained pending and flags were unchanged no longer applies
to the three selected sources. Public-display permission remains unresolved.
This approval does not select religious records or supply Sharia specialist approval.
Only the owner downloads and places selected files in `data/raw/`.


## Owner licence decision (2026-10-03 night)

Owner decision routed in build event d1ca230495eeeb02218c21be73825d975b9a7af7494651623f6cd5fec32bb5ec: challenge-app ingestion is allowed for kfc-mushaf, sahih-bukhari and dorar-hadith; redistribution is prohibited. Raw files and the built corpus never enter the public repository. Content review remains pending. Machine-readable gates and runtime support are a separate backend task.
This records the routed owner's scope decision, not independently inspected publisher
licences. It supersedes the earlier unresolved ingestion/redistribution status for
these three sources. The private artifact uses committed hashes only, following
[PR #25](https://github.com/M7-KB/tabayyan/pull/25).

The machine-readable table and approved_sources.json now record confirmed challenge-app
ingestion for these three sources, with redistribution false. Offline validation checks that
ingestion scope. Runtime additionally requires recorded public-display permission. The historical false flags below are superseded for KFC and Dorar by the 2026-10-05 decision. Do not set approved_by to sharia-reviewer-1:
owner-selected records stay pending; new test items require needs_sharia_review: true.
Pending-review runtime use requires the explicit default-off ALLOW_PENDING_REVIEW flag,
reported by /health. Owner selection is not specialist approval.

Sahih Muslim remains an approved reference under the challenge brief, retained in
this register and approved_sources.json. It is **not in current selection** in the
manifest; its edition-specific permission remains pending. The three-source decision
does not extend to Muslim.

## Owner public-display decision (2026-10-05)

The owner permits public display in the deployed challenge app for `kfc-mushaf`,
`dorar-hadith`, and live results from the allowlisted sources in SPEC section 0.3.
Scope: only the matched verse, hadith, grading or short excerpt, with visible source
and link. No bulk display, no download, no redistribution of files.
Basis: the organizers' written reply of 2026-10-03 and the challenge data package,
as reported by the owner; the correspondence remains with the owner. This is an
owner scope decision, not an independently inspected publisher licence grant.
Evidence: owner Buzz event `62e18dbe42e11a40f175e75c987826e5b4b202b3b65e2ec679ccdb3756742209`,
routed by Luffy in `e660ae834c34b4c7632f3e857e5aafb932e03922d007b3f5319985dc3934bbb2`.
No specialist approval is required. Nami reviews the implementation; the owner merges.

`public_display_allowed` is now true for KFC and Dorar hadith; redistribution remains
false. Future live connectors must record this scope for their exact selected source
and enforce same-request text/source binding. A display flag does not enable a
connector, approve arbitrary URLs, settle underlying publisher terms, or authorize
bulk ingestion. Legacy pending entries retain their acquisition gates. Shamela and
the islamic-content.com glossary are link-only; no copied text is authorized from them.

The local artifact contains only KFC standard-Unicode Hafs version 30, supplied at
`data/raw/kfc-mushaf/kfgqpc_hafs_unicode_v30/kfgqpc_hafs_v30-data/kfgqpc_hafs_v30.json`.
Hafs Smart data/font and the four local Bukhari records are dropped. Match on
`aya_text_emlaey`; display `aya_text_unicode` of the same `(sura_no, aya_no)` record,
unchanged including the end-of-ayah mark. Hadith claims abstain with referral until
the live Dorar connector is available. No new edition-specific publisher grant was
found in the supplied ten-file v30 package inventory; font terms do not confer text rights.
`approved_by` remains `pending`; deployment uses `ALLOW_PENDING_REVIEW=true`.
Owner review belongs in handoff metadata, not a substituted validator identity.

## Jamhara permission evidence (2026-10-03)

The owner's evening update in planning (Buzz event
`c960d48e041c2476131ab9147e86ed542005aa6765018921490ea025ac6d1cb0`)
records the [Jamhara copyright policy](https://islamic-content.com/page/copyright)
as scholarly use for personal, non-commercial purposes only, with mixed provenance.
Public display or redistribution permission is not stated in that evidence.
The policy check reported in build (Buzz event
`8be08934b8ca8418eb13916ff030b297537edd130a0831c87bafcc15457f38c1`)
records the same scope and mixed site-edited/republished provenance, including removal
on rights-holder objection. Luffy's routing instruction (Buzz event
`e6b14b35243be3b14ead8252916e571607014dcaec222c9939655f4c03de44be`)
requires retaining **needs owner action**. These are consolidated evidence reports,
not an item-specific permission grant or a blanket conclusion about every item's rights.

Both `jamhara-glossary` and `jamhara-dawah` stay **needs owner action**.
The machine-readable `license` remains `pending`; ingestion and redistribution remain
disabled. Obtain written permission covering the exact selected items, their underlying
references and the intended public application display and redistribution. Mixed provenance
requires checking the selected item's rights rather than treating the website policy as
clearance for every attributed passage. The owner is requesting organizer and Jamhara
confirmation in writing. The earlier request alone was not permission; the later
challenge-use reply is recorded above and still does not settle redistribution.

An English equivalent also requires its own cleared source and provenance. An outbound
entry link alone does not clear copied, translated or generated religious content.
Without cleared evidence, T07 and T08 must abstain with referral, as directed in build
(Buzz event `94f8362d5cbfaee0b74ad6446b5484d2f52778833f95de7eb4aa2a13735785ef`).
The proposed Oct 4 selections remain in the separate
[checklist PR #33](https://github.com/M7-KB/tabayyan/pull/33).

## Public-history disclosure

As of 2026-10-02, base main `52a39836d266ca30fa520bd2d8f1e9f4302408d7`
contains eight files under `data/raw/kfgqpc_hafs_smart_4/`, merged by
[PR #12](https://github.com/M7-KB/tabayyan/pull/12). They are the `kfc-mushaf`
KFGQPC Hafs Uthmanic package: six data formats, `read.me`, and `HafsSmart_08.docx`.
The JSON file is 4,192,442 bytes (`git ls-tree -r --long 52a3983 data/raw/kfgqpc_hafs_smart_4/`).
These source files are already in public history despite pending licence clearance.
[PR #13](https://github.com/M7-KB/tabayyan/pull/13) removed the raw
package and `docs/raw/` from the tree, ignored both paths, and added the README
disclosure. Removal does not erase public history. No ingestion or
redistribution permission follows from their presence.

## Web fonts (2026-10-04)

- `@fontsource/amiri-quran` 5.3.0 — Amiri Quran, used for scripture quotes in `web/src/components/card/card.css`. Licence: SIL Open Font License 1.1 (`node_modules/@fontsource/amiri-quran/LICENSE`). Self-hosted through the npm package; no third-party font CDN.
- `@fontsource/ibm-plex-sans-arabic` — interface font, already in use. Licence: SIL Open Font License 1.1.

## Machine-readable register

Test-set reference only (T14–T18): [Dorar fake-hadith page 4](https://dorar.net/fake-hadith/4),
supplied by the owner in Buzz event
`7d78b080b3c5e859e2f52de5cb19457982961ccdc2887bab6f6e9453d1a6c453` (2026-10-03).
License: **pending**; the page footer reserves rights and establishes no dataset grant.
Only the link is recorded; the test inputs come verbatim from the owner's message.
No Dorar commentary or grading text is copied, and this citation does not add a source
to the corpus allowlist or authorize ingestion. See [eval/TESTSET_NOTES.md](eval/TESTSET_NOTES.md).

`domain` uses the nine-value enum in SPEC section 4.1. `use` is descriptive text.
`license_url` is the publisher policy/licence document to cross-check under SPEC section 4.2
rule 5, or `pending` when none is established. `Licence evidence URL` may instead
be a catalogue or landing page; it is not a licence grant. The separate Owner decision evidence URL column corresponds to `license_evidence_url`
in the allowlist; neither is a publisher policy. Bukhari and Dorar have no established
publisher policy URL, so their `license_url` is restored to `pending`, rather than inventing
a grant from a catalogue page. Their records cannot validate until the owner supplies
the applicable publisher document. Pending entries cannot satisfy ingestion clearance. A policy URL with `license: pending` does not establish permission.

| Source id | domain | use | Source URL | license | license_url | Licence evidence URL | Licence finding | Redistribution / ingestion | Owner decision evidence URL |
|---|---|---|---|---|---|---|---|---|---|
| kfc-mushaf | quran | unchanged Arabic text | https://qurancomplex.gov.sa/techquran/dev/techquran-dev-mushf/ | Owner-authorized challenge-app use only; matched verse, hadith, grading or short excerpt with visible source and link; no bulk display, download or file redistribution | https://policy.qurancomplex.gov.sa/?Lan=en | https://policy.qurancomplex.gov.sa/?Lan=en | Owner-reported challenge-app display scope, 2026-10-05; underlying publisher terms are not independently cleared. | Ingestion and matched public display allowed; file redistribution prohibited; private artifact or same-request live result only. | https://github.com/M7-KB/tabayyan/blob/docs/display-20261005/SOURCES.md#owner-public-display-decision-2026-10-05 |
| sahih-bukhari | hadith | Sultaniyya / Dar Tawq al-Najah reproduction, Shamela 1681 | https://shamela.ws/book/1681 | Owner-authorized challenge-app use only; no redistribution | pending | https://shamela.ws/book/1681 | Owner-reported challenge-app permission, dated 2026-10-03; correspondence retained by owner. Not an independently inspected rights-holder grant. | Challenge-app ingestion allowed; redistribution prohibited; private artifact only; specialist review pending. | https://github.com/M7-KB/tabayyan/blob/f82ba58058c8194bdd47ad02402ca7b4a3c4fbe9/SOURCES.md#owner-licence-decision-2026-10-03-night |
| sahih-muslim | hadith | Abd al-Baqi, 1955 edition, Shamela 1727 | https://shamela.ws/book/1727 | pending | pending | https://shamela.ws/book/1727 | No edition-specific redistribution grant established from the book card. | Pending; local only; do not ingest | pending |
| dorar-hadith | hadith | exact grading, grader and reference per item | https://dorar.net/hadith | Owner-authorized challenge-app use only; matched verse, hadith, grading or short excerpt with visible source and link; no bulk display, download or file redistribution | pending | https://dorar.net/hadith | Owner-reported challenge-app display scope, 2026-10-05; underlying publisher terms are not independently cleared. | Ingestion and matched public display allowed; file redistribution prohibited; private artifact or same-request live result only. | https://github.com/M7-KB/tabayyan/blob/docs/display-20261005/SOURCES.md#owner-public-display-decision-2026-10-05 |
| jamhara-glossary | glossary | Arabic definition and supplied English equivalent | https://islamic-content.com/dictionary | pending | https://islamic-content.com/page/copyright | https://islamic-content.com/page/copyright | Policy describes personal noncommercial scholarly use; public redistribution/application use not established. | Pending; local only; do not ingest | pending |
| bayyinat | faq | doubts and dialogue, Usul Center 2024 / 1445 AH | https://dawa.center/file/7937 | pending | pending | https://dawa.center/file/7937 | Catalogue has rights-reserved footer. PDF-specific terms not inspected. | Pending; local only; do not ingest | pending |
| approved-quran-translation | quran_translation | English, linked to Arabic verse | https://quranpedia.net/translations/languages | pending | pending | https://quranpedia.net/translations/languages | Translator, edition, exact file and its licence all pending selection. KFC-approved translation is also permitted by the brief. | Pending; local only; do not ingest | pending |
| dorar-tafsir | tafsir | separate commentary from scripture | https://dorar.net/tafseer | pending | pending | https://dorar.net/tafseer | Rights-reserved footer; public redistribution permission not established. | Pending; local only; do not ingest | pending |
| dorar-aqeeda | aqeeda | approved creed material | https://dorar.net/aqeeda | pending | pending | https://dorar.net/aqeeda | Rights-reserved footer; public redistribution permission not established. | Pending; local only; do not ingest | pending |
| dorar-fiqh | fiqh | general sourced positions, never personal rulings | https://dorar.net/feqhia | pending | pending | https://dorar.net/feqhia | Rights-reserved footer; public redistribution permission not established. | Pending; local only; do not ingest | pending |
| dorar-history | seerah | history with qualifications | https://dorar.net/history | pending | pending | https://dorar.net/history | Rights-reserved footer; public redistribution permission not established. | Pending; local only; do not ingest | pending |
| dawa-other | faq | individually selected da'wah resources | https://dawa.center/ | pending | pending | https://dawa.center/ | No particular item selected; item licence must be checked separately. | Pending selection/licence; do not ingest | pending |
| jamhara-dawah | faq | individually selected da'wah content | https://islamic-content.com/ | pending | https://islamic-content.com/page/copyright | https://islamic-content.com/page/copyright | Same personal-use policy; selected item and public-use permission pending. | Pending; do not ingest | pending |

The brief also permits early tafsir/creed/history sources, approved books of the four schools, and other authenticity-checked hadith editions on Shamela. These are **pending exact title/edition selection**, not permission to ingest arbitrary pages from those domains. Register each selection and licence before adding it to the allowlist.

Publisher copyright pages and book cards above are the evidence for the pending decisions, not affirmative licence grants. Unknown permission does not mean permanently prohibited. The owner can supply package terms or rights-holder permission for review; this register then records the permitted scope explicitly.

## HadeethEnc runtime item adapter (2026-10-05)

Owner authority: planning event
`0f6d019222f73b47c0b897a50d377c9372d315569be21ba05a07cb20f96aed9c`,
including the section 12.7 grading decision. The item connector uses the
[official HadeethEnc API](https://github.com/islamhouse-dev/hadith-api) on
`hadeethenc.com`, with canonical item links on the same exact host.
It copies the hadith and grade from one Arabic item response, labels the grade
as HadeethEnc's, and drops records without grade, attribution or reference.

Licence: owner-authorized matched challenge-app display with visible source and
link, under the scope above. The official API documentation establishes the API
shape; it is not treated as an underlying-text redistribution licence. No bulk
fetch, download, dataset publication or response persistence is permitted.
The item adapter does not create a local HadeethEnc corpus or change P-03 flags.

Discovery routing authority: build event
`74955bb4a1b90316e3a47f4f39bd1e785f28b286b8ba27415bdd66f65b2b910d` (2026-10-05).
The same official API documents `/api/v1/categories/list/` and
`/api/v1/hadeeths/list/` (`language`, `category_id`, `page`, `per_page`). The adapter
uses one category metadata response and one bounded page for ID discovery only;
neither titles nor metadata authorize a quote. Full Arabic item responses remain
request-scoped, with `grading_source_id: hadeethenc`. Display permission is the
same owner-authorized scope above; underlying-text redistribution terms remain
uncleared. No responses are retained or added to the local corpus.
