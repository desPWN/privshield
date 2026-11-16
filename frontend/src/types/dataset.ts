export type SensitivityCategory = 
  | 'direct_identifier' 
  | 'quasi_identifier' 
  | 'sensitive_attribute' 
  | 'insensitive';

export type IndustryId = 
  | 'healthcare' 
  | 'finance' 
  | 'education' 
  | 'government' 
  | 'hr' 
  | 'ecommerce' 
  | 'custom';

export interface ColumnProfile {
  column_name: string;
  detected_type: SensitivityCategory;
  specific_type: string;
  confidence: number; // 0.0 to 1.0
  explanation: string;
  sample_values_masked: string[];
  unique_count: number;
  null_count: number;
  is_overridden?: boolean;
  user_category?: SensitivityCategory | null;
}

export interface DatasetMetadata {
  id: string;
  name: string;
  original_filename: string;
  filename?: string;
  file_format: string;
  format?: string;
  record_count: number;
  row_count?: number;
  column_count: number;
  file_size_bytes: number;
  is_synthetic: boolean;
  is_encrypted?: boolean;
  industry?: string;
  industry_profile?: string;
  storage_path: string;
  raw_storage_path?: string;
  created_at: string;
  columns?: ColumnProfile[];
}

export interface PaginatedPreview {
  dataset_id: string;
  page: number;
  size: number;
  total_records: number;
  total_pages: number;
  columns: string[];
  rows?: Record<string, any>[];
  records?: Record<string, any>[];
  has_masked_values?: boolean;
}

export interface ColumnOverrideItem {
  column_name: string;
  user_category: SensitivityCategory;
  specific_type?: string;
  notes?: string;
}

export interface ColumnOverrideRequest {
  overrides: ColumnOverrideItem[];
}

export interface IndustryProfile {
  id: string;
  name: string;
  industry: string;
  description: string;
  icon: string;
  suggested_rules: {
    k_metric?: number;
    l_metric?: number;
    t_metric?: number;
    suppression_strategy?: 'record' | 'cell';
    max_suppression_pct?: number;
    masking_rules?: Record<string, string>;
    generalization_levels?: Record<string, number>;
    quasi_identifiers?: string[];
    sensitive_attributes?: string[];
  };
  is_built_in: boolean;
}
