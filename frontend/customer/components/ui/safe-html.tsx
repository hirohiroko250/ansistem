'use client';

import { useMemo } from 'react';

// Whitelist of allowed tags
const ALLOWED_TAGS = new Set([
  'div', 'p', 'br', 'span',
  'strong', 'b', 'em', 'i', 'u', 's', 'strike', 'del',
  'h1', 'h2', 'h3', 'h4',
  'ul', 'ol', 'li',
  'blockquote',
  'a', 'img', 'video',
  'font',
]);

// Allowed attributes per tag
const ALLOWED_ATTRS: Record<string, Set<string>> = {
  '*': new Set(['class', 'style']),
  a: new Set(['href', 'target', 'rel']),
  img: new Set(['src', 'alt', 'width', 'height']),
  video: new Set(['src', 'controls', 'width', 'height', 'preload', 'poster']),
  font: new Set(['size', 'color', 'face']),
};

// Allowed CSS properties (for style attribute sanitization)
const ALLOWED_STYLE_PROPS = new Set([
  'color', 'background-color', 'font-size', 'font-weight', 'font-style',
  'text-align', 'text-decoration', 'line-height', 'margin', 'padding',
  'margin-top', 'margin-bottom', 'margin-left', 'margin-right',
  'padding-top', 'padding-bottom', 'padding-left', 'padding-right',
  'max-width', 'width', 'height', 'display', 'border-radius',
]);

function sanitizeStyle(style: string): string {
  return style
    .split(';')
    .map(rule => rule.trim())
    .filter(rule => {
      const colonIndex = rule.indexOf(':');
      if (colonIndex === -1) return false;
      const prop = rule.substring(0, colonIndex).trim().toLowerCase();
      return ALLOWED_STYLE_PROPS.has(prop);
    })
    .join('; ');
}

function sanitizeNode(node: Node): Node | null {
  if (node.nodeType === Node.TEXT_NODE) {
    return node.cloneNode(true);
  }

  if (node.nodeType !== Node.ELEMENT_NODE) {
    return null;
  }

  const el = node as HTMLElement;
  const tagName = el.tagName.toLowerCase();

  if (!ALLOWED_TAGS.has(tagName)) {
    // If tag is not allowed, still process children (unwrap)
    const fragment = document.createDocumentFragment();
    for (let i = 0; i < el.childNodes.length; i++) {
      const child = sanitizeNode(el.childNodes[i]);
      if (child) fragment.appendChild(child);
    }
    return fragment;
  }

  const newEl = document.createElement(tagName);

  // Copy allowed attributes
  const globalAttrs = ALLOWED_ATTRS['*'];
  const tagAttrs = ALLOWED_ATTRS[tagName];

  for (let i = 0; i < el.attributes.length; i++) {
    const attr = el.attributes[i];
    const name = attr.name.toLowerCase();

    if (globalAttrs?.has(name) || tagAttrs?.has(name)) {
      if (name === 'style') {
        const sanitized = sanitizeStyle(attr.value);
        if (sanitized) newEl.setAttribute('style', sanitized);
      } else if (name === 'href') {
        // Only allow http/https/mailto links
        const val = attr.value.trim().toLowerCase();
        if (val.startsWith('http://') || val.startsWith('https://') || val.startsWith('mailto:')) {
          newEl.setAttribute(name, attr.value);
        }
      } else if (name === 'src') {
        // Only allow http/https and relative URLs
        const val = attr.value.trim().toLowerCase();
        if (val.startsWith('http://') || val.startsWith('https://') || val.startsWith('/')) {
          newEl.setAttribute(name, attr.value);
        }
      } else {
        newEl.setAttribute(name, attr.value);
      }
    }
  }

  // For links, add safety attributes
  if (tagName === 'a') {
    newEl.setAttribute('target', '_blank');
    newEl.setAttribute('rel', 'noopener noreferrer');
  }

  // For videos, ensure controls
  if (tagName === 'video') {
    newEl.setAttribute('controls', '');
  }

  // Recursively sanitize children (except void elements)
  if (!['img', 'br'].includes(tagName)) {
    for (let i = 0; i < el.childNodes.length; i++) {
      const child = sanitizeNode(el.childNodes[i]);
      if (child) newEl.appendChild(child);
    }
  }

  return newEl;
}

function sanitizeHtml(html: string): string {
  if (typeof window === 'undefined') return html;

  const parser = new DOMParser();
  const doc = parser.parseFromString(html, 'text/html');
  const fragment = document.createDocumentFragment();

  for (let i = 0; i < doc.body.childNodes.length; i++) {
    const child = sanitizeNode(doc.body.childNodes[i]);
    if (child) fragment.appendChild(child);
  }

  const container = document.createElement('div');
  container.appendChild(fragment);
  return container.innerHTML;
}

function isHtml(text: string): boolean {
  return /<[a-z][\s\S]*>/i.test(text);
}

function hasInlineMedia(html: string): boolean {
  return /<(img|video)\s/i.test(html);
}

interface SafeHtmlProps {
  content: string;
  className?: string;
}

export function SafeHtml({ content, className = '' }: SafeHtmlProps) {
  const sanitized = useMemo(() => {
    if (!content) return '';
    if (!isHtml(content)) return '';
    return sanitizeHtml(content);
  }, [content]);

  // Plain text content - render as-is with whitespace preserved
  if (!content || !isHtml(content)) {
    return (
      <span className={className}>
        {content}
      </span>
    );
  }

  // HTML content - render sanitized
  return (
    <div
      className={`feed-content ${className}`}
      dangerouslySetInnerHTML={{ __html: sanitized }}
    />
  );
}

// Export helper for checking inline media
export { hasInlineMedia, isHtml };
