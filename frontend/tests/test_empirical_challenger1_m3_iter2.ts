import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import fs from 'fs';
import path from 'path';
import { DiscoveryView } from '../src/views/Discovery/DiscoveryView';
import { PaginatedPreview, DatasetMetadata, ColumnProfile } from '../src/types/dataset';

console.log('================================================================');
console.log('CHALLENGER 1 EMPIRICAL HARNESS: M3 ITERATION 2 RE-VERIFICATION');
console.log('================================================================');

let totalTests = 0;
let passedTests = 0;
let failedTests = 0;

function assert(condition: boolean, testName: string, detail?: string) {
  totalTests++;
  if (condition) {
    passedTests++;
    console.log(`[PASS] ${testName}`);
  } else {
    failedTests++;
    console.error(`[FAIL] ${testName}${detail ? ` -> ${detail}` : ''}`);
  }
}

const mockDataset: DatasetMetadata = {
  id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
  name: 'adversarial_test_dataset.csv',
  original_filename: 'adversarial_test_dataset.csv',
  file_format: 'csv',
  record_count: 500,
  column_count: 5,
  file_size_bytes: 25000,
  is_synthetic: true,
  storage_path: 'storage/raw/a1b2c3d4-e5f6-7890-abcd-ef1234567890',
  created_at: new Date().toISOString(),
};

const mockProfiles: ColumnProfile[] = [
  {
    column_name: 'PatientID',
    detected_type: 'direct_identifier',
    confidence: 1.0,
    explanation: 'Direct Patient ID',
    sample_values_masked: ['P***01'],
    unique_count: 500,
    null_count: 0,
  },
  {
    column_name: 'Age',
    detected_type: 'quasi_identifier',
    confidence: 0.95,
    explanation: 'Age Quasi-ID',
    sample_values_masked: ['35'],
    unique_count: 60,
    null_count: 0,
  },
  {
    column_name: 'Diagnosis',
    detected_type: 'sensitive_attribute',
    confidence: 0.9,
    explanation: 'ICD-10 Sensitive Condition',
    sample_values_masked: ['I10'],
    unique_count: 25,
    null_count: 0,
  },
  {
    column_name: 'Notes',
    detected_type: 'insensitive',
    confidence: 0.8,
    explanation: 'General Notes',
    sample_values_masked: ['Routine check'],
    unique_count: 100,
    null_count: 5,
  },
  {
    column_name: 'Special<Col>&"Test"',
    detected_type: 'insensitive',
    confidence: 0.8,
    explanation: 'Special Characters Header',
    sample_values_masked: ['N/A'],
    unique_count: 10,
    null_count: 0,
  },
];

// ============================================================================
// TEST SUITE 1: DiscoveryView Preview Table Runtime TypeError Stress Test
// ============================================================================
console.log('\n--- SUITE 1: DiscoveryView Preview Table Runtime Stress ---');

// Case 1.1: Backend standard payload (has "records", "rows" is undefined)
try {
  const payloadBackend: any = {
    dataset_id: mockDataset.id,
    page: 1,
    size: 5,
    total_records: 500,
    total_pages: 100,
    columns: ['PatientID', 'Age', 'Diagnosis', 'Notes'],
    records: [
      { PatientID: 'P0001', Age: 25, Diagnosis: 'J45', Notes: 'Stable' },
      { PatientID: 'P0002', Age: 42, Diagnosis: 'E11', Notes: 'Followup' },
    ],
  };
  const html = renderToStaticMarkup(
    React.createElement(DiscoveryView, {
      currentDataset: mockDataset,
      profiles: mockProfiles,
      previewData: payloadBackend,
      onUpdateOverrides: async () => {},
      onNavigate: () => {},
    })
  );
  assert(
    html.includes('Sanitized Sample Preview (First 2 Records)') &&
      html.includes('••••••••') && // Direct ID masked by default
      html.includes('J45'),
    '1.1 Backend payload with records array renders without TypeError and masks direct IDs'
  );
} catch (e: any) {
  assert(false, '1.1 Backend payload with records array', e.message);
}

// Case 1.2: Legacy payload (has "rows", "records" is undefined)
try {
  const payloadLegacy: any = {
    dataset_id: mockDataset.id,
    page: 1,
    size: 5,
    total_records: 500,
    total_pages: 100,
    columns: ['PatientID', 'Age', 'Diagnosis', 'Notes'],
    rows: [
      { PatientID: 'P0003', Age: 61, Diagnosis: 'I25', Notes: 'Review' },
    ],
  };
  const html = renderToStaticMarkup(
    React.createElement(DiscoveryView, {
      currentDataset: mockDataset,
      profiles: mockProfiles,
      previewData: payloadLegacy,
      onUpdateOverrides: async () => {},
      onNavigate: () => {},
    })
  );
  assert(
    html.includes('Sanitized Sample Preview (First 1 Records)') && html.includes('I25'),
    '1.2 Legacy payload with rows array renders cleanly without TypeError'
  );
} catch (e: any) {
  assert(false, '1.2 Legacy payload with rows array', e.message);
}

// Case 1.3: Malformed payload where BOTH rows and records are undefined
try {
  const payloadMalformed: any = {
    dataset_id: mockDataset.id,
    page: 1,
    size: 5,
    total_records: 0,
    total_pages: 0,
    columns: ['PatientID', 'Age', 'Diagnosis', 'Notes'],
    rows: undefined,
    records: undefined,
  };
  const html = renderToStaticMarkup(
    React.createElement(DiscoveryView, {
      currentDataset: mockDataset,
      profiles: mockProfiles,
      previewData: payloadMalformed,
      onUpdateOverrides: async () => {},
      onNavigate: () => {},
    })
  );
  assert(
    html.includes('Sanitized Sample Preview (First 0 Records)'),
    '1.3 Malformed payload with both rows & records undefined safely defaults to 0 rows without TypeError'
  );
} catch (e: any) {
  assert(false, '1.3 Malformed payload with both rows & records undefined', e.message);
}

// Case 1.4: Empty arrays for both rows and records
try {
  const payloadEmpty: any = {
    dataset_id: mockDataset.id,
    page: 1,
    size: 15,
    total_records: 0,
    total_pages: 0,
    columns: ['PatientID', 'Age'],
    records: [],
    rows: [],
  };
  const html = renderToStaticMarkup(
    React.createElement(DiscoveryView, {
      currentDataset: mockDataset,
      profiles: mockProfiles,
      previewData: payloadEmpty,
      onUpdateOverrides: async () => {},
      onNavigate: () => {},
    })
  );
  assert(
    html.includes('Sanitized Sample Preview (First 0 Records)'),
    '1.4 Empty records array renders header and 0 row entries safely'
  );
} catch (e: any) {
  assert(false, '1.4 Empty records array', e.message);
}

// Case 1.5: Adversarial cell types (null, undefined, 0, false, empty string, symbols)
try {
  const payloadAdversarialCells: any = {
    dataset_id: mockDataset.id,
    page: 1,
    size: 5,
    total_records: 4,
    total_pages: 1,
    columns: ['PatientID', 'Age', 'Diagnosis', 'Notes', 'Special<Col>&"Test"'],
    records: [
      { PatientID: null, Age: 0, Diagnosis: false, Notes: '', 'Special<Col>&"Test"': '<script>alert(1)</script>' },
      { PatientID: undefined, Age: -99, Diagnosis: null, Notes: undefined, 'Special<Col>&"Test"': 'Safe & Clean' },
      { PatientID: 'P0005', Age: null, Diagnosis: 'Z00.0', Notes: '   ', 'Special<Col>&"Test"': 12345.678 },
    ],
  };
  const html = renderToStaticMarkup(
    React.createElement(DiscoveryView, {
      currentDataset: mockDataset,
      profiles: mockProfiles,
      previewData: payloadAdversarialCells,
      onUpdateOverrides: async () => {},
      onNavigate: () => {},
    })
  );
  assert(
    html.includes('Sanitized Sample Preview (First 3 Records)') &&
      html.includes('—') && // Null / undefined placeholder
      html.includes('12345.678'),
    '1.5 Adversarial cell types (null, undefined, false, 0, special chars) render cleanly without throwing'
  );
} catch (e: any) {
  assert(false, '1.5 Adversarial cell types', e.message);
}

// Case 1.6: Volume stress test: 500 records in previewData
try {
  const largeRecords = Array.from({ length: 500 }, (_, i) => ({
    PatientID: `P${String(i).padStart(5, '0')}`,
    Age: 20 + (i % 60),
    Diagnosis: `D${i % 10}`,
    Notes: `Record ${i}`,
    'Special<Col>&"Test"': `Val-${i}`,
  }));
  const payload500: any = {
    dataset_id: mockDataset.id,
    page: 1,
    size: 500,
    total_records: 500,
    total_pages: 1,
    columns: ['PatientID', 'Age', 'Diagnosis', 'Notes', 'Special<Col>&"Test"'],
    records: largeRecords,
  };
  const start = performance.now();
  const html = renderToStaticMarkup(
    React.createElement(DiscoveryView, {
      currentDataset: mockDataset,
      profiles: mockProfiles,
      previewData: payload500,
      onUpdateOverrides: async () => {},
      onNavigate: () => {},
    })
  );
  const duration = performance.now() - start;
  assert(
    html.includes('Sanitized Sample Preview (First 500 Records)') && duration < 500,
    `1.6 Volume stress test (500 records) renders in ${duration.toFixed(1)}ms (< 500ms limit)`
  );
} catch (e: any) {
  assert(false, '1.6 Volume stress test', e.message);
}

// Case 1.7: SanitizedPreviewTable component retired with wizard migration

// ============================================================================
// TEST SUITE 2: Root Document Overflow Containment Verification
// ============================================================================
console.log('\n--- SUITE 2: Root Document Overflow Containment ---');

const baseDir = process.cwd();
const indexHtmlPath = fs.existsSync(path.resolve(baseDir, 'frontend/index.html'))
  ? path.resolve(baseDir, 'frontend/index.html')
  : path.resolve(baseDir, 'index.html');
const indexCssPath = fs.existsSync(path.resolve(baseDir, 'frontend/src/index.css'))
  ? path.resolve(baseDir, 'frontend/src/index.css')
  : path.resolve(baseDir, 'src/index.css');

assert(fs.existsSync(indexHtmlPath), '2.1 frontend/index.html exists');
assert(fs.existsSync(indexCssPath), '2.2 frontend/src/index.css exists');

const indexHtmlContent = fs.readFileSync(indexHtmlPath, 'utf8');
const indexCssContent = fs.readFileSync(indexCssPath, 'utf8');

// Check html tag in index.html
const htmlTagMatch = indexHtmlContent.match(/<html[^>]*>/i);
assert(
  htmlTagMatch !== null && htmlTagMatch[0].includes('overflow-x-hidden'),
  `2.3 <html> tag in index.html declares overflow-x-hidden (found: ${htmlTagMatch ? htmlTagMatch[0] : 'none'})`
);

// Check body tag in index.html
const bodyTagMatch = indexHtmlContent.match(/<body[^>]*>/i);
assert(
  bodyTagMatch !== null && bodyTagMatch[0].includes('overflow-x-hidden'),
  `2.4 <body> tag in index.html declares overflow-x-hidden (found: ${bodyTagMatch ? bodyTagMatch[0] : 'none'})`
);

// Check #root div in index.html
const rootTagMatch = indexHtmlContent.match(/<div[^>]*id=["']root["'][^>]*>/i);
assert(
  rootTagMatch !== null && rootTagMatch[0].includes('overflow-x-hidden'),
  `2.5 <div id="root"> in index.html declares overflow-x-hidden (found: ${rootTagMatch ? rootTagMatch[0] : 'none'})`
);

// Check index.css rule: html, body, #root { overflow-x: hidden; }
const cssRulePattern = /html\s*,\s*body\s*,\s*#root\s*\{[^}]*overflow-x\s*:\s*hidden\s*;?[^}]*\}/i;
const hasCssRule = cssRulePattern.test(indexCssContent);
assert(
  hasCssRule,
  '2.6 frontend/src/index.css declares "html, body, #root { overflow-x: hidden; }"'
);

// Verify no contradictory overflow-x rules overriding html, body, or #root with visible
const visibleOverflowMatches = indexCssContent.match(/(?:html|body|#root)[^{]*\{[^}]*overflow-x\s*:\s*(?:visible|auto|scroll)/gi);
assert(
  visibleOverflowMatches === null,
  '2.7 No contradictory overflow-x: visible/auto/scroll rules exist in index.css'
);

// ============================================================================
// TEST SUITE 3: Production Build Dist Output Validation
// ============================================================================
console.log('\n--- SUITE 3: Production Build Artifact Validation ---');

const distHtmlPath = fs.existsSync(path.resolve(baseDir, 'frontend/dist/index.html'))
  ? path.resolve(baseDir, 'frontend/dist/index.html')
  : path.resolve(baseDir, 'dist/index.html');
const distAssetsDir = fs.existsSync(path.resolve(baseDir, 'frontend/dist/assets'))
  ? path.resolve(baseDir, 'frontend/dist/assets')
  : path.resolve(baseDir, 'dist/assets');

assert(fs.existsSync(distHtmlPath), '3.1 dist/index.html exists after build');
if (fs.existsSync(distHtmlPath)) {
  const distHtml = fs.readFileSync(distHtmlPath, 'utf8');
  assert(
    distHtml.includes('overflow-x-hidden'),
    '3.2 dist/index.html retains overflow-x-hidden classes on root elements'
  );
}

if (fs.existsSync(distAssetsDir)) {
  const cssFiles = fs.readdirSync(distAssetsDir).filter((f) => f.endsWith('.css'));
  assert(cssFiles.length > 0, `3.3 Compiled CSS asset exists in dist/assets (${cssFiles.join(', ')})`);
  if (cssFiles.length > 0) {
    const compiledCss = fs.readFileSync(path.join(distAssetsDir, cssFiles[0]), 'utf8');
    assert(
      compiledCss.includes('overflow-x:hidden'),
      '3.4 Compiled production CSS asset contains "overflow-x:hidden"'
    );
  }
}

// ============================================================================
// SUMMARY & VERDICT
// ============================================================================
console.log('\n================================================================');
console.log(`TOTAL TESTS: ${totalTests}`);
console.log(`PASSED: ${passedTests}`);
console.log(`FAILED: ${failedTests}`);
console.log('================================================================');

if (failedTests > 0) {
  console.error(`VERDICT: REJECT (${failedTests} tests failed)`);
  process.exit(1);
} else {
  console.log('VERDICT: APPROVE (100% tests passed)');
  process.exit(0);
}
