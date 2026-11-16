import React, { useState } from 'react';
import {
  FileText,
  Download,
  Settings,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  HardDrive,
  Cpu,
  RefreshCw,
  Shield,
} from 'lucide-react';
import { RunAnalytics } from '../../types/analytics';
import { DatasetMetadata, IndustryId } from '../../types/dataset';
import { Button } from '../../components/common/Button';

interface ReportsSettingsViewProps {
  currentDataset: DatasetMetadata | null;
  activeRun: RunAnalytics | null;
  onDownloadExport: (format: 'csv' | 'xlsx' | 'json') => Promise<void>;
  onDownloadPdf: () => Promise<void>;
  selectedIndustry: IndustryId;
  onSelectIndustry: (id: IndustryId) => void;
  defaultK?: number;
  onSelectDefaultK?: (k: number) => void;
  isLoading?: boolean;
  onNavigate?: (view: any) => void;
}

export const ReportsSettingsView: React.FC<ReportsSettingsViewProps> = ({
  activeRun,
  onDownloadExport,
  onDownloadPdf,
  selectedIndustry,
  onSelectIndustry,
  defaultK = 3,
  onSelectDefaultK,
  onNavigate,
}) => {
  const [activeTab, setActiveTab] = useState<'reports' | 'settings'>('reports');
  const [isExporting, setIsExporting] = useState<string | null>(null);

  const isExportBlocked = Boolean(
    activeRun &&
    (!activeRun.k_satisfied || activeRun.retained_records === 0)
  );

  const handleExport = async (format: 'csv' | 'xlsx' | 'json') => {
    if (isExportBlocked) return;
    try {
      setIsExporting(format);
      await onDownloadExport(format);
    } finally {
      setIsExporting(null);
    }
  };

  const handlePdf = async () => {
    try {
      setIsExporting('pdf');
      await onDownloadPdf();
    } finally {
      setIsExporting(null);
    }
  };

  return (
    <div className="space-y-6 select-none">
      {/* Header Banner */}
      <div className="p-6 rounded-2xl bg-surface-panel/90 border border-white/[0.08] shadow-apple-card flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs">
            <span className="inline-flex items-center gap-1.5 font-medium text-accent">
              <span className="w-2 h-2 rounded-full bg-accent" />
              Governance & Export Gateway
            </span>
            <span className="text-white/20">•</span>
            <span className="text-text-muted font-mono">
              Certified Multi-Format Output
            </span>
          </div>
          <h2 className="text-xl font-bold text-text-primary tracking-tight">
            Compliance Reports & Platform Settings
          </h2>
          <p className="text-xs text-text-secondary leading-relaxed">
            Generate executive ReportLab PDF compliance certifications, download formula-sanitized datasets, and manage local sandbox parameters.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center bg-canvas p-1 rounded-xl border border-white/[0.07] text-xs">
          <button
            onClick={() => setActiveTab('reports')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg font-medium transition-all ${
              activeTab === 'reports'
                ? 'bg-surface-elevated text-text-primary shadow-apple-sm border border-white/[0.09]'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Reports & Exports</span>
          </button>
          <button
            onClick={() => setActiveTab('settings')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg font-medium transition-all ${
              activeTab === 'settings'
                ? 'bg-surface-elevated text-text-primary shadow-apple-sm border border-white/[0.09]'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            <Settings className="w-3.5 h-3.5" />
            <span>System Settings</span>
          </button>
        </div>
      </div>

      {activeTab === 'reports' ? (
        <div className="space-y-6">
          {/* Executive PDF Report Card */}
          <div className="p-6 rounded-2xl bg-surface-panel border border-white/[0.07] shadow-apple-card flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            <div className="space-y-3 max-w-xl">
              <div className="flex items-center gap-2.5">
                <div className="w-10 h-10 rounded-xl bg-accent/15 border border-accent/30 flex items-center justify-center text-accent">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-text-primary">
                    Executive Privacy Compliance Report (PDF)
                  </h3>
                  <p className="text-xs text-text-muted">
                    Publication-grade ReportLab document with dynamic NumberedCanvas pagination
                  </p>
                </div>
              </div>

              <p className="text-xs text-text-secondary leading-relaxed">
                Contains verified K-anonymity scorecards, L-diversity and T-closeness audit tables, re-identification threat risk models, and 5-dimension CURS utility metrics. Certified zero-PII leak.
              </p>

              <div className="flex items-center gap-3 text-[11px] font-mono text-text-secondary">
                <span className="flex items-center gap-1.5 text-success">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Mathematical Proof Included
                </span>
                <span className="flex items-center gap-1.5 text-info">
                  <Shield className="w-3.5 h-3.5" /> Industry Profile Seal
                </span>
              </div>
            </div>

            <div className="flex-shrink-0">
              <Button
                variant="primary"
                size="lg"
                icon={Download}
                isLoading={isExporting === 'pdf'}
                disabled={!activeRun}
                onClick={handlePdf}
                className="w-full lg:w-auto"
              >
                Download Executive PDF Report
              </Button>
            </div>
          </div>

          {/* Multi-Format Sanitized Dataset Export */}
          <div className="p-6 rounded-2xl bg-surface-panel/90 border border-white/[0.07] shadow-apple-card space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-text-primary">
                  Sanitized Dataset Exports
                </h3>
                <p className="text-xs text-text-muted">
                  Downloads the transformed dataset with spreadsheet formula injection neutralization
                </p>
              </div>
            </div>

            {/* Privacy Verification Gateway Export Lock Notice */}
            {isExportBlocked && (
              <div className="p-4 rounded-xl bg-danger/10 border border-danger/30 text-xs text-danger flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <div className="font-semibold text-danger">
                      Pre-Export Privacy Verification Gateway: Export Locked
                    </div>
                    <p className="text-[11px] text-text-muted leading-relaxed">
                      {activeRun?.retained_records === 0
                        ? '0 records were retained because exact timestamps or unique IDs were selected as Quasi-Identifiers. Deselect timestamps in Studio and re-run to retain all records.'
                        : 'Strict K-anonymity invariant was not satisfied (suppression exceeded configured limit). Re-run in Studio with broader quasi-identifier generalization or increase Max Suppression.'}
                    </p>
                  </div>
                </div>

                {onNavigate && (
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => onNavigate('studio')}
                    className="flex-shrink-0 whitespace-nowrap"
                  >
                    Adjust in Studio &rarr;
                  </Button>
                )}
              </div>
            )}

            {/* Formula Injection Neutralization Notice */}
            <div className="p-3.5 rounded-xl bg-warning/10 border border-warning/25 text-xs text-warning flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <div className="space-y-0.5 text-[11px] leading-relaxed">
                <strong className="font-semibold text-warning">Spreadsheet DDE Injection Guard Active: </strong>
                All cell values beginning with `= `, `+ `, `- `, `@ `, `\t `, or `\r ` have been automatically prepended with a single quote (`'`) to neutralize malicious formula execution in Microsoft Excel and LibreOffice Calc.
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
              {/* CSV Export Card */}
              <div className="p-4 rounded-xl bg-surface-elevated/70 border border-white/[0.06] flex flex-col justify-between space-y-3">
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-text-primary">.CSV Format</span>
                    <span className="text-[11px] text-text-muted">
                      Universal
                    </span>
                  </div>
                  <p className="text-[11px] text-text-muted">
                    Comma-separated values with formula guard and UTF-8 encoding.
                  </p>
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  icon={Download}
                  isLoading={isExporting === 'csv'}
                  disabled={!activeRun || isExportBlocked}
                  onClick={() => handleExport('csv')}
                >
                  Download CSV
                </Button>
              </div>

              {/* XLSX Export Card */}
              <div className="p-4 rounded-xl bg-surface-elevated/70 border border-white/[0.06] flex flex-col justify-between space-y-3">
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-text-primary">.XLSX Format</span>
                    <span className="text-[11px] text-text-muted">
                      Excel
                    </span>
                  </div>
                  <p className="text-[11px] text-text-muted">
                    OpenPyXL native workbook with styled headers and column widths.
                  </p>
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  icon={Download}
                  isLoading={isExporting === 'xlsx'}
                  disabled={!activeRun || isExportBlocked}
                  onClick={() => handleExport('xlsx')}
                >
                  Download Excel
                </Button>
              </div>

              {/* JSON Export Card */}
              <div className="p-4 rounded-xl bg-surface-elevated/70 border border-white/[0.06] flex flex-col justify-between space-y-3">
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-text-primary">.JSON Format</span>
                    <span className="text-[11px] text-text-muted">
                      API-Ready
                    </span>
                  </div>
                  <p className="text-[11px] text-text-muted">
                    Array of records formatted for downstream analytics pipelines.
                  </p>
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  icon={Download}
                  isLoading={isExporting === 'json'}
                  disabled={!activeRun || isExportBlocked}
                  onClick={() => handleExport('json')}
                >
                  Download JSON
                </Button>
              </div>
            </div>
          </div>

          {/* Local Mathematical Compliance Certification Badge */}
          <div className="p-5 rounded-2xl bg-canvas/80 border border-white/[0.06] flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-success/15 border border-success/30 flex items-center justify-center text-success">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-text-primary">
                  100% Local Mathematical Execution Stamp
                </h4>
                <p className="text-[11px] text-text-muted">
                  Cryptographically isolated. Zero external cloud API calls or off-premise telemetry.
                </p>
              </div>
            </div>
            <span className="inline-flex items-center gap-1.5 text-xs text-success font-medium">
              <span className="w-2 h-2 rounded-full bg-success" />
              Verified Sandbox
            </span>
          </div>
        </div>
      ) : (
        /* Settings Tab */
        <div className="space-y-6">
          <div className="p-6 rounded-2xl bg-surface-panel/90 border border-white/[0.07] shadow-apple-card space-y-6">
            <div className="space-y-1 border-b border-white/[0.07] pb-4">
              <h3 className="text-base font-bold text-text-primary">
                Industry Profile Customization & Defaults
              </h3>
              <p className="text-xs text-text-muted">
                Configure default privacy boundaries and detection weights across the platform.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-text-primary">
                  Default Industry Profile
                </label>
                <select
                  value={selectedIndustry}
                  onChange={(e) => onSelectIndustry(e.target.value as IndustryId)}
                  className="w-full bg-surface-elevated border border-white/[0.08] focus:border-accent/40 rounded-lg px-3 py-2 text-xs text-text-primary outline-none"
                >
                  <option value="healthcare">Healthcare (HIPAA Rules)</option>
                  <option value="finance">Banking & Finance (CBJ / GDPR)</option>
                  <option value="education">Education (FERPA Rules)</option>
                  <option value="government">Government & Civic</option>
                  <option value="hr">Human Resources (HR)</option>
                  <option value="ecommerce">E-Commerce & Retail</option>
                  <option value="custom">Custom Specification</option>
                </select>
                <p className="text-[10px] text-text-muted">
                  Controls pre-selected classification rules during sensitive data discovery.
                </p>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-text-primary">
                  Default K-Anonymity Target
                </label>
                <select
                  value={defaultK.toString()}
                  onChange={(e) => onSelectDefaultK?.(parseInt(e.target.value, 10))}
                  className="w-full bg-surface-elevated border border-white/[0.08] focus:border-accent/40 rounded-lg px-3 py-2 text-xs text-text-primary outline-none cursor-pointer"
                >
                  <option value="2">K = 2 (Small Dataset / Minimal Suppression)</option>
                  <option value="3">K = 3 (High Utility Research)</option>
                  <option value="5">K = 5 (Standard Enterprise Default)</option>
                  <option value="10">K = 10 (Strict Regulatory Compliance)</option>
                </select>
                <p className="text-[10px] text-text-muted">
                  Minimum equivalence class size initialized in Anonymization Studio.
                </p>
              </div>
            </div>

            <div className="space-y-3 pt-4 border-t border-white/[0.07]">
              <h4 className="text-xs font-semibold text-text-primary">
                System diagnostics & telemetry
              </h4>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                <div className="p-3 rounded-xl bg-canvas/60 border border-white/[0.06] space-y-1">
                  <div className="flex items-center gap-2 text-text-muted">
                    <Cpu className="w-3.5 h-3.5" /> Engine
                  </div>
                  <div className="font-mono font-semibold text-text-primary">FastAPI + NumPy</div>
                </div>

                <div className="p-3 rounded-xl bg-canvas/60 border border-white/[0.06] space-y-1">
                  <div className="flex items-center gap-2 text-text-muted">
                    <HardDrive className="w-3.5 h-3.5" /> Database
                  </div>
                  <div className="font-mono font-semibold text-text-primary">SQLite 3 (WAL Mode)</div>
                </div>

                <div className="p-3 rounded-xl bg-canvas/60 border border-white/[0.06] space-y-1">
                  <div className="flex items-center gap-2 text-text-muted">
                    <RefreshCw className="w-3.5 h-3.5" /> Frontend
                  </div>
                  <div className="font-mono font-semibold text-text-primary">React 19 + Vite + Tailwind</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
