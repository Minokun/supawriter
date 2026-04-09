import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { sanitizePreviewHtml } from '../frontend/src/lib/sanitize-preview-html.js'

test('removes scripts and inline event handlers', () => {
  const html = sanitizePreviewHtml(`
    <h1>Safe title</h1>
    <img src="x" onerror="window.__xss = true">
    <script>window.__xss = true</script>
  `)

  assert.match(html, /Safe title/)
  assert.doesNotMatch(html, /<script/i)
  assert.doesNotMatch(html, /onerror=/i)
})

test('keeps normal formatting tags used by the preview', () => {
  const html = sanitizePreviewHtml('<p><strong>Hello</strong> <em>world</em></p>')
  assert.match(html, /<strong>Hello<\/strong>/)
  assert.match(html, /<em>world<\/em>/)
})

test('removes dangerous javascript url schemes', () => {
  const html = sanitizePreviewHtml('<a href="javascript:alert(1)">Click</a>')
  assert.match(html, /Click/)
  assert.doesNotMatch(html, /href=["']javascript:/i)
})

test('SplitEditor sanitizes html at dangerouslySetInnerHTML sink', () => {
  const source = readFileSync(
    new URL('../frontend/src/components/writer/SplitEditor.tsx', import.meta.url),
    'utf8'
  )

  assert.match(
    source,
    /dangerouslySetInnerHTML=\{\s*\{\s*__html:\s*sanitizePreviewHtml\(platformPreview\.content\)\s*\}\s*\}/
  )
})
