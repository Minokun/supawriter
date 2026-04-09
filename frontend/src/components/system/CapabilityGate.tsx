'use client';

import Link from 'next/link';

interface CapabilityGateProps {
  title: string;
  description: string;
  ctaHref: string;
  ctaLabel: string;
}

export function CapabilityGate({ title, description, ctaHref, ctaLabel }: CapabilityGateProps) {
  return (
    <div
      data-testid="capability-gate"
      className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-amber-900"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold">{title}</p>
          <p className="mt-1 text-sm leading-6 text-amber-800">{description}</p>
        </div>
        <Link
          href={ctaHref}
          className="rounded-lg bg-amber-500 px-3 py-2 text-sm font-medium text-white transition hover:bg-amber-600"
        >
          {ctaLabel}
        </Link>
      </div>
    </div>
  );
}
