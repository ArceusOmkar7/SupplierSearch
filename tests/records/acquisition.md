# Core 002 acquisition log

Checked 19 October 2026. Original bytes and manifests are private local files under
`.local/records/`; they are not committed or sent to a cloud model.

| Actual source | Result | Supported use |
|---|---|---|
| [BIS copyright policy](https://bis.gov.in/copyright-policy/?lang=en) | Retrieved; same-domain language redirect checked; attributed reuse policy verified | Policy provenance; excludes identified third-party content |
| [BIS licence list as of 27 August 2020](https://bis.gov.in/wp-content/uploads/2020/08/Licenses_IS_9473_27082020.pdf) | Actual one-page PDF retrieved; SHA256 verified by loader | Historical IS9473 mask-supplier rows; not current status, casting capability, or independently verified capacity |
| [BIS UTM procurement request](https://bis.gov.in/wp-content/themes/bisnew/page-templates/uploads/pdf/Tender/CL_UTM_Tender_27032019.pdf) | Actual 58-page PDF retrieved; SHA256 verified | Genuine historical public buyer request for UTM-1200kN; not a live tender, private buyer instruction or submitted order |
| [BIS QCO catalog](https://bis.gov.in/product-certification/products-under-compulsory-certification/?lang=en) | Response truncated; no successful content manifest created | Unavailable in this attempt; no applicability finding |

The original robots URL returned a language redirect. Following bounded redirects
within the same official domain produced usable directives; no restriction was bypassed.
All saved manifests passed schema and original-byte hash validation. Actual HTTP
outcomes and timestamps are in the ignored acquisition-attempt JSON files.

This is a minimal genuine-record baseline. The supplier records are attributed official
historical records, not captured supplier websites. Supplier-site/issuer pages with
verified collection/reuse scope, naturally locked/scanned certificates, relevant
contradictory evidence, four-supplier journeys, independent auditor labels and the
30-supplier active-time evaluation remain missing. Do not create replacement records,
infer a matching supplier capability from this procurement document, or count this
baseline as successful core acceptance. Missing specialist samples stay explicit.

## Additions on 20 October 2026

Captured with `capture-source` (robots checked, destination guarded; each capture has a manifest,
original bytes and SHA256 under ignored `.local/records/`). Rights are recorded as "public page; no
reuse licence verified; retained privately as verification evidence", except BIS pages, which follow
the BIS reuse policy above.

| Actual source | Result | Supported use |
|---|---|---|
| [BIS QCO catalog index](https://www.bis.gov.in/product-certification/products-under-compulsory-certification/?lang=en) | Retrieved on the second attempt (first, 19 Oct, was truncated) | Provenance only: it is largely site navigation linking to scheme pages |
| [BIS QCO Scheme-I table](https://www.bis.gov.in/product-certification/products-under-compulsory-certification/scheme-1/?lang=en) | Retrieved | Product / IS number / order-notification rows; the linked order PDFs were not read, so coverage is partial |
| [NABCB management-system certification](https://nabcb.qci.org.in/management-system-certification/) | Retrieved | Issuer accreditation page text only |
| BSI client-directory profile, SBICAP Securities Limited (certificate IS 822433) | Retrieved | A real issuer-published certificate record (ISO/IEC 27001:2022, 2025-04-10 to 2028-04-09); not a casting supplier |
| BSI client-directory profile, Crescent Foundry Co. Pvt. Ltd. | Retrieved | Three real certificates (ISO 45001:2018, ISO 14001:2015, ISO 9001:2015 FM 689386) for a ferrous casting company |
| [GPI ISO 9001 certificate](https://www.gpi.co.in/uploads/general/certificates/2025/3-ISO-9001-GPI.pdf) | Retrieved (one-page text PDF) | Actual DNV certificate C615162, valid 30 Sep 2023 – 29 Sep 2026; expired when used on 20 Oct 2026 |
| [Amruta Industries product page](https://www.amrutaindustries.in/pumppartinvest.html) | Retrieved (robots.txt returned 404) | Real supplier self-report |
| [Karam Industries catalogue page](https://www.karam.in/catalogue/group-profile) | Retrieved | A natural CAPTCHA-gated catalogue download page ("Solve to Verify"); the product treats it as blocked |
| TUV Rheinland India client list PDF (cited in research.md) | HTTP 404 | Not captured; no successful content manifest |

A live crawl on 20 October of the sites whose domains appear in the licence-list contact emails read
pages from seven of fourteen candidates (karam.in, midassafety.com, parknonwoven.com, thea-tex.com,
josephleslie.com, promaxmask.com, rosmertatech.com); for the others the destination did not resolve
(aamr.in, vijayss.com, grandwayinc.com) or crawling permission could not be established (venusohs.com,
paramountsurgimedltd.com, narmadapolymers.com, matrixclothing.in). No certificate PDF link was found on
the pages read.

Still missing: a naturally locked or scanned certificate, a contradicted real claim, a genuine buyer
request that matches these suppliers, independent human audit labels, and observed per-supplier
active-time records for 30 suppliers.
