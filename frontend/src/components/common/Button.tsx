import React from 'react';
import { LucideIcon } from 'lucide-react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline';
  size?: 'xs' | 'sm' | 'md' | 'lg';
  icon?: LucideIcon;
  iconPosition?: 'left' | 'right';
  isLoading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'secondary',
  size = 'md',
  icon: Icon,
  iconPosition = 'left',
  isLoading = false,
  disabled,
  className = '',
  ...props
}) => {
  const variantStyles = {
    primary:
      'bg-accent text-canvas font-semibold hover:bg-accent-hover active:scale-[0.98] shadow-apple-sm focus-visible:ring-2 focus-visible:ring-accent/50',
    secondary:
      'bg-surface-elevated text-text-primary border border-white/[0.08] hover:bg-surface-hover hover:border-white/[0.14] active:scale-[0.98] shadow-apple-sm focus-visible:ring-2 focus-visible:ring-accent/40',
    ghost:
      'text-text-secondary hover:text-text-primary hover:bg-white/[0.05] active:scale-[0.98] focus-visible:ring-2 focus-visible:ring-accent/40',
    danger:
      'bg-danger/15 text-danger border border-danger/30 hover:bg-danger/25 active:scale-[0.98] focus-visible:ring-2 focus-visible:ring-danger/40',
    outline:
      'border border-white/[0.12] text-text-primary hover:bg-white/[0.04] hover:border-white/[0.2] active:scale-[0.98] focus-visible:ring-2 focus-visible:ring-accent/40',
  }[variant];

  const sizeStyles = {
    xs: 'text-xs px-2.5 py-1 rounded-md gap-1.5 min-h-[26px]',
    sm: 'text-xs px-3 py-1.5 rounded-lg gap-2 min-h-[32px]',
    md: 'text-sm px-4 py-2 rounded-lg gap-2 min-h-[40px]',
    lg: 'text-base px-5 py-2.5 rounded-xl gap-2.5 min-h-[48px]',
  }[size];

  const isDisabled = disabled || isLoading;

  return (
    <button
      disabled={isDisabled}
      className={`inline-flex items-center justify-center font-medium transition-all duration-150 ease-out select-none cursor-pointer disabled:opacity-50 disabled:pointer-events-none disabled:active:scale-100 ${variantStyles} ${sizeStyles} ${className}`}
      {...props}
    >
      {isLoading ? (
        <svg
          className="animate-spin -ml-0.5 mr-2 h-4 w-4 text-current"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      ) : Icon && iconPosition === 'left' ? (
        <Icon className={size === 'xs' ? 'w-3 h-3' : size === 'sm' ? 'w-3.5 h-3.5' : 'w-4 h-4'} />
      ) : null}

      {children}

      {!isLoading && Icon && iconPosition === 'right' && (
        <Icon className={size === 'xs' ? 'w-3 h-3' : size === 'sm' ? 'w-3.5 h-3.5' : 'w-4 h-4'} />
      )}
    </button>
  );
};
