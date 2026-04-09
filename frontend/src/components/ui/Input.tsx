import { InputHTMLAttributes, forwardRef } from 'react';
import clsx from 'clsx';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  errorMessage?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, errorMessage, className, type = 'text', ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-[15px] font-semibold text-text-primary mb-2 font-body">
            {label}
          </label>
        )}
        <input
          ref={ref}
          type={type}
          className={clsx(
            'w-full h-12 px-4 bg-bg border-[1.5px] border-border rounded-lg',
            'font-body text-[15px] text-text-primary placeholder:text-text-tertiary',
            'transition-all duration-200',
            'focus:border-primary focus:outline-none focus:ring-3 focus:ring-primary/10',
            error
              ? 'border-error bg-error/5'
              : 'border-border',
            error && 'animate-shake',
            className
          )}
          {...props}
        />
        {(error || errorMessage) && (
          <p className="mt-1 text-sm text-error animate-in fade-in slide-in-from-left-2 duration-200">
            {error || errorMessage}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export { Input };
export default Input;
