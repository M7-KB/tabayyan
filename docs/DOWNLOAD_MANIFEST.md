# P-04 manual source collection manifest

Baseline pre-work, 2026-10-02. Authority: [challenge brief](challenge-brief.md), approved references by domain. No corpus files were downloaded or scraped. URLs below are publisher entry pages, not invented direct file links. Preserve the original downloaded filename inside the suggested directory.

**All redistribution decisions are pending. Keep every raw file local; do not commit it or derived excerpts/indexes until its particular licence permits public redistribution and application use.** A free download, an ancient author's work, or approval in the brief does not settle the edition's rights. [SOURCES.md](../SOURCES.md) records the evidence for these decisions. Local possession does not authorize ingestion: pending licences block ingestion too.

## First collection pass

| Check | Source and exact entry URL | Owner action and format | Local destination | Licence / redistribution |
|---|---|---|---|---|
| [ ] | King Fahd Complex, Hafs Unicode Mushaf: https://qurancomplex.gov.sa/techquran/dev/techquran-dev-mushf/ (developer portal: https://qurancomplex.gov.sa/techquran/dev/) | Select the **Hafs Unicode text package**, preferably JSON or CSV, not a font-only or page-image package. The official indexed portal advertises JSON, CSV, XML, SQL, Excel, HTML5 and PDF. Entry page timed out during verification; exact current archive name/direct URL **pending owner confirmation**. Save package terms with the file. | `data/raw/kfc-quran/` | Pending: general KFC policy reserves rights except explicitly released resources. No public commit until package-specific permission is recorded. |
| [ ] | Sahih al-Bukhari, Sultaniyya edition: https://shamela.ws/book/1681 | Save selected numbered hadith pages using the browser (HTML), including the book card. Edition: 1311 AH Sultaniyya, reproduced by Dar Tawq al-Najah 1422 AH with added numbering/notes. No verified bulk-export file URL. | `data/raw/sahih-bukhari/` | Pending: book card identifies the edition but gives no redistribution licence. Keep local. |
| [ ] | Sahih Muslim, Abd al-Baqi edition: https://shamela.ws/book/1727 | Save selected numbered hadith pages (HTML) and book card. Edition: Isa al-Babi al-Halabi, Cairo, 1374 AH / 1955; 5 parts including index. No verified bulk-export file URL. | `data/raw/sahih-muslim/` | Pending: edition-specific redistribution permission not established. Keep local. |
| [ ] | Gradings for **each** selected hadith: https://dorar.net/hadith ; edition catalogue: https://dorar.net/hadith/refs | Search the exact selected text manually; save the matching result/detail page (HTML). Record collection + number, exact grade, grader, grading reference and exact permalink. **No grade inferred from the collection title.** Selected hadith list/permalinks remain pending until owner supplies the chosen records. | `data/raw/dorar-hadith/` | Pending: Dorar footer reserves rights; no dataset redistribution grant established. Keep local. |
| [ ] | Al-Jamhara glossary: https://islamic-content.com/dictionary ; Tawhid entry: https://islamic-content.com/dictionary/word/3529 | Save selected term pages (HTML), with their references; use the language selector to save the corresponding English page **only if provided**. Begin with Tawhid; add Sharia for English case 12. Do not machine-translate a missing equivalent. Exact Sharia entry and English permalinks pending selection. | `data/raw/jamhara-glossary/` | Personal noncommercial scholarly use described at https://islamic-content.com/page/copyright . Public repository/application redistribution **not established**; keep local, permission pending. |
| [ ] | Bayyinat, Usul Center, 2024 / 1445 AH: https://dawa.center/file/7937 | On this exact page, choose the single **PDF** attachment's Download button. Keep the original filename plus the material details page. The attachment is present; direct attachment URL/filename not asserted without downloading. | `data/raw/bayyinat/` | Pending: catalogue footer says all rights reserved; attachment-specific terms not inspected. Keep local; obtain rights for excerpts and application use. |

## Remaining approved domains

For both Bukhari (Shamela 1681) and Muslim (Shamela 1727), grading provenance is the **matching Dorar hadith record**, saved separately with exact grade, grader, grading reference and permalink. Each collection is blocked until those per-item records arrive; the edition card alone never supplies a grading.

These are exact starting URLs, not a claim that an entire website or every edition is eligible. Save **only selected pages/files**, with their individual reference, edition, licence and URL. Item selection is still pending where the brief names a class of books rather than a title.

| Domain | Exact URL / approved alternative | Format and owner action | Local destination | Licence / redistribution |
|---|---|---|---|---|
| Qur'an translation | https://quranpedia.net/translations/languages (alternative: KFC-approved translation) | Select a named approved English translator/edition and save the publisher file or selected HTML pages. Exact edition/file URL pending; do not use machine translation. | `data/raw/quran-translation/` | Pending for the selected translation; keep local. |
| Tafsir | https://dorar.net/tafseer ; alternatively early sources from the first three centuries named in the brief | Selected HTML pages, with exegete and reference. Specific early-source editions must be identified and checked before adding. | `data/raw/dorar-tafsir/` | Pending; Dorar rights-reserved footer. Keep local. |
| Creed | https://dorar.net/aqeeda ; alternatively approved early sources | Selected HTML pages, with references; early-source edition selection pending. | `data/raw/dorar-aqeeda/` | Pending; keep local. |
| General fiqh | https://dorar.net/feqhia ; alternatively approved books of the four schools | Selected HTML pages holding at least two sourced positions where needed; no ranking. Specific school-book editions pending specialist selection. | `data/raw/dorar-fiqh/` | Pending; keep local. |
| Seerah/history | https://dorar.net/history ; alternatively approved early sources | Selected HTML pages, retain every citation and uncertainty qualification. Exact early-source edition pending. | `data/raw/dorar-history/` | Pending; keep local. |
| Other da'wah topics | https://dawa.center/ ; https://islamic-content.com/ | Owner selects an individually identified item; save its offered PDF/HTML and catalogue page. Bayyinat and the glossary above are the initial concrete selections. | `data/raw/dawah/` | Per-item permission pending; keep local. |
| Other hadith collections | https://dorar.net/hadith ; https://shamela.ws/ | Specific approved edition required, plus per-hadith authenticity evidence. No other collection is selected for v0. | `data/raw/other-hadith/` | Pending per edition and grading source; keep local. |

## Handoff checklist

1. Keep downloads in the ignored folders above. Do not use `git add -f`.
2. Alongside each source, save its exact download/page URL, original filename, edition, acquisition date, licence text/URL, and any written permission. Include rights for public raw files **and** derived corpus passages/application display; permission for one is not permission for the other.
3. Keep scripture unchanged. Save translation separately with translator/edition. Save hadith grading separately with its exact permalink and reference.
4. Tell the team which files are ready. Ingestion reads only human-provided `data/raw/` files and leaves unclear licences pending in SOURCES.md. Content/test-set approval by the Sharia specialist is a separate gate.

`corpus/approved_sources.json` is a **candidate source allowlist**, not licence clearance or content approval. Broad alternative classes in the brief are recorded as pending selection, not blanket host permissions.
