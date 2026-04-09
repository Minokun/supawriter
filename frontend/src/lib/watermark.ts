import type { MembershipTier } from '@/types/api';

const WATERMARK_LINK = 'https://supawriter.com?ref=watermark';
const MARKDOWN_WATERMARK = `---\n本文由 [SupaWriter](${WATERMARK_LINK}) AI 辅助创作`;

export function shouldInjectWatermark(tier: MembershipTier): boolean {
  return tier === 'free';
}

export function injectMarkdownWatermarkIfNeeded(content: string, tier: MembershipTier): string {
  if (!content || !shouldInjectWatermark(tier)) {
    return content;
  }

  if (content.includes(WATERMARK_LINK)) {
    return content;
  }

  const trimmed = content.trimEnd();
  return `${trimmed}\n\n${MARKDOWN_WATERMARK}`;
}
