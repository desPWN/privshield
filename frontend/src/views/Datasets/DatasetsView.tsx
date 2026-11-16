import React, { useState, useRef } from 'react';
import {
  UploadCloud,
  Database,
  ArrowRight,
  Building2,
  Search,
} from 'lucide-react';
import { DatasetMetadata } from '../../types/dataset';
import { Button } from '../../components/common/Button';

interface DatasetsViewProps {
  datasets: DatasetMetadata[];
  currentDataset: DatasetMetadata | null;
  onSelectDataset: (dataset: DatasetMetadata) => void;
  onUploadFile: (file: File) => Promise<void>;
  onLoadDemo: (industry: string) => Promise<void>;
  onNavigate: (view: any) => void;
  isLoading?: boolean;
}

export const DatasetsView: React.FC<DatasetsViewProps> = ({
  datasets,
  currentDataset,
  onSelectDataset,
  onUploadFile,
  onLoadDemo,
  onNavigate,
  isLoading = false,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<'all' | 'encrypted' | 'synthetic'>('all');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      await onUploadFile(file);
    }
  };

  const handleFileInput = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      await onUploadFile(file);
    }
  };

  // Filter datasets
  const filteredDatasets = datasets.filter((d) => {
    const dName = (d.name || '').toLowerCase();
    const dFmt = (d.file_format || d.format || '').toLowerCase();
    const q = searchQuery.toLowerCase();
    const matchesSearch = dName.includes(q) || dFmt.includes(q);

    if (activeTab === 'encrypted') {
      return matchesSearch && Boolean(d.is_encrypted);
    }
    if (activeTab === 'synthetic') {
      return matchesSearch && Boolean(d.is_synthetic);
    }
    return matchesSearch;
  });

  const demoIndustries = [
    {
      id: 'healthcare',
      title: 'Hospital Patient Records',
      industry: 'Healthcare (HIPAA)',
      records: '1,000 records',
      desc: 'MRN, Patient Name, DOB, Gender, ICD-10 Code, Diagnosis, Ward, Admission Date',
      icon: '🏥',
    },
    {
      id: 'finance',
      title: 'Bank Financial Transactions',
      industry: 'Banking & Finance (CBJ)',
      records: '1,000 records',
      desc: 'National ID, IBAN, Account, Amount, City, Merchant, Transaction Timestamp',
      icon: '💳',
    },
    {
      id: 'education',
      title: 'University Student Database',
      industry: 'Education (FERPA)',
      records: '1,000 records',
      desc: 'Student ID, GPA, Degree, Major, Financial Aid, Cohort Year, Postal Code',
      icon: '🎓',
    },
    {
      id: 'hr',
      title: 'Corporate Employee Records',
      industry: 'Human Resources (HR)',
      records: '1,000 records',
      desc: 'SSN, Employee Name, Department, Salary, Performance Rating, City, Start Date',
      icon: '👥',
    },
    {
      id: 'ecommerce',
      title: 'E-Commerce Customer DB',
      industry: 'Retail & Commerce',
      records: '1,000 records',
      desc: 'Customer ID, Email, Phone, Lifetime Value, Postal Code, Orders Count',
      icon: '🛍️',
    },
    {
      id: 'government',
      title: 'Public Registry Database',
      industry: 'Government & Civic',
      records: '1,000 records',
      desc: 'National Registry ID, Full Name, District, DOB, Voter Status, Tax Bracket',
      icon: '🏛️',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-text-primary tracking-tight">
            Dataset Management
          </h2>
          <p className="text-xs text-text-secondary mt-1">
            Universal ingestion workspace supporting CSV, XLSX, and JSON formats with local cryptographic protection.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileInput}
            accept=".csv,.xlsx,.xls,.json"
            className="hidden"
          />
          <Button
            variant="primary"
            size="md"
            icon={UploadCloud}
            isLoading={isLoading}
            onClick={() => fileInputRef.current?.click()}
          >
            Upload Structured File
          </Button>
        </div>
      </div>

      {/* Drag & Drop Upload Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`p-8 rounded-2xl border-2 border-dashed transition-all duration-200 cursor-pointer flex flex-col items-center justify-center text-center space-y-3 ${
          isDragging
            ? 'border-accent bg-accent/10 shadow-apple-card scale-[0.99]'
            : 'border-white/[0.12] bg-surface-panel/60 hover:border-white/[0.25] hover:bg-surface-panel'
        }`}
      >
        <div className="w-12 h-12 rounded-xl bg-accent/15 border border-accent/30 flex items-center justify-center text-accent shadow-apple-sm">
          <UploadCloud className="w-6 h-6" />
        </div>

        <div className="space-y-1">
          <p className="text-sm font-semibold text-text-primary">
            Drag & drop your dataset here, or <span className="text-accent underline">browse local files</span>
          </p>
          <p className="text-xs text-text-muted">
            Supports CSV, Microsoft Excel (XLSX, XLS), and JSON files up to 100MB. Zero external telemetry.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs text-text-muted pt-1">
          <span>.CSV</span>
          <span className="text-white/20">•</span>
          <span>.XLSX</span>
          <span className="text-white/20">•</span>
          <span>.JSON</span>
        </div>
      </div>

      {/* 1-Click Multi-Industry Demo Generator */}
      <div className="p-5 rounded-2xl bg-surface-panel/90 border border-white/[0.07] shadow-apple-card space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Building2 className="w-4 h-4 text-accent" />
            <h3 className="text-sm font-semibold text-text-primary tracking-tight">
              1-Click Multi-Industry Synthetic Datasets
            </h3>
          </div>
          <span className="text-xs text-text-muted font-mono">
            Certified Synthetic • No Column Hardcoding
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {demoIndustries.map((ind) => (
            <div
              key={ind.id}
              className="p-3.5 rounded-xl bg-surface-elevated/70 border border-white/[0.06] hover:border-accent/30 hover:bg-surface-hover transition-all flex flex-col justify-between space-y-3 group"
            >
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-xl">{ind.icon}</span>
                  <span className="text-[11px] font-medium text-accent tracking-wide uppercase">
                    {ind.industry}
                  </span>
                </div>
                <h4 className="text-xs font-semibold text-text-primary group-hover:text-accent transition-colors">
                  {ind.title}
                </h4>
                <p className="text-[11px] text-text-muted line-clamp-2 leading-relaxed">
                  {ind.desc}
                </p>
              </div>

              <div className="pt-2 border-t border-white/[0.06] flex items-center justify-between">
                <span className="text-[11px] font-mono text-text-secondary">{ind.records}</span>
                <Button
                  variant="secondary"
                  size="xs"
                  isLoading={isLoading}
                  onClick={() => onLoadDemo(ind.id)}
                >
                  Load Dataset
                </Button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Dataset Registry Table */}
      <div className="p-5 rounded-2xl bg-surface-panel/90 border border-white/[0.07] shadow-apple-card space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-info" />
            <h3 className="text-sm font-semibold text-text-primary">
              Registered Dataset Library ({datasets.length})
            </h3>
          </div>

          <div className="flex items-center gap-3">
            {/* Tabs */}
            <div className="flex items-center bg-canvas p-0.5 rounded-lg border border-white/[0.06] text-xs">
              <button
                onClick={() => setActiveTab('all')}
                className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                  activeTab === 'all'
                    ? 'bg-surface-elevated text-text-primary'
                    : 'text-text-muted hover:text-text-primary'
                }`}
              >
                All
              </button>
              <button
                onClick={() => setActiveTab('encrypted')}
                className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                  activeTab === 'encrypted'
                    ? 'bg-surface-elevated text-text-primary'
                    : 'text-text-muted hover:text-text-primary'
                }`}
              >
                Encrypted
              </button>
              <button
                onClick={() => setActiveTab('synthetic')}
                className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                  activeTab === 'synthetic'
                    ? 'bg-surface-elevated text-text-primary'
                    : 'text-text-muted hover:text-text-primary'
                }`}
              >
                Synthetic
              </button>
            </div>

            {/* Search */}
            <div className="relative w-48">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Filter datasets..."
                className="w-full bg-surface-elevated border border-white/[0.08] focus:border-accent/40 rounded-lg pl-8 pr-2.5 py-1 text-xs text-text-primary outline-none"
              />
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto rounded-xl border border-white/[0.06] bg-canvas/40">
          <table className="w-full text-left text-xs">
            <thead className="bg-surface-elevated/70 text-text-muted font-semibold uppercase text-[10px] tracking-wider border-b border-white/[0.06]">
              <tr>
                <th className="py-2.5 px-3">Dataset Name</th>
                <th className="py-2.5 px-3 text-center">Format</th>
                <th className="py-2.5 px-3 text-right">Records</th>
                <th className="py-2.5 px-3 text-right">Columns</th>
                <th className="py-2.5 px-3 text-right">Size</th>
                <th className="py-2.5 px-3 text-center">Security Status</th>
                <th className="py-2.5 px-3 text-right">Ingested</th>
                <th className="py-2.5 px-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {filteredDatasets.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-text-muted italic">
                    No datasets found in this view.
                  </td>
                </tr>
              ) : (
                filteredDatasets.map((d) => {
                  const isCurrent = currentDataset?.id === d.id;
                  const sizeFormatted = d.file_size_bytes
                    ? `${(d.file_size_bytes / 1024).toFixed(1)} KB`
                    : '—';

                  return (
                    <tr
                      key={d.id}
                      className={`hover:bg-white/[0.02] transition-colors ${
                        isCurrent ? 'bg-accent/5' : ''
                      }`}
                    >
                      <td className="py-3 px-3">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-text-primary truncate max-w-xs">
                            {d.name}
                          </span>
                          {isCurrent && (
                            <span className="text-[9px] font-mono uppercase px-1.5 py-0.2 rounded bg-accent/20 text-accent border border-accent/30">
                              Active
                            </span>
                          )}
                        </div>
                        <span className="text-[10px] text-text-muted truncate block max-w-xs">
                          {d.original_filename || d.storage_path}
                        </span>
                      </td>

                      <td className="py-3 px-3 text-center font-mono">
                        <span className="text-[10px] uppercase px-1.5 py-0.5 rounded bg-white/[0.06] text-text-secondary border border-white/[0.06]">
                          {d.file_format || d.format || 'CSV'}
                        </span>
                      </td>

                      <td className="py-3 px-3 text-right font-mono tabular-nums text-text-primary">
                        {(d.record_count ?? d.row_count ?? 0).toLocaleString()}
                      </td>

                      <td className="py-3 px-3 text-right font-mono tabular-nums text-text-secondary">
                        {d.column_count}
                      </td>

                      <td className="py-3 px-3 text-right font-mono tabular-nums text-text-muted">
                        {sizeFormatted}
                      </td>

                      <td className="py-3 px-3 text-center font-mono text-[11px] text-text-secondary">
                        {d.is_encrypted ? 'AES-256 Vault' : 'Plaintext'}
                      </td>

                      <td className="py-3 px-3 text-right text-text-muted font-mono text-[11px]">
                        {d.created_at ? new Date(d.created_at).toLocaleDateString() : 'Today'}
                      </td>

                      <td className="py-3 px-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          {!isCurrent ? (
                            <Button
                              variant="outline"
                              size="xs"
                              onClick={() => onSelectDataset(d)}
                            >
                              Set Active
                            </Button>
                          ) : null}

                          <Button
                            variant="secondary"
                            size="xs"
                            onClick={() => {
                              onSelectDataset(d);
                              onNavigate('discovery');
                            }}
                          >
                            Discovery
                          </Button>

                          <Button
                            variant="primary"
                            size="xs"
                            icon={ArrowRight}
                            iconPosition="right"
                            onClick={() => {
                              onSelectDataset(d);
                              onNavigate('studio');
                            }}
                          >
                            Studio
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
