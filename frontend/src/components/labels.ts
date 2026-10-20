/** Plain-language names for backend vocabulary. */
export const IDENTIFIER_TYPES: [string, string][] = [
  ['name', 'Name'],
  ['website', 'Website'],
  ['gstin', 'GSTIN'],
  ['udyam', 'Udyam number'],
  ['cin', 'CIN'],
  ['llpin', 'LLPIN'],
  ['licence_number', 'BIS licence number'],
  ['certificate_number', 'Certificate number'],
  ['listing_url', 'Marketplace listing link (kept as text, never opened)'],
];

export const CLAIM_LABELS: Record<string, string> = {
  legal_existence: 'Legal existence',
  manufacturer: 'Manufacturer',
  part_capability: 'Part capability',
  certificate: 'Certificate',
  regulatory: 'Regulatory compliance',
  capacity: 'Capacity',
};

export const CHECK_LABELS: Record<string, string> = {
  local_export_lookup: 'Official export lookup',
  bis_applicability: 'BIS order applicability',
  website_traversal: 'Supplier website',
  certificate_document: 'Certificate documents',
  certificate_issuer_lookup: 'Issuer records',
  certificate_qr_follow: 'Official links on certificates',
  coverage_unsupported: 'Country coverage',
};

export const TASK_STATE_LABELS: Record<string, { text: string; mark: string }> = {
  queued: { text: 'Queued', mark: '○' },
  running: { text: 'Checking', mark: '◐' },
  succeeded: { text: 'Complete', mark: '●' },
  no_evidence: { text: 'No evidence found', mark: '◌' },
  failed: { text: 'Failed', mark: '✕' },
  waiting_input: { text: 'Waiting for you', mark: '!' },
  cancelled: { text: 'Cancelled', mark: '–' },
};

export const OUTCOME_LABELS: Record<string, string> = {
  success: 'Retrieved',
  no_record: 'No matching record',
  blocked: 'Blocked by the source',
  unavailable: 'Unavailable',
  timeout: 'Timed out',
  transient_error: 'Temporary error',
  invalid_input: 'Unreadable input',
  uncertain_outcome: 'Outcome uncertain',
  skipped: 'Not attempted',
};

export const REASON_LABELS: Record<string, string> = {
  not_configured: 'not configured',
  permission_unverified: 'crawling permission not established',
  robots_disallowed: 'the site disallows automated access',
  consent_missing: 'authorization missing',
  budget_exhausted: 'budget used',
  quota_exhausted: 'rate limit reached',
  not_supported: 'not supported for this source',
  missing_identifier: 'no identifier to look up',
  captcha: 'the source requires a CAPTCHA',
  locked_document: 'document is locked',
  unsupported_language: 'unsupported language',
  too_large: 'too large',
  malformed_document: 'document could not be read',
  deadline: 'time limit reached',
  ocr_unavailable: 'text recognition unavailable',
};

export const FIELD_LABELS: Record<string, string> = {
  part_description: 'Part or equipment',
  materials: 'Materials',
  processes: 'Processes',
  quantity: 'Quantity',
  certifications: 'Required certifications',
  tolerance: 'Tolerance',
  standards: 'Standards',
};
