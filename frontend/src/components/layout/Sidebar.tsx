import React from 'react';
import {
  LayoutDashboard,
  Database,
  ScanSearch,
  Sliders,
  ShieldCheck,
  Activity,
  FileText,
  ChevronLeft,
  ChevronRight,
  Shield,
} from 'lucide-react';
import { DatasetMetadata } from '../../types/dataset';

export type WorkspaceViewId =
  | 'overview'
  | 'datasets'
  | 'discovery'
  | 'studio'
  | 'privacy-analysis'
  | 'utility-analysis'
  | 'reports-settings';

interface SidebarProps {
  activeView: WorkspaceViewId;
  onSelectView: (view: WorkspaceViewId) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  currentDataset: DatasetMetadata | null;
  isBackendOnline?: boolean;
}

interface NavItem {
  id: WorkspaceViewId;
  label: string;
  icon: React.ElementType;
  badge?: string;
}

interface NavGroup {
  groupName: string;
  items: NavItem[];
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeView,
  onSelectView,
  isCollapsed,
  onToggleCollapse,
  currentDataset,
}) => {
  const navGroups: NavGroup[] = [
    {
      groupName: 'Core Workspaces',
      items: [
        { id: 'overview', label: 'Privacy Overview', icon: LayoutDashboard },
        { id: 'datasets', label: 'Dataset Management', icon: Database },
        { id: 'discovery', label: 'Data Discovery', icon: ScanSearch },
        { id: 'studio', label: 'Anonymization Studio', icon: Sliders },
      ],
    },
    {
      groupName: 'Evaluation & Auditing',
      items: [
        { id: 'privacy-analysis', label: 'Privacy Analysis', icon: ShieldCheck },
        { id: 'utility-analysis', label: 'Utility Analysis', icon: Activity },
      ],
    },
    {
      groupName: 'Governance & Output',
      items: [
        { id: 'reports-settings', label: 'Reports & Export', icon: FileText },
      ],
    },
  ];

  return (
    <aside
      className={`fixed left-0 top-0 bottom-0 z-40 bg-surface-sidebar border-r border-white/[0.07] flex flex-col justify-between transition-all duration-200 ease-out select-none ${
        isCollapsed ? 'w-16' : 'w-60'
      }`}
    >
      {/* Top Branding Section */}
      <div className="flex flex-col">
        <div className="h-16 px-4 flex items-center justify-between border-b border-white/[0.07]">
          <div
            onClick={() => onSelectView('overview')}
            className="flex items-center gap-2.5 cursor-pointer overflow-hidden"
          >
            <div className="w-8 h-8 rounded-lg bg-accent/15 border border-accent/30 flex items-center justify-center flex-shrink-0 text-accent shadow-apple-sm">
              <Shield className="w-4 h-4" />
            </div>

            {!isCollapsed && (
              <div className="flex flex-col truncate">
                <div className="flex items-center gap-1.5">
                  <span className="font-semibold text-sm tracking-tight text-text-primary">
                    PrivShield
                  </span>
                </div>
                <span className="text-[10px] text-text-muted truncate">
                  Enterprise Anonymization
                </span>
              </div>
            )}
          </div>

          <button
            onClick={onToggleCollapse}
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            className="p-1 rounded-md text-text-muted hover:text-text-primary hover:bg-white/[0.05] transition-colors"
          >
            {isCollapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <ChevronLeft className="w-4 h-4" />
            )}
          </button>
        </div>

        {/* Navigation Items */}
        <div className="py-4 px-2.5 space-y-5 overflow-y-auto max-h-[calc(100vh-190px)]">
          {navGroups.map((group) => (
            <div key={group.groupName} className="space-y-1">
              {!isCollapsed && (
                <div className="px-2.5 py-1 text-[10px] font-semibold tracking-wider text-text-muted uppercase">
                  {group.groupName}
                </div>
              )}

              {group.items.map((item) => {
                const Icon = item.icon;
                const isActive = activeView === item.id;

                return (
                  <button
                    key={item.id}
                    onClick={() => onSelectView(item.id)}
                    title={isCollapsed ? item.label : undefined}
                    className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs font-medium transition-all duration-150 ${
                      isActive
                        ? 'bg-accent/15 text-accent border border-accent/30 shadow-apple-sm font-semibold'
                        : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.04] border border-transparent'
                    } ${isCollapsed ? 'justify-center px-0' : ''}`}
                  >
                    <Icon className="w-4 h-4 flex-shrink-0" />

                    {!isCollapsed && (
                      <span className="truncate flex-1 text-left">{item.label}</span>
                    )}

                    {!isCollapsed && item.badge && (
                      <span className="text-[9px] font-mono uppercase px-1.5 py-0.2 rounded bg-white/[0.06] text-text-muted">
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Bottom Summary Panel */}
      {!isCollapsed && currentDataset && (
        <div className="p-3 border-t border-white/[0.07] bg-canvas/40">
          <div className="p-2 rounded-lg bg-surface-panel border border-white/[0.07] text-xs">
            <div className="flex items-center justify-between text-[10px] text-text-muted mb-1">
              <span className="font-semibold uppercase tracking-wider">Active Dataset</span>
              <span className="font-mono">{currentDataset.file_format?.toUpperCase()}</span>
            </div>
            <div className="font-medium text-text-primary truncate" title={currentDataset.name}>
              {currentDataset.name}
            </div>
            <div className="flex items-center justify-between text-[11px] text-text-secondary font-mono mt-1">
              <span>{currentDataset.record_count?.toLocaleString()} rows</span>
              <span>{currentDataset.column_count} cols</span>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
};
