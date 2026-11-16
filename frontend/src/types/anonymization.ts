export type ProcessingMode = 'irreversible_anonymization';

export interface AnonymizationConfig {
  processing_mode?: ProcessingMode;
  quasi_identifiers: string[];
  sensitive_attributes: string[];
  k_metric: number;
  l_metric?: number | null;
  t_metric?: number | null;
  suppression_strategy: 'record' | 'cell';
  max_suppression_pct: number;
  masking_rules: Record<string, string>;
  generalization_levels: Record<string, number>;
}

export interface PresetRuleConfig {
  k_metric?: number;
  l_metric?: number;
  t_metric?: number;
  max_suppression_pct?: number;
  suppression_strategy?: 'record' | 'cell';
  masking_rules?: Record<string, string>;
  generalization_levels?: Record<string, number>;
  processing_mode?: ProcessingMode;
}

export interface AnonymizationPreset {
  id: string;
  name: string;
  description: string;
  rules_json?: string;
  rules?: PresetRuleConfig;
  is_system_preset?: number | boolean;
  created_at?: string;
}

export interface MaskingRuleOption {
  id: string;
  label: string;
  description: string;
  example: string;
}

export interface HierarchyLevelOption {
  level: number;
  label: string;
  description: string;
  example: string;
}
