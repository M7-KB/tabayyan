# KFC Quran v30 private artifact handoff

Authority: owner decision 2026-10-05, Buzz event
`62e18dbe42e11a40f175e75c987826e5b4b202b3b65e2ec679ccdb3756742209`,
routed by Luffy in build event `e660ae834c34b4c7632f3e857e5aafb932e03922d007b3f5319985dc3934bbb2`.
Display scope is in [SOURCES.md](../SOURCES.md#owner-public-display-decision-2026-10-05)
and [PR #61](https://github.com/M7-KB/tabayyan/pull/61). This metadata PR depends on #61.

| Property | Verified value |
|---|---|
| Supplied source | `data/raw/kfc-mushaf/kfgqpc_hafs_unicode_v30/kfgqpc_hafs_v30-data/kfgqpc_hafs_v30.json` in the original checkout |
| Raw SHA-256 | `d7adf8aeeef5a7b6798060706a55735dffbcdb542b290a3907bd9f70c498f4d3` |
| Raw bytes | 3,691,596 |
| Version | Standard-Unicode Hafs v30, as identified by owner and package filenames; no independently asserted release date |
| Count | 6,236 records, 6,236 unique `(sura_no, aya_no)` keys, 114 surahs |
| Sequence checks | IDs 1 through 6,236; each surah's verse numbers contiguous from 1 |
| Artifact version | `kfc-hafs-unicode-v30-20261005` |
| Artifact SHA-256 | `74f8424bad4e5920254f723f0936dc39561751b3cea66d9bdcabbc7dd47a38e8` |
| Artifact bytes | 9,576,033 |
| Local private path | `REPOS/tabayyan-display-20261005/corpus/private/quran-kfc-v30-20261005.jsonl` relative to the Buzz workspace |
| Private handoff | Same directory: `quran-kfc-v30-handoff.json` and `build_quran_v30_20261005.py` |
| Public manifest | [corpus/manifest.json](../corpus/manifest.json), checksum and version only |

Only `kfc-mushaf` Quran records are included. No Bukhari or other hadith records,
Hafs Smart text/font, translations, API religious content or generated religious text.
Each row has source name/URL, reference, level A, language, recorded licence scope,
licence URL, original-file hash, source record ID and `approved_by: pending`.
No hadith grading is invented or added to Quran records.

## Same-record field mapping

- `corpus_id`: `quran:<sura_no>:<aya_no>`; `ref`: `{surah, ayah}`.
- `text_ar` and `aya_text_emlaey`: the source's standard-spelling string, unchanged.
- `text_normalized`: existing ar-v1 normalization of that matching string.
- `checksum_sha256`: SHA-256 of the unchanged matching string's UTF-8 bytes.
- `aya_text_unicode`: the same source record's Uthmani display string, unchanged,
  including the end-of-ayah mark. `checksum_unicode_sha256` checks its UTF-8 bytes.
- `sura_no` and `aya_no` are also retained as explicit source keys.

Every row's two strings were compared with the corresponding raw record after the
private loader reread the checksummed JSONL. Existing `validate_records` and
`load_private_corpus` passed with `allow_pending_review=True` and public-display
permission required, against the display branch's SOURCES/register. The validator
is unchanged. These are provenance/structure checks, not an independent theological
or printed-Mushaf review. Owner selection/field review authority is in the private
handoff metadata; pending record identity is preserved exactly as instructed.

## Licence and deployment limits

The ten-file supplied package inventory has seven data formats and three font/demo
files. No standalone item-specific text licence was present in that inventory.
Do not infer text rights from its font. The owner's recorded challenge scope permits
matched public display with source and link, but no bulk display, download or file
redistribution. The general KFC policy is recorded in SOURCES; this is owner-reported
scope, not an independently inspected rights-holder grant.

The artifact stays ignored/private. The owner mounts it on Render after Nami reviews
the metadata and Vegapunk's separate field-binding PR. Set `PRIVATE_CORPUS_PATH` to
the mounted JSONL, use the committed manifest, and keep `ALLOW_PENDING_REVIEW=true`.
The current runtime still consumes `text_ar`; it must be changed to match on
`aya_text_emlaey` and copy `aya_text_unicode` from the same record for display.
This handoff alone does not authorize enabling live cards. Hadith claims abstain
with referral until the live Dorar connector lands.
