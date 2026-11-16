import React, { useState, useEffect, useCallback } from 'react';
import { api } from './api/client';
import {
  ColumnOverrideItem,
  ColumnProfile,
  DatasetMetadata,
  IndustryId,
  PaginatedPreview,
} from './types/dataset';
import { AnonymizationConfig } from './types/anonymization';
import { DiffResponse, RunAnalytics } from './types/analytics';
import { Sidebar, WorkspaceViewId } from './components/layout/Sidebar';
import { TopNav } from './components/layout/TopNav';
import { OverviewView } from './views/Overview/OverviewView';
import { DatasetsView } from './views/Datasets/DatasetsView';
import { DiscoveryView } from './views/Discovery/DiscoveryView';
import { StudioView } from './views/Studio/StudioView';
import { PrivacyAnalysisView } from './views/PrivacyAnalysis/PrivacyAnalysisView';
import { UtilityAnalysisView } from './views/UtilityAnalysis/UtilityAnalysisView';
import { ReportsSettingsView } from './views/ReportsSettings/ReportsSettingsView';
import { Modal } from './components/common/Modal';
import { UploadCloud, CheckCircle2, AlertCircle } from 'lucide-react';

const VALID_VIEWS: WorkspaceViewId[] = [
  'overview',
  'datasets',
  'discovery',
  'studio',
  'privacy-analysis',
  'utility-analysis',
  'reports-settings',
];

export const App: React.FC = () => {
  // Navigation & Shell state
  const [activeView, setActiveView] = useState<WorkspaceViewId>(() => {
    const hash = window.location.hash.replace(/^#\/?/, '') as WorkspaceViewId;
    return VALID_VIEWS.includes(hash) ? hash : 'overview';
  });

  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(() => {
    return typeof window !== 'undefined' && window.innerWidth <= 1366;
  });

  // Data & Entities state
  const [datasets, setDatasets] = useState<DatasetMetadata[]>([]);
  const [currentDataset, setCurrentDataset] = useState<DatasetMetadata | null>(null);
  const [profiles, setProfiles] = useState<ColumnProfile[]>([]);
  const [preview, setPreview] = useState<PaginatedPreview | null>(null);
  const [activeRun, setActiveRun] = useState<RunAnalytics | null>(null);
  const [diff, setDiff] = useState<DiffResponse | null>(null);
  const [selectedIndustry, setSelectedIndustry] = useState<IndustryId>('custom');
  const [defaultK, setDefaultK] = useState<number>(() => {
    const saved = localStorage.getItem('privshield_default_k');
    return saved ? parseInt(saved, 10) : 3;
  });

  const handleSelectDefaultK = (k: number) => {
    setDefaultK(k);
    localStorage.setItem('privshield_default_k', k.toString());
    setConfig((prev) => ({ ...prev, k_metric: k }));
  };

  // Studio Anonymization Configuration (Custom Universal Defaults)
  const [config, setConfig] = useState<AnonymizationConfig>({
    processing_mode: 'irreversible_anonymization',
    quasi_identifiers: ['City', 'Age', 'Gender'],
    sensitive_attributes: ['TransactionAmount', 'AccountBalance', 'TransactionCategory'],
    k_metric: defaultK,
    l_metric: 2,
    t_metric: 0.2,
    suppression_strategy: 'cell',
    max_suppression_pct: 0.30,
    masking_rules: {},
    generalization_levels: {
      City: 1,
      Age: 1,
      Timestamp: 1,
      TransactionAmount: 1,
    },
  });

  // System & Loading state
  const [isBackendOnline, setIsBackendOnline] = useState<boolean>(true);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isExecuting, setIsExecuting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [notification, setNotification] = useState<{ message: string; type: 'success' | 'info' | 'error' } | null>(null);
  const [isImportModalOpen, setIsImportModalOpen] = useState<boolean>(false);

  // Sync hash routing
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace(/^#\/?/, '') as WorkspaceViewId;
      if (VALID_VIEWS.includes(hash)) {
        setActiveView(hash);
      } else {
        setActiveView('overview');
      }
    };

    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const navigateTo = (view: WorkspaceViewId) => {
    setActiveView(view);
    setErrorMessage(null);
    window.location.hash = view;
  };

  // Toast notification timer
  useEffect(() => {
    if (notification) {
      const t = setTimeout(() => setNotification(null), 4000);
      return () => clearTimeout(t);
    }
  }, [notification]);

  // Error message auto-dismiss timer
  useEffect(() => {
    if (errorMessage) {
      const t = setTimeout(() => setErrorMessage(null), 8000);
      return () => clearTimeout(t);
    }
  }, [errorMessage]);

  // Synchronize diff data whenever activeRun is active
  useEffect(() => {
    if (activeRun && (!diff || diff.run_id !== activeRun.run_id)) {
      api.getRunDiff(activeRun.run_id, 1, 50)
        .then((res) => setDiff(res))
        .catch(() => {});
    }
  }, [activeRun, diff]);

  // Health check
  const checkHealth = useCallback(async () => {
    try {
      await api.checkHealth();
      setIsBackendOnline(true);
    } catch {
      setIsBackendOnline(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, [checkHealth]);

  // Initial data loading
  const loadInitialData = useCallback(async () => {
    try {
      const datasetList = await api.listDatasets().catch(() => []);

      setDatasets(datasetList || []);

      // If datasets exist and none selected, auto-select first
      if (datasetList && datasetList.length > 0 && !currentDataset) {
        for (const ds of datasetList) {
          try {
            await selectAndLoadDataset(ds);
            break;
          } catch {
            continue;
          }
        }
      }
    } catch {
      // Non-blocking initialization fallback
    }
  }, [currentDataset]);

  useEffect(() => {
    loadInitialData();
  }, []);

  // Load dataset details
  const selectAndLoadDataset = async (ds: DatasetMetadata) => {
    setIsLoading(true);
    setErrorMessage(null);
    setCurrentDataset(ds);

    try {
      const [discRes, prevRes, latestRun] = await Promise.all([
        api.discoverDataset(ds.id),
        api.getDatasetPreview(ds.id, 1, 20, true),
        api.getLatestRunForDataset(ds.id).catch(() => null),
      ]);

      const foundProfiles = discRes.profiles || [];
      setProfiles(foundProfiles);
      setPreview(prevRes);

      if (latestRun) {
        setActiveRun(latestRun);
        api.getRunDiff(latestRun.run_id, 1, 50)
          .then((d) => setDiff(d))
          .catch(() => {});
      }

      // Auto-extract QIs, sensitive attributes, and direct IDs
      const qis: string[] = [];
      const sens: string[] = [];
      const directIds: string[] = [];
      const defaultRules: Record<string, string> = {};
      const defaultLevels: Record<string, number> = {};

      const totalRows = prevRes.total_records || ds.record_count || 100;

      foundProfiles.forEach((p) => {
        const cat = p.user_category || p.detected_type;
        const colLower = p.column_name.toLowerCase();
        const isHighEntropyTimestamp =
          (colLower.includes('timestamp') || colLower.includes('time')) &&
          p.unique_count > 0.5 * totalRows;

        if (cat === 'quasi_identifier' && !isHighEntropyTimestamp) {
          qis.push(p.column_name);
          defaultLevels[p.column_name] = 1;
        } else if (cat === 'sensitive_attribute' || (cat === 'quasi_identifier' && isHighEntropyTimestamp)) {
          sens.push(p.column_name);
        } else if (cat === 'direct_identifier') {
          directIds.push(p.column_name);
          defaultRules[p.column_name] = 'preserve_trailing';
        }
      });

      // Avoid curse of dimensionality: on datasets < 500 rows, default to the 2 primary demographic QIs (e.g. age & gender)
      // This prevents 147 out of 150 rows from being masked with '*'
      let activeQIs = qis;
      if (qis.length > 2 && totalRows < 500) {
        const ageCol = qis.find((c) => c.toLowerCase().includes('age'));
        const genderCol = qis.find((c) => c.toLowerCase().includes('gender') || c.toLowerCase().includes('sex'));
        if (ageCol && genderCol) {
          activeQIs = [ageCol, genderCol];
        } else {
          activeQIs = qis.slice(0, 2);
        }
      }

      setConfig((prev) => ({
        ...prev,
        quasi_identifiers: activeQIs.length > 0 ? activeQIs : prev.quasi_identifiers,
        sensitive_attributes: sens.length > 0 ? sens : prev.sensitive_attributes,
        masking_rules: Object.keys(defaultRules).length > 0 ? defaultRules : prev.masking_rules,
        generalization_levels: Object.keys(defaultLevels).length > 0 ? defaultLevels : prev.generalization_levels,
        k_metric: 3,
        suppression_strategy: 'cell',
        max_suppression_pct: 0.30,
      }));
    } catch (err: any) {
      setErrorMessage(err.message || `Failed to load details for ${ds.name}.`);
    } finally {
      setIsLoading(false);
    }
  };

  // Upload file
  const handleFileUpload = async (file: File) => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const res = await api.uploadDataset(file);
      const updatedDatasets = await api.listDatasets();
      setDatasets(updatedDatasets);

      const target = updatedDatasets.find((d) => d.id === res.dataset_id) || {
        id: res.dataset_id,
        name: file.name,
        original_filename: file.name,
        file_format: file.name.split('.').pop() || 'csv',
        record_count: res.row_count,
        column_count: res.columns.length,
        file_size_bytes: file.size,
        is_synthetic: false,
        storage_path: `storage/raw/${res.dataset_id}`,
        created_at: new Date().toISOString(),
      };

      await selectAndLoadDataset(target);
      setIsImportModalOpen(false);
      setNotification({ message: `Successfully uploaded ${file.name} (${res.row_count} rows)`, type: 'success' });
      navigateTo('discovery');
    } catch (err: any) {
      setErrorMessage(err.message || 'File upload failed.');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  // Load industry demo dataset
  const handleLoadDemo = async (industry: string) => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const res = await api.loadIndustryDemo(industry);
      const updatedDatasets = await api.listDatasets();
      setDatasets(updatedDatasets);

      const target = updatedDatasets.find((d) => d.id === res.dataset_id);
      if (target) {
        await selectAndLoadDataset(target);
      }

      setNotification({
        message: `Loaded synthetic ${industry} demonstration dataset (${res.row_count} records).`,
        type: 'success',
      });
      navigateTo('discovery');
    } catch (err: any) {
      setErrorMessage(err.message || `Failed to load demo dataset for ${industry}.`);
    } finally {
      setIsLoading(false);
    }
  };

  // Update classification overrides
  const handleUpdateOverrides = async (overrides: ColumnOverrideItem[]) => {
    if (!currentDataset) return;
    setIsLoading(true);
    try {
      const res = await api.updateOverrides(currentDataset.id, overrides);
      setProfiles(res.profiles);

      // Refresh preview to reflect updated backend classification
      const refreshedPreview = await api.getDatasetPreview(currentDataset.id, 1, 20, true).catch(() => null);
      if (refreshedPreview) {
        setPreview(refreshedPreview);
      }

      // Re-adjust config
      const qis = res.profiles
        .filter((p) => (p.user_category || p.detected_type) === 'quasi_identifier')
        .map((p) => p.column_name);

      const sens = res.profiles
        .filter((p) => (p.user_category || p.detected_type) === 'sensitive_attribute')
        .map((p) => p.column_name);

      const directIdCols = new Set(
        res.profiles
          .filter((p) => (p.user_category || p.detected_type) === 'direct_identifier')
          .map((p) => p.column_name)
      );

      const updatedMaskingRules: Record<string, string> = {};
      Object.entries(config.masking_rules).forEach(([col, rule]) => {
        if (directIdCols.has(col)) {
          updatedMaskingRules[col] = rule;
        }
      });
      directIdCols.forEach((col) => {
        if (!updatedMaskingRules[col]) {
          updatedMaskingRules[col] = 'preserve_trailing';
        }
      });

      setConfig((prev) => ({
        ...prev,
        quasi_identifiers: qis.length > 0 ? qis : prev.quasi_identifiers,
        sensitive_attributes: sens.length > 0 ? sens : prev.sensitive_attributes,
        masking_rules: updatedMaskingRules,
      }));

      setNotification({ message: 'Classification overrides updated and persisted.', type: 'success' });
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to update classification overrides.');
    } finally {
      setIsLoading(false);
    }
  };

  // Execute Anonymization Pipeline
  const handleExecuteAnonymization = async () => {
    if (!currentDataset) return;
    setIsExecuting(true);
    setErrorMessage(null);

    try {
      const runResult = await api.anonymizeDataset(currentDataset.id, config);
      setActiveRun(runResult);

      // Load diff data
      const diffRes = await api.getRunDiff(runResult.run_id, 1, 50);
      setDiff(diffRes);

      setNotification({
        message: `Pipeline executed successfully. Achieved K=${runResult.achieved_k} with ${runResult.retained_records} retained rows.`,
        type: 'success',
      });

      navigateTo('privacy-analysis');
    } catch (err: any) {
      setErrorMessage(err.message || 'Anonymization execution failed.');
    } finally {
      setIsExecuting(false);
    }
  };

  // Exports
  const handleDownloadExport = async (format: 'csv' | 'xlsx' | 'json') => {
    if (!activeRun) return;
    try {
      await api.downloadExport(activeRun.run_id, format);
      setNotification({
        message: `Successfully downloaded anonymized data (${format.toUpperCase()})`,
        type: 'success',
      });
    } catch (err: any) {
      setErrorMessage(err.message || `Failed to export ${format.toUpperCase()} dataset.`);
    }
  };

  const handleDownloadPdf = async () => {
    if (!activeRun) return;
    try {
      await api.downloadPdfReport(activeRun.run_id);
      setNotification({
        message: 'Successfully downloaded Executive Privacy Compliance Report (PDF)',
        type: 'success',
      });
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to download PDF compliance report.');
    }
  };

  return (
    <div className="min-h-screen bg-canvas text-text-primary flex select-none">
      {/* Persistent Compact Sidebar */}
      <Sidebar
        activeView={activeView}
        onSelectView={navigateTo}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        currentDataset={currentDataset}
        isBackendOnline={isBackendOnline}
      />

      {/* Main Workspace Shell */}
      <div
        className={`flex-1 flex flex-col min-w-0 transition-all duration-200 ease-out ${
          isSidebarCollapsed ? 'pl-16' : 'pl-60'
        }`}
      >
        {/* Minimal Top Navigation */}
        <TopNav
          activeView={activeView}
          onNavigate={navigateTo}
          onOpenImport={() => setIsImportModalOpen(true)}
          onExecutePipeline={handleExecuteAnonymization}
          isExecuting={isExecuting}
        />

        {/* Global Notification Banner */}
        {notification && (
          <div className="fixed top-20 right-8 z-50 animate-modal-enter">
            <div
              className={`px-4 py-3 rounded-xl shadow-apple-card border flex items-center gap-2.5 text-xs font-medium ${
                notification.type === 'success'
                  ? 'bg-success/15 border-success/30 text-success'
                  : 'bg-info/15 border-info/30 text-info'
              }`}
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>{notification.message}</span>
            </div>
          </div>
        )}

        {/* Global Error Banner */}
        {errorMessage && (
          <div className="mx-6 mt-4 p-3 rounded-xl bg-danger/10 border border-danger/30 text-danger text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{errorMessage}</span>
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-xs text-text-muted hover:text-text-primary"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Active View Mounting Canvas */}
        <main className="flex-1 p-6 lg:p-8 overflow-y-auto">
          {activeView === 'overview' && (
            <OverviewView
              datasets={datasets}
              activeRun={activeRun}
              onNavigate={navigateTo}
              onLoadDemo={handleLoadDemo}
              onSelectDataset={selectAndLoadDataset}
              isLoading={isLoading}
            />
          )}

          {activeView === 'datasets' && (
            <DatasetsView
              datasets={datasets}
              currentDataset={currentDataset}
              onSelectDataset={selectAndLoadDataset}
              onUploadFile={handleFileUpload}
              onLoadDemo={handleLoadDemo}
              onNavigate={navigateTo}
              isLoading={isLoading}
            />
          )}

          {activeView === 'discovery' && (
            <DiscoveryView
              currentDataset={currentDataset}
              profiles={profiles}
              previewData={preview}
              onUpdateOverrides={handleUpdateOverrides}
              onNavigate={navigateTo}
              isLoading={isLoading}
            />
          )}

          {activeView === 'studio' && (
            <StudioView
              currentDataset={currentDataset}
              profiles={profiles}
              config={config}
              onChangeConfig={setConfig}
              onExecute={handleExecuteAnonymization}
              isExecuting={isExecuting}
              onNavigate={navigateTo}
            />
          )}

          {activeView === 'privacy-analysis' && (
            <PrivacyAnalysisView
              activeRun={activeRun}
              onNavigate={navigateTo}
            />
          )}

          {activeView === 'utility-analysis' && (
            <UtilityAnalysisView
              activeRun={activeRun}
              diffData={diff}
              onNavigate={navigateTo}
            />
          )}

          {activeView === 'reports-settings' && (
            <ReportsSettingsView
              currentDataset={currentDataset}
              activeRun={activeRun}
              onDownloadExport={handleDownloadExport}
              onDownloadPdf={handleDownloadPdf}
              selectedIndustry={selectedIndustry}
              onSelectIndustry={setSelectedIndustry}
              defaultK={defaultK}
              onSelectDefaultK={handleSelectDefaultK}
              isLoading={isLoading}
              onNavigate={navigateTo}
            />
          )}
        </main>
      </div>

      {/* Quick Import File Modal */}
      <Modal
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
        title="Import Structured Dataset"
        subtitle="Upload a local CSV, Microsoft Excel (XLSX), or JSON file into PrivShield"
      >
        <div className="space-y-4">
          <label className="block p-8 border-2 border-dashed border-white/[0.12] rounded-xl hover:border-accent/40 bg-surface-elevated/40 text-center cursor-pointer transition-colors">
            <UploadCloud className="w-8 h-8 text-accent mx-auto mb-2" />
            <span className="text-xs font-semibold text-text-primary block">
              Click to select file or drag and drop
            </span>
            <span className="text-[10px] text-text-muted">
              Supported formats: .CSV, .XLSX, .JSON (up to 100MB)
            </span>
            <input
              type="file"
              accept=".csv,.xlsx,.xls,.json"
              className="hidden"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  handleFileUpload(e.target.files[0]);
                }
              }}
            />
          </label>
        </div>
      </Modal>
    </div>
  );
};

export default App;
