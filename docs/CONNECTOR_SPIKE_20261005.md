---
title: "Tabayyan bounded source and OpenAI spike"
tags: [tabayyan, api, spike]
status: active
created: 2026-10-05
---

Authority: owner event 62e18dbe42e11a40f175e75c987826e5b4b202b3b65e2ec679ccdb3756742209 and Luffy routing e660ae834c34b4c7632f3e857e5aafb932e03922d007b3f5319985dc3934bbb2. Exactly two OpenAI HTTP requests, no automatic retries, model returned `gpt-6.1-sol`, `store:false`. Input was synthetic connectivity/documentation prompts, no user queries or raw files. No corpus ingestion from these API results. Metadata-only result log is retained in the private Buzz workspace at RESEARCH/TABAYYAN_SPIKE_20261005_RESULTS.json; the measured public table below contains the findings. Latencies are single local-machine samples, not production measurements.

| Probe | Result and response shape | Seconds | Documentation / terms evidence |
|---|---|---|---|
| Dorar GET `/dorar_api.json?skey=...` | HTTP 403 HTML; no usable JSON from this machine | 0.27 | https://dorar.net/article/389 documents JSON/JSONP display; footer reserves rights; no separate licence grant inferred |
| HadeethEnc `/api/v1/categories/list/?language=en` | 200 JSON array; id/title/hadeeths_count/parent_id; 452 metadata entries | 1.45 | https://github.com/islamhouse-dev/hadith-api ; item-specific content terms pending |
| HadeethEnc `/api/v1/hadeeths/one/?language=ar&id=2962` | 200 object: id/title/hadeeth/attribution/grade/explanation/hints/categories/translations/hadeeth_intro/words_meanings/reference; grade/reference present, not reproduced | 1.44 | Same official API documentation; source is https://hadeethenc.com/ar/browse/hadith/2962 |
| Direct MCP `/mcp`: initialize, tools/list, one `get_quran_verses` (1:1) | 200 SSE with JSON-RPC result; single verse call returned SSE (2,566 bytes), content retained only in memory | 0.41 / 0.12 / 0.56 | https://mcp.islamiccontent.org/terms.html : free read-only access to published texts; not a blanket underlying-content redistribution licence |
| icadb docs schema and `/api/languages/list/` | Schema 200 OpenAPI JSON (Swagger 2); language list 200 JSON array, 154 metadata entries: id/name/short_name/iso_code/native_name/english_name/iso_version/alternative_names | 1.73 (language call) | https://icadb.com/api/docs/?format=openapi ; publisher licence/terms URL pending; schema advertises Basic auth, language call worked anonymously |
| OpenAI Responses remote MCP, only `list_languages` allowed | 200; mcp_list_tools, completed mcp_call with raw output, completed message; 1,161 input + 23 output tokens | 10.59 | https://developers.openai.com/api/docs/guides/tools-connectors-mcp |
| OpenAI Responses web_search, allowed_domains=[dorar.net] | 200; search action with sources, open_page action, reasoning, message; 8,555 input + 194 output tokens | 11.25 | https://developers.openai.com/api/docs/guides/tools-web-search |

Observed MCP tool names: `search`, `fetch`, `get_quran_verses`, `list_quran_translations`, `get_quran_audio`, `get_hadith`, `browse_hadith_categories`, `browse_library`, `get_library_item`, `list_library_categories`, `list_languages`. The expected `terminologyenc`, `byenah` and other service-specific names were not in this response. This does not prove those services are covered indirectly. Term-case integration remains unverified.

The web-search sources include `test.dorar.net`. OpenAI's documented filter includes subdomains; it does not implement the app's exact-host boundary. The observed response supplies citations/source URLs, not raw page bodies suitable for the verbatim gatekeeper. Do not accept model prose as source text. Remote MCP raw tool output exists, but the tested OpenAI call fetched language metadata only: religious-evidence validation is not established by that call. Use app-controlled connectors with exact-host checks and raw source-bound text.

Additional exploratory calls: icadb docs HTML and OpenAPI schema; a misspelled `/hadiths/list/` returned 404 before the documented `/hadeeths/one/` probe. No bulk religious download, no persistence of API religious text, no rate-limit response observed in the listed calls. Dorar 403 is specific to this execution environment; Render reachability still needs Vegapunk's authorized smoke probe. Total provider tokens 9,933; dollar cost not measured, no budget claim inferred.
