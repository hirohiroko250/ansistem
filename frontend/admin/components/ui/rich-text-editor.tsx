"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Bold,
  Italic,
  List,
  ListOrdered,
  Heading1,
  Heading2,
  Heading3,
  Quote,
  Code,
  Link as LinkIcon,
  Image as ImageIcon,
  Eye,
  Code2,
  Upload,
  Loader2,
  Undo,
  Redo,
  Table,
  Minus,
  AlignLeft,
  AlignCenter,
  AlignRight,
} from "lucide-react";
import { getAccessToken } from "@/lib/api/client";

interface RichTextEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  minHeight?: string;
  className?: string;
}

// Markdown to HTML converter (simple)
function markdownToHtml(markdown: string): string {
  let html = markdown;

  // Headers
  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

  // Bold and Italic
  html = html.replace(/\*\*\*(.*?)\*\*\*/gim, '<strong><em>$1</em></strong>');
  html = html.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');
  html = html.replace(/\*(.*?)\*/gim, '<em>$1</em>');

  // Links
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/gim, '<a href="$2">$1</a>');

  // Images
  html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/gim, '<img src="$2" alt="$1" />');

  // Code blocks
  html = html.replace(/```([\s\S]*?)```/gim, '<pre><code>$1</code></pre>');
  html = html.replace(/`([^`]+)`/gim, '<code>$1</code>');

  // Blockquotes
  html = html.replace(/^> (.*$)/gim, '<blockquote>$1</blockquote>');

  // Unordered lists
  html = html.replace(/^\- (.*$)/gim, '<li>$1</li>');
  html = html.replace(/^\* (.*$)/gim, '<li>$1</li>');

  // Ordered lists
  html = html.replace(/^\d+\. (.*$)/gim, '<li>$1</li>');

  // Horizontal rule
  html = html.replace(/^---$/gim, '<hr />');

  // Line breaks
  html = html.replace(/\n/gim, '<br />');

  return html;
}

// Simple Markdown preview renderer
function renderMarkdownPreview(content: string): React.ReactNode {
  if (!content) return <p className="text-gray-400">プレビューがここに表示されます</p>;

  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];
  let inCodeBlock = false;
  let codeContent: string[] = [];

  lines.forEach((line, index) => {
    // Code block handling
    if (line.startsWith('```')) {
      if (inCodeBlock) {
        elements.push(
          <pre key={`code-${index}`} className="bg-gray-100 p-3 rounded-lg overflow-x-auto my-2">
            <code className="text-sm font-mono">{codeContent.join('\n')}</code>
          </pre>
        );
        codeContent = [];
        inCodeBlock = false;
      } else {
        inCodeBlock = true;
      }
      return;
    }

    if (inCodeBlock) {
      codeContent.push(line);
      return;
    }

    // Headers
    if (line.startsWith('### ')) {
      elements.push(<h3 key={index} className="text-lg font-bold mt-4 mb-2">{line.slice(4)}</h3>);
    } else if (line.startsWith('## ')) {
      elements.push(<h2 key={index} className="text-xl font-bold mt-6 mb-3">{line.slice(3)}</h2>);
    } else if (line.startsWith('# ')) {
      elements.push(<h1 key={index} className="text-2xl font-bold mt-6 mb-3">{line.slice(2)}</h1>);
    }
    // Blockquote
    else if (line.startsWith('> ')) {
      elements.push(
        <blockquote key={index} className="border-l-4 border-gray-300 pl-4 my-2 text-gray-600 italic">
          {formatInline(line.slice(2))}
        </blockquote>
      );
    }
    // Horizontal rule
    else if (line.trim() === '---' || line.trim() === '***') {
      elements.push(<hr key={index} className="my-4 border-gray-300" />);
    }
    // Unordered list
    else if (line.startsWith('- ') || line.startsWith('* ')) {
      elements.push(
        <li key={index} className="ml-4 list-disc">{formatInline(line.slice(2))}</li>
      );
    }
    // Ordered list
    else if (/^\d+\. /.test(line)) {
      const text = line.replace(/^\d+\. /, '');
      elements.push(
        <li key={index} className="ml-4 list-decimal">{formatInline(text)}</li>
      );
    }
    // Image
    else if (/!\[.*?\]\(.*?\)/.test(line)) {
      const match = line.match(/!\[(.*?)\]\((.*?)\)/);
      if (match) {
        elements.push(
          <div key={index} className="my-4">
            <img
              src={match[2]}
              alt={match[1]}
              className="max-w-full h-auto rounded-lg border"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
            {match[1] && <p className="text-sm text-gray-500 mt-1">{match[1]}</p>}
          </div>
        );
      }
    }
    // Empty line
    else if (line.trim() === '') {
      elements.push(<div key={index} className="h-2" />);
    }
    // Regular text
    else {
      elements.push(<p key={index} className="mb-2">{formatInline(line)}</p>);
    }
  });

  return <>{elements}</>;
}

// Format inline elements
function formatInline(text: string): React.ReactNode {
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let key = 0;

  while (remaining.length > 0) {
    // Bold
    const boldMatch = remaining.match(/\*\*([^*]+)\*\*/);
    if (boldMatch && boldMatch.index !== undefined) {
      if (boldMatch.index > 0) {
        parts.push(formatInlineCode(remaining.slice(0, boldMatch.index), key++));
      }
      parts.push(<strong key={key++}>{boldMatch[1]}</strong>);
      remaining = remaining.slice(boldMatch.index + boldMatch[0].length);
      continue;
    }

    // Italic
    const italicMatch = remaining.match(/\*([^*]+)\*/);
    if (italicMatch && italicMatch.index !== undefined) {
      if (italicMatch.index > 0) {
        parts.push(formatInlineCode(remaining.slice(0, italicMatch.index), key++));
      }
      parts.push(<em key={key++}>{italicMatch[1]}</em>);
      remaining = remaining.slice(italicMatch.index + italicMatch[0].length);
      continue;
    }

    // Link
    const linkMatch = remaining.match(/\[([^\]]+)\]\(([^)]+)\)/);
    if (linkMatch && linkMatch.index !== undefined) {
      if (linkMatch.index > 0) {
        parts.push(formatInlineCode(remaining.slice(0, linkMatch.index), key++));
      }
      parts.push(
        <a key={key++} href={linkMatch[2]} className="text-blue-600 hover:underline" target="_blank" rel="noopener noreferrer">
          {linkMatch[1]}
        </a>
      );
      remaining = remaining.slice(linkMatch.index + linkMatch[0].length);
      continue;
    }

    // No more matches, process rest as inline code
    parts.push(formatInlineCode(remaining, key++));
    break;
  }

  return parts.length === 1 ? parts[0] : <>{parts}</>;
}

// Format inline code
function formatInlineCode(text: string, keyPrefix: number): React.ReactNode {
  const parts: React.ReactNode[] = [];
  const codeRegex = /`([^`]+)`/g;
  let lastIndex = 0;
  let match;

  while ((match = codeRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    parts.push(
      <code key={`${keyPrefix}-${parts.length}`} className="bg-gray-100 px-1 py-0.5 rounded text-sm font-mono text-red-600">
        {match[1]}
      </code>
    );
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length === 1 ? parts[0] : <>{parts}</>;
}

export function RichTextEditor({
  value,
  onChange,
  placeholder = "内容を入力...",
  minHeight = "300px",
  className = "",
}: RichTextEditorProps) {
  const [mode, setMode] = useState<"visual" | "code">("visual");
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const visualEditorRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [history, setHistory] = useState<string[]>([value]);
  const [historyIndex, setHistoryIndex] = useState(0);

  // Save to history
  const saveToHistory = useCallback((newValue: string) => {
    setHistory(prev => {
      const newHistory = prev.slice(0, historyIndex + 1);
      newHistory.push(newValue);
      return newHistory.slice(-50); // Keep last 50 states
    });
    setHistoryIndex(prev => Math.min(prev + 1, 49));
  }, [historyIndex]);

  // Undo
  const handleUndo = useCallback(() => {
    if (historyIndex > 0) {
      setHistoryIndex(prev => prev - 1);
      onChange(history[historyIndex - 1]);
    }
  }, [historyIndex, history, onChange]);

  // Redo
  const handleRedo = useCallback(() => {
    if (historyIndex < history.length - 1) {
      setHistoryIndex(prev => prev + 1);
      onChange(history[historyIndex + 1]);
    }
  }, [historyIndex, history, onChange]);

  // Insert text at cursor position
  const insertAtCursor = useCallback((before: string, after: string = "", placeholder: string = "") => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = value.slice(start, end) || placeholder;

    const newValue = value.slice(0, start) + before + selectedText + after + value.slice(end);
    onChange(newValue);
    saveToHistory(newValue);

    // Restore cursor position
    setTimeout(() => {
      textarea.focus();
      const newCursorPos = start + before.length + selectedText.length;
      textarea.setSelectionRange(newCursorPos, newCursorPos);
    }, 0);
  }, [value, onChange, saveToHistory]);

  // Toolbar actions
  const toolbarActions = {
    bold: () => insertAtCursor("**", "**", "太字テキスト"),
    italic: () => insertAtCursor("*", "*", "斜体テキスト"),
    h1: () => insertAtCursor("# ", "", "見出し1"),
    h2: () => insertAtCursor("## ", "", "見出し2"),
    h3: () => insertAtCursor("### ", "", "見出し3"),
    ul: () => insertAtCursor("- ", "", "リスト項目"),
    ol: () => insertAtCursor("1. ", "", "リスト項目"),
    quote: () => insertAtCursor("> ", "", "引用テキスト"),
    code: () => insertAtCursor("`", "`", "コード"),
    codeBlock: () => insertAtCursor("```\n", "\n```", "コードブロック"),
    link: () => {
      const url = prompt("URLを入力してください:");
      if (url) insertAtCursor("[", `](${url})`, "リンクテキスト");
    },
    hr: () => insertAtCursor("\n---\n", ""),
    table: () => insertAtCursor("\n| 見出し1 | 見出し2 | 見出し3 |\n|---------|---------|--------|\n| セル1 | セル2 | セル3 |\n", ""),
  };

  // Image upload
  const uploadImage = useCallback(async (file: File) => {
    if (!file.type.startsWith("image/")) {
      alert("画像ファイルのみアップロードできます");
      return;
    }

    setUploading(true);

    try {
      const token = getAccessToken();
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const formData = new FormData();
      formData.append("image", file);

      const response = await fetch(`${baseUrl}/knowledge/manuals/upload_image/`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || "アップロードに失敗しました");
      }

      const data = await response.json();

      // Insert markdown image at cursor
      const imageMarkdown = `\n![${file.name}](${data.url})\n`;
      const textarea = textareaRef.current;
      if (textarea) {
        const start = textarea.selectionStart;
        const newValue = value.slice(0, start) + imageMarkdown + value.slice(start);
        onChange(newValue);
        saveToHistory(newValue);
      } else {
        onChange(value + imageMarkdown);
        saveToHistory(value + imageMarkdown);
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : "画像のアップロードに失敗しました");
    } finally {
      setUploading(false);
    }
  }, [value, onChange, saveToHistory]);

  // Handle file input change
  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      uploadImage(files[0]);
    }
    e.target.value = "";
  }, [uploadImage]);

  // Drag and drop handlers
  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (file.type.startsWith("image/")) {
        uploadImage(file);
      }
    }
  }, [uploadImage]);

  // Paste handler for images
  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    const items = e.clipboardData.items;
    for (let i = 0; i < items.length; i++) {
      if (items[i].type.startsWith("image/")) {
        e.preventDefault();
        const file = items[i].getAsFile();
        if (file) {
          uploadImage(file);
        }
        break;
      }
    }
  }, [uploadImage]);

  // Handle text change with history
  const handleTextChange = useCallback((newValue: string) => {
    onChange(newValue);
    // Debounced history save would be better, but keeping simple for now
  }, [onChange]);

  // Save to history on blur
  const handleBlur = useCallback(() => {
    if (value !== history[historyIndex]) {
      saveToHistory(value);
    }
  }, [value, history, historyIndex, saveToHistory]);

  return (
    <div className={`border rounded-lg overflow-hidden ${className}`}>
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-1 p-2 bg-gray-50 border-b">
        {/* Mode toggle */}
        <div className="flex rounded-md border bg-white mr-2">
          <Button
            type="button"
            variant={mode === "visual" ? "default" : "ghost"}
            size="sm"
            onClick={() => setMode("visual")}
            className="rounded-r-none"
          >
            <Eye className="w-4 h-4 mr-1" />
            ビジュアル
          </Button>
          <Button
            type="button"
            variant={mode === "code" ? "default" : "ghost"}
            size="sm"
            onClick={() => setMode("code")}
            className="rounded-l-none"
          >
            <Code2 className="w-4 h-4 mr-1" />
            コード
          </Button>
        </div>

        <div className="h-6 w-px bg-gray-300 mx-1" />

        {/* Undo/Redo */}
        <Button type="button" variant="ghost" size="sm" onClick={handleUndo} disabled={historyIndex === 0} title="元に戻す">
          <Undo className="w-4 h-4" />
        </Button>
        <Button type="button" variant="ghost" size="sm" onClick={handleRedo} disabled={historyIndex === history.length - 1} title="やり直す">
          <Redo className="w-4 h-4" />
        </Button>

        <div className="h-6 w-px bg-gray-300 mx-1" />

        {/* Formatting */}
        <Button type="button" variant="ghost" size="sm" onClick={toolbarActions.bold} title="太字 (Ctrl+B)">
          <Bold className="w-4 h-4" />
        </Button>
        <Button type="button" variant="ghost" size="sm" onClick={toolbarActions.italic} title="斜体 (Ctrl+I)">
          <Italic className="w-4 h-4" />
        </Button>

        <div className="h-6 w-px bg-gray-300 mx-1" />

        {/* Headings */}
        <Button type="button" variant="ghost" size="sm" onClick={toolbarActions.h1} title="見出し1">
          <Heading1 className="w-4 h-4" />
        </Button>
        <Button type="button" variant="ghost" size="sm" onClick={toolbarActions.h2} title="見出し2">
          <Heading2 className="w-4 h-4" />
        </Button>
        <Button type="button" variant="ghost" size="sm" onClick={toolbarActions.h3} title="見出し3">
          <Heading3 className="w-4 h-4" />
        </Button>

        <div className="h-6 w-px bg-gray-300 mx-1" />

        {/* Lists */}
        <Button type="button" variant="ghost" size="sm" onClick={toolbarActions.ul} title="箇条書きリスト">
          <List className="w-4 h-4" />
        </Button>
        <Button type="button" variant="ghost" size="sm" onClick={toolbarActions.ol} title="番号付きリスト">
          <ListOrdered className="w-4 h-4" />
        </Button>

        <div className="h-6 w-px bg-gray-300 mx-1" />

        {/* Block elements */}
        <Button type="button" variant="ghost" size="sm" onClick={toolbarActions.quote} title="引用">
          <Quote className="w-4 h-4" />
        </Button>
        <Button type="button" variant="ghost" size="sm" onClick={toolbarActions.code} title="インラインコード">
          <Code className="w-4 h-4" />
        </Button>
        <Button type="button" variant="ghost" size="sm" onClick={toolbarActions.hr} title="水平線">
          <Minus className="w-4 h-4" />
        </Button>
        <Button type="button" variant="ghost" size="sm" onClick={toolbarActions.table} title="テーブル">
          <Table className="w-4 h-4" />
        </Button>

        <div className="h-6 w-px bg-gray-300 mx-1" />

        {/* Links and Images */}
        <Button type="button" variant="ghost" size="sm" onClick={toolbarActions.link} title="リンク">
          <LinkIcon className="w-4 h-4" />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          title="画像を挿入"
        >
          {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ImageIcon className="w-4 h-4" />}
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleFileChange}
          className="hidden"
        />
      </div>

      {/* Editor area */}
      <div
        className={`relative ${dragActive ? "ring-2 ring-blue-500 ring-inset" : ""}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        {mode === "code" ? (
          <Textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => handleTextChange(e.target.value)}
            onBlur={handleBlur}
            onPaste={handlePaste}
            placeholder={placeholder}
            className="border-0 rounded-none resize-none font-mono text-sm focus:ring-0"
            style={{ minHeight }}
          />
        ) : (
          <div className="flex" style={{ minHeight }}>
            {/* Editor */}
            <div className="flex-1 border-r">
              <Textarea
                ref={textareaRef}
                value={value}
                onChange={(e) => handleTextChange(e.target.value)}
                onBlur={handleBlur}
                onPaste={handlePaste}
                placeholder={placeholder}
                className="border-0 rounded-none resize-none h-full focus:ring-0"
                style={{ minHeight }}
              />
            </div>
            {/* Preview */}
            <div
              ref={visualEditorRef}
              className="flex-1 p-4 overflow-y-auto bg-white prose prose-sm max-w-none"
              style={{ minHeight }}
            >
              {renderMarkdownPreview(value)}
            </div>
          </div>
        )}

        {/* Drag overlay */}
        {dragActive && (
          <div className="absolute inset-0 bg-blue-100/80 flex items-center justify-center pointer-events-none">
            <div className="text-center">
              <Upload className="w-12 h-12 text-blue-500 mx-auto mb-2" />
              <p className="text-blue-700 font-medium">画像をドロップしてアップロード</p>
            </div>
          </div>
        )}

        {/* Uploading overlay */}
        {uploading && (
          <div className="absolute inset-0 bg-white/80 flex items-center justify-center">
            <div className="text-center">
              <Loader2 className="w-8 h-8 text-blue-500 mx-auto mb-2 animate-spin" />
              <p className="text-gray-600">画像をアップロード中...</p>
            </div>
          </div>
        )}
      </div>

      {/* Footer help */}
      <div className="px-3 py-2 bg-gray-50 border-t text-xs text-gray-500">
        <span>Markdown記法対応</span>
        <span className="mx-2">•</span>
        <span>画像はドラッグ＆ドロップまたはペーストで挿入</span>
        <span className="mx-2">•</span>
        <span>Ctrl+Z: 元に戻す, Ctrl+Y: やり直す</span>
      </div>
    </div>
  );
}

export default RichTextEditor;
