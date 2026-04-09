import { ButtonHTMLAttributes, ReactNode } from 'react';
import clsx from 'clsx';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'text' | 'cta';
  size?: 'sm' | 'md' | 'lg';
  icon?: ReactNode;
  children: ReactNode;
}

export function Button({
  variant = 'primary',
  size = 'md',
  icon,
  children,
  className,
  ...props
}: ButtonProps) {
  const baseStyles = 'inline-flex items-center justify-center gap-2 font-body font-semibold transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed';

  const variantStyles = {
    // Primary 按钮：hover 时发光效果
    primary: 'bg-primary text-white border-none hover:bg-[#B91C1C] hover:-translate-y-0.5 hover:shadow-[0_0_20px_rgba(220,38,38,0.3)] active:scale-[0.96]',
    // Secondary 按钮：边框颜色变化
    secondary: 'bg-transparent text-primary border-2 border-primary hover:border-[#B91C1C] hover:text-[#B91C1C]',
    // Text 按钮：颜色变化
    text: 'bg-transparent text-primary border-none hover:text-[#B91C1C]',
    // CTA 按钮：金色系
    cta: 'bg-cta text-white border-none hover:bg-[#A16207] hover:-translate-y-0.5 hover:shadow-[0_0_20px_rgba(202,138,4,0.3)] active:scale-[0.96]',
  };

  const sizeStyles = {
    sm: 'h-10 px-4 text-sm rounded-md',
    md: 'h-11 px-5 text-[15px] rounded-md',
    lg: 'h-[52px] px-6 text-base rounded-lg',
  };

  return (
    <button
      className={clsx(
        baseStyles,
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
      {...props}
    >
      {icon && <span className="text-xl transition-transform duration-200 group-hover:scale-110">{icon}</span>}
      {children}
    </button>
  );
}

export default Button;
