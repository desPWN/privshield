import React from 'react';
import { SensitivityCategory } from '../../types/dataset';

export type BadgeRole = 
  | SensitivityCategory 
  | 'k_satisfied' 
  | 'k_violated' 
  | 'masked' 
  | 'generalized' 
  | 'suppressed' 
  | 'unchanged' 
  | 'custom'
  | 'info'
  | 'success'
  | 'warning'
  | 'danger';

interface BadgeProps {
  role?: BadgeRole;
  text: string;
  size?: 'xs' | 'sm' | 'md';
  customClass?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  role = 'insensitive',
  text,
  size = 'xs',
  customClass = '',
}) => {
  let colorStyles = 'bg-white/[0.06] text-text-secondary border-transparent';

  switch (role) {
    case 'direct_identifier':
    case 'masked':
      colorStyles = 'bg-accent/15 text-accent border-transparent';
      break;
    case 'quasi_identifier':
    case 'info':
      colorStyles = 'bg-info/15 text-info border-transparent';
      break;
    case 'sensitive_attribute':
      case 'generalized':
    case 'warning':
      colorStyles = 'bg-warning/15 text-warning border-transparent';
      break;
    case 'k_satisfied':
    case 'success':
      colorStyles = 'bg-success/15 text-success border-transparent';
      break;
    case 'k_violated':
    case 'suppressed':
    case 'danger':
      colorStyles = 'bg-danger/15 text-danger border-transparent';
      break;
    case 'unchanged':
    case 'insensitive':
      colorStyles = 'bg-white/[0.06] text-text-secondary border-transparent';
      break;
  }

  const sizeStyles = {
    xs: 'text-[11px] px-2 py-0.5 leading-tight',
    sm: 'text-xs px-2.5 py-0.5 leading-tight',
    md: 'text-xs px-3 py-1 leading-normal',
  }[size];

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full transition-colors ${sizeStyles} ${colorStyles} ${customClass}`}
    >
      {text}
    </span>
  );
};
