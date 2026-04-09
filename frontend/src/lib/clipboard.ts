export function stripHtml(html: string): string {
  if (typeof window === 'undefined') {
    return html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
  }

  const container = document.createElement('div');
  container.innerHTML = html;
  return (container.textContent || container.innerText || '').replace(/\s+/g, ' ').trim();
}

export function buildClipboardHtmlDocument(htmlBody: string): string {
  return `<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
</head>
<body>${htmlBody}</body>
</html>`;
}

function copyHtmlWithExecCommand(html: string): boolean {
  const container = document.createElement('div');
  container.contentEditable = 'true';
  container.setAttribute('aria-hidden', 'true');
  container.style.position = 'fixed';
  container.style.pointerEvents = 'none';
  container.style.opacity = '0';
  container.style.left = '-9999px';
  container.style.top = '0';
  container.innerHTML = html;

  document.body.appendChild(container);

  const selection = window.getSelection();
  if (!selection) {
    document.body.removeChild(container);
    return false;
  }

  const previousRanges = [] as Range[];
  for (let i = 0; i < selection.rangeCount; i += 1) {
    previousRanges.push(selection.getRangeAt(i));
  }

  const range = document.createRange();
  range.selectNodeContents(container);
  selection.removeAllRanges();
  selection.addRange(range);

  let success = false;
  try {
    success = document.execCommand('copy');
  } finally {
    selection.removeAllRanges();
    previousRanges.forEach((savedRange) => selection.addRange(savedRange));
    document.body.removeChild(container);
  }

  return success;
}

export async function copyRichTextToClipboard({
  html,
  plainText,
}: {
  html: string;
  plainText?: string;
}): Promise<void> {
  const normalizedHtml = buildClipboardHtmlDocument(html);
  const fallbackText = plainText?.trim() || stripHtml(html);

  if (typeof navigator !== 'undefined' && navigator.clipboard && typeof ClipboardItem !== 'undefined') {
    try {
      await navigator.clipboard.write([
        new ClipboardItem({
          'text/html': new Blob([normalizedHtml], { type: 'text/html' }),
          'text/plain': new Blob([fallbackText], { type: 'text/plain' }),
        }),
      ]);
      return;
    } catch (error) {
      console.warn('Rich text clipboard write failed, falling back to execCommand:', error);
    }
  }

  const copied = copyHtmlWithExecCommand(html);
  if (copied) {
    return;
  }

  if (typeof navigator !== 'undefined' && navigator.clipboard) {
    await navigator.clipboard.writeText(fallbackText);
    return;
  }

  throw new Error('Clipboard API is unavailable');
}
