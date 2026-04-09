import { TextareaHTMLAttributes, forwardRef } from 'react';
import clsx from 'clsx';

interface TextAreaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}

const TextArea = forwardRef<HTMLTextAreaElement, TextAreaProps>(
  ({ label, error, className, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-[15px] font-semibold text-text-primary mb-2 font-body">
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          className={clsx(
            'w-full min-h-[120px] px-[14px] py-[14px] bg-bg border-[1.5px] border-border rounded-lg',
            'font-body text-[15px] text-text-primary placeholder:text-text-tertiary',
            'transition-all duration-200 resize-y',
            'focus:border-primary focus:outline-none focus:ring-3 focus:ring-primary/10',
            error && 'border-error',
            className
          )}
          {...props}
        />
        {error && (
          <p className="mt-1 text-sm text-error">{error}</p>
        )}
      </div>
    );
  }
);

TextArea.displayName = 'TextArea';

export { TextArea };
export default TextArea;
