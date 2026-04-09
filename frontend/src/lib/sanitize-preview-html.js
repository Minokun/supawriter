import DOMPurify from 'isomorphic-dompurify'

export function sanitizePreviewHtml(html) {
  return DOMPurify.sanitize(html, {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ['script', 'style'],
  })
}
