"use client";

import {
  useState,
  useRef,
  useCallback,
  useEffect,
  forwardRef,
  useImperativeHandle,
} from "react";
import {
  Bold,
  Italic,
  Underline,
  Strikethrough,
  AlignLeft,
  AlignCenter,
  AlignRight,
  List,
  ListOrdered,
  Quote,
  Link2,
  Unlink,
  Undo2,
  Redo2,
  ChevronDown,
} from "lucide-react";

// ---- Options ----
const FONT_SIZES = [
  { label: "小", value: "1" },
  { label: "標準", value: "3" },
  { label: "大", value: "5" },
  { label: "特大", value: "7" },
];

const BLOCK_FORMATS = [
  { label: "段落", tag: "p" },
  { label: "見出し1", tag: "h2" },
  { label: "見出し2", tag: "h3" },
  { label: "見出し3", tag: "h4" },
];

const TEXT_COLORS = [
  "#000000", "#e53e3e", "#dd6b20", "#d69e2e",
  "#38a169", "#3182ce", "#805ad5", "#d53f8c", "#718096",
];

const BG_COLORS = [
  "transparent", "#FEF3C7", "#FECACA", "#BBF7D0",
  "#BFDBFE", "#DDD6FE", "#FBCFE8", "#E5E7EB",
];

// ---- Public API ----
export interface FeedEditorHandle {
  insertImage: (url: string) => void;
  insertVideo: (url: string) => void;
  getContent: () => string;
}

interface FeedEditorProps {
  initialContent?: string;
  onChange?: (html: string) => void;
  className?: string;
}

// ---- Component ----
const FeedEditor = forwardRef<FeedEditorHandle, FeedEditorProps>(
  ({ initialContent = "", onChange, className }, ref) => {
    const editorRef = useRef<HTMLDivElement>(null);
    const initializedRef = useRef(false);
    const [activeDropdown, setActiveDropdown] = useState<string | null>(null);

    useEffect(() => {
      if (editorRef.current && !initializedRef.current) {
        editorRef.current.innerHTML = initialContent;
        initializedRef.current = true;
      }
    }, [initialContent]);

    useEffect(() => {
      if (!activeDropdown) return;
      const handler = () => setActiveDropdown(null);
      document.addEventListener("click", handler);
      return () => document.removeEventListener("click", handler);
    }, [activeDropdown]);

    const handleInput = useCallback(() => {
      if (editorRef.current && onChange) {
        onChange(editorRef.current.innerHTML);
      }
    }, [onChange]);

    useImperativeHandle(ref, () => ({
      insertImage: (url: string) => {
        const editor = editorRef.current;
        if (!editor) return;
        editor.focus();
        document.execCommand(
          "insertHTML",
          false,
          `<div style="margin:8px 0;text-align:center;"><img src="${url}" alt="" style="max-width:100%;height:auto;border-radius:4px;" /></div><p><br></p>`
        );
        handleInput();
      },
      insertVideo: (url: string) => {
        const editor = editorRef.current;
        if (!editor) return;
        editor.focus();
        document.execCommand(
          "insertHTML",
          false,
          `<div style="margin:8px 0;"><video src="${url}" controls style="max-width:100%;height:auto;border-radius:4px;"></video></div><p><br></p>`
        );
        handleInput();
      },
      getContent: () => editorRef.current?.innerHTML || "",
    }));

    const exec = useCallback(
      (cmd: string, value?: string) => {
        editorRef.current?.focus();
        document.execCommand(cmd, false, value);
        handleInput();
      },
      [handleInput]
    );

    const toggleDropdown = (name: string, e: React.MouseEvent) => {
      e.stopPropagation();
      setActiveDropdown(activeDropdown === name ? null : name);
    };

    const handleLink = () => {
      const selection = window.getSelection();
      const currentUrl =
        selection?.anchorNode?.parentElement?.closest("a")?.href || "";
      const url = prompt("URLを入力してください:", currentUrl || "https://");
      if (url) {
        exec("createLink", url);
      }
    };

    const ToolBtn = ({
      icon: Icon,
      title,
      onClick,
    }: {
      icon: React.ComponentType<{ className?: string }>;
      title: string;
      onClick: () => void;
    }) => (
      <button
        type="button"
        className="h-8 w-8 p-0 inline-flex items-center justify-center rounded hover:bg-gray-200 transition-colors"
        onClick={onClick}
        title={title}
      >
        <Icon className="w-4 h-4" />
      </button>
    );

    const Divider = () => <div className="w-px h-6 bg-gray-300 mx-1" />;

    return (
      <div className={`border rounded-lg bg-white flex flex-col overflow-hidden ${className || ""}`}>
        {/* Toolbar Row 1: 文字サイズ | 段落 | B I U S | テキスト色 | 背景色 */}
        <div className="flex items-center gap-0.5 px-2 py-1.5 border-b bg-gray-50 flex-wrap">
          {/* Font Size */}
          <div className="relative">
            <button
              type="button"
              className="h-8 px-2 text-xs inline-flex items-center gap-1 rounded hover:bg-gray-200"
              onClick={(e) => toggleDropdown("fontSize", e)}
            >
              文字サイズ <ChevronDown className="w-3 h-3" />
            </button>
            {activeDropdown === "fontSize" && (
              <div className="absolute top-full left-0 mt-1 bg-white border rounded shadow-lg z-50 min-w-[100px]">
                {FONT_SIZES.map((s) => (
                  <button
                    key={s.value}
                    type="button"
                    className="block w-full text-left px-3 py-1.5 text-sm hover:bg-gray-100"
                    onClick={() => { exec("fontSize", s.value); setActiveDropdown(null); }}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Block Format */}
          <div className="relative">
            <button
              type="button"
              className="h-8 px-2 text-xs inline-flex items-center gap-1 rounded hover:bg-gray-200"
              onClick={(e) => toggleDropdown("blockFormat", e)}
            >
              段落 <ChevronDown className="w-3 h-3" />
            </button>
            {activeDropdown === "blockFormat" && (
              <div className="absolute top-full left-0 mt-1 bg-white border rounded shadow-lg z-50 min-w-[120px]">
                {BLOCK_FORMATS.map((f) => (
                  <button
                    key={f.tag}
                    type="button"
                    className="block w-full text-left px-3 py-1.5 text-sm hover:bg-gray-100"
                    onClick={() => { exec("formatBlock", `<${f.tag}>`); setActiveDropdown(null); }}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          <Divider />

          <ToolBtn icon={Bold} title="太字" onClick={() => exec("bold")} />
          <ToolBtn icon={Italic} title="斜体" onClick={() => exec("italic")} />
          <ToolBtn icon={Underline} title="下線" onClick={() => exec("underline")} />
          <ToolBtn icon={Strikethrough} title="取り消し線" onClick={() => exec("strikeThrough")} />

          <Divider />

          {/* Text Color */}
          <div className="relative">
            <button
              type="button"
              className="h-8 px-2 text-xs inline-flex items-center gap-1 rounded hover:bg-gray-200"
              onClick={(e) => toggleDropdown("textColor", e)}
            >
              <span className="font-bold text-red-500 text-sm">A</span>
              <ChevronDown className="w-3 h-3" />
            </button>
            {activeDropdown === "textColor" && (
              <div className="absolute top-full left-0 mt-1 bg-white border rounded shadow-lg z-50 p-2">
                <div className="grid grid-cols-5 gap-1.5">
                  {TEXT_COLORS.map((c) => (
                    <button
                      key={c}
                      type="button"
                      className="w-6 h-6 rounded border border-gray-200 hover:scale-125 transition-transform"
                      style={{ backgroundColor: c }}
                      onClick={() => { exec("foreColor", c); setActiveDropdown(null); }}
                      title={c}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Background Color */}
          <div className="relative">
            <button
              type="button"
              className="h-8 px-2 text-xs inline-flex items-center gap-1 rounded hover:bg-gray-200"
              onClick={(e) => toggleDropdown("bgColor", e)}
            >
              <span className="font-bold text-sm bg-yellow-200 px-0.5 rounded">A</span>
              <ChevronDown className="w-3 h-3" />
            </button>
            {activeDropdown === "bgColor" && (
              <div className="absolute top-full left-0 mt-1 bg-white border rounded shadow-lg z-50 p-2">
                <div className="grid grid-cols-4 gap-1.5">
                  {BG_COLORS.map((c, i) => (
                    <button
                      key={i}
                      type="button"
                      className="w-6 h-6 rounded border border-gray-200 hover:scale-125 transition-transform"
                      style={{ backgroundColor: c === "transparent" ? "#fff" : c }}
                      onClick={() => { exec("hiliteColor", c); setActiveDropdown(null); }}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Toolbar Row 2: リンク | 揃え | リスト・引用 | 戻す/やり直し */}
        <div className="flex items-center gap-0.5 px-2 py-1.5 border-b bg-gray-50 flex-wrap">
          <ToolBtn icon={Link2} title="リンク挿入" onClick={handleLink} />
          <ToolBtn icon={Unlink} title="リンク解除" onClick={() => exec("unlink")} />

          <Divider />

          <ToolBtn icon={AlignLeft} title="左揃え" onClick={() => exec("justifyLeft")} />
          <ToolBtn icon={AlignCenter} title="中央揃え" onClick={() => exec("justifyCenter")} />
          <ToolBtn icon={AlignRight} title="右揃え" onClick={() => exec("justifyRight")} />

          <Divider />

          <ToolBtn icon={List} title="箇条書き" onClick={() => exec("insertUnorderedList")} />
          <ToolBtn icon={ListOrdered} title="番号付きリスト" onClick={() => exec("insertOrderedList")} />
          <ToolBtn icon={Quote} title="引用" onClick={() => exec("formatBlock", "<blockquote>")} />

          <Divider />

          <ToolBtn icon={Undo2} title="元に戻す" onClick={() => exec("undo")} />
          <ToolBtn icon={Redo2} title="やり直し" onClick={() => exec("redo")} />
        </div>

        {/* Editor Area */}
        <div
          ref={editorRef}
          contentEditable
          suppressContentEditableWarning
          onInput={handleInput}
          className={`flex-1 p-4 outline-none overflow-y-auto leading-relaxed text-sm
            [&:empty]:before:content-[attr(data-placeholder)] [&:empty]:before:text-gray-400
            [&_img]:max-w-full [&_img]:h-auto [&_img]:rounded
            [&_video]:max-w-full [&_video]:h-auto
            [&_blockquote]:border-l-4 [&_blockquote]:border-gray-300 [&_blockquote]:pl-4 [&_blockquote]:italic [&_blockquote]:text-gray-600
            [&_h2]:text-xl [&_h2]:font-bold [&_h2]:my-3
            [&_h3]:text-lg [&_h3]:font-bold [&_h3]:my-2
            [&_h4]:text-base [&_h4]:font-bold [&_h4]:my-2
            [&_a]:text-blue-600 [&_a]:underline
            [&_ul]:list-disc [&_ul]:pl-6
            [&_ol]:list-decimal [&_ol]:pl-6`}
          style={{ minHeight: "400px" }}
          data-placeholder="本文を入力してください..."
        />
      </div>
    );
  }
);

FeedEditor.displayName = "FeedEditor";
export default FeedEditor;
