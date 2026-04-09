import { SelectHTMLAttributes, forwardRef } from 'react';
import clsx from 'clsx';

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  options: { value: string; label: string }[];
}

const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, options, className, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-[15px] font-semibold text-text-primary mb-2 font-body">
            {label}
          </label>
        )}
        <select
          ref={ref}
          className={clsx(
            'w-full h-12 px-4 bg-bg border-[1.5px] border-border rounded-lg',
            'font-body text-[15px] text-text-primary',
            'transition-all duration-200 appearance-none cursor-pointer',
            'focus:border-primary focus:outline-none focus:ring-3 focus:ring-primary/10',
            error && 'border-error',
            className
          )}
          {...props}
        >
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {error && (
          <p className="mt-1 text-sm text-error">{error}</p>
        )}
      </div>
    );
  }
);

Select.displayName = 'Select';

export default Select;
