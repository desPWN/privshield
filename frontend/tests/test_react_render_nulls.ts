import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

// Mock Recharts ResponsiveContainer to avoid SVG width/height issues in static rendering
// (Recharts ResponsiveContainer needs DOM dimensions in browser)
import { OverviewView } from '../src/views/Overview/OverviewView';
import { DatasetsView } from '../src/views/Datasets/DatasetsView';
import { DiscoveryView } from '../src/views/Discovery/DiscoveryView';
import { StudioView } from '../src/views/Studio/StudioView';
import { PrivacyAnalysisView } from '../src/views/PrivacyAnalysis/PrivacyAnalysisView';
import { UtilityAnalysisView } from '../src/views/UtilityAnalysis/UtilityAnalysisView';
import { ReportsSettingsView } from '../src/views/ReportsSettings/ReportsSettingsView';

console.log('--- Testing Null State Rendering Across All 7 Views ---');

const defaultConfig: any = {
  processing_mode: 'irreversible_anonymization',
  quasi_identifiers: ['City', 'Age'],
  sensitive_attributes: ['Salary'],
  k_metric: 5,
  l_metric: 3,
  t_metric: 0.15,
  suppression_strategy: 'record',
  max_suppression_pct: 0.20,
  masking_rules: {},
  generalization_levels: {},
};

const views = [
  {
    name: 'View 1: OverviewView (datasets=[], activeRun=null)',
    render: () => renderToStaticMarkup(
      React.createElement(OverviewView, {
        datasets: [],
        activeRun: null,
        onNavigate: () => {},
        onLoadDemo: () => {},
        onSelectDataset: () => {},
      })
    ),
  },
  {
    name: 'View 2: DatasetsView (datasets=[], currentDataset=null)',
    render: () => renderToStaticMarkup(
      React.createElement(DatasetsView, {
        datasets: [],
        currentDataset: null,
        onSelectDataset: () => {},
        onUploadFile: async () => {},
        onLoadDemo: async () => {},
        onNavigate: () => {},
      })
    ),
  },
  {
    name: 'View 3: DiscoveryView (currentDataset=null, profiles=[], previewData=null)',
    render: () => renderToStaticMarkup(
      React.createElement(DiscoveryView, {
        currentDataset: null,
        profiles: [],
        previewData: null,
        onUpdateOverrides: async () => {},
        onNavigate: () => {},
      })
    ),
  },
  {
    name: 'View 4: StudioView (currentDataset=null, profiles=[])',
    render: () => renderToStaticMarkup(
      React.createElement(StudioView, {
        currentDataset: null,
        profiles: [],
        config: defaultConfig,
        onChangeConfig: () => {},
        onExecute: async () => {},
        onNavigate: () => {},
      })
    ),
  },
  {
    name: 'View 5: PrivacyAnalysisView (activeRun=null)',
    render: () => renderToStaticMarkup(
      React.createElement(PrivacyAnalysisView, {
        activeRun: null,
        onNavigate: () => {},
      })
    ),
  },
  {
    name: 'View 6: UtilityAnalysisView (activeRun=null, diffData=null)',
    render: () => renderToStaticMarkup(
      React.createElement(UtilityAnalysisView, {
        activeRun: null,
        diffData: null,
        onNavigate: () => {},
      })
    ),
  },
  {
    name: 'View 7: ReportsSettingsView (currentDataset=null, activeRun=null)',
    render: () => renderToStaticMarkup(
      React.createElement(ReportsSettingsView, {
        currentDataset: null,
        activeRun: null,
        onDownloadExport: async () => {},
        onDownloadPdf: async () => {},
        selectedIndustry: 'healthcare',
        onSelectIndustry: () => {},
      })
    ),
  },
];

let passCount = 0;
let failCount = 0;

for (const v of views) {
  try {
    const html = v.render();
    if (html && html.length > 0) {
      console.log(`[PASS] ${v.name} -> rendered ${html.length} chars`);
      passCount++;
    } else {
      console.error(`[FAIL] ${v.name} -> rendered empty markup`);
      failCount++;
    }
  } catch (err: any) {
    console.error(`[CRASH] ${v.name} -> Exception: ${err.message}`);
    failCount++;
  }
}

console.log(`\nResult: ${passCount} PASSED, ${failCount} FAILED out of ${views.length}`);
if (failCount > 0) {
  process.exit(1);
}
