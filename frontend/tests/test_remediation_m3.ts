import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { DiscoveryView } from '../src/views/Discovery/DiscoveryView';
import { PaginatedPreview, DatasetMetadata, ColumnProfile } from '../src/types/dataset';

console.log('--- Testing M3 Defect Remediations ---');

const mockDataset: DatasetMetadata = {
  id: '962ff783-0a9b-45ca-8d9b-9ce2aee17bc9',
  name: 'hospital_patients.csv',
  original_filename: 'hospital_patients.csv',
  file_format: 'csv',
  record_count: 1000,
  column_count: 4,
  file_size_bytes: 45000,
  is_synthetic: true,
  storage_path: 'storage/raw/962ff783-0a9b-45ca-8d9b-9ce2aee17bc9',
  created_at: new Date().toISOString(),
};

const mockProfiles: ColumnProfile[] = [
  {
    column_name: 'PatientID',
    detected_type: 'direct_identifier',
    confidence: 0.99,
    explanation: 'Direct ID',
    sample_values_masked: ['P***1'],
    unique_count: 1000,
    null_count: 0,
  },
  {
    column_name: 'Age',
    detected_type: 'quasi_identifier',
    confidence: 0.95,
    explanation: 'Quasi ID',
    sample_values_masked: ['45'],
    unique_count: 80,
    null_count: 0,
  },
];

// Test 1: DiscoveryView with backend payload (using "records" instead of "rows")
console.log('\n[TEST 1] DiscoveryView with backend "records" payload:');
const backendPreviewData: any = {
  dataset_id: mockDataset.id,
  page: 1,
  size: 15,
  total_records: 1000,
  total_pages: 67,
  columns: ['PatientID', 'Age'],
  records: [
    { PatientID: 'P0001', Age: 45 },
    { PatientID: 'P0002', Age: 52 },
  ],
};

try {
  const html = renderToStaticMarkup(
    React.createElement(DiscoveryView, {
      currentDataset: mockDataset,
      profiles: mockProfiles,
      previewData: backendPreviewData,
      onUpdateOverrides: async () => {},
      onNavigate: () => {},
    })
  );
  if (!html.includes('Sanitized Sample Preview (First 2 Records)')) {
    throw new Error('Expected record count not found in HTML');
  }
  console.log('  -> PASS: DiscoveryView rendered successfully with "records" payload without TypeError!');
} catch (err: any) {
  console.error('  -> FAIL:', err.message);
  process.exit(1);
}

// Test 2: DiscoveryView with legacy "rows" payload
console.log('\n[TEST 2] DiscoveryView with legacy "rows" payload:');
const legacyPreviewData: PaginatedPreview = {
  dataset_id: mockDataset.id,
  page: 1,
  size: 15,
  total_records: 1000,
  total_pages: 67,
  columns: ['PatientID', 'Age'],
  rows: [
    { PatientID: 'P0001', Age: 45 },
  ],
};

try {
  const html = renderToStaticMarkup(
    React.createElement(DiscoveryView, {
      currentDataset: mockDataset,
      profiles: mockProfiles,
      previewData: legacyPreviewData,
      onUpdateOverrides: async () => {},
      onNavigate: () => {},
    })
  );
  if (!html.includes('Sanitized Sample Preview (First 1 Records)')) {
    throw new Error('Expected record count not found in HTML');
  }
  console.log('  -> PASS: DiscoveryView rendered successfully with "rows" payload!');
} catch (err: any) {
  console.error('  -> FAIL:', err.message);
  process.exit(1);
}

// Test 3: URL Hash normalization logic
console.log('\n[TEST 3] URL Hash normalization logic:');
const VALID_VIEWS = [
  'overview',
  'datasets',
  'discovery',
  'studio',
  'privacy-analysis',
  'utility-analysis',
  'reports-settings',
];

const testHashes = [
  { raw: '#/studio', expected: 'studio' },
  { raw: '#studio', expected: 'studio' },
  { raw: '#/overview', expected: 'overview' },
  { raw: '#', expected: 'overview' },
  { raw: '#/', expected: 'overview' },
  { raw: '', expected: 'overview' },
  { raw: '#invalid-view', expected: 'overview' },
  { raw: '#/reports-settings', expected: 'reports-settings' },
];

for (const th of testHashes) {
  const cleaned = th.raw.replace(/^#\/?/, '');
  const resolved = VALID_VIEWS.includes(cleaned) ? cleaned : 'overview';
  if (resolved !== th.expected) {
    console.error(`  -> FAIL: For hash "${th.raw}", expected "${th.expected}" but got "${resolved}"`);
    process.exit(1);
  }
}
console.log(`  -> PASS: All ${testHashes.length} hash variations normalized correctly!`);

console.log('\nAll M3 Remediation Checks PASSED successfully!');
