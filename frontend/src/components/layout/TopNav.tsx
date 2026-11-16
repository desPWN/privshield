import React from 'react';
import {
  ChevronRight,
  Sliders,
  Download,
} from 'lucide-react';
import { WorkspaceViewId } from './Sidebar';
import { Button } from '../common/Button';

interface TopNavProps {
  activeView: WorkspaceViewId;
  onNavigate: (view: WorkspaceViewId) => void;
  onOpenImport: () => void;
  onExecutePipeline?: () => void;
  isExecuting?: boolean;
}

export const TopNav: React.FC<TopNavProps> = ({
  activeView,
  onNavigate,
  onOpenImport,
  onExecutePipeline,
  isExecuting = false,
}) => {
  const viewMeta: Record<
    WorkspaceViewId,
    { title: string; section: string }
  > = {
    overview: { title: 'Privacy Overview', section: 'Core' },
    datasets: { title: 'Dataset Management', section: 'Core' },
    discovery: { title: 'Data Discovery', section: 'Core' },
    studio: { title: 'Anonymization Studio', section: 'Core' },
    'privacy-analysis': { title: 'Privacy Analysis', section: 'Evaluation' },
    'utility-analysis': { title: 'Utility Analysis', section: 'Evaluation' },
    'reports-settings': { title: 'Reports & Settings', section: 'Governance' },
  };

  const currentMeta = viewMeta[activeView] || { title: 'Workspace', section: 'PrivShield' };

  return (
    <header className="sticky top-0 z-30 h-16 bg-canvas/85 backdrop-blur-xl border-b border-white/[0.07] px-6 flex items-center justify-between select-none">
      {/* Left Breadcrumb & View Title */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex items-center gap-1.5 text-xs text-text-muted">
          <span
            onClick={() => onNavigate('overview')}
            className="hover:text-text-primary cursor-pointer transition-colors font-medium"
          >
            PrivShield
          </span>
          <ChevronRight className="w-3.5 h-3.5 opacity-40 flex-shrink-0" />
          <span className="text-text-secondary">{currentMeta.section}</span>
          <ChevronRight className="w-3.5 h-3.5 opacity-40 flex-shrink-0" />
        </div>
        <h1 className="text-sm font-semibold text-text-primary tracking-tight truncate">
          {currentMeta.title}
        </h1>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3">
        {/* Global Quick Actions */}
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={onOpenImport}
            className="hidden sm:inline-flex"
          >
            Import Data
          </Button>

          {activeView === 'studio' && onExecutePipeline && (
            <Button
              variant="primary"
              size="sm"
              icon={Sliders}
              isLoading={isExecuting}
              onClick={onExecutePipeline}
            >
              Execute Pipeline
            </Button>
          )}

          {(activeView === 'privacy-analysis' || activeView === 'utility-analysis') && (
            <Button
              variant="secondary"
              size="sm"
              icon={Download}
              onClick={() => onNavigate('reports-settings')}
            >
              Export
            </Button>
          )}
        </div>
      </div>
    </header>
  );
};
