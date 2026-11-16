import React, { useState, useEffect } from 'react';
import {
  ScanSearch,
  ArrowRight,
  Database,
  Eye,
  EyeOff,
  Check,
  Lock,
  Loader2,
} from 'lucide-react';
import { api } from '../../api/client';
import {
  ColumnOverrideItem,
  ColumnProfile,
  DatasetMetadata,
  PaginatedPreview,
  SensitivityCategory,
} from '../../types/dataset';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';

interface DiscoveryViewProps {
  currentDataset: DatasetMetadata | null;
  profiles: ColumnProfile[];
  previewData: PaginatedPreview | null;
  onUpdateOverrides: (overrides: ColumnOverrideItem[]) => Promise<void>;
  onNavigate: (view: any) => void;
  isLoading?: boolean;
}

export const DiscoveryView: React.FC<DiscoveryViewProps> = ({
  currentDataset,
  profiles,
  previewData,
  onUpdateOverrides,
  onNavigate,
}) => {
  const [filterRole, setFilterRole] = useState<'all' | SensitivityCategory>('all');
  const [showRawValues, setShowRawValues] = useState(false);
  const [showRawWarningModal, setShowRawWarningModal] = useState(false);
  const [rawPreviewData, setRawPreviewData] = useState<PaginatedPreview | null>(null);
  const [isLoadingRaw, setIsLoadingRaw] = useState(false);
  const [pendingOverrides, setPendingOverrides] = useState<Record<string, SensitivityCategory>>({});
  const [isSaving, setIsSaving] = useState(false);

  // Reset raw view state whenever dataset changes
  useEffect(() => {
    setShowRawValues(false);
    setRawPreviewData(null);
  }, [currentDataset?.id]);

  // Counts
  const directIdCount = profiles.filter((p) => (pendingOverrides[p.column_name] || p.user_category || p.detected_type) === 'direct_identifier').length;
  const quasiIdCount = profiles.filter((p) => (pendingOverrides[p.column_name] || p.user_category || p.detected_type) === 'quasi_identifier').length;
  const sensitiveCount = profiles.filter((p) => (pendingOverrides[p.column_name] || p.user_category || p.detected_type) === 'sensitive_attribute').length;
  const insensitiveCount = profiles.filter((p) => (pendingOverrides[p.column_name] || p.user_category || p.detected_type) === 'insensitive').length;

  const activePreview = showRawValues && rawPreviewData ? rawPreviewData : previewData;
  const previewRows = activePreview?.rows || (activePreview as any)?.records || [];
  const previewColumns = activePreview?.columns || previewData?.columns || [];

  const handleAuthorizeReveal = async () => {
    setShowRawWarningModal(false);
    if (!currentDataset) return;
    setIsLoadingRaw(true);
    try {
      const raw = await api.getDatasetPreview(currentDataset.id, 1, 20, false);
      setRawPreviewData(raw);
      setShowRawValues(true);
    } catch (err) {
      console.error('Failed to load raw values:', err);
    } finally {
      setIsLoadingRaw(false);
    }
  };

  const handleRoleChange = async (columnName: string, newRole: SensitivityCategory) => {
    setPendingOverrides((prev) => ({
      ...prev,
      [columnName]: newRole,
    }));
    try {
      setIsSaving(true);
      await onUpdateOverrides([{ column_name: columnName, user_category: newRole }]);
      setPendingOverrides((prev) => {
        const next = { ...prev };
        delete next[columnName];
        return next;
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveOverrides = async () => {
    const overrideList: ColumnOverrideItem[] = Object.entries(pendingOverrides).map(
      ([column_name, user_category]) => ({
        column_name,
        user_category,
      })
    );

    if (overrideList.length === 0) return;

    try {
      setIsSaving(true);
      await onUpdateOverrides(overrideList);
      setPendingOverrides({});
    } finally {
      setIsSaving(false);
    }
  };

  const hasPendingChanges = Object.keys(pendingOverrides).length > 0;

  const filteredProfiles = profiles.filter((p) => {
    const effectiveRole = pendingOverrides[p.column_name] || p.user_category || p.detected_type;
    if (filterRole === 'all') return true;
    return effectiveRole === filterRole;
  });

  if (!currentDataset) {
    return (
      <div className="p-12 rounded-2xl bg-surface-panel border border-white/[0.08] text-center space-y-4 shadow-apple-card">
        <div className="w-12 h-12 rounded-xl bg-accent/15 border border-accent/30 flex items-center justify-center text-accent mx-auto">
          <Database className="w-6 h-6" />
        </div>
        <div className="space-y-1">
          <h3 className="text-base font-semibold text-text-primary">No Dataset Selected</h3>
          <p className="text-xs text-text-muted max-w-md mx-auto">
            Please select or ingest a structured dataset from the Dataset Management workspace to initiate sensitive attribute discovery.
          </p>
        </div>
        <Button
          variant="primary"
          size="sm"
          icon={ArrowRight}
          iconPosition="right"
          onClick={() => onNavigate('datasets')}
        >
          Go to Datasets
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Banner & Summary Badges */}
      <div className="p-6 rounded-2xl bg-surface-panel/90 border border-white/[0.08] shadow-apple-card flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs">
            <span className="inline-flex items-center gap-1.5 font-medium text-accent">
              <span className="w-2 h-2 rounded-full bg-accent" />
              4-Tier Detection Active
            </span>
            <span className="text-white/20">•</span>
            <span className="text-text-muted">
              Taxonomy • Regex/Checksums • Dictionaries • Shannon Entropy
            </span>
          </div>
          <h2 className="text-xl font-bold text-text-primary tracking-tight">
            Data Discovery & Classification: {currentDataset.name}
          </h2>
          <p className="text-xs text-text-secondary leading-relaxed">
            Autonomous multi-industry classification. Review inferred roles, confidence ratios, and override attributes before configuring anonymization rules.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {hasPendingChanges && (
            <Button
              variant="primary"
              size="sm"
              icon={Check}
              isLoading={isSaving}
              onClick={handleSaveOverrides}
            >
              Save Overrides ({Object.keys(pendingOverrides).length})
            </Button>
          )}

          <Button
            variant="secondary"
            size="sm"
            icon={ArrowRight}
            iconPosition="right"
            onClick={() => onNavigate('studio')}
          >
            Open in Studio
          </Button>
        </div>
      </div>

      {/* Role Counts Filter Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <button
          onClick={() => setFilterRole(filterRole === 'direct_identifier' ? 'all' : 'direct_identifier')}
          className={`p-3.5 rounded-xl border text-left transition-all ${
            filterRole === 'direct_identifier'
              ? 'bg-accent/20 border-accent text-accent shadow-apple-sm'
              : 'bg-surface-panel border-white/[0.07] hover:border-white/[0.15]'
          }`}
        >
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="font-semibold uppercase tracking-wider text-accent">Direct Identifiers</span>
            <span className="text-lg font-bold font-mono tabular-nums text-text-primary">{directIdCount}</span>
          </div>
          <span className="text-[10px] text-text-muted">Requires Masking / Redaction</span>
        </button>

        <button
          onClick={() => setFilterRole(filterRole === 'quasi_identifier' ? 'all' : 'quasi_identifier')}
          className={`p-3.5 rounded-xl border text-left transition-all ${
            filterRole === 'quasi_identifier'
              ? 'bg-info/20 border-info text-info shadow-apple-sm'
              : 'bg-surface-panel border-white/[0.07] hover:border-white/[0.15]'
          }`}
        >
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="font-semibold uppercase tracking-wider text-info">Quasi-Identifiers</span>
            <span className="text-lg font-bold font-mono tabular-nums text-text-primary">{quasiIdCount}</span>
          </div>
          <span className="text-[10px] text-text-muted">K-Anonymity & Hierarchy</span>
        </button>

        <button
          onClick={() => setFilterRole(filterRole === 'sensitive_attribute' ? 'all' : 'sensitive_attribute')}
          className={`p-3.5 rounded-xl border text-left transition-all ${
            filterRole === 'sensitive_attribute'
              ? 'bg-warning/20 border-warning text-warning shadow-apple-sm'
              : 'bg-surface-panel border-white/[0.07] hover:border-white/[0.15]'
          }`}
        >
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="font-semibold uppercase tracking-wider text-warning">Sensitive Attributes</span>
            <span className="text-lg font-bold font-mono tabular-nums text-text-primary">{sensitiveCount}</span>
          </div>
          <span className="text-[10px] text-text-muted">L-Diversity & T-Closeness</span>
        </button>

        <button
          onClick={() => setFilterRole(filterRole === 'insensitive' ? 'all' : 'insensitive')}
          className={`p-3.5 rounded-xl border text-left transition-all ${
            filterRole === 'insensitive'
              ? 'bg-white/10 border-white/30 text-text-primary shadow-apple-sm'
              : 'bg-surface-panel border-white/[0.07] hover:border-white/[0.15]'
          }`}
        >
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="font-semibold uppercase tracking-wider text-text-secondary">Insensitive Fields</span>
            <span className="text-lg font-bold font-mono tabular-nums text-text-primary">{insensitiveCount}</span>
          </div>
          <span className="text-[10px] text-text-muted">Pass-through Retained</span>
        </button>
      </div>

      {/* Column Classification Table */}
      <div className="p-5 rounded-2xl bg-surface-panel/90 border border-white/[0.07] shadow-apple-card space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ScanSearch className="w-4 h-4 text-accent" />
            <h3 className="text-sm font-semibold text-text-primary">
              Classified Attributes ({filteredProfiles.length} of {profiles.length})
            </h3>
          </div>

          <div className="text-xs text-text-muted font-mono">
            {filterRole !== 'all' ? `Filtered by ${filterRole}` : 'Showing All Columns'}
          </div>
        </div>

        <div className="overflow-x-auto rounded-xl border border-white/[0.06] bg-canvas/40">
          <table className="w-full text-left text-xs">
            <thead className="bg-surface-elevated/70 text-text-muted font-semibold uppercase text-[10px] tracking-wider border-b border-white/[0.06]">
              <tr>
                <th className="py-2.5 px-3">Column Name</th>
                <th className="py-2.5 px-3">Effective Role</th>
                <th className="py-2.5 px-3">Inferred Pattern</th>
                <th className="py-2.5 px-3 text-right">Confidence</th>
                <th className="py-2.5 px-3">Detection Rationale</th>
                <th className="py-2.5 px-3">Sample Masked Values</th>
                <th className="py-2.5 px-3 text-right">Role Override</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {filteredProfiles.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-text-muted italic">
                    No column profiles match the active filter.
                  </td>
                </tr>
              ) : (
                filteredProfiles.map((col) => {
                  const effectiveRole =
                    pendingOverrides[col.column_name] ||
                    col.user_category ||
                    col.detected_type;

                  const isModified = Boolean(pendingOverrides[col.column_name]);

                  return (
                    <tr
                      key={col.column_name}
                      className={`hover:bg-white/[0.02] transition-colors ${
                        isModified ? 'bg-accent/5' : ''
                      }`}
                    >
                      <td className="py-3 px-3">
                        <div className="font-semibold text-text-primary font-mono text-xs">
                          {col.column_name}
                        </div>
                        <div className="text-[10px] text-text-muted font-mono">
                          {col.unique_count} distinct • {col.null_count} nulls
                        </div>
                      </td>

                      <td className="py-3 px-3">
                        <Badge role={effectiveRole} text={effectiveRole.replace('_', ' ')} size="xs" />
                      </td>

                      <td className="py-3 px-3 font-mono text-[11px] text-text-secondary">
                        <span className="px-1.5 py-0.5 rounded bg-white/[0.04] border border-white/[0.06]">
                          {col.specific_type}
                        </span>
                      </td>

                      <td className="py-3 px-3 text-right font-mono tabular-nums text-text-primary">
                        <div className="flex items-center justify-end gap-2">
                          <div className="w-12 h-1.5 rounded-full bg-white/[0.08] overflow-hidden">
                            <div
                              className="h-full bg-accent rounded-full"
                              style={{ width: `${Math.round(col.confidence * 100)}%` }}
                            />
                          </div>
                          <span>{Math.round(col.confidence * 100)}%</span>
                        </div>
                      </td>

                      <td className="py-3 px-3 text-text-secondary text-[11px] max-w-xs truncate" title={col.explanation}>
                        {col.explanation}
                      </td>

                      <td className="py-3 px-3 font-mono text-[11px] text-text-muted max-w-xs truncate">
                        {col.sample_values_masked?.length > 0
                          ? col.sample_values_masked.slice(0, 3).join(', ')
                          : '—'}
                      </td>

                      <td className="py-3 px-3 text-right">
                        <select
                          value={effectiveRole}
                          onChange={(e) =>
                            handleRoleChange(col.column_name, e.target.value as SensitivityCategory)
                          }
                          className="bg-surface-elevated border border-white/[0.1] rounded-lg px-2 py-1 text-xs text-text-primary outline-none focus:border-accent/40 cursor-pointer"
                        >
                          <option value="direct_identifier" className="bg-surface-panel">
                            Direct Identifier
                          </option>
                          <option value="quasi_identifier" className="bg-surface-panel">
                            Quasi-Identifier
                          </option>
                          <option value="sensitive_attribute" className="bg-surface-panel">
                            Sensitive Attribute
                          </option>
                          <option value="insensitive" className="bg-surface-panel">
                            Insensitive Field
                          </option>
                        </select>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Sanitized Dataset Preview Table */}
      {previewData && (
        <div className="p-5 rounded-2xl bg-surface-panel/90 border border-white/[0.07] shadow-apple-card space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-text-primary">
                Sanitized Sample Preview (First {previewRows.length} Records)
              </h3>
              <p className="text-xs text-text-muted">
                Direct identifiers rendered with security masks in compliance with privacy guidelines.
              </p>
            </div>

            <button
              disabled={isLoadingRaw}
              onClick={() => {
                if (!showRawValues) {
                  setShowRawWarningModal(true);
                } else {
                  setShowRawValues(false);
                }
              }}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${
                isLoadingRaw
                  ? 'opacity-60 cursor-not-allowed bg-accent/15 border-accent/30 text-accent'
                  : showRawValues
                  ? 'bg-warning/15 border-warning/30 text-warning hover:bg-warning/25 cursor-pointer'
                  : 'bg-accent/15 border-accent/30 text-accent hover:bg-accent/25 cursor-pointer'
              }`}
            >
              {isLoadingRaw ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : showRawValues ? (
                <EyeOff className="w-3.5 h-3.5" />
              ) : (
                <Eye className="w-3.5 h-3.5" />
              )}
              <span>
                {isLoadingRaw
                  ? 'Loading Raw Values...'
                  : showRawValues
                  ? 'Re-mask Sensitive Values'
                  : 'Reveal Raw Values (Audit Logged)'}
              </span>
            </button>
          </div>

          <div className="overflow-x-auto rounded-xl border border-white/[0.06] bg-canvas/40 max-h-72">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 bg-surface-elevated/90 backdrop-blur-md text-text-muted font-semibold uppercase text-[10px] tracking-wider border-b border-white/[0.06]">
                <tr>
                  <th className="py-2 px-3 text-center w-12">#</th>
                  {previewColumns.map((c) => (
                    <th key={c} className="py-2 px-3 font-mono">
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {previewRows.map((row: any, idx: number) => (
                  <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-1.5 px-3 text-center text-text-muted font-mono tabular-nums text-[11px]">
                      {idx + 1}
                    </td>
                    {previewColumns.map((c) => {
                      const profile = profiles.find((p) => p.column_name === c);
                      const effectiveRole = pendingOverrides[c] || profile?.user_category || profile?.detected_type;
                      const isDirect = effectiveRole === 'direct_identifier';
                      const val = row[c];

                      let displayVal = val;
                      if (!showRawValues && isDirect && val !== null && val !== undefined) {
                        displayVal = '••••••••';
                      }

                      return (
                        <td key={c} className="py-1.5 px-3 font-mono text-[11px] text-text-primary truncate max-w-xs">
                          {displayVal !== null && displayVal !== undefined ? (
                            String(displayVal)
                          ) : (
                            <span className="text-text-muted opacity-40">—</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Security Warning Modal for Raw Reveal */}
      {showRawWarningModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="bg-surface-panel border border-warning/40 rounded-2xl shadow-apple-modal max-w-md w-full p-6 space-y-4 animate-modal-enter">
            <div className="flex items-center gap-2.5 text-warning">
              <Lock className="w-5 h-5" />
              <h3 className="text-base font-bold text-text-primary">
                Security Authorization Warning
              </h3>
            </div>
            <p className="text-xs text-text-secondary leading-relaxed">
              Revealing plaintext direct identifiers temporarily exposes raw personal information in memory. This event is logged in the local audit trail for security compliance.
            </p>
            <div className="flex items-center justify-end gap-2.5 pt-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowRawWarningModal(false)}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={handleAuthorizeReveal}
              >
                Authorize & Reveal
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
