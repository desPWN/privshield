import { AnonymizationConfig } from './anonymization';

export interface PrivacyRiskMetrics {
  prosecutor_risk: number;
  journalist_risk: number;
  marketer_risk: number;
  average_risk: number;
  transaction_linkage_risk: number;
  smallest_class_size: number;
  largest_class_size: number;
  average_class_size: number;
  k_achieved: number;
}

export interface UtilityMetrics {
  record_retention: number;
  numerical_distribution_fidelity: number;
  categorical_distribution_fidelity: number;
  correlation_retention: number;
  granularity_retention: number;
  composite_utility_score: number;
  mean_relative_error?: Record<string, number>;
  std_relative_error?: Record<string, number>;
  suppressed_records: number;
  suppression_rate: number;
}

export interface LDiversityClassViolation {
  qi_values: Record<string, any>;
  class_size: number;
  distinct_count: number;
  values_present: any[];
  frequency_breakdown: Record<string, number>;
}

export interface LDiversityResult {
  target_l: number;
  sensitive_attribute: string;
  satisfied: boolean;
  total_classes: number;
  violating_classes_count: number;
  violating_records_count: number;
  min_observed_distinct_values: number;
  violation_details: LDiversityClassViolation[];
}

export interface TClosenessClassViolation {
  class_id: number;
  qi_values: Record<string, any>;
  class_size: number;
  distance: number;
  threshold_t: number;
  is_violation: boolean;
}

export interface TClosenessResult {
  target_t: number;
  sensitive_attribute: string;
  attribute_type: 'numeric' | 'categorical';
  satisfied: boolean;
  total_classes: number;
  violating_classes_count: number;
  violating_records_count: number;
  max_observed_distance: number;
  average_distance: number;
  violation_details: TClosenessClassViolation[];
}

export interface RunAnalytics {
  run_id: string;
  dataset_id: string;
  dataset_name: string;
  k_satisfied: boolean;
  achieved_k: number;
  target_k: number;
  achieved_l?: number | null;
  target_l?: number | null;
  achieved_t?: number | null;
  target_t?: number | null;
  total_records: number;
  retained_records: number;
  suppressed_records: number;
  suppression_rate: number;
  num_equivalence_classes: number;
  min_equivalence_class_size: number;
  avg_equivalence_class_size: number;
  max_equivalence_class_size: number;
  ec_histogram: { size: number; count: number }[];
  l_diversity_results: Record<string, LDiversityResult>;
  t_closeness_results: Record<string, TClosenessResult>;
  privacy_risk: PrivacyRiskMetrics;
  utility_metrics: UtilityMetrics;
  config: AnonymizationConfig;
  execution_time_ms: number;
  processing_mode?: string;
}

export interface DiffCell {
  original: any;
  anonymized: any;
  change_type: 'masked' | 'generalized' | 'suppressed' | 'modified' | 'unchanged';
}

export interface DiffRow {
  row_index: number;
  status: 'retained' | 'suppressed';
  cells: Record<string, DiffCell>;
}

export interface DiffResponse {
  run_id: string;
  page: number;
  size: number;
  total_records: number;
  total_pages: number;
  columns: string[];
  rows: DiffRow[];
}
