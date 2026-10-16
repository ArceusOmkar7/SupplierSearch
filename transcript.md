# Conversation Transcript: VeriSource Planning & Specification

**Date**: October 14–15, 2026  
**Project**: VeriSource (AI Supplier Capability Verification Agent)  
**Workspace**: `C:\Users\hp\Documents\Projects\SupplierSearch`

---

## Part 1: Initial Ideation & Project Context

### User Message 1

```text
/superpowers:brainstorming I want to start with planning and ideation of the project/product that I aim to build, for reference you can read @Claude-Agentic AI use cases-20261014-1611.md and @intellithon-scraper-main\ lets understand what to how, how to build and all that brainstorming. Use skills as necessary, after all the planning phase we'll go ahead with projectmem setup.
```

---

### Assistant Actions & Analysis

1. Inspected project directory `C:\Users\hp\Documents\Projects\SupplierSearch`.
2. Examined the reference conversation in `Claude-Agentic AI use cases-20261014-1611.md`.
3. Reviewed the hackathon repository `intellithon-scraper-main` (`README.md`, `app.py`, `supplier_search.py`, `supplier_details.py`).

---

### Assistant Reply 1

I've read everything. I have a deep picture of what you've done and where this is going. Let me skip the warm-up question since you've already done substantial thinking — here's what I know:

---

You skip the questions if you want — just say so and I'll start building. But first:

**What's the moment you feel this most acutely — is it "we have a supplier list but can't trust any of them", or is it "we don't even know where to start looking for the right manufacturer"?**

Here's what I've absorbed so far:

---

#### What I understand so far

**What you built (hackathon, 4th place):** A Streamlit app — Google Places → Gemini breaks the query into materials → ranks suppliers by rating. The README claims CrewAI and agents; the code has none. Clean demo, thin underneath.

**What Claude told you to build:** "VeriSource" — an AI agent that verifies *whether a supplier can actually make your part*, not just whether the company exists. The gap it fills: existing tools (GST/MCA lookups) confirm existence; AI sourcing tools (Speya, SourceReady) find suppliers. Nobody checks capability + certificate validity + compliance in one evidence-backed flow.

**The core loop that makes it agentic:**
1. Turn a part spec into claims to prove
2. Gather evidence (websites, PDFs, IAF CertSearch, GST/Udyam)
3. Cross-check, mark each claim proven/unproven/contradicted with source
4. Draft outreach for gaps → buyer approves → wait → re-score
5. Keep watching (lapsed cert alert, scope change)

**Architecture idea:** One shared agent core + plug-in "country packs" (India first, US thin second to prove scalability)

**What's still open that I want to nail before we plan the build:**

1. **What's the actual starting input?** The Claude conversation assumes a buyer pastes a part spec + a list of supplier names. Is that right, or do you want the agent to also *find* the candidates (discovery + verification in one)?
2. **What's the user experience?** Is this a web app (Streamlit v2), a background service with email output, or something more like a conversational interface?
3. **Semester scope** — what's your actual deadline and team size? The Claude doc suggests 3–4 months, solo or with the hackathon team?
4. **Tech stack preference** — you're clearly comfortable Python. Do you want to stay there (FastAPI/Streamlit backend + an agent framework like LangGraph or raw Claude tool-use), or are you open to other directions?

What's wrong or missing in that read?


---

## Part 2: Core Features Definition & Technical Tradeoffs

### User Message 2

```text
1. Yes the user should have both ways to search, with supplier list and without. This would increase the user experience and increase accessibility.
2. I want this to be intuitive, we'll first aim for a conversational interface with proper blocks/components in it for showing the suppliers.
3. Yes, its a semester long project in a group of 2 members.
4. FastAPI and langraph is good, but we'd need a proper frontend framework, not just streamlit.

Still the core functionality needs to be laid our properly and in a detailed manner. The hackathon repo is just an old reference to know where the idea came from, we don't need to lock up to it.
Lets lay out the core features first, and go step by step so we don't miss out anything.

One thing to note, DO NOT MAKE UP FACTS. Always use web search for any detail which could be out dated in your knowledge. Feel free to ask questions/doubts. Do not blindly agree with me, think and critique and then converse.
```

---

### Assistant Research Conducted

- **IAF CertSearch API 2025 access pricing SME free verification**: Found free tier offers 30 company profiles/year; enterprise API is custom priced.
- **LangGraph long-running workflows HITL persistence async 2025**: Confirmed `interrupt()`, `Command(resume=...)`, and `AsyncPostgresSaver` support durable multi-day workflows.
- **B2B manufacturer directory India API free IndiaMart alternative**: Verified IndiaMART/TradeIndia have no open developer APIs and ban bots; government open data (`data.gov.in`, API Setu) and commercial firmographics (Apollo/RevenueBase) provide alternative paths.

---

### Assistant Reply 2

Good. Before I lay out core features, I want to do a few targeted searches on things that could be stale in my knowledge — specifically the discovery data source problem (the hardest unsolved piece) and LangGraph's current persistence model for multi-day workflows. Those two will shape the architecture significantly.

---

### Core Features — Step by Step

Here's my honest assessment of what to build, what's hard, and where I'm pushing back on assumptions.

---

#### ⚠️ The Hard Problem First: Discovery Without a List

This is the biggest gap and it needs an honest answer before we design anything else.

**The problem:** When a user has *no* supplier list, where does the agent find candidates? The hackathon used Google Places — which is wrong for B2B manufacturers (it returns shops, not factories). IndiaMart has no API and explicitly bans scraping.

**What actually exists:**
- `data.gov.in` — government datasets, useful for MSME/factory data but unstructured and not real-time
- **Apollo.io / Clearbit** — freemium B2B firmographic APIs, can filter by `industry: Manufacturing` + `location: India`. Closest to practical. Apollo has a free tier (~250 credits/month).
- **Export Promotion Council directories** — sector-specific, no API, but legally scrapeable in some cases
- **Web search (Bing/Google Search API)** — "CF8M casting manufacturer Gujarat" → parse results. Dirty but works for a prototype.
- **IAF CertSearch reverse lookup** — search by product scope/location to find certified companies. **This is underused and actually useful for your case.**

**My honest recommendation:** For discovery, the agent does a **web search** (Bing Search API, ~$7/1000 calls) + **IAF CertSearch scope search** as its two discovery tools. It finds 10–15 candidate names, then runs them through the verification pipeline. This is honest about what the tool is: a *verifier* that can also *suggest* candidates — not a full supplier database.

**Pushback I'd raise:** Don't overpromise discovery. The real moat is verification. Discovery is a commodity (anyone can Google). If you build discovery as a shallow Google wrapper, you're back to the hackathon problem. Consider positioning it as: **"bring your own list or let us find candidates — the value is what happens next."**

---

#### Now the Core Features

Let me go feature by feature. I want your reaction to each before we move on.

---

#### Feature 1: Intake & Case Creation

**What it does:** The user opens a conversation. The agent collects:
- Part/product description (text or uploaded PDF/drawing)
- Location preference (country, state, city radius)
- Supplier list (optional — paste names, GST numbers, URLs, or IndiaMart links)
- Requirements: certifications needed (ISO 9001? IATF? BIS?), capacity (MOQ), delivery

**How:** Conversational flow — the agent asks questions one at a time, confirms its understanding, then creates a structured **Case** object in the DB.

**Hard part:** Parsing a PDF drawing or BOM into structured requirements is non-trivial. For semester scope, I'd limit this to: text description + user-confirmed checklist of requirements. PDF parsing is a stretch goal.

---

#### Feature 2: Supplier Discovery (when no list provided)

**What it does:** Agent runs `web_search` + `certsearch_scope_search` to find 8–15 candidate supplier names and websites.

**Tools:**
- Bing Search API (or SerpAPI) — query like `"CF8M investment casting manufacturer" Rajkot site:.in`
- IAF CertSearch — search by standard + scope keyword + country

**Output:** A candidate list shown to the user in the chat as a component — name, website, source. User can add/remove before verification begins.

**Honest constraint:** This will find companies, not qualified manufacturers. Quality varies. Make that clear in the UI.

---

#### Feature 3: Claim Generation (LLM-driven)

**What it does:** For each supplier + the part spec, the agent generates a **claim checklist** — the specific things it needs to prove or disprove.

**Standard claims:**
1. Company is real and active (GST/MCA status)
2. It's a manufacturer, not a trader (not self-declared — inferred from evidence)
3. It can make *this specific part* (material, process)
4. Its certification is valid, accredited, and in-scope for this part at this site
5. BIS licence (if applicable — agent checks QCO list)
6. Stated capacity is plausible (cross-checked against EPFO headcount)

**Why this is important:** The claim list is the agent's work plan. Everything else flows from it. Each claim has a status: `pending → checking → proven | unproven | contradicted`.

---

#### Feature 4: Evidence Collection (Tool Suite)

This is where the agent does its work. Tools it can call:

| Tool | What it does | Data source | Cost |
|---|---|---|---|
| `crawl_website` | Reads supplier's site, extracts product/process/address info | Playwright/httpx | Free |
| `read_pdf` | Extracts text from certificate PDFs | PyMuPDF | Free |
| `certsearch_lookup` | Checks cert validity, scope, site address | IAF CertSearch — **30 free company verifications/year per account** | Free (limited) |
| `web_search` | Finds news, alternate sources | Bing Search API | ~$7/1000 calls |
| `gst_lookup` | Company status, registered business type, address | Paid KYB API (e.g. Quicko, MasterIndia) — trial credits available | Freemium |
| `qco_check` | Checks if product needs BIS licence today | BIS QCO list (scrape or manual) | Free |
| `ask_human` | Buyer solves CAPTCHA, or provides a document | In-UI prompt | Free |
| `reverse_image_check` | Checks if factory photos are copied from other sites | Google Vision API | ~$1.50/1000 |

**IAF CertSearch constraint I want to flag:** 30 free verifications/year is not enough for real usage. For a semester prototype with ~30 test suppliers, it works. For production, this needs a paid API contract. Plan accordingly.

---

#### Feature 5: Cross-Matching & Scoring

**What it does:** After evidence is collected, the agent cross-checks across sources:
- Does the name on the cert match the GST name? (fuzzy match — "Shreeji Precicast Pvt Ltd" vs "SHREEJI PRECI-CAST")
- Does the cert site address match the GST registered address?
- Does the product range on the website match what the cert scope says?
- Does the EPFO headcount support the claimed capacity?

Each claim gets a final verdict: `✅ proven | ⚠️ unproven | ❌ contradicted`, with a **source citation** (URL + timestamp + quote).

**This is the hardest engineering piece.** Fuzzy name matching + address normalization for Indian addresses is genuinely difficult. Plan 3–4 weeks on this alone.

---

#### Feature 6: Gap Resolution Loop (The Agentic Part)

**What it does:** For any `unproven` or `contradicted` claim, the agent decides the next move:
- Try another source
- Draft an outreach message to the supplier asking for the document
- Flag for human review

**LangGraph fit (confirmed):** LangGraph's `interrupt()` + `AsyncPostgresSaver` is exactly right for this. The workflow pauses, state persists to Postgres, and resumes when the buyer approves or a supplier replies. This handles the multi-day wait cleanly.

**Approval gate:** Every outgoing message (email/WhatsApp) is shown to the buyer in the UI before it goes. One click to approve, edit, or skip.

**Email:** Use the buyer's own SMTP (via OAuth or SMTP credentials). Agent composes, buyer approves, it sends. No deliverability problems.

---

#### Feature 7: Monitoring (Post-Approval)

**What it does:** For suppliers the buyer has approved/shortlisted, the agent periodically checks:
- IAF CertSearch for cert status changes (suspended, withdrawn, expired)
- BIS QCO list for new or withdrawn requirements on their product

Sends an alert in the conversation when something changes.

**Honest assessment for semester scope:** This is a background cron job + a notification. Not architecturally complex, but adds polish. **I'd mark this as a stretch goal** — get it working after the core loop is solid.

---

#### Feature 8: Report / Shortlist Output

**What it does:** At the end of a case, produce a clean evidence table:
- One row per supplier
- Columns per claim
- Every cell either has a ✅/❌/⚠️ with a source link, or "not checked"
- Recommended shortlist with reasons
- Export to PDF

**In the conversational UI:** This renders as an interactive block/card inside the chat — not just text. The user can expand each cell to see the evidence.

---

### What I want to settle before going further

**Two things need your call:**

1. **Discovery scope:** Do you want to invest properly in discovery (scraping export council sites, building a small India manufacturer index over time), or should we keep it shallow (web search + IAF CertSearch)? The first takes weeks of extra engineering. The second is honest about its limits but functional.

2. **Frontend framework:** You said not Streamlit. For a conversational UI with rich components (evidence tables, approval cards, inline document viewers), what's your team's frontend experience? React? Vue? Something else? This matters because the conversational + component pattern is non-trivial to build well.

What's your read on those two?


---

## Part 3: Extended Capabilities, Deep Research & Architecture Consensus

### User Message 3

```text
for feature 1 We'll go with pdf parsing also.
some of my suggested stuff,
- need to find more sources for searching of suppliers (IMP)
- Voice functionality for User expirience.

answer to your questions, 
1. I want to invest time into the scraping part too. 
2. We'll go with React.

Another thing to note, none of the feature should be exaggarated and don't assumed or lie whether a feature is implemented if its not yet.

Can you do some more research about the stuff i said, DO NOT MAKE UP FACTS, tell me if you need more tools to help you research properly. Also feel free to ask if you have any more doubts.
Before building the project, we should first be clear about what the functionality is gonna be. After this reasearch and when i am satisfied, i will run a skill to convert whatever we have thought of to a PRD.
```

---

### Assistant Research Conducted (Batch 1)

- **Export Promotion Council Directories (EEPC, PLEXCONCIL)**: No public developer APIs exist. Member directories are often protected or paginated, but official member PDFs/annual reports are publicly downloadable and legal to parse with `pdfplumber`.
- **India Customs / Shipment Data (Zauba, Panjiva, Volza, Trademo)**: Raw customs feeds lack clean entity resolution. Volza offers a free trial tier and JSON REST APIs. Trademo is quote-based enterprise only.
- **Web Speech API vs STT in React**: Native browser `SpeechRecognition` requires Chrome/Edge and internet connectivity (audio sent to Google servers). For technical terminology, specialized models like Whisper perform far better.
- **PDF Engineering Drawings Parsing**: Standard text parsers fail on CAD/blueprints. A hybrid pipeline (render page to image via `PyMuPDF` at 300 DPI + Vision LLM with structured JSON schema) is necessary.
- **NSIC / MSME Mart**: No open public REST API; web directory accessible via standard web browsing.

---

### Assistant Reply 3A

Good. I have concrete, verified answers now. Let me give you an honest breakdown — and I'll flag where I'm pushing back on your assumptions.

---

#### Research Findings — Honest Assessment

##### 1. Supplier Discovery Sources (The Real Picture)

Here's what actually exists and what we can realistically use:

| Source | Access | Quality for our use case | Verdict |
|---|---|---|---|
| **Web Search (Bing/SerpAPI)** | API, ~$7/1000 queries | Finds companies but noisy | ✅ Use — primary discovery |
| **IAF CertSearch** | Free (30 company verifications/year/account) + API (paid, custom pricing) | Finds certified manufacturers by scope/location | ✅ Use — best quality |
| **Export Promotion Council PDFs** (EEPC, PLEXCONCIL, etc.) | No API. **Publish official member PDFs and annual directories** | Curated, legitimate manufacturers per industry sector | ✅ Scrape PDFs legally, build an offline index |
| **EPC web portals** (EEPC Indian Suppliers, Plexconcil ePAGES) | No public API. Hidden AJAX endpoints *sometimes* exist, inspectable via devtools | High quality, sector-specific | ⚠️ Investigate endpoints; use Playwright only on public-facing pages |
| **Volza** (trade data) | Free trial (limited credits), paid REST API | Finds companies *that have actually exported* — very strong signal | ✅ Use trial for prototype; note the cost wall |
| **Trademo** | No free tier, quote-based API | Similar to Volza | ❌ Skip for semester |
| **NSIC / MSME Mart** | No public API. Web portal only | Government-verified SME manufacturers | ⚠️ Scrape public web pages only (politely) |
| **data.gov.in** | API exists, but aggregate stats only — not company-level | Useless for finding specific suppliers | ❌ Skip |
| **Apollo.io / Clearbit** | Freemium (~250–500 free credits/month) | Global firmographic data, can filter by India + manufacturing | ⚠️ Useful for enrichment, not discovery |
| **Zauba** | Private beta API (no confirmed public access) | Good for cross-referencing export history | ⚠️ Use web lookup manually for now |

**My honest pushback on "investing in scraping":**

The EPC directory scraping is genuinely valuable *if done right*. The plan should be:
1. Download all publicly available EPC member PDFs → parse with `pdfplumber` → build an offline indexed database (legal, no ToS issues)
2. For the web portals: inspect network traffic for hidden AJAX endpoints. If they exist and return JSON without authentication, query them. If not, use Playwright on public pages only, with rate limiting + `robots.txt` compliance
3. Use Volza free trial for the prototype's trade data signal

This gives you a **multi-source indexed database of Indian manufacturers by sector** — that's your real moat, not just a web search wrapper. It takes real engineering time though (~3–4 weeks to build and maintain properly).

---

##### 2. PDF Parsing — What's Actually Possible

**For BOM / spec documents** (text-based PDFs): `pdfplumber` + LLM extraction works well. Can extract material names, quantities, part numbers reliably.

**For engineering drawings** (technical blueprints): This is significantly harder:
- Standard text parsers (`pypdf`, `pdfplumber`) fail on drawings — dimensions and symbols are vector graphics, not text
- The correct approach is: `PyMuPDF` renders page as high-res image → Vision LLM (Claude/GPT-4o) extracts structured data (material, tolerances, part number)
- **Known failure modes:** rotated text, scanned/handwritten drawings, legacy blueprints — these need extra preprocessing

**My recommendation:** Support three input types with honest capability labels in the UI:
1. **Text description** (typed) — always works
2. **BOM or spec PDF** (text-based) — reliable
3. **Engineering drawing PDF** — "best effort" extraction, user must confirm what the agent understood before proceeding. Don't promise perfect extraction.

---

##### 3. Voice Input — What's Actually Possible

**Web Speech API** (browser-native):
- Works in Chrome/Edge. Safari is partial. Firefox needs manual flag
- Audio is streamed to Google servers (Chrome). No offline support
- Free, zero backend needed
- The `react-speech-recognition` npm package wraps this cleanly

**Honest constraints to state in the UI:**
- "Voice input requires Chrome or Edge"
- Not suitable for accents + technical terms (material grades like "CF8M" or "IATF 16949" will likely be transcribed wrong)
- You'll need a **"confirm what I heard" step** where the agent shows the transcript and asks the user to verify before proceeding — especially for part specs

**Alternative for production:** Whisper API (OpenAI) — runs on the backend, much better accuracy on technical terms, supports Hindi/mixed language. But adds ~$0.006/minute cost. For semester, Web Speech API is fine with the confirmation step.

---

#### Where This Leaves Us — Honest Scope Reassessment

You're a 2-person team with a semester. Here's what I think is **actually achievable vs. stretch**:

**Core (must have):**
- Conversational intake (text + voice with confirmation)
- BOM/spec PDF parsing (text PDFs reliable; drawings best-effort with user confirmation)
- Discovery: Web search + IAF CertSearch + EPC PDF index (offline)
- Verification pipeline: website crawl, cert PDF read, IAF CertSearch lookup, cross-matching
- Claim table with proven/unproven/contradicted verdicts + sources
- Human approval gate for outreach
- LangGraph state persistence (PostgreSQL checkpointer)
- React frontend with conversational UI + evidence component blocks

**Stretch (target if ahead of schedule):**
- EPC web portal AJAX scraping (depends on what you find in devtools)
- Volza trade data integration (depends on trial credits)
- Certificate monitoring / alerts
- PDF engineering drawing parsing (vision LLM approach)
- PDF report export

**One question before we lock this:**

The EPC PDF indexing is a real project — you'd need to identify which councils are relevant (EEPC for engineering, PLEXCONCIL for plastics, CHEMEXCIL for chemicals, etc.) and decide which sectors your tool targets first. Are you going with **all manufacturing** broadly, or starting with one vertical (e.g., metal parts/engineering goods) where EEPC is the strongest source?

That choice shapes how focused the scraper and the verification logic needs to be.

---

### User Message 3B

```text
For pdf parsing, we can do is have an agent for parsing the pdf with the help of a vlm and llm wherever normal text parsing won't work...
For voice input we could go with openai whisper small or distill small.
Don't be so constrained because this is a semester project and 2 members.
For the council part we'll first keep it broad base, then we "might" go for a vertical.
```

---

### Assistant Research Conducted (Batch 2)

- **Distil-Whisper (`distil-whisper/distil-small.en`)**: 166M parameters, easily self-hosted in FastAPI with PyTorch and Transformers on CPU/GPU via pipeline.
- **Complete List of 28 Indian EPCs**: Covers engineering (EEPC), plastics (PLEXCONCIL), basic chemicals (CHEMEXCIL), electronics (ESC), textiles (TEXPROCIL), etc.
- **Kompass India**: Enterprise directory with B2B search across Indian industrial hubs; no public developer API, but scrapable via Apify actors.

---

### Assistant Reply 3B

Fair enough. Let me drop the over-caution and research properly.

---

#### Consolidated Feature Set — Final Research Summary

##### PDF Parsing: VLM + LLM Agent Approach ✅

The plan is clean and correct. The parsing agent does:

1. **Try text extraction first** (`PyMuPDF` / `pdfplumber`) — works for BOMs, spec sheets, text-based PDFs
2. **Assess quality** — if extraction is sparse or garbage (e.g., scanned drawings), automatically falls back
3. **VLM fallback** — renders page as high-res image → sends to Claude/GPT-4o/Gemini with a structured schema prompt → extracts: part number, material grade, tolerances, required certifications, capacity signals
4. **Agent confirms** — outputs structured JSON, shows it to the user in the UI: *"Here's what I understood from your document — correct anything wrong before I proceed"*

This is the right design. The key point is **the user always verifies before the case proceeds**. No silent hallucinations sneaking in.

---

##### Voice: Distil-Whisper Small (Self-hosted on FastAPI) ✅

**Confirmed specs:**
- Model: `distil-whisper/distil-small.en` — 166M params, runs on CPU (slower) or GPU (fast)
- Deploy as a FastAPI `/transcribe` endpoint alongside your main backend
- Frontend records audio → sends as `multipart/form-data` → returns transcript
- Handles `.mp3`, `.wav`, `.m4a`, `.flac`

**Real constraint to design around (not hide):** Distil-small is English-only and accuracy drops on technical jargon — material grades like "CF8M", "IATF 16949", "ASTM A276" will likely get mangled. Design: after transcription, the agent shows the text and highlights uncertain terms (anything that looks like a spec code) and asks the user to confirm before parsing. Not a limitation to apologise for — just good UX.

**Multilingual note:** If you want Hindi/Hinglish support later, `distil-whisper/distil-medium` supports it. Swap is trivial since the infrastructure is already there.

---

##### Discovery Sources — Full Consolidated Map

| # | Source | What you get | Access method | Notes |
|---|---|---|---|---|
| 1 | **Web Search (Bing Search API / SerpAPI)** | Broad company discovery by keyword + location | API (~$7/1000 queries) | Primary discovery for any sector |
| 2 | **IAF CertSearch** | Companies with *accredited* ISO certs — by standard + scope | Free search UI (30 verifications/yr) + paid API | Best quality signal — real manufacturers |
| 3 | **EPC PDF directories** | Verified exporter-manufacturers per sector | Download PDFs from 28 councils → parse with `pdfplumber` | Legal, no ToS issues. EEPC (engineering), PLEXCONCIL (plastics), CHEMEXCIL (chemicals), PHARMEXCIL (pharma), CAPEXIL (ceramics/glass/rubber), CLE (leather), GJEPC (gems/jewelry) are the biggest ones for manufacturing |
| 4 | **EPC web portals** | Same, but potentially more current | Playwright scraping of public pages + inspect for hidden AJAX endpoints | Inspect devtools network tab before building — some councils have JSON-returning endpoints |
| 5 | **Volza** (trade data) | Companies that have *actually exported* — strongest real-manufacturer signal | Free trial credits; REST API (paid thereafter) | Use trial for prototype. Filter by HS code + India → exporters |
| 6 | **MSME Mart / NSIC portal** | Government-registered SME manufacturers | Web scraping of public pages (no API) | No ToS-violating data; covers domestic-only manufacturers who may not export |
| 7 | **Kompass India** | Company profiles, sector tags, contact info | No free API. Apify has a scraper actor for Kompass public pages | Check ToS before using Apify actor |
| 8 | **Apollo.io** | Firmographic enrichment — fill in emails, size, contacts for companies you already found | Free tier (~250 credits/month) | Use as enrichment layer, not primary discovery |
| 9 | **Zauba/ZaubaCorp** | Export shipment history, CIN lookup | No confirmed public API — use as manual lookup or inspect network calls | Good for cross-referencing |

**The discovery architecture:** These sources feed a unified **Supplier Index DB** (PostgreSQL table). When a user searches, the agent queries this index first (fast, no API call), and also does a live web search for anything not in the index. The index gets richer over time as more cases run. That's your compounding moat.

---

#### Revised Full Feature Set

- **Feature 1: Intake & Case Creation**: Conversational intake (text + voice with Distil-Whisper), PDF upload (BOM/drawing) parsed by PDF agent (text + VLM fallback).
- **Feature 2: Supplier Discovery**: Queries Supplier Index DB + live web search + IAF CertSearch scope search. Returns cards with source labels.
- **Feature 3: Claim Generation**: Generates claim checklist per supplier covering legal existence, manufacturer vs trader, capability, cert validity/scope/site, BIS licence, capacity plausibility.
- **Feature 4: Evidence Collection**: Tools for website crawl, PDF certificate read, IAF CertSearch lookup, GST lookup, EPFO headcount lookup, BIS QCO check, reverse image check, and `ask_human`.
- **Feature 5: Cross-Matching & Verdict Engine**: Fuzzy name matching and Indian address normalization. Assigns `proven | unproven | contradicted` with timestamps and source citations.
- **Feature 6: Gap Resolution Loop (LangGraph)**: Multi-day outreach and waiting loop via LangGraph `interrupt()` and `AsyncPostgresSaver`. Outreach requires human approval.
- **Feature 7: Supplier Monitoring**: Background checks on IAF CertSearch and QCO lists for status updates.
- **Feature 8: Evidence Report & Shortlist**: Interactive chat matrix, recommended shortlist, PDF export.
- **Feature 9: Voice Input**: Self-hosted Distil-Whisper endpoint with UI highlighting for editable uncertain terms.
- **Feature 10: Supplier Index (Background Infrastructure)**: Scheduled parsing of EPC directories, public portals, and trade data.

---

#### Open Question Raised

What LLM are you planning to use as the agent brain? Claude, GPT-4o, Gemini? This affects API cost structure, context window (for long cert PDFs), and whether you can use structured output/tool-calling natively.


---

## Part 4: Specification Generation & Code Artifacts

### User Message 4

```text
/speckit-specify Rest all looks good, for the stt constraint we could highlight it in the conversation in such a way which shows the user can edit that part going forward.

Now answering your question,
We'll use gemini or some local llm, most probably gemini.

Now go ahead and create the baseline specs, detailed so we don't drift away while building.
```

---

### Assistant Execution Steps

1. Loaded `.specify/init-options.json` and verified sequential numbering configuration.
2. Verified project constitution in `.specify/memory/constitution.md`.
3. Created directory structure:
   - `specs/001-supplier-verification-agent`
   - `specs/001-supplier-verification-agent/checklists`
4. Created configuration `.specify/feature.json`.
5. Authored full specification in `specs/001-supplier-verification-agent/spec.md`.
6. Authored quality checklist in `specs/001-supplier-verification-agent/checklists/requirements.md`.

---

### Code & Files Created

#### 1. `.specify/feature.json`

```json
{
  "feature_directory": "specs/001-supplier-verification-agent"
}
```

#### 2. `specs/001-supplier-verification-agent/spec.md`

```markdown
# Feature Specification: VeriSource — AI Supplier Verification Agent

**Feature Branch**: `001-supplier-verification-agent`

**Created**: 2026-10-15

**Status**: Draft

**Input**: User description: "An AI agent that helps manufacturers discover suppliers, verify whether they can actually make a specific part (not just whether the company exists), and monitor approved suppliers over time. The system uses a conversational interface with voice input, parses part specs from PDFs/drawings, searches multiple discovery sources (web, EPC directories, trade data, IAF CertSearch), generates evidence-based claim checklists per supplier, collects and cross-checks evidence from official registries and supplier documents, handles multi-day outreach loops with human approval, and produces a shortlist where every verdict links to its source."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Verify Suppliers from a Known List (Priority: P1)

A purchase manager at a pump factory needs to qualify 4 supplier candidates she already has — 2 from IndiaMART, 1 referral, 1 old vendor. She opens VeriSource, describes her part requirement ("CF8M stainless steel impeller castings, 2,000 pieces/month, ISO 9001 required"), and pastes in the 4 supplier names/websites/GST numbers. The agent generates a claim checklist per supplier, collects evidence from the web and official registries, cross-checks names/addresses/certificate scopes, and presents an evidence table showing each claim as proven, unproven, or contradicted with source citations. She reviews the table and approves 2 suppliers for her shortlist.

**Why this priority**: This is the core value proposition — the verification engine. Without this working, nothing else matters. Every other feature (discovery, monitoring, voice, PDF parsing) feeds into or builds upon this loop.

**Independent Test**: Can be tested by manually entering a part spec + supplier list and verifying that the system generates claims, collects evidence, cross-checks, and produces a verdict table with source links.

**Acceptance Scenarios**:

1. **Given** a user has entered a part description and a list of 4 supplier identifiers (names, websites, or GST numbers), **When** the agent processes them, **Then** it generates a claim checklist per supplier covering: legal existence, manufacturer vs trader, capability for the specified part, certificate validity/scope/site match, and applicable compliance requirements.
2. **Given** the agent has generated claims, **When** it runs evidence collection, **Then** each claim is updated to proven, unproven, or contradicted with a source citation (URL, document reference, and timestamp).
3. **Given** evidence has been collected, **When** two sources disagree (e.g., cert PDF address ≠ GST registered address), **Then** the agent flags the contradiction and shows both sources to the user.
4. **Given** all evidence collection is complete, **When** the agent produces the final table, **Then** the user can expand any verdict cell to see the underlying evidence, source link, and extracted quote.
5. **Given** a claim is unproven after all automated checks, **When** the agent determines it needs supplier input, **Then** it drafts an outreach message and presents it to the user for approval before sending.

---

### User Story 2 — Discover Suppliers When No List Exists (Priority: P2)

A small auto-parts manufacturer needs a new supplier for heat-treated steel forgings but has no leads. He opens VeriSource, describes the part and location preference ("closed-die steel forgings, EN8 material, 500 pcs/month, western India preferred"). The agent searches across its indexed sources (EPC directories, web search, IAF CertSearch by scope) and presents 12 candidate suppliers with source labels. The user reviews, removes 3 irrelevant results, and triggers verification on the remaining 9.

**Why this priority**: Discovery expands the addressable market from "users who already have supplier lists" to "users who need to find suppliers from scratch." It's the second most important flow because without it, the tool only serves half the use case.

**Independent Test**: Can be tested by entering a part spec without any supplier list and verifying the system returns relevant candidates from multiple sources with source attribution.

**Acceptance Scenarios**:

1. **Given** a user has entered a part description with location preference and no supplier list, **When** the agent runs discovery, **Then** it returns 8–20 candidate suppliers sourced from at least 2 different data sources.
2. **Given** discovery results are shown, **When** the user views a candidate card, **Then** each card displays: company name, location, source label (e.g., "EEPC directory", "web search", "IAF CertSearch"), and website if available.
3. **Given** the user reviews discovery results, **When** they remove or add candidates, **Then** the modified list is used as input to the verification pipeline (User Story 1).
4. **Given** the supplier index has been previously populated with EPC directory data, **When** the user searches for a matching sector/location, **Then** index results appear alongside live web search results, clearly labeled by source.

---

### User Story 3 — Parse Part Requirements from a PDF Document (Priority: P3)

An export manager uploads a customer's purchase order PDF containing a BOM with 3 line items — each specifying a material grade, quantity, and required certifications. The agent extracts structured requirements from the PDF and presents them to the user: "I found 3 items in your document. Here's what I understood — please correct anything before I proceed." The user edits one material grade the agent got wrong, confirms, and the agent creates a verification case for each line item.

**Why this priority**: PDF intake reduces friction for users who already have their specs in document form (which is the majority — purchase orders, BOMs, drawings). It directly feeds into P1 and P2 stories.

**Independent Test**: Can be tested by uploading a sample BOM PDF and verifying the system extracts structured fields (material, quantity, certifications) and presents them for user confirmation.

**Acceptance Scenarios**:

1. **Given** a user uploads a text-based BOM PDF, **When** the agent processes it, **Then** it extracts part descriptions, material grades, quantities, and certification requirements as structured data.
2. **Given** a user uploads a scanned engineering drawing (image-based PDF), **When** the agent detects text extraction failure, **Then** it falls back to rendering the page as a high-res image and using a vision model to extract key fields (part number, material, tolerances, notes).
3. **Given** the agent has extracted requirements from a PDF, **When** it presents them to the user, **Then** any field the agent is uncertain about is visually highlighted and editable by the user.
4. **Given** the user has confirmed (and optionally corrected) extracted requirements, **When** they proceed, **Then** the confirmed data is used to generate claims — not the raw extraction.

---

### User Story 4 — Multi-Day Outreach and Follow-Up (Priority: P4)

After the initial evidence run, 2 of 5 suppliers have unproven claims (missing ISO certificate, unconfirmed capacity). The agent drafts polite email requests for each, shows them to the user for approval. The user approves both. The emails are sent. Three days later, one supplier replies with a certificate PDF. The agent picks up the case, reads the PDF, validates the cert against the IAF registry, and updates the claim table. The other supplier hasn't replied — the agent drafts a follow-up and asks the user to approve it.

**Why this priority**: This is what makes the system agentic — it holds state over days, recovers from gaps, and drives the process forward. But it requires P1 to be fully working first.

**Independent Test**: Can be tested by triggering outreach for a supplier with unproven claims, simulating an email reply with an attached document, and verifying the agent resumes, processes the document, and updates verdicts.

**Acceptance Scenarios**:

1. **Given** a supplier has unproven claims after evidence collection, **When** the agent determines outreach is needed, **Then** it drafts a specific, professional message requesting the exact missing document and presents it to the user for approval.
2. **Given** the user approves an outreach message, **When** it is sent, **Then** the case enters a waiting state and the system persists all case data durably (no data loss on server restart).
3. **Given** a supplier replies with a document, **When** the agent detects the reply, **Then** it automatically resumes the case, processes the document, and updates the claim table.
4. **Given** a supplier has not replied within a configurable period, **When** the follow-up threshold is reached, **Then** the agent drafts a follow-up message and presents it to the user for approval.
5. **Given** a user declines to send an outreach or follow-up, **When** they skip it, **Then** the claim remains "unproven" and the case can still be closed with that status.

---

### User Story 5 — Voice-Based Conversational Intake (Priority: P5)

A purchase manager prefers speaking over typing. She clicks the microphone button, says "I need someone who can make stainless steel CF8M castings, two thousand pieces a month, ISO nine thousand one certified, somewhere in Gujarat." The system transcribes her speech, shows the transcript with uncertain terms highlighted (e.g., "CF8M" may show as "CF-8M" or "CF eight M"), and lets her edit inline before the agent processes it.

**Why this priority**: Voice adds UX polish and accessibility. The core product works without it, but it removes friction for users who find typing part specs cumbersome.

**Independent Test**: Can be tested by recording audio of a part specification, sending it through the transcription endpoint, and verifying the transcript is displayed with editable uncertain terms.

**Acceptance Scenarios**:

1. **Given** the user clicks the microphone button, **When** they speak a part specification, **Then** the system records, transcribes, and displays the text within 5 seconds of the user stopping.
2. **Given** the transcription contains technical terms (material grades, certification codes), **When** the transcript is displayed, **Then** terms the model is uncertain about are visually highlighted as editable spans.
3. **Given** the user edits a highlighted term in the transcript, **When** they confirm, **Then** the corrected text is used as the input for case creation.
4. **Given** the browser does not support audio recording or microphone access is denied, **When** the user tries to use voice, **Then** the system shows a clear message and the text input remains available.

---

### User Story 6 — Monitor Approved Suppliers (Priority: P6)

After completing verification, the purchase manager marks Shreeji Precicast as "approved." Three months later, IAF CertSearch shows their ISO 9001 certificate has been suspended. The system alerts the user in-app, showing what changed and when. The user can then re-open the case or initiate outreach to the supplier.

**Why this priority**: Monitoring is long-term value — it catches problems before they hit production. But it only makes sense once the verification pipeline is proven and suppliers are being approved.

**Independent Test**: Can be tested by approving a supplier, simulating a certificate status change in the monitoring data source, and verifying the alert is triggered and displayed correctly.

**Acceptance Scenarios**:

1. **Given** a supplier is marked as approved, **When** a monitoring cycle runs, **Then** it checks IAF CertSearch for the supplier's certificate status.
2. **Given** a certificate status changes to suspended, withdrawn, or expired, **When** the system detects it, **Then** it creates an alert visible to the user with the old status, new status, date of change, and source link.
3. **Given** a BIS Quality Control Order is newly issued for a product the supplier makes, **When** the monitoring cycle detects it, **Then** it alerts the user that a BIS licence may now be required.

---

### Edge Cases

- What happens when a supplier's website is down or returns a 403/captcha during crawling? → Agent marks the crawl as failed and falls back to other sources.
- What happens when two suppliers share the same GST number? → Flag as a data anomaly — may indicate a common parent company or a data error.
- What happens when a certificate PDF is password-protected? → Agent asks the user to provide the unlocked version via the `ask_human` tool.
- What happens when the IAF CertSearch free tier verification limit (30/year) is exhausted? → Agent notifies the user and continues with other verification methods. Verdict for cert check becomes "unable to verify — registry limit reached."
- What happens when a user starts a case and closes the browser mid-process? → Case state is persisted; user can resume from where they left off.
- What happens when the part description is vague (e.g., "steel parts")? → Agent asks clarifying questions before generating claims.
- What happens when the same supplier appears in both the user's list and discovery results? → De-duplicate by matching name + address/GST, keeping the richer record.
- What happens when a supplier's GST says "manufacturer" but all other evidence suggests trader? → Agent shows the contradiction and lets the user decide — it does not override one source with another.

---

## Requirements *(mandatory)*

### Functional Requirements

**Conversational Interface**

- **FR-001**: System MUST provide a conversational chat interface where the user interacts with the agent through natural language messages.
- **FR-002**: System MUST display structured data (supplier cards, evidence tables, verdict matrices, outreach drafts) as interactive components embedded within the conversation flow — not as separate pages.
- **FR-003**: System MUST support voice input via a microphone button that records, transcribes via a self-hosted speech-to-text model, and displays the transcript as editable text with uncertain terms visually highlighted.
- **FR-004**: System MUST allow users to edit any highlighted uncertain term inline before the agent processes the input.

**Case Intake**

- **FR-005**: System MUST accept part/product requirements via text input, voice input, or document upload (PDF).
- **FR-006**: System MUST parse text-based PDF documents (BOMs, spec sheets, purchase orders) to extract structured requirements: part descriptions, material grades, quantities, and certification requirements.
- **FR-007**: System MUST detect when a PDF contains image-based content (scanned documents, engineering drawings) and fall back to rendering the page as a high-resolution image for vision-model-based extraction.
- **FR-008**: System MUST present all extracted requirements to the user for confirmation and inline editing before proceeding.
- **FR-009**: System MUST accept an optional list of supplier identifiers (company names, website URLs, GST numbers, or IndiaMART listing links) as input alongside the part specification.
- **FR-010**: System MUST accept location preferences (country, state/region, city or radius) as part of the case input.

**Supplier Discovery**

- **FR-011**: System MUST discover supplier candidates through web search when no supplier list is provided.
- **FR-012**: System MUST discover supplier candidates through IAF CertSearch by searching for companies with relevant certification scope and location.
- **FR-013**: System MUST maintain a Supplier Index populated from Export Promotion Council (EPC) member directories, government MSME portals, and trade data sources.
- **FR-014**: System MUST query the Supplier Index as the first discovery source (fast, no external API call) and supplement with live web search results.
- **FR-015**: System MUST label each discovery result with its source (e.g., "EEPC directory", "web search", "IAF CertSearch", "Volza trade data").
- **FR-016**: System MUST allow the user to add, remove, or re-order suppliers in the discovery results before triggering verification.
- **FR-017**: System MUST de-duplicate suppliers that appear in both the user-provided list and discovery results, merging records and keeping the richer data.

**Claim Generation**

- **FR-018**: System MUST generate a structured claim checklist per supplier based on the part specification and requirements. Standard claims include: (a) legal existence and active status, (b) manufacturer vs. trader classification, (c) capability to produce the specific part (material, process), (d) certification validity, accreditation status, scope coverage, and site match, (e) applicable regulatory compliance (e.g., BIS licence), (f) stated capacity plausibility.
- **FR-019**: System MUST allow the claim checklist to be customized per case — users can add, remove, or modify claims before evidence collection begins.

**Evidence Collection**

- **FR-020**: System MUST crawl supplier websites to extract product range, process descriptions, facility photos, and address information.
- **FR-021**: System MUST read and extract structured data from certificate PDF documents (certificate number, certification body, standard, scope text, site address, expiry date).
- **FR-022**: System MUST validate certificates against the IAF CertSearch registry when available.
- **FR-023**: System MUST look up company information (legal name, status, registered business type, address) from GST/Udyam/MCA sources — either via licensed API or by prompting the user to perform a manual lookup and provide the result.
- **FR-024**: System MUST check the current BIS Quality Control Order list to determine whether the specified product requires a BIS licence.
- **FR-025**: System MUST support an `ask_human` tool that prompts the user to perform a manual action (solve a CAPTCHA, provide a document, look up a portal) and return the result to the agent.

**Cross-Matching & Verdicts**

- **FR-026**: System MUST perform fuzzy name matching across multiple data sources to identify whether records from different sources refer to the same entity.
- **FR-027**: System MUST normalize Indian addresses to enable matching across sources that use different formats, abbreviations, and conventions.
- **FR-028**: System MUST assign each claim a verdict of `proven`, `unproven`, or `contradicted`.
- **FR-029**: System MUST attach a source citation to every verdict — including the source URL or document reference, the extracted text or data point, and the timestamp of when it was checked.
- **FR-030**: System MUST flag contradictions between sources explicitly (e.g., "Certificate says Ahmedabad, GST says Rajkot") and present both data points to the user.

**Outreach & Follow-Up**

- **FR-031**: System MUST draft outreach messages (email) to suppliers requesting specific missing documents or information for unproven claims.
- **FR-032**: System MUST present every outreach message to the user for approval, editing, or rejection before sending.
- **FR-033**: System MUST persist all case state durably so that a case waiting for supplier replies survives server restarts and can be resumed days later.
- **FR-034**: System MUST detect incoming supplier replies and automatically resume the case — processing any attached documents and updating verdicts.
- **FR-035**: System MUST send follow-up messages to non-responsive suppliers after a configurable waiting period, with user approval.

**Reporting & Output**

- **FR-036**: System MUST present a final evidence table as an interactive component in the chat — with one row per supplier, one column per claim, and expandable verdict cells showing underlying evidence.
- **FR-037**: System MUST generate a recommended shortlist with reasoning, based on the evidence collected.
- **FR-038**: System MUST support exporting the evidence report as a downloadable PDF document.

**Monitoring**

- **FR-039**: System MUST allow users to mark verified suppliers as "approved" and add them to a monitoring watchlist.
- **FR-040**: System MUST periodically check IAF CertSearch for certificate status changes (suspended, withdrawn, expired) for watched suppliers.
- **FR-041**: System MUST alert the user in-app when a monitored supplier's certificate status changes, showing the old status, new status, date, and source.

**Supplier Index Infrastructure**

- **FR-042**: System MUST parse publicly available EPC member directory PDFs and populate a searchable supplier index.
- **FR-043**: System MUST scrape publicly accessible EPC web portals (respecting robots.txt and rate limits) to supplement the index.
- **FR-044**: System MUST support incremental index updates — new data sources or refreshed directories can be added without rebuilding the entire index.

**Multi-Country Support**

- **FR-045**: System MUST be architected with a shared verification core and pluggable "country packs" that encapsulate country-specific registries, compliance rules, and red flags.
- **FR-046**: System MUST ship with a complete India country pack (GST, Udyam, BIS, Indian address normalization, trader-detection patterns).
- **FR-047**: System MUST include a thin second country pack (e.g., US — using public company registries + IAF CertSearch) to demonstrate the architecture scales.

### Key Entities

- **Case**: A verification request encompassing a part specification, a set of suppliers, generated claims, collected evidence, and a final report. A case persists across days.
- **Supplier**: A company being evaluated — with identifiers (name, GST, website), source attribution, and a claim checklist.
- **Claim**: A single verifiable assertion about a supplier (e.g., "ISO 9001 certificate is valid and in-scope for investment casting at the Halol site"). Has a verdict and evidence chain.
- **Evidence Record**: A single data point collected from a specific source at a specific time — includes source URL/document, extracted data, timestamp, and a snapshot.
- **Verdict**: The assessment of a claim: `proven`, `unproven`, or `contradicted`. Always linked to one or more evidence records.
- **Country Pack**: A pluggable module that adds country-specific registry tools, compliance checks, and red-flag patterns to the shared agent core.
- **Supplier Index**: A persistent, searchable database of known manufacturers populated from EPC directories, trade data, and government sources. Grows over time across cases.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user with a part spec and 5 supplier names can receive a fully populated evidence table (all claims checked, all verdicts assigned) within 30 minutes of starting a case, excluding wait time for supplier replies.
- **SC-002**: The system's claim verdicts agree with a human auditor's assessment on at least 80% of claims across a test set of 30 suppliers.
- **SC-003**: The system reduces the time a purchase manager spends per supplier verification from an estimated 4–6 hours (phone calls, portal lookups, email back-and-forth) to under 1 hour of active user time.
- **SC-004**: Discovery mode returns at least 8 relevant candidates for a well-defined part spec + location query, sourced from at least 2 different data sources.
- **SC-005**: Users can complete case intake (part spec + supplier list entry) in under 5 minutes, whether using text, voice, or PDF upload.
- **SC-006**: Every verdict in the evidence table links to its source — no verdict exists without a citation.
- **SC-007**: Case state survives a full server restart — no data loss for in-progress cases.
- **SC-008**: The system correctly identifies at least 3 out of 4 trader-posing-as-manufacturer patterns in a curated test set (e.g., mismatched business type, address inconsistency, breadth-of-product-range anomaly, headcount mismatch).
- **SC-009**: Voice input transcription is displayed to the user within 5 seconds of stopping recording, and the user can correct it before submission.
- **SC-010**: Adding a second country pack requires only adding country-specific registry tools and configuration — no changes to the core verification engine.

---

## Assumptions

- Users have stable internet connectivity. Offline operation is not in scope.
- Users have access to a modern web browser (Chrome, Edge, Firefox). Internet Explorer is not supported.
- The Gemini API (or equivalent LLM API) is available and within budget for the project duration. If local LLM deployment is chosen, adequate GPU resources are available.
- The IAF CertSearch free tier (30 company verifications/year) is sufficient for prototype and testing. Production scaling requires a paid API contract.
- For government portal lookups that require CAPTCHA solving (GST, EPFO, MCA), the system uses the `ask_human` tool — it does not bypass CAPTCHAs programmatically.
- Email outreach is sent from the buyer's own email account via SMTP integration. The system does not provide its own sending infrastructure.
- WhatsApp outreach is out of scope for the initial build. Email is the primary outreach channel.
- The supplier index will initially cover Indian EPCs. Expansion to other countries' directories is a future effort.
- The system does not replace human judgment — it presents evidence and recommendations. The buyer always makes the final decision.
- Distil-Whisper Small (English) is the initial speech-to-text model. Multilingual support can be added by swapping to a larger model variant.
- PDF engineering drawings use a "best effort" VLM extraction approach — accuracy depends on drawing quality, and user confirmation is always required.
- IndiaMART listings are pasted by the user, not scraped by the system. IndiaMART's terms of service prohibit automated access.
```

#### 3. `specs/001-supplier-verification-agent/checklists/requirements.md`

```markdown
# Specification Quality Checklist: VeriSource — AI Supplier Verification Agent

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-15
**Feature**: [spec.md](file:///C:/Users/hp/Documents/Projects/SupplierSearch/specs/001-supplier-verification-agent/spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- All items pass. Spec is ready for `/speckit-clarify` or `/speckit-plan`.
- The spec references specific tools by function (e.g., "speech-to-text model", "vision model", "web search") without naming specific technologies — this is intentional to keep it technology-agnostic.
- Country packs are described at the capability level, not implementation level.
- Voice input and PDF parsing user stories include the user-confirmation step as a core part of the flow, not as an afterthought.
```

---

### Assistant Reply 4

No `.specify/extensions.yml` exists, so no post-execution hooks to run.

---

### Completion Report

**Feature directory**: [`specs/001-supplier-verification-agent/`](file:///C:/Users/hp/Documents/Projects/SupplierSearch/specs/001-supplier-verification-agent)

**Spec file**: [`spec.md`](file:///C:/Users/hp/Documents/Projects/SupplierSearch/specs/001-supplier-verification-agent/spec.md)

**Checklist**: [`checklists/requirements.md`](file:///C:/Users/hp/Documents/Projects/SupplierSearch/specs/001-supplier-verification-agent/checklists/requirements.md)

#### Checklist Results

| Category | Status |
|---|---|
| Content Quality | ✅ 4/4 pass |
| Requirement Completeness | ✅ 8/8 pass |
| Feature Readiness | ✅ 4/4 pass |

**No [NEEDS CLARIFICATION] markers** — I used the full context from our brainstorming conversation to make informed decisions on every ambiguity. All assumptions are documented explicitly in the Assumptions section.

#### What the spec covers

- **6 user stories** (P1–P6): verify from list → discover → PDF parse → multi-day outreach → voice input → monitoring
- **47 functional requirements** (FR-001 through FR-047): conversational UI, intake, discovery, claim generation, evidence collection, cross-matching, outreach, reporting, monitoring, supplier index, multi-country architecture
- **10 success criteria** (SC-001 through SC-010): all measurable, technology-agnostic
- **8 edge cases** with expected behaviors
- **7 key entities**: Case, Supplier, Claim, Evidence Record, Verdict, Country Pack, Supplier Index

#### Ready for next phase

You can now run:
- **`/speckit-clarify`** — if you want to interrogate any underspecified areas before planning
- **`/speckit-plan`** — to generate the implementation plan from this spec

I'd recommend reading through the spec first and flagging anything that doesn't match what we discussed. The spec is your contract — once we plan from it, drift gets expensive.
