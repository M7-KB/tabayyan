# Source and licence register

P-03 source register, status checked 2026-10-03 against the evidence recorded below and [docs/DOWNLOAD_MANIFEST.md](docs/DOWNLOAD_MANIFEST.md). Content approval comes from [docs/challenge-brief.md](docs/challenge-brief.md). Acquisition steps belong to P-04. This register does not build a corpus. **No source has confirmed licence clearance; no raw or derived content is authorized for public commitment by this register.**

## Current source status

Each line covers source readiness, not approval in the challenge brief. `confirmed` requires
written permission on file for the exact item/edition and intended use, with an evidence path
and permitted scope recorded here. `pending` means that evidence review is incomplete;
`needs owner action` identifies a missing selection, file or permission the owner must supply.
Neither status permits ingestion. All 13 sources currently need owner action; none is confirmed.
The owner's request for organizer confirmation is not itself written permission on file.

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

The machine-readable licence fields below and the candidate allowlist remain `pending` with
ingestion/redistribution disabled. A readiness status does not change those gates or substitute
for Sharia specialist review. Use-only permission, if supplied, must record its exact scope;
whether public verbatim display is permitted remains an owner/organizer decision.


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

## Machine-readable register

`domain` uses the nine-value enum in SPEC section 4.1. `use` is descriptive text.
`license_url` is the policy/licence document to cross-check under SPEC section 4.2
rule 5, or `pending` when none is established. `Licence evidence URL` may instead
be a catalogue or landing page; it is not a licence grant. Pending entries cannot
satisfy ingestion clearance. A policy URL with `license: pending` does not establish permission.

| Source id | domain | use | Source URL | license | license_url | Licence evidence URL | Licence finding | Redistribution / ingestion |
|---|---|---|---|---|---|---|---|---|
| kfc-mushaf | quran | unchanged Arabic text | https://qurancomplex.gov.sa/techquran/dev/techquran-dev-mushf/ | pending | https://policy.qurancomplex.gov.sa/?Lan=en | https://policy.qurancomplex.gov.sa/?Lan=en | General policy reserves rights with exceptions for explicitly released resources; exact package terms pending. Portal timeout; formats confirmed only by official indexed developer-page description. | Raw files removed by #13 but remain in public history. No further ingestion or redistribution authorized. |
| sahih-bukhari | hadith | Sultaniyya / Dar Tawq al-Najah reproduction, Shamela 1681 | https://shamela.ws/book/1681 | pending | pending | https://shamela.ws/book/1681 | No edition-specific redistribution grant established from the book card. | Pending; local only; do not ingest |
| sahih-muslim | hadith | Abd al-Baqi, 1955 edition, Shamela 1727 | https://shamela.ws/book/1727 | pending | pending | https://shamela.ws/book/1727 | No edition-specific redistribution grant established from the book card. | Pending; local only; do not ingest |
| dorar-hadith | hadith | exact grading, grader and reference per item | https://dorar.net/hadith | pending | pending | https://dorar.net/hadith | Rights-reserved footer; no dataset licence established. Edition list: https://dorar.net/hadith/refs . | Pending; local only; do not ingest |
| jamhara-glossary | glossary | Arabic definition and supplied English equivalent | https://islamic-content.com/dictionary | pending | https://islamic-content.com/page/copyright | https://islamic-content.com/page/copyright | Policy describes personal noncommercial scholarly use; public redistribution/application use not established. | Pending; local only; do not ingest |
| bayyinat | faq | doubts and dialogue, Usul Center 2024 / 1445 AH | https://dawa.center/file/7937 | pending | pending | https://dawa.center/file/7937 | Catalogue has rights-reserved footer. PDF-specific terms not inspected. | Pending; local only; do not ingest |
| approved-quran-translation | quran_translation | English, linked to Arabic verse | https://quranpedia.net/translations/languages | pending | pending | https://quranpedia.net/translations/languages | Translator, edition, exact file and its licence all pending selection. KFC-approved translation is also permitted by the brief. | Pending; local only; do not ingest |
| dorar-tafsir | tafsir | separate commentary from scripture | https://dorar.net/tafseer | pending | pending | https://dorar.net/tafseer | Rights-reserved footer; public redistribution permission not established. | Pending; local only; do not ingest |
| dorar-aqeeda | aqeeda | approved creed material | https://dorar.net/aqeeda | pending | pending | https://dorar.net/aqeeda | Rights-reserved footer; public redistribution permission not established. | Pending; local only; do not ingest |
| dorar-fiqh | fiqh | general sourced positions, never personal rulings | https://dorar.net/feqhia | pending | pending | https://dorar.net/feqhia | Rights-reserved footer; public redistribution permission not established. | Pending; local only; do not ingest |
| dorar-history | seerah | history with qualifications | https://dorar.net/history | pending | pending | https://dorar.net/history | Rights-reserved footer; public redistribution permission not established. | Pending; local only; do not ingest |
| dawa-other | faq | individually selected da'wah resources | https://dawa.center/ | pending | pending | https://dawa.center/ | No particular item selected; item licence must be checked separately. | Pending selection/licence; do not ingest |
| jamhara-dawah | faq | individually selected da'wah content | https://islamic-content.com/ | pending | https://islamic-content.com/page/copyright | https://islamic-content.com/page/copyright | Same personal-use policy; selected item and public-use permission pending. | Pending; do not ingest |

The brief also permits early tafsir/creed/history sources, approved books of the four schools, and other authenticity-checked hadith editions on Shamela. These are **pending exact title/edition selection**, not permission to ingest arbitrary pages from those domains. Register each selection and licence before adding it to the allowlist.

Publisher copyright pages and book cards above are the evidence for the pending decisions, not affirmative licence grants. Unknown permission does not mean permanently prohibited. The owner can supply package terms or rights-holder permission for review; this register then records the permitted scope explicitly.
