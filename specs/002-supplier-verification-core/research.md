# Research: Local-First Supplier Verification Core

**Checked**: 2026-10-17 | **Authority**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Governing decisions

The user requires a working local product before hosting, no required paid data/model APIs, no AWS/LocalStack, and **real-world data only**. No demo suppliers, synthetic datasets, fabricated certificate/provider responses or invented verdict evidence may populate the application or acceptance corpus. Tests can replay faithfully captured real records with provenance; controlled restart/fault/clock conditions must be disclosed and must not fabricate source content or masquerade as live retrieval.

Research used primary documentation and actual public pages. No paid account, cloud storage or government API entitlement was obtained. Public source inspection establishes accessible content and documented scope, not unrestricted access rights or comprehensive current verification. Existing paid-service-first design decisions are superseded by this revision.

## D01 — Local application stack

- **Decision**: Keep React19/Vite8/TypeScript, Python3.14/FastAPI, SQLAlchemy2/Alembic1/psycopg3, PostgreSQL17 and LangGraph1 with its Postgres checkpointer. API and one durable worker run as local processes; PostgreSQL runs free locally, natively or in a single Docker service. No hosted database, Keycloak, cloud proxy or managed queue is required.
- **Rationale**: PostgreSQL itself costs no service fee and preserves the existing durable transaction/job design. Native Ollama/API/frontend processes avoid allocating scarce laptop RAM to a larger container stack. Docker, Node, Python, uv and Ollama were found installed; their exact compatibility remains an implementation check.
- **Alternatives considered**: SQLite is viable for a smaller single-writer prototype, but switching domain/checkpoint/queue concurrency adds unnecessary change to the already selected Postgres design. Hosted PostgreSQL, Redis/Celery, Kubernetes and server-rendering infrastructure are deferred.
- **Sources**: [React](https://react.dev/versions), [Vite](https://vite.dev/guide/), [Python support](https://devguide.python.org/versions/), [PostgreSQL](https://www.postgresql.org/about/), [SQLAlchemy](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html), [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence).

## D02 — Machine and local-model selection

Read-only hardware inspection found AMD Ryzen7 7840HS (8 cores/16 threads),15.3GiB usable RAM, NVIDIA RTX4060 Laptop GPU with8188MiB VRAM and approximately65.3GiB free on C at inspection. Installed Ollama models include `qwen3.5:4b` (about3.3GB, digest prefix `d8b0f5e9760c`) and `qwen2.5-coder:latest`. These are machine observations, not claims about available memory while other apps run.

- **Decision**: Start with the already installed `qwen3.5:4b` local model, pinned by digest. One inference at a time,4096-token initial context, chunk documents by page/section and validate schema/field spans. Keep cloud functionality disabled for local runs and bind Ollama to loopback. Do not download larger models merely because they exist.
- **Rationale**: The official library describes this4B quantized vision/text model, and its installed file size fits a sensible trial on8GB VRAM. Context/runtime/other apps consume additional memory, so weight size does not establish actual fit or speed. It must be evaluated on genuine source records before adopting performance/accuracy claims.
- **Alternatives considered**: Smaller local models if memory constrained; another4B model only if measured real-record quality warrants it. Larger8B+ models and a second mandatory model are deferred. A coding-focused model is not presumed suitable for evidence extraction.
- **Sources**: [Qwen3.5:4b](https://ollama.com/library/qwen3.5:4b), [Ollama Windows](https://docs.ollama.com/windows), [GPU support](https://docs.ollama.com/gpu), [runtime/context memory](https://docs.ollama.com/faq), [running-model inspection](https://docs.ollama.com/api/ps), [structured output](https://docs.ollama.com/capabilities/structured-outputs).

No result from an earlier synthetic smoke check is used as product data or acceptance evidence. The remaining model benchmark must use real retrieved material with its original URL/time/hash. No end-to-end local-model quality or latency result is claimed yet.

## D03 — Optional Gemini free tier

- **Decision**: Offer Gemini free-tier extraction as a configured alternative for public business facts and other demonstrably nonconfidential/nonpersonal inputs. The current pricing page lists free input/output for `gemini-3.5-flash-lite` and `gemini-3.8-flash`; start with explicitly configured Flash-Lite, no automatic paid fallback. Do not require a billing-enabled project.
- **Rationale**: Free tier can reduce local compute cost but actual account/model quota must be checked in AI Studio. Queue calls, cache allowed content, bound429 retries and expose quota exhaustion. There is no assumed numeric free RPM/RPD and no promise that additional keys increase the project quota.
- **Alternatives considered**: Paid Gemini is optional future work only. Google Search grounding, paid search APIs and paid verification services are not prototype dependencies. Local extraction works without any Gemini key.
- **Sources**: [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing), [project rate limits](https://ai.google.dev/gemini-api/docs/rate-limits), [Gemini terms](https://ai.google.dev/gemini-api/terms).

Unpaid-service terms allow product improvement/human review and instruct against sensitive/confidential/personal submissions. Public scraping does not automatically remove personal information: exclude unnecessary contact names/emails/phones and Udyam demographic fields. Private buyer requirements/documents stay local; user opt-in cannot waive provider restrictions. Never silently send a full private case to a free cloud model. Model extraction never authorizes fetches, confirms input or independently establishes a verdict.

## D04 — Local identity and file storage

- **Decision**: Two or more operator-provisioned local buyer accounts, pwdlib Argon2 password hashing and opaque database-backed sessions, HttpOnly/SameSite cookies, CSRF/Origin/Host validation and immediate logout invalidation. No public registration, email/reset provider or external identity server in this local release.
- **Rationale**: Preserves private signed-in case ownership without a Java identity service or hosting dependency. Use maintained hashing/session primitives, rate-limit login and keep credentials out of source/logs. Loopback development permits a narrowly scoped non-TLS cookie profile; any future network deployment requires TLS/security review.
- **Alternatives considered**: Keycloak/OIDC can be added for hosting later; anonymous auto-login would violate the clarified owner-isolation requirement.
- **Source**: [FastAPI password hashing guidance](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/).

Documents, retrieved pages, extraction artifacts and PDFs are ordinary immutable files under a configured private data root, separate from frontend public assets and Git. Generate case/UUID paths; authorize every API read and defend against path traversal/symlink/junction escapes. Use a tiny filesystem storage interface (put/read/delete/list) rather than implementing S3 compatibility. OS access is restricted to the application user's account; browser buyer isolation does not protect against the machine's privileged local operator.

## D05 — Free source collection and real local imports

- **Decision**: HTTPX for permitted public HTML/PDF/CSV/XLSX and Playwright only where an eligible public source needs rendering; preserve original content and dates. Use pdfplumber, pypdfium2/Tesseract and ReportLab locally. Government-export ingestion is a local source corpus for known-supplier checks, not feature003's discovery index.
- **Rationale**: Scraping, bulk files and local lookup avoid per-request fees. Retrieval failure triggers permitted free alternatives or honest unproven gaps, never mandatory paid upgrade or buyer portal work. Operator acquisition of a legitimately available bulk export is distinct from asking every buyer to perform manual lookups.
- **Alternatives considered**: Universal portal scraping is not feasible where CAPTCHAs/login/access restrictions apply. API Setu is conditional organization/publisher access, not an anonymous free API. Sandbox/FinAGG/Cashfree and IAF Enterprise are excluded from required implementation/acceptance.
- **Sources**: [HTTPX timeouts](https://www.python-httpx.org/advanced/timeouts/), [Playwright network](https://playwright.dev/python/docs/network), [pdfplumber](https://github.com/jsvine/pdfplumber), [Tesseract](https://tesseract-ocr.github.io/tessdoc/Installation.html), [ReportLab](https://docs.reportlab.com/reportlab/userguide/ch7_tables/).

| Free source | Concrete material / actual research finding | Use and limitation |
|---|---|---|
| Supplier sites | [Amruta Industries investment-cast pump parts](https://www.amrutaindustries.in/pumppartinvest.html) publishes relevant materials/components. | Real supplier self-report, not independent manufacturing/capacity proof. Crawl eligible supplied domains and product/contact/certificate links with attribution. |
| BIS | [QCO catalog](https://www.bis.gov.in/product-certification/products-under-compulsory-certification/?lang=en), [SchemeI](https://www.bis.gov.in/product-certification/products-under-compulsory-certification/scheme-1/?lang=en), [upcoming orders](https://www.bis.gov.in/upcoming-qcos-notified-and-due-for-implementation/?lang=en). | Initial live official document corpus with order/amendment/effective-date provenance. [BIS reuse policy](https://www.bis.gov.in/copyright-policy/?lang=en) permits accurate attributed reproduction except excluded third-party content; not every standards document inherits that permission. |
| MCA/OGD | [Company master-data catalog](https://data.gov.in/catalog/company-master-data), [MCA CDM](https://www.mcacdm.nic.in/company-master-details). | Candidate legitimate export import by exact CIN/LLPIN. Actual current export bytes/schema were not validated; the OGD page showed missing resources/sandbox text and indexed/live dates differed. Dated data supports its stated historical period, not current status. |
| Udyam exports | [Official registered-unit resource](https://www.data.gov.in/resource/list-msme-registered-units-under-udyam). | Advertises state/district downloads with login; actual export needs acquisition/schema validation. Advertised Daily granularity is not proof of current refresh. |
| Udyam QR | [Official portal](https://udyamregistration.gov.in/) describes dynamic QR verification; a real official QR-linked enterprise page was publicly readable in research. | Follow only the exact official link extracted from an actual obtained certificate, subject to source policy. Do not manufacture/enumerate tokens. No general API claim; omit unnecessary personal/demographic data. |
| GST | [Official search manual](https://tutorial.gst.gov.in/userguide/taxpayersdashboard/Search_Taxpayer_manual.htm) requires CAPTCHA. | Retain/validate supplied GSTIN syntax; show current registry check unavailable if no permitted free route exists. Syntax is not verification. |
| BIS licences | Current [Manak search](https://www.manakonline.in/MANAK/ApplicationLicenceRelatedrpt) is CAPTCHA-protected; [dated official licence PDF](https://bis.gov.in/wp-content/uploads/2020/08/Licenses_IS_9473_27082020.pdf) is an actual historical export. | The2020 mask list can validate historical import, never current casting compliance. Missing licence lookup cannot prove no licence needed. |
| API Setu | [Overview](https://docs.apisetu.gov.in/document-central/explore-apisetu/Overview.html), [official SOP](https://cdn.apisetu.gov.in/portal/assets/SOP-APISETU.pdf). | Optional later access subject to registration/publisher permission; no initial dependency or assumed free quota. |

[Government Open Data Licence–India](https://data.gov.in/Godl) permits reuse subject to its attribution/conditions/exclusions and does not guarantee future updates. Verify each actual resource's applicable licence. Imported records need publisher/sourceURL, obtained time, publication/cutoff, entity/geographic coverage, licence/attribution, original file hash, schema/import version and original row/page locator. Malformed or provenance-incomplete files are quarantined, not padded with invented rows. Obtaining an old file today does not refresh its facts.

## D06 — Free certificate evidence

- **Decision**: Use eligible public issuer pages/downloaded lists plus supplier certificates and accreditation directories. IAF is unavailable in the free automated path; no Enterprise account or successful IAF check is required to build/run the prototype.
- **Rationale**: Real public material supports narrow certificate/issuer assertions, with scope/freshness gaps explicit. Free IAF browser allowance provides neither API access nor scraping permission. A source's incomplete record cannot be strengthened by a model.
- **Alternatives considered**: IAF browser scraping is prohibited by its terms; its API/paid services are deferred. Paid credentials are not a readiness gate for the local product.

| Source | Real observed material | Evidence boundary |
|---|---|---|
| [NABCB](https://nabcb.qci.org.in/management-system-certification/) | Issuer, accreditation scheme/dates and scope references. | Accreditation of issuer, not validation of a supplier certificate. |
| [TUV Rheinland India list](https://www.tuv.com/content-media-files/india/pdfs/1009-certification-according-to-en-iso-13485/tuev-rheinland-india-list-of-clients.pdf) via [official issuer page](https://www.tuv.com/india/en/en-iso-13485-certification.html) | Actual names/certificate numbers for limited ISO13485 clients. | Historical/existence association; no invented current status/expiry. |
| [TUV SUD finder](https://exapps.tuvsud.com/SA/CertificateList/CertificateFinderTool) | Certificate-number lookup described for Mumbai-issued certificates, stated fortnightly update. | Narrow candidate; automatic form submission not verified. |
| [BSI real public profile](https://www.bsigroup.com/en-GB/products-and-services/assessment-and-certification/validation-and-verification/client-directory-profile/SBICAP-0047981876-001) | Actual company/address/certificate/scope/standard/start/expiry fields. | Public HTML observed; source-specific access/reuse policy still applies. Do not infer every issuer permits collection. |
| [IAF terms](https://www.iafcertsearch.org/policies/subscription-terms) | Browser scraping restriction; licensed API has separate terms. | Explicit unavailable coverage; try eligible free issuer alternatives, then unproven. |

Robots directives and reuse rights are distinct. [TUV robots](https://www.tuv.com/robots.txt) and [BSI robots](https://www.bsigroup.com/robots.txt) were inspected for the relevant public paths; neither constitutes blanket permission. No CAPTCHA bypass, paid-upgrade requirement, IndiaMART crawl or invented successful issuer response.

## D07 — Durability, evidence and zero-spend bounds

Retain canonical domain rows, immutable revisions/checklists/snapshots and independent leased checks. LangGraph Postgres checkpoints do not replace the persisted dispatcher. Use at-least-once jobs, stable operation keys, lease/fencing checks, separate SQLAlchemy sessions and restart recovery. Late/closed/deleted work cannot overwrite current snapshots or recreate deleted cases.

Only admissible actual observations can support proven/contradicted. Historical exports, copied-origin marketing and missing/conflicting identity or currency remain qualified or unproven under the shared policy. Required claims all proven qualifies; unproven/no required contradiction is a separate follow-up candidate. Real limited coverage may produce an empty shortlist. Never fabricate data to make a test pass or fill the shortlist.

Default cash-spend cap is zero. A free source/local dataset needs no paid-provider account, tariff configuration or purchase. Free Gemini calls require confirmed free-project eligibility and configured actual quota; no billing-enabled fallback, paid search grounding or paid API dispatch. Later paid adapters require a new explicit user decision and are outside current task dependencies.

Initial local limits: one active verification batch of up to5 suppliers, larger lists queued within the case; four outbound requests globally, one/domain, one browser context and one inference concurrently;20 pages and up to5 certificate PDFs per supplier, depth2;20-second requests, at most one transient retry,15-minute website collection budget within the30-minute five-supplier report target. Document parsing max20MiB/50pages; model chunks initially4K context. Respect tighter source/project quotas and stop honestly at limits. These are application choices, not published source limits or measured targets achieved.

Collector rejects internal/link-local/metadata targets, unsafe redirects and path/credential tricks, including browser subresources; treat source text as untrusted data and never executable instructions. [OWASP SSRF](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html), [prompt injection](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html).

## D08 — Local retention, backup and deletion

- **Decision**: Keep live case records/files until owner deletion. Immediate application access revocation, cancel/fence work, purge case files/temp/checkpoints/rows and verify before completion. Append/fsync a minimal deletion ledger outside managed snapshot restore paths; no cloud bucket or hosted ledger.
- **Rationale**: Meets durable local operation and prevents a stale app-managed restore from recreating a completed deletion. A crash-safe local journal is enough for the current trust/deployment boundary; same-disk copies do not protect against total disk failure.
- **Alternatives considered**: Mandatory remote backups, two S3 ledgers,35-day cloud retention and cloud disaster-recovery SLAs are removed. Arbitrary user-made copies and forensic SSD erasure cannot be guaranteed by application deletion.

Provide an explicit local snapshot command, not a required backup service: quiesce writes, save PostgreSQL state plus immutable files/checkpoints and a hash manifest; default retain the last3 app-managed snapshots to bound laptop disk growth. Physically remove each affected managed snapshot, or verify a sanitized reconstruction and physically remove its original before completion. Metadata invalidation alone is insufficient; inspect actual DB dumps, checkpoint copies, blobs and temporary archives for residual private content. Preserve other cases in active storage and independently acquired public corpus. Restore is offline and reconciles current deletion ledger before access/workers; missing ledger fails closed. Offline restore must remove all restored login sessions and pre-auth bootstrap state before traffic/workers and require fresh sign-in. Old cookies and CSRF tokens must fail, including sessions logged out or expired after snapshot capture; fresh owner login must succeed. Undeleted active cases have no age-based expiry. External user copies are outside managed deletion and are not represented as erased.

## D09 — Real-data validation and unclaimed work

Local acceptance needs zero paid keys and genuine public/authorized source records. Capture allowed actual bytes, URL, publisher, collection/publication dates, licence/hash and claim coverage. Repeatability uses those genuine captured records; their replay is labeled as replay, not live retrieval. Controlled network failure/restart/clock advancement tests keep the original domain records intact and disclose conditions; they must not manufacture official no-record/invalid/valid certificate results.

At least one actual public supplier page and official document retrieval/import must be demonstrated during implementation. Government exports whose files remain unavailable are recorded unavailable; no seeded replacement. Thirty-supplier accuracy evaluation requires real records and actual human-auditor labels across verdict/claim classes; until acquired/evaluated, SC-002 remains unmet. Use the same 30 real suppliers across six five-supplier cases as SC-002. Record active intervals for intake, corrections, confirmations, evidence review and decision/report actions; divide shared case time equally across evaluated suppliers and never double-count overlapping intervals. Report all 30 per-supplier totals and the maximum; every total must be under one hour. Separately record unattended collection and excluded actual waits. Missing any supplier timing leaves SC-003 unmeasured; a five-supplier timing run or average alone cannot pass it. The estimated manual baseline remains unverified. Confidential-data flows stay local even if a public-data Gemini path is configured. Local-model quality, account free quota, dataset schema coverage and end-to-end timing remain unmeasured.

Hosting, managed storage, paid APIs/models, enterprise identity, cloud backup/SLA, global discovery and recurring monitoring are deferred. Existing proof, ownership, confirmation and durable-history requirements remain in force.
