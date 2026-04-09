// ==UserScript==
// @name         Supawriter CSDN Autofill
// @namespace    https://supawriter.local
// @version      0.1.0
// @description  Read Supawriter auto-publish task from window.name and autofill CSDN editor
// @match        https://editor.csdn.net/md*
// @run-at       document-idle
// @grant        none
// ==/UserScript==

(function () {
  'use strict';

  const WINDOW_NAME_PREFIX = 'supawriter:auto-publish:';
  const STATUS_ID = 'supawriter-csdn-autofill-status';

  function parseTask() {
    if (typeof window.name !== 'string' || !window.name.startsWith(WINDOW_NAME_PREFIX)) {
      return null;
    }

    try {
      const payload = window.name.slice(WINDOW_NAME_PREFIX.length);
      const task = JSON.parse(payload);
      if (!task || task.platform !== 'csdn' || !task.title || !task.body) {
        return null;
      }
      return task;
    } catch (error) {
      console.error('[Supawriter] Failed to parse auto publish task', error);
      return null;
    }
  }

  function showStatus(message, type) {
    const existing = document.getElementById(STATUS_ID);
    if (existing) {
      existing.remove();
    }

    const el = document.createElement('div');
    el.id = STATUS_ID;
    el.textContent = message;
    el.style.position = 'fixed';
    el.style.top = '16px';
    el.style.right = '16px';
    el.style.zIndex = '999999';
    el.style.padding = '10px 14px';
    el.style.borderRadius = '12px';
    el.style.fontSize = '13px';
    el.style.fontWeight = '600';
    el.style.boxShadow = '0 12px 32px rgba(0,0,0,0.18)';
    el.style.color = '#fff';
    el.style.background = type === 'error' ? '#dc2626' : '#16a34a';
    document.body.appendChild(el);

    window.setTimeout(() => {
      el.remove();
    }, 4000);
  }

  function fireInputEvents(element) {
    ['input', 'change', 'blur'].forEach((eventName) => {
      element.dispatchEvent(new Event(eventName, { bubbles: true }));
    });
  }

  function setNativeValue(element, value) {
    const prototype = Object.getPrototypeOf(element);
    const descriptor = Object.getOwnPropertyDescriptor(prototype, 'value');
    if (descriptor && descriptor.set) {
      descriptor.set.call(element, value);
    } else {
      element.value = value;
    }
    fireInputEvents(element);
  }

  function tryFillTitle(title) {
    const selectors = [
      'input[placeholder*="标题"]',
      'input[placeholder*="请输入文章标题"]',
      'input[placeholder*="文章标题"]',
      'input[maxlength][type="text"]',
      'textarea[placeholder*="标题"]'
    ];

    for (const selector of selectors) {
      const element = document.querySelector(selector);
      if (element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement) {
        element.focus();
        setNativeValue(element, title);
        return true;
      }
    }

    return false;
  }

  function tryFillTextareaBody(body) {
    const selectors = [
      'textarea',
      '.CodeMirror textarea',
      '.monaco-editor textarea',
      '[data-name="editor"] textarea'
    ];

    for (const selector of selectors) {
      const element = document.querySelector(selector);
      if (element instanceof HTMLTextAreaElement) {
        element.focus();
        setNativeValue(element, body);
        return true;
      }
    }

    return false;
  }

  function tryFillContentEditableBody(body) {
    const selectors = [
      '[contenteditable="true"]',
      '.editor [contenteditable="true"]',
      '.bytemd-body [contenteditable="true"]',
      '.toastui-editor-contents[contenteditable="true"]'
    ];

    for (const selector of selectors) {
      const element = document.querySelector(selector);
      if (!(element instanceof HTMLElement)) {
        continue;
      }

      if (element.innerText.trim().length > 0 && element.innerText.trim().length < 20) {
        continue;
      }

      element.focus();
      element.innerHTML = '';
      const lines = body.split('\n');
      lines.forEach((line, index) => {
        const p = document.createElement('p');
        p.textContent = line || '\u00A0';
        element.appendChild(p);
        if (index === lines.length - 1 && !line) {
          p.innerHTML = '<br>';
        }
      });
      fireInputEvents(element);
      return true;
    }

    return false;
  }

  function clearTask() {
    window.name = '';
  }

  function autofill(task) {
    const titleFilled = tryFillTitle(task.title);
    const bodyFilled = tryFillTextareaBody(task.body) || tryFillContentEditableBody(task.body);

    if (titleFilled && bodyFilled) {
      showStatus('Supawriter 已自动填充 CSDN 标题和正文', 'success');
      clearTask();
      return true;
    }

    if (titleFilled || bodyFilled) {
      showStatus('Supawriter 已部分填充，请检查标题和正文区域', 'success');
      return true;
    }

    return false;
  }

  function boot() {
    const task = parseTask();
    if (!task) {
      return;
    }

    let attempts = 0;
    const timer = window.setInterval(() => {
      attempts += 1;
      const success = autofill(task);
      if (success || attempts >= 20) {
        window.clearInterval(timer);
        if (!success) {
          showStatus('Supawriter 未找到可填充的 CSDN 编辑器，请手动粘贴', 'error');
        }
      }
    }, 1000);
  }

  boot();
})();
