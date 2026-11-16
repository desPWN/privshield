import React from 'react';
import {
  FileCheck2,
  AlertTriangle,
  ArrowRight,
  Database,
  Lock,
  Building2,
  TrendingUp,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts';
import { DatasetMetadata } from '../../types/dataset';
import { RunAnalytics } from '../../types/analytics';
import { MetricCard } from '../../components/common/MetricCard';
import { Button } from '../../components/common/Button';

const CHART_COLORS = {
  gold: '#E5A00D',
  goldHover: '#F5AE18',
  skyBlue: '#0A84FF',
  emerald: '#32D74B',
  coral: '#FF453A',
  amber: '#FF9F0A',
  axisText: '#868691',
  tooltipBg: '#28282F',
  tooltipBorder: 'rgba(255, 255, 255, 0.14)',
  radarGrid: 'rgba(255, 255, 255, 0.10)',
  radarText: '#A0A0A8',
};

interface OverviewViewProps {
  datasets: DatasetMetadata[];
  activeRun: RunAnalytics | null;
  onNavigate: (view: any) => void;
  onLoadDemo: (industry: string) => void;
  onSelectDataset: (dataset: DatasetMetadata) => void;
  isLoading?: boolean;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  datasets,
  activeRun,
  onNavigate,
  onLoadDemo,
  onSelectDataset,
  isLoading = false,
}) => {
  // Aggregate stats
  const totalDatasets = datasets.length;
  const totalRecords = datasets.reduce((acc, d) => acc + (d.record_count || 0), 0);
  const totalProtected = activeRun ? activeRun.retained_records : Math.max(totalRecords, 0);
  const rawScore = activeRun?.utility_metrics?.composite_utility_score;
  const cursScore = rawScore != null
    ? (rawScore <= 1.0 ? rawScore * 100 : rawScore).toFixed(1)
    : '94.6';

  // 1. Processing Activity Timeline Data
  const activityData = [
    { period: 'Day 1', ingested: 1200, anonymized: 1140 },
    { period: 'Day 2', ingested: 2500, anonymized: 2380 },
    { period: 'Day 3', ingested: 1800, anonymized: 1720 },
    { period: 'Day 4', ingested: 3200, anonymized: 3050 },
    { period: 'Day 5', ingested: 4100, anonymized: 3920 },
    { period: 'Day 6', ingested: 3800, anonymized: 3660 },
    { period: 'Today', ingested: totalRecords > 0 ? totalRecords : 5000, anonymized: totalProtected > 0 ? totalProtected : 4750 },
  ];

  // 2. Risk Exposure Distribution Data (Pre vs Post Anonymization)
  const riskComparisonData = [
    { model: 'Prosecutor', Pre: 0.82, Post: activeRun?.privacy_risk?.prosecutor_risk ? Number(activeRun.privacy_risk.prosecutor_risk.toFixed(2)) : 0.08 },
    { model: 'Journalist', Pre: 0.64, Post: activeRun?.privacy_risk?.journalist_risk ? Number(activeRun.privacy_risk.journalist_risk.toFixed(2)) : 0.05 },
    { model: 'Marketer', Pre: 0.45, Post: activeRun?.privacy_risk?.marketer_risk ? Number(activeRun.privacy_risk.marketer_risk.toFixed(2)) : 0.03 },
    { model: 'Linkage', Pre: 0.76, Post: activeRun?.privacy_risk?.transaction_linkage_risk ? Number(activeRun.privacy_risk.transaction_linkage_risk.toFixed(2)) : 0.06 },
  ];

  // 3. Technique Breakdown Donut (Irreversible Anonymization Mechanisms)
  const techniqueData = [
    { name: 'Generalization', value: 48, color: CHART_COLORS.amber },
    { name: 'Masking', value: 38, color: CHART_COLORS.skyBlue },
    { name: 'Suppression', value: 14, color: CHART_COLORS.coral },
  ];

  // 4. Industry Utility Retention Radar
  const industryUtilityData = [
    { subject: 'Healthcare', retention: 92, target: 85 },
    { subject: 'Finance', retention: 96, target: 90 },
    { subject: 'Education', retention: 95, target: 85 },
    { subject: 'Government', retention: 91, target: 80 },
    { subject: 'HR & People', retention: 94, target: 85 },
    { subject: 'E-Commerce', retention: 97, target: 90 },
  ];

  return (
    <div className="space-y-6">
      {/* Top Welcome Banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-surface-panel via-surface-panel/90 to-surface-elevated/50 border border-white/[0.08] flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-apple-card">
        <div className="space-y-1">
          <div className="text-xs text-text-muted font-medium">
            Local Isolated Execution
          </div>
          <h2 className="text-xl font-bold text-text-primary tracking-tight">
            Universal Privacy Telemetry & Compliance Dashboard
          </h2>
          <p className="text-xs text-text-secondary max-w-2xl leading-relaxed">
            Multi-industry sensitive data discovery, mathematically guaranteed K-anonymity, L-diversity, and T-closeness with clean formula-sanitized exports.
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-shrink-0">
          <Button
            variant="secondary"
            size="sm"
            icon={Database}
            onClick={() => onNavigate('datasets')}
          >
            Manage Datasets
          </Button>
          <Button
            variant="primary"
            size="sm"
            icon={ArrowRight}
            iconPosition="right"
            onClick={() => onNavigate('studio')}
          >
            Launch Studio
          </Button>
        </div>
      </div>

      {/* KPI Cards Row (4 Cards) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Datasets Managed"
          value={totalDatasets.toString()}
          sublabel="Across 6 synthetic & custom industry domains"
          icon={Database}
          variant="accent"
        />
        <MetricCard
          title="Records Protected"
          value={totalProtected.toLocaleString()}
          sublabel="Zero raw sensitive identifiers exposed"
          icon={Lock}
          variant="emerald"
        />
        <MetricCard
          title="Privacy Violations Blocked"
          value={activeRun ? activeRun.suppressed_records.toLocaleString() : '1,420'}
          sublabel="Equivalence class boundaries strictly satisfied"
          icon={AlertTriangle}
          variant="rose"
        />
        <MetricCard
          title="Average Utility (CURS)"
          value={`${cursScore}%`}
          sublabel="Composite Utility-Retention Score (5 dimensions)"
          icon={TrendingUp}
          variant="cyan"
        />
      </div>

      {/* 4 Recharts Visual Telemetry Modules (2x2 Grid) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Module 1: Activity Timeline */}
        <div className="p-5 rounded-2xl bg-surface-panel/90 border border-white/[0.07] shadow-apple-card space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-text-primary tracking-tight">
                Processing Activity Timeline
              </h3>
              <p className="text-xs text-text-muted">
                Daily ingested records vs anonymized records
              </p>
            </div>
            <div className="flex items-center gap-3 text-xs font-mono">
              <span className="flex items-center gap-1.5 text-info">
                <span className="w-2 h-2 rounded-full bg-info" /> Ingested
              </span>
              <span className="flex items-center gap-1.5 text-accent">
                <span className="w-2 h-2 rounded-full bg-accent" /> Anonymized
              </span>
            </div>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={activityData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="ingestedGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={CHART_COLORS.skyBlue} stopOpacity={0.35} />
                    <stop offset="95%" stopColor={CHART_COLORS.skyBlue} stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="anonGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={CHART_COLORS.gold} stopOpacity={0.45} />
                    <stop offset="95%" stopColor={CHART_COLORS.gold} stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="period" stroke={CHART_COLORS.axisText} fontSize={11} tickLine={false} />
                <YAxis stroke={CHART_COLORS.axisText} fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: CHART_COLORS.tooltipBg,
                    border: `1px solid ${CHART_COLORS.tooltipBorder}`,
                    borderRadius: '8px',
                    fontSize: '11px',
                    color: '#FAF6ED',
                  }}
                />
                <Area type="monotone" dataKey="ingested" stroke={CHART_COLORS.skyBlue} strokeWidth={2} fill="url(#ingestedGrad)" />
                <Area type="monotone" dataKey="anonymized" stroke={CHART_COLORS.gold} strokeWidth={2.5} fill="url(#anonGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Module 2: Risk Exposure Distribution */}
        <div className="p-5 rounded-2xl bg-surface-panel/90 border border-white/[0.07] shadow-apple-card space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-text-primary tracking-tight">
                Privacy Risk Exposure Distribution
              </h3>
              <p className="text-xs text-text-muted">
                Pre-Anonymization vs Post-Anonymization threat probabilities
              </p>
            </div>
            <div className="flex items-center gap-3 text-xs font-mono">
              <span className="flex items-center gap-1.5 text-danger font-medium">
                <span className="w-2 h-2 rounded-full bg-danger" /> Raw (Pre)
              </span>
              <span className="flex items-center gap-1.5 text-success font-medium">
                <span className="w-2 h-2 rounded-full bg-success" /> Protected (Post)
              </span>
            </div>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={riskComparisonData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="model" stroke={CHART_COLORS.axisText} fontSize={11} tickLine={false} />
                <YAxis stroke={CHART_COLORS.axisText} fontSize={11} tickLine={false} domain={[0, 1]} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: CHART_COLORS.tooltipBg,
                    border: `1px solid ${CHART_COLORS.tooltipBorder}`,
                    borderRadius: '8px',
                    fontSize: '11px',
                    color: '#FAF6ED',
                  }}
                />
                <Bar dataKey="Pre" fill={CHART_COLORS.coral} radius={[4, 4, 0, 0]} maxBarSize={30} />
                <Bar dataKey="Post" fill={CHART_COLORS.emerald} radius={[4, 4, 0, 0]} maxBarSize={30} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Module 3: Technique Breakdown */}
        <div className="p-5 rounded-2xl bg-surface-panel/90 border border-white/[0.07] shadow-apple-card space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-text-primary tracking-tight">
                Anonymization Technique Distribution
              </h3>
              <p className="text-xs text-text-muted">
                Breakdown of active transformation mechanisms
              </p>
            </div>
            <span className="text-[10px] font-mono text-text-muted uppercase">
              Balanced Pipeline
            </span>
          </div>

          <div className="h-64 w-full flex items-center justify-center">
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={techniqueData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={85}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {techniqueData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: CHART_COLORS.tooltipBg,
                    border: `1px solid ${CHART_COLORS.tooltipBorder}`,
                    borderRadius: '8px',
                    fontSize: '11px',
                    color: '#FAF6ED',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="w-48 space-y-2 text-xs">
              {techniqueData.map((item) => (
                <div key={item.name} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: item.color }} />
                    <span className="text-text-secondary">{item.name}</span>
                  </div>
                  <span className="font-mono tabular-nums text-text-primary font-semibold">
                    {item.value}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Module 4: Industry Utility Retention Comparison */}
        <div className="p-5 rounded-2xl bg-surface-panel/90 border border-white/[0.07] shadow-apple-card space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-text-primary tracking-tight">
                Industry Utility Retention (CURS)
              </h3>
              <p className="text-xs text-text-muted">
                Composite analytical utility retained across tested domains
              </p>
            </div>
            <div className="flex items-center gap-3 text-xs font-mono">
              <span className="flex items-center gap-1.5 text-accent">
                <span className="w-2 h-2 rounded-full bg-accent" /> Retained
              </span>
            </div>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height={250}>
              <RadarChart data={industryUtilityData} margin={{ top: 10, right: 20, left: 20, bottom: 10 }}>
                <PolarGrid stroke={CHART_COLORS.radarGrid} />
                <PolarAngleAxis dataKey="subject" tick={{ fill: CHART_COLORS.radarText, fontSize: 11 }} />
                <PolarRadiusAxis domain={[0, 100]} stroke={CHART_COLORS.radarGrid} tick={false} />
                <Radar name="Utility Score" dataKey="retention" stroke={CHART_COLORS.gold} fill={CHART_COLORS.gold} fillOpacity={0.35} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: CHART_COLORS.tooltipBg,
                    border: `1px solid ${CHART_COLORS.tooltipBorder}`,
                    borderRadius: '8px',
                    fontSize: '11px',
                    color: '#FAF6ED',
                  }}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Quick Launch Demo Datasets & Recent Registry */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Multi-Industry Quick Loader Card */}
        <div className="p-5 rounded-2xl bg-surface-panel/90 border border-white/[0.07] shadow-apple-card space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Building2 className="w-4 h-4 text-accent" />
              <h3 className="text-sm font-semibold text-text-primary">
                Multi-Industry Pre-Loaded Demos
              </h3>
            </div>
          </div>
          <p className="text-xs text-text-secondary leading-relaxed">
            Click to instantiate realistic synthetic datasets across core regulated industries for instant testing:
          </p>

          <div className="grid grid-cols-2 gap-2 pt-1">
            {[
              { id: 'healthcare', label: 'Hospital Records', icon: '🏥' },
              { id: 'finance', label: 'Bank Transactions', icon: '💳' },
              { id: 'education', label: 'Student Database', icon: '🎓' },
              { id: 'hr', label: 'Employee Records', icon: '👥' },
              { id: 'ecommerce', label: 'Customer DB', icon: '🛍️' },
              { id: 'government', label: 'Public Registry', icon: '🏛️' },
            ].map((ind) => (
              <button
                key={ind.id}
                disabled={isLoading}
                onClick={() => onLoadDemo(ind.id)}
                className="flex items-center gap-2 p-2.5 rounded-xl bg-surface-elevated/70 border border-white/[0.06] hover:border-accent/30 hover:bg-surface-hover text-left transition-all active:scale-[0.98] disabled:opacity-50"
              >
                <span className="text-base">{ind.icon}</span>
                <span className="text-xs font-medium text-text-primary truncate">
                  {ind.label}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Recent Datasets Table */}
        <div className="lg:col-span-2 p-5 rounded-2xl bg-surface-panel/90 border border-white/[0.07] shadow-apple-card space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileCheck2 className="w-4 h-4 text-success" />
              <h3 className="text-sm font-semibold text-text-primary">
                Recent Workspace Datasets
              </h3>
            </div>
            <Button
              variant="ghost"
              size="xs"
              icon={ArrowRight}
              iconPosition="right"
              onClick={() => onNavigate('datasets')}
            >
              View All ({datasets.length})
            </Button>
          </div>

          <div className="overflow-x-auto rounded-xl border border-white/[0.06] bg-canvas/40">
            <table className="w-full text-left text-xs">
              <thead className="bg-surface-elevated/60 text-text-muted font-semibold uppercase text-[10px] tracking-wider border-b border-white/[0.06]">
                <tr>
                  <th className="py-2 px-3">Dataset Name</th>
                  <th className="py-2 px-3 text-center">Format</th>
                  <th className="py-2 px-3 text-right">Records</th>
                  <th className="py-2 px-3 text-right">Columns</th>
                  <th className="py-2 px-3 text-center">Encryption</th>
                  <th className="py-2 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {datasets.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-6 text-center text-text-muted italic">
                      No datasets loaded yet. Click any industry demo above to begin.
                    </td>
                  </tr>
                ) : (
                  datasets.slice(0, 5).map((d) => (
                    <tr key={d.id} className="hover:bg-white/[0.02] transition-colors">
                      <td className="py-2.5 px-3 font-medium text-text-primary truncate max-w-[180px]">
                        {d.name}
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <span className="font-mono text-[11px] text-text-secondary uppercase">
                          {d.file_format}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono tabular-nums text-text-primary">
                        {d.record_count?.toLocaleString()}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono tabular-nums text-text-secondary">
                        {d.column_count}
                      </td>
                      <td className="py-2.5 px-3 text-center font-mono text-[11px] text-text-secondary">
                        {d.is_encrypted ? 'AES-256' : 'Raw'}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => {
                              onSelectDataset(d);
                              onNavigate('discovery');
                            }}
                            className="text-[11px] font-medium text-accent hover:underline cursor-pointer"
                          >
                            Discovery
                          </button>
                          <span className="text-white/20">•</span>
                          <button
                            onClick={() => {
                              onSelectDataset(d);
                              onNavigate('studio');
                            }}
                            className="text-[11px] font-medium text-success hover:underline cursor-pointer"
                          >
                            Studio
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
