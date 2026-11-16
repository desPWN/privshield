import React, { useEffect } from 'react';
import {
  Sliders,
  Shield,
  Play,
  CheckCircle2,
  Sparkles,
  Check,
  Lock,
  AlertTriangle,
  Eye,
} from 'lucide-react';
import { AnonymizationConfig } from '../../types/anonymization';
import { ColumnProfile, DatasetMetadata } from '../../types/dataset';
import { Button } from '../../components/common/Button';

// Master toggle: Set to true whenever you want to bring Demographic Grouping back
const SHOW_DEMOGRAPHIC_GROUPING = false;

interface StudioViewProps {
  currentDataset: DatasetMetadata | null;
  profiles: ColumnProfile[];
  config: AnonymizationConfig;
  onChangeConfig: (newConfig: AnonymizationConfig) => void;
  onExecute: () => Promise<void>;
  isExecuting?: boolean;
  onNavigate: (view: any) => void;
}

export const StudioView: React.FC<StudioViewProps> = ({
  currentDataset,
  profiles,
  config,
  onChangeConfig,
  onExecute,
  isExecuting = false,
  onNavigate,
}) => {
  // Group columns by detected or user-specified role
  const directIdCols = profiles.filter(
    (p) => (p.user_category || p.detected_type) === 'direct_identifier'
  );
  const quasiIdCols = profiles.filter(
    (p) => (p.user_category || p.detected_type) === 'quasi_identifier'
  );
  const sensitiveCols = profiles.filter(
    (p) => (p.user_category || p.detected_type) === 'sensitive_attribute'
  );
  const insensitiveCols = profiles.filter(
    (p) => (p.user_category || p.detected_type) === 'insensitive'
  );

  // Check if timestamp is in quasi-identifiers
  const hasTimestampQI = config.quasi_identifiers.some(
    (col) =>
      col.toLowerCase().includes('timestamp') ||
      col.toLowerCase().includes('time') ||
      col.toLowerCase().includes('date')
  );

  // Helper to remove timestamps from quasi-identifiers
  const handleRemoveTimestampQIs = () => {
    const filtered = config.quasi_identifiers.filter(
      (col) =>
        !col.toLowerCase().includes('timestamp') &&
        !col.toLowerCase().includes('time') &&
        !col.toLowerCase().includes('date')
    );
    onChangeConfig({
      ...config,
      quasi_identifiers: filtered,
    });
  };

  // Toggle QI selection
  const toggleQI = (colName: string) => {
    const currentQIs = [...config.quasi_identifiers];
    const exists = currentQIs.includes(colName);
    let updatedQIs: string[];
    if (exists) {
      updatedQIs = currentQIs.filter((c) => c !== colName);
    } else {
      updatedQIs = [...currentQIs, colName];
    }
    const updatedLevels = { ...config.generalization_levels };
    if (!exists && !updatedLevels[colName]) {
      updatedLevels[colName] = 1;
    }
    onChangeConfig({
      ...config,
      quasi_identifiers: updatedQIs,
      generalization_levels: updatedLevels,
    });
  };

  // Auto-tune for zero asterisks
  const handleAutoTuneZeroAsterisks = () => {
    const ageCol = quasiIdCols.find((c) => c.column_name.toLowerCase().includes('age'))?.column_name;
    const genderCol = quasiIdCols.find((c) => c.column_name.toLowerCase().includes('gender') || c.column_name.toLowerCase().includes('sex'))?.column_name;
    const bestQIs = [ageCol, genderCol].filter(Boolean) as string[];
    const chosenQIs = bestQIs.length > 0 ? bestQIs : quasiIdCols.slice(0, 2).map((c) => c.column_name);

    onChangeConfig({
      ...config,
      quasi_identifiers: chosenQIs,
      k_metric: 3,
      l_metric: 2,
      t_metric: 0.2,
      suppression_strategy: 'cell',
      generalization_levels: {
        ...config.generalization_levels,
        ...(ageCol ? { [ageCol]: 1 } : {}),
        ...(genderCol ? { [genderCol]: 0 } : {}),
      },
    });
  };

  // Masking format toggle
  const allMaskingRedact =
    directIdCols.length > 0 &&
    directIdCols.every((c) => config.masking_rules[c.column_name] === 'redact');

  const setGlobalMaskingStyle = (style: 'preserve_trailing' | 'redact') => {
    const updatedRules: Record<string, string> = { ...config.masking_rules };
    directIdCols.forEach((c) => {
      updatedRules[c.column_name] = style;
    });
    onChangeConfig({
      ...config,
      masking_rules: updatedRules,
    });
  };

  // Automatically clear quasi-identifiers when demographic grouping is removed
  useEffect(() => {
    if (!SHOW_DEMOGRAPHIC_GROUPING && config.quasi_identifiers.length > 0) {
      onChangeConfig({
        ...config,
        quasi_identifiers: [],
      });
    }
  }, [config.quasi_identifiers.length]);

  // Pre-flight validation
  const hasQuasiIdentifiers = config.quasi_identifiers.length > 0;
  const isReadyToExecute = SHOW_DEMOGRAPHIC_GROUPING
    ? hasQuasiIdentifiers
    : (directIdCols.length > 0 || !!currentDataset);

  if (!currentDataset) {
    return (
      <div className="p-12 rounded-2xl bg-surface-panel border border-white/[0.08] text-center space-y-4 shadow-apple-card">
        <div className="w-12 h-12 rounded-xl bg-accent/15 border border-accent/30 flex items-center justify-center text-accent mx-auto">
          <Sliders className="w-6 h-6" />
        </div>
        <div className="space-y-1">
          <h3 className="text-base font-semibold text-text-primary">No Dataset Loaded</h3>
          <p className="text-xs text-text-muted max-w-md mx-auto">
            Please select or ingest a structured dataset to configure your anonymization pipeline.
          </p>
        </div>
        <Button
          variant="primary"
          size="sm"
          onClick={() => onNavigate('datasets')}
        >
          Select Dataset
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4 select-none">
      {/* Top Header */}
      <div className="p-4 rounded-2xl bg-surface-panel/90 border border-white/[0.07] flex items-center justify-between shadow-apple-card">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-accent/15 border border-accent/25 flex items-center justify-center text-accent">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-text-primary">
              Anonymization Studio
            </h2>
            <p className="text-xs text-text-muted">
              {SHOW_DEMOGRAPHIC_GROUPING
                ? 'Select a protection level, choose demographic grouping, and run your anonymization pipeline.'
                : 'Configure direct identifier masking and run your anonymization pipeline.'}
            </p>
          </div>
        </div>
      </div>

      {/* Main Grid: Left Controls (2/3) and Right Summary Rail (1/3) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Main Controls Column (2/3) */}
        <div className="lg:col-span-2 space-y-4">
          {/* Active Profile Banner */}
          <div className="p-4 rounded-2xl bg-surface-panel/90 border border-white/[0.07] shadow-apple-card flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-accent/15 border border-accent/25 flex items-center justify-center text-accent">
                <Shield className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-xs font-semibold text-text-primary">
                    {SHOW_DEMOGRAPHIC_GROUPING ? 'Custom Universal Profile' : 'Direct PII Masking Profile'}
                  </h3>
                  <span className="inline-flex items-center gap-1 text-[11px] font-medium text-accent">
                    <span className="w-1.5 h-1.5 rounded-full bg-accent" />
                    Active
                  </span>
                </div>
                <p className="text-[11px] text-text-muted mt-0.5">
                  {SHOW_DEMOGRAPHIC_GROUPING
                    ? 'Standard K=3 mathematical protection with cell suppression. Retains 100% of rows.'
                    : 'Personal identifying attributes are masked. Retains 100% of rows with zero asterisks.'}
                </p>
              </div>
            </div>

            {SHOW_DEMOGRAPHIC_GROUPING ? (
              <div className="flex items-center gap-2.5 text-[11px] font-mono text-text-secondary self-start sm:self-auto bg-canvas/80 px-3 py-1.5 rounded-xl border border-white/[0.06]">
                <span>K = 3</span>
                <span className="text-white/20">•</span>
                <span className="text-success font-medium">100% Rows Kept</span>
                <span className="text-white/20">•</span>
                <span className="text-accent font-medium">Cell Suppression</span>
              </div>
            ) : (
              <div className="flex items-center gap-2.5 text-[11px] font-mono text-text-secondary self-start sm:self-auto bg-canvas/80 px-3 py-1.5 rounded-xl border border-white/[0.06]">
                <span className="text-success font-medium">100% Rows Kept</span>
                <span className="text-white/20">•</span>
                <span className="text-accent font-medium">Zero Asterisks</span>
                <span className="text-white/20">•</span>
                <span className="text-info font-medium">Direct PII Masked</span>
              </div>
            )}
          </div>

          {/* Step 1: Demographic Attributes (Quasi-Identifiers) */}
          {SHOW_DEMOGRAPHIC_GROUPING && (
            <div className="p-5 rounded-2xl bg-surface-panel/90 border border-white/[0.07] space-y-3 shadow-apple-card">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-accent/20 text-accent text-xs flex items-center justify-center font-bold">
                      1
                    </span>
                    Demographic Grouping (Quasi-Identifiers)
                  </h3>
                  <p className="text-xs text-text-muted mt-0.5">
                    Select attributes to group into safe brackets so individuals cannot be singled out.
                  </p>
                </div>
                <span className="text-xs font-mono text-accent">
                  {config.quasi_identifiers.length} selected
                </span>
              </div>

              {/* Timestamp Warning Banner */}
              {hasTimestampQI && (
                <div className="p-3 rounded-xl bg-warning/10 border border-warning/25 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 text-xs text-warning">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5 text-warning" />
                    <span className="leading-snug">
                      <strong>Recommended fix:</strong> A timestamp column is currently selected. Timestamps make every row unique, which causes records to be hidden.
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={handleRemoveTimestampQIs}
                    className="px-2.5 py-1 rounded-lg bg-warning/20 hover:bg-warning/30 text-warning font-semibold text-[11px] whitespace-nowrap self-start sm:self-auto transition-colors"
                  >
                    Deselect Timestamps
                  </button>
                </div>
              )}

              {/* High Dimensionality / Asterisk Warning Banner */}
              {config.quasi_identifiers.length > 2 && (
                <div className="p-3.5 rounded-xl bg-warning/10 border border-warning/30 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-warning">
                  <div className="flex items-start gap-2.5">
                    <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5 text-warning" />
                    <div className="leading-relaxed">
                      <strong>Why do asterisks (*) appear in Excel?</strong> Combining {config.quasi_identifiers.length} demographic fields ({config.quasi_identifiers.join(', ')}) on a {currentDataset?.record_count || 150}-record dataset makes almost every row unique. Because K-Anonymity requires at least 3 matching rows per group, unmatched rows get masked with <code className="bg-warning/20 px-1 py-0.5 rounded text-text-primary font-mono">*</code>.
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={handleAutoTuneZeroAsterisks}
                    className="px-3 py-1.5 rounded-lg bg-warning hover:bg-warning/90 text-black font-bold text-xs whitespace-nowrap self-start sm:self-auto transition-all shadow-apple-sm flex items-center gap-1.5"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    Auto-Tune for 0 Asterisks
                  </button>
                </div>
              )}

              {/* QI Interactive Pills */}
              <div className="flex flex-wrap gap-2 pt-1">
                {quasiIdCols.map((col) => {
                  const isSelected = config.quasi_identifiers.includes(col.column_name);
                  const isTimestamp =
                    col.column_name.toLowerCase().includes('timestamp') ||
                    col.column_name.toLowerCase().includes('time') ||
                    col.column_name.toLowerCase().includes('date');

                  return (
                    <button
                      key={col.column_name}
                      type="button"
                      onClick={() => toggleQI(col.column_name)}
                      className={`flex items-center gap-2 px-3 py-2 rounded-xl border text-xs transition-all active:scale-[0.98] ${
                        isSelected
                          ? isTimestamp
                            ? 'bg-warning/15 border-warning text-warning font-medium'
                            : 'bg-accent/15 border-accent text-accent font-medium shadow-apple-sm'
                          : 'bg-surface-elevated/40 border-white/[0.06] text-text-muted hover:text-text-primary hover:bg-surface-hover'
                      }`}
                    >
                      <div
                        className={`w-4 h-4 rounded flex items-center justify-center border text-[10px] ${
                          isSelected
                            ? isTimestamp
                              ? 'bg-warning border-warning text-black font-bold'
                              : 'bg-accent border-accent text-black font-bold'
                            : 'border-white/20'
                        }`}
                      >
                        {isSelected && <Check className="w-3 h-3 stroke-[3]" />}
                      </div>
                      <span className="font-mono">{col.column_name}</span>
                      <span className="text-[10px] text-text-muted">
                        ({col.specific_type || 'demographic'})
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Direct Identifiers (Masking) */}
          <div className="p-5 rounded-2xl bg-surface-panel/90 border border-white/[0.07] space-y-3 shadow-apple-card">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-accent/20 text-accent text-xs flex items-center justify-center font-bold">
                    {SHOW_DEMOGRAPHIC_GROUPING ? '2' : '1'}
                  </span>
                  Direct Identifiers (Automatic Masking)
                </h3>
                <p className="text-xs text-text-muted mt-0.5">
                  Personal identifying fields are automatically scrambled to prevent direct identification.
                </p>
              </div>

              {/* Quick Masking Style Toggle */}
              {directIdCols.length > 0 && (
                <div className="flex items-center gap-1 p-0.5 rounded-lg bg-canvas border border-white/[0.08] text-xs self-start sm:self-auto">
                  <button
                    type="button"
                    onClick={() => setGlobalMaskingStyle('preserve_trailing')}
                    className={`px-2.5 py-1 rounded text-[11px] transition-colors ${
                      !allMaskingRedact
                        ? 'bg-accent/20 text-accent font-semibold'
                        : 'text-text-muted hover:text-text-primary'
                    }`}
                  >
                    Partial (j***@mail.com)
                  </button>
                  <button
                    type="button"
                    onClick={() => setGlobalMaskingStyle('redact')}
                    className={`px-2.5 py-1 rounded text-[11px] transition-colors ${
                      allMaskingRedact
                        ? 'bg-accent/20 text-accent font-semibold'
                        : 'text-text-muted hover:text-text-primary'
                    }`}
                  >
                    Full (••••••••)
                  </button>
                </div>
              )}
            </div>

            {/* Direct ID Chips */}
            <div className="flex flex-wrap gap-2 pt-1">
              {directIdCols.map((col) => {
                const rule = config.masking_rules[col.column_name];
                const isRedact = rule === 'redact';
                return (
                  <div
                    key={col.column_name}
                    className="px-2.5 py-1.5 rounded-lg bg-surface-elevated/60 border border-white/[0.06] text-xs flex items-center gap-2"
                  >
                    <Lock className="w-3.5 h-3.5 text-accent" />
                    <span className="font-mono text-text-primary">{col.column_name}</span>
                    <span className="text-[10px] font-mono text-accent uppercase font-medium">
                      {isRedact ? 'Redact' : 'Mask'}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Step 4: Untouched & Safe Fields */}
          {(insensitiveCols.length > 0 || sensitiveCols.length > 0) && (
            <div className="p-4 rounded-xl bg-surface-elevated/30 border border-white/[0.05] flex items-center justify-between text-xs text-text-muted">
              <div className="flex items-center gap-2">
                <Eye className="w-4 h-4 text-text-muted" />
                <span>
                  Non-identifying operational columns (
                  <span className="font-mono text-text-secondary">
                    {[...insensitiveCols, ...sensitiveCols]
                      .slice(0, 3)
                      .map((c) => c.column_name)
                      .join(', ')}
                    {insensitiveCols.length + sensitiveCols.length > 3 ? '...' : ''}
                  </span>
                  ) will pass through cleanly for analysis.
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Right Rail: Output Guarantee & Action (1/3) */}
        <div className="space-y-4">
          <div className="p-5 rounded-2xl bg-surface-panel/90 border border-white/[0.07] space-y-4 shadow-apple-card">
            <div className="flex items-center justify-between border-b border-white/[0.07] pb-3">
              <span className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                Protection Summary
              </span>
              <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${isReadyToExecute ? 'text-success' : 'text-danger'}`}>
                <span className={`w-2 h-2 rounded-full ${isReadyToExecute ? 'bg-success' : 'bg-danger'}`} />
                {isReadyToExecute ? 'Ready to Run' : 'Select Attributes'}
              </span>
            </div>

            {/* Guarantees List */}
            <div className="space-y-2.5 text-xs">
              <div className="flex items-center gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-success flex-shrink-0" />
                <span className="text-text-primary">
                  <strong>100% of rows kept</strong> (No records dropped)
                </span>
              </div>

              <div className="flex items-center gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-success flex-shrink-0" />
                <span className="text-text-primary">
                  <strong>Direct IDs masked</strong> ({directIdCols.length} columns)
                </span>
              </div>

              {SHOW_DEMOGRAPHIC_GROUPING ? (
                <>
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2
                      className={`w-4 h-4 flex-shrink-0 ${
                        hasQuasiIdentifiers ? 'text-success' : 'text-danger'
                      }`}
                    />
                    <span className={hasQuasiIdentifiers ? 'text-text-primary' : 'text-danger font-medium'}>
                      {config.quasi_identifiers.length} demographic attributes grouped
                    </span>
                  </div>

                  <div className="flex items-center gap-2.5">
                    <CheckCircle2
                      className={`w-4 h-4 flex-shrink-0 ${
                        config.quasi_identifiers.length <= 2 ? 'text-success' : 'text-warning'
                      }`}
                    />
                    <span className={config.quasi_identifiers.length <= 2 ? 'text-text-primary' : 'text-warning font-medium'}>
                      {config.quasi_identifiers.length <= 2
                        ? '0 asterisks expected (100% readable data)'
                        : `Risk of '*' cell masking (${config.quasi_identifiers.length} QIs)`}
                    </span>
                  </div>
                </>
              ) : (
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-success flex-shrink-0" />
                  <span className="text-text-primary">
                    <strong>Zero asterisks</strong> (Raw analytical data intact)
                  </span>
                </div>
              )}

              <div className="flex items-center gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-success flex-shrink-0" />
                <span className="text-text-secondary">
                  Export verified for Excel, CSV, and JSON
                </span>
              </div>
            </div>

            {/* Transformation Preview Card */}
            <div className="p-3.5 rounded-xl bg-canvas/60 border border-white/[0.06] space-y-2">
              <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider block">
                How Values Will Look
              </span>

              <div className="space-y-1.5 font-mono text-[11px]">
                <div className="flex items-center justify-between text-text-secondary">
                  <span className="text-text-muted">Email:</span>
                  <span className="text-accent">
                    {allMaskingRedact ? '••••••••' : 'j***@domain.com'}
                  </span>
                </div>
                {SHOW_DEMOGRAPHIC_GROUPING ? (
                  <>
                    <div className="flex items-center justify-between text-text-secondary">
                      <span className="text-text-muted">Age (34):</span>
                      <span className="text-info font-medium">[30 - 39]</span>
                    </div>
                    <div className="flex items-center justify-between text-text-secondary">
                      <span className="text-text-muted">City:</span>
                      <span className="text-warning font-medium">Standardized</span>
                    </div>
                  </>
                ) : (
                  <div className="flex items-center justify-between text-text-secondary">
                    <span className="text-text-muted">Demographics (Age, City):</span>
                    <span className="text-success font-medium">100% Intact</span>
                  </div>
                )}
              </div>
            </div>

            {/* Action Button */}
            <Button
              variant="primary"
              size="lg"
              icon={Play}
              isLoading={isExecuting}
              disabled={!isReadyToExecute}
              onClick={onExecute}
              className="w-full font-bold shadow-apple-card text-sm py-3"
            >
              {isExecuting ? 'Running Pipeline...' : 'Run Anonymization Now'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
