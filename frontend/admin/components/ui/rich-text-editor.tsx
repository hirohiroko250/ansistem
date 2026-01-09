"use client";

import { useState, useCallback, useRef, useEffect, useMemo } from "react";
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
  Plus,
  GripVertical,
} from "lucide-react";
import { getAccessToken } from "@/lib/api/client";

interface RichTextEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  minHeight?: string;
  className?: string;
}

// Parse content into blocks
interface Block {
  id: string;
  type: "heading1" | "heading2" | "heading3" | "paragraph" | "list" | "quote" | "code" | "image" | "hr" | "empty";
  content: string;
  raw: string;
}

function parseContentToBlocks(content: string): Block[] {
  const lines = content.split('\n');
  const blocks: Block[] = [];
  let inCodeBlock = false;
  let codeContent: string[] = [];
  let codeStartLine = 0;

  lines.forEach((line, index) => {
    const id = `block-${index}`;

    // Code block handling
    if (line.startsWith('```')) {
      if (inCodeBlock) {
        blocks.push({
          id: `block-code-${codeStartLine}`,
          type: "code",
          content: codeContent.join('\n'),
          raw: '```\n' + codeContent.join('\n') + '\n```',
        });
        codeContent = [];
        inCodeBlock = false;
      } else {
        inCodeBlock = true;
        codeStartLine = index;
      }
      return;
    }

    if (inCodeBlock) {
      codeContent.push(line);
      return;
    }

    // Headers
    if (line.startsWith('### ')) {
      blocks.push({ id, type: "heading3", content: line.slice(4), raw: line });
    } else if (line.startsWith('## ')) {
      blocks.push({ id, type: "heading2", content: line.slice(3), raw: line });
    } else if (line.startsWith('# ')) {
      blocks.push({ id, type: "heading1", content: line.slice(2), raw: line });
    }
    // Quote
    else if (line.startsWith('> ')) {
      blocks.push({ id, type: "quote", content: line.slice(2), raw: line });
    }
    // HR
    else if (line.trim() === '---' || line.trim() === '***') {
      blocks.push({ id, type: "hr", content: "", raw: line });
    }
    // List
    else if (line.startsWith('- ') || line.startsWith('* ') || /^\d+\. /.test(line)) {
      blocks.push({ id, type: "list", content: line, raw: line });
    }
    // Image
    else if (/!\[.*?\]\(.*?\)/.test(line)) {
      const match = line.match(/!\[(.*?)\]\((.*?)\)/);
      blocks.push({
        id,
        type: "image",
        content: match ? match[2] : "",
        raw: line
      });
    }
    // Empty line
    else if (line.trim() === '') {
      blocks.push({ id, type: "empty", content: "", raw: "" });
    }
    // Paragraph
    else {
      blocks.push({ id, type: "paragraph", content: line, raw: line });
    }
  });

  return blocks;
}

// Render block preview
function BlockPreview({ block }: { block: Block }) {
  switch (block.type) {
    case "heading1":
      return <h1 className="text-2xl font-bold my-2">{formatInlinePreview(block.content)}</h1>;
    case "heading2":
      return <h2 className="text-xl font-bold my-2">{formatInlinePreview(block.content)}</h2>;
    case "heading3":
      return <h3 className="text-lg font-bold my-1">{formatInlinePreview(block.content)}</h3>;
    case "quote":
      return (
        <blockquote className="border-l-4 border-gray-300 pl-4 my-2 text-gray-600 italic">
          {formatInlinePreview(block.content)}
        </blockquote>
      );
    case "hr":
      return <hr className="my-4 border-gray-300" />;
    case "list":
      return <li className="ml-4">{formatInlinePreview(block.content.replace(/^[-*]\s|^\d+\.\s/, ''))}</li>;
    case "code":
      return (
        <pre className="bg-gray-100 p-3 rounded-lg overflow-x-auto my-2">
          <code className="text-sm font-mono">{block.content}</code>
        </pre>
      );
    case "image":
      const match = block.raw.match(/!\[(.*?)\]\((.*?)\)/);
      if (match) {
        return (
          <div className="my-4">
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
      return null;
    case "empty":
      return <div className="h-2" />;
    case "paragraph":
    default:
      return <p className="my-1">{formatInlinePreview(block.content)}</p>;
  }
}

// Format inline elements for preview
function formatInlinePreview(text: string): React.ReactNode {
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let key = 0;

  while (remaining.length > 0) {
    // Bold
    const boldMatch = remaining.match(/\*\*([^*]+)\*\*/);
    if (boldMatch && boldMatch.index !== undefined) {
      if (boldMatch.index > 0) {
        parts.push(formatCodePreview(remaining.slice(0, boldMatch.index), key++));
      }
      parts.push(<strong key={key++}>{boldMatch[1]}</strong>);
      remaining = remaining.slice(boldMatch.index + boldMatch[0].length);
      continue;
    }

    // Italic
    const italicMatch = remaining.match(/\*([^*]+)\*/);
    if (italicMatch && italicMatch.index !== undefined) {
      if (italicMatch.index > 0) {
        parts.push(formatCodePreview(remaining.slice(0, italicMatch.index), key++));
      }
      parts.push(<em key={key++}>{italicMatch[1]}</em>);
      remaining = remaining.slice(italicMatch.index + italicMatch[0].length);
      continue;
    }

    // Link
    const linkMatch = remaining.match(/\[([^\]]+)\]\(([^)]+)\)/);
    if (linkMatch && linkMatch.index !== undefined) {
      if (linkMatch.index > 0) {
        parts.push(formatCodePreview(remaining.slice(0, linkMatch.index), key++));
      }
      parts.push(
        <a key={key++} href={linkMatch[2]} className="text-blue-600 hover:underline" target="_blank" rel="noopener noreferrer">
          {linkMatch[1]}
        </a>
      );
      remaining = remaining.slice(linkMatch.index + linkMatch[0].length);
      continue;
    }

    parts.push(formatCodePreview(remaining, key++));
    break;
  }

  return parts.length === 1 ? parts[0] : <>{parts}</>;
}

function formatCodePreview(text: string, keyPrefix: number): React.ReactNode {
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

// Drop zone component
function DropZone({
  isActive,
  onDrop,
  index,
}: {
  isActive: boolean;
  onDrop: (index: number) => void;
  index: number;
}) {
  return (
    <div
      className={`
        h-1 transition-all duration-200 rounded-full mx-2
        ${isActive
          ? 'h-16 bg-blue-100 border-2 border-dashed border-blue-400 flex items-center justify-center'
          : 'bg-transparent hover:bg-gray-200'
        }
      `}
      onDragOver={(e) => {
        e.preventDefault();
        e.stopPropagation();
      }}
      onDrop={(e) => {
        e.preventDefault();
        e.stopPropagation();
        onDrop(index);
      }}
    >
      {isActive && (
        <div className="flex items-center gap-2 text-blue-600">
          <Plus className="w-5 h-5" />
          <span className="text-sm font-medium">ここに画像をドロップ</span>
        </div>
      )}
    </div>
  );
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
  const [dropIndex, setDropIndex] = useState<number | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const visualEditorRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [history, setHistory] = useState<string[]>([value]);
  const [historyIndex, setHistoryIndex] = useState(0);

  // Parse content into blocks for visual editor
  const blocks = useMemo(() => parseContentToBlocks(value), [value]);

  // Save to history
  const saveToHistory = useCallback((newValue: string) => {
    setHistory(prev => {
      const newHistory = prev.slice(0, historyIndex + 1);
      newHistory.push(newValue);
      return newHistory.slice(-50);
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

    setTimeout(() => {
      textarea.focus();
      const newCursorPos = start + before.length + selectedText.length;
      textarea.setSelectionRange(newCursorPos, newCursorPos);
    }, 0);
  }, [value, onChange, saveToHistory]);

  // Insert image at specific block index
  const insertImageAtIndex = useCallback((imageMarkdown: string, index: number) => {
    const lines = value.split('\n');

    // Calculate the line number to insert at
    let lineIndex = 0;
    let currentBlockIndex = 0;
    let inCodeBlock = false;

    for (let i = 0; i < lines.length && currentBlockIndex < index; i++) {
      if (lines[i].startsWith('```')) {
        inCodeBlock = !inCodeBlock;
      }
      if (!inCodeBlock) {
        currentBlockIndex++;
      }
      lineIndex = i + 1;
    }

    // Insert the image markdown at the calculated position
    lines.splice(lineIndex, 0, '', imageMarkdown, '');
    const newValue = lines.join('\n');
    onChange(newValue);
    saveToHistory(newValue);
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
  const uploadImage = useCallback(async (file: File, insertIndex?: number) => {
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
      const imageMarkdown = `![${file.name}](${data.url})`;

      if (insertIndex !== undefined) {
        // Insert at specific block position
        insertImageAtIndex(imageMarkdown, insertIndex);
      } else {
        // Insert at cursor in code mode
        const textarea = textareaRef.current;
        if (textarea && mode === "code") {
          const start = textarea.selectionStart;
          const newValue = value.slice(0, start) + '\n' + imageMarkdown + '\n' + value.slice(start);
          onChange(newValue);
          saveToHistory(newValue);
        } else {
          // Append to end
          const newValue = value + '\n' + imageMarkdown + '\n';
          onChange(newValue);
          saveToHistory(newValue);
        }
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : "画像のアップロードに失敗しました");
    } finally {
      setUploading(false);
      setDragActive(false);
      setDropIndex(null);
    }
  }, [value, onChange, saveToHistory, insertImageAtIndex, mode]);

  // Handle file input change
  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      uploadImage(files[0]);
    }
    e.target.value = "";
  }, [uploadImage]);

  // Drag and drop handlers for visual editor blocks
  const handleBlockDragOver = useCallback((e: React.DragEvent, index: number) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
    setDropIndex(index);
  }, []);

  const handleBlockDrop = useCallback((index: number) => {
    // The actual file drop is handled in the main drop handler
  }, []);

  // Main drag handlers
  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      // Only set to false if leaving the editor entirely
      const rect = e.currentTarget.getBoundingClientRect();
      const x = e.clientX;
      const y = e.clientY;
      if (x < rect.left || x > rect.right || y < rect.top || y > rect.bottom) {
        setDragActive(false);
        setDropIndex(null);
      }
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (file.type.startsWith("image/")) {
        uploadImage(file, dropIndex !== null ? dropIndex : undefined);
      }
    }
    setDragActive(false);
    setDropIndex(null);
  }, [uploadImage, dropIndex]);

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

  // Handle text change
  const handleTextChange = useCallback((newValue: string) => {
    onChange(newValue);
  }, [onChange]);

  // Save to history on blur
  const handleBlur = useCallback(() => {
    if (value !== history[historyIndex]) {
      saveToHistory(value);
    }
  }, [value, history, historyIndex, saveToHistory]);

  return (
    <div className={`border rounded-lg overflow-hidden bg-white ${className}`}>
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-1 p-2 bg-gray-50 border-b sticky top-0 z-10">
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
        <Button type="button" variant="ghost" size="sm" onClick={toolbarActions.bold} title="太字">
          <Bold className="w-4 h-4" />
        </Button>
        <Button type="button" variant="ghost" size="sm" onClick={toolbarActions.italic} title="斜体">
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
        <Button type="button" variant="ghost" size="sm" onClick={toolbarActions.ul} title="箇条書き">
          <List className="w-4 h-4" />
        </Button>
        <Button type="button" variant="ghost" size="sm" onClick={toolbarActions.ol} title="番号付き">
          <ListOrdered className="w-4 h-4" />
        </Button>

        <div className="h-6 w-px bg-gray-300 mx-1" />

        {/* Block elements */}
        <Button type="button" variant="ghost" size="sm" onClick={toolbarActions.quote} title="引用">
          <Quote className="w-4 h-4" />
        </Button>
        <Button type="button" variant="ghost" size="sm" onClick={toolbarActions.code} title="コード">
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
        className="relative"
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        {mode === "code" ? (
          /* Code mode - plain textarea */
          <Textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => handleTextChange(e.target.value)}
            onBlur={handleBlur}
            onPaste={handlePaste}
            placeholder={placeholder}
            className="border-0 rounded-none resize-none font-mono text-sm focus:ring-0 focus-visible:ring-0"
            style={{ minHeight }}
          />
        ) : (
          /* Visual mode - split view with block-based preview */
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
                className="border-0 rounded-none resize-none h-full focus:ring-0 focus-visible:ring-0 font-mono text-sm"
                style={{ minHeight }}
              />
            </div>

            {/* Preview with drop zones */}
            <div
              ref={visualEditorRef}
              className="flex-1 p-4 overflow-y-auto bg-gray-50"
              style={{ minHeight }}
            >
              {blocks.length === 0 ? (
                <div className="text-gray-400 text-center py-8">
                  <ImageIcon className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p>プレビューがここに表示されます</p>
                  <p className="text-sm mt-2">画像をドラッグ&ドロップで挿入できます</p>
                </div>
              ) : (
                <>
                  {/* Drop zone at the top */}
                  <DropZone
                    isActive={dragActive && dropIndex === 0}
                    onDrop={() => setDropIndex(0)}
                    index={0}
                  />
                  <div
                    onDragOver={(e) => handleBlockDragOver(e, 0)}
                    className="h-2"
                  />

                  {blocks.map((block, index) => (
                    <div key={block.id}>
                      {/* Block content */}
                      <div
                        className={`
                          group relative rounded transition-all
                          ${dragActive ? 'opacity-70' : ''}
                        `}
                      >
                        <BlockPreview block={block} />
                      </div>

                      {/* Drop zone after each block */}
                      <div
                        onDragOver={(e) => handleBlockDragOver(e, index + 1)}
                        className="py-1"
                      >
                        <DropZone
                          isActive={dragActive && dropIndex === index + 1}
                          onDrop={() => setDropIndex(index + 1)}
                          index={index + 1}
                        />
                      </div>
                    </div>
                  ))}
                </>
              )}
            </div>
          </div>
        )}

        {/* Global drag overlay for code mode */}
        {dragActive && mode === "code" && (
          <div className="absolute inset-0 bg-blue-100/80 flex items-center justify-center pointer-events-none">
            <div className="text-center bg-white p-6 rounded-lg shadow-lg">
              <Upload className="w-12 h-12 text-blue-500 mx-auto mb-2" />
              <p className="text-blue-700 font-medium">画像をドロップしてアップロード</p>
            </div>
          </div>
        )}

        {/* Uploading overlay */}
        {uploading && (
          <div className="absolute inset-0 bg-white/80 flex items-center justify-center z-20">
            <div className="text-center bg-white p-6 rounded-lg shadow-lg">
              <Loader2 className="w-8 h-8 text-blue-500 mx-auto mb-2 animate-spin" />
              <p className="text-gray-600">画像をアップロード中...</p>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-3 py-2 bg-gray-50 border-t text-xs text-gray-500 flex items-center justify-between">
        <div>
          <span>Markdown記法対応</span>
          <span className="mx-2">•</span>
          <span>画像はドラッグ&ドロップで挿入</span>
        </div>
        <div className="text-gray-400">
          {blocks.length} ブロック
        </div>
      </div>
    </div>
  );
}

export default RichTextEditor;
