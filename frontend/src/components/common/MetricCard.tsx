import React from 'react';
import { LucideIcon } from 'lucide-react';

export interface MetricCardProps {
  title: string;
  value: string | number;
  sublabel?: string;
  icon?: LucideIcon;
  variant?: 'neutral' | 'accent' | 'emerald' | 'cyan' | 'amber' | 'rose' | 'purple';
  statusBadge?: {
    text: string;
    variant: 'emerald' | 'cyan' | 'amber' | 'rose' | 'neutral' | 'accent';
  };
  className?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  sublabel,
  icon: Icon,
  variant = 'neutral',
  className = '',
}) => {
  const iconColors = {
    neutral: 'text-text-muted bg-white/[0.04]',
    accent: 'text-accent bg-accent/10 border border-accent/20',
    emerald: 'text-success bg-success/10 border border-success/20',
    cyan: 'text-info bg-info/10 border border-info/20',
    amber: 'text-warning bg-warning/10 border border-warning/20',
    rose: 'text-danger bg-danger/10 border border-danger/20',
    purple: 'text-accent bg-accent/10 border border-accent/20',
  }[variant];

  return (
    <div
      className={`p-4 rounded-xl bg-surface-panel/90 backdrop-blur-md border border-white/[0.07] hover:border-white/[0.14] transition-all duration-200 shadow-apple-card ${className}`}
    >
      <div className="flex items-center justify-between gap-3 mb-2.5">
        <span className="text-xs font-medium text-text-secondary">
          {title}
        </span>
        {Icon && (
          <div className={`p-2 rounded-lg ${iconColors}`}>
            <Icon className="w-4 h-4" />
          </div>
        )}
      </div>

      <div className="flex items-baseline gap-2.5 flex-wrap">
        <div className="text-2xl font-bold tracking-tight text-text-primary tabular-nums font-mono">
          {value}
        </div>
      </div>

      {sublabel && (
        <div className="text-xs text-text-secondary mt-1.5 leading-relaxed">
          {sublabel}
        </div>
      )}
    </div>
  );
};
