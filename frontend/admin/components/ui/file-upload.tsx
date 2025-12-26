"use client";

import { useState, useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Upload, X, Image as ImageIcon, Film, Loader2 } from "lucide-react";
import { getAccessToken } from "@/lib/api/client";

interface UploadedFile {
  url: string;
  filename: string;
  size: number;
  type: "image" | "video";
}

interface FileUploadProps {
  onUpload: (file: UploadedFile) => void;
  accept?: string;
  multiple?: boolean;
  maxSize?: number; // MB
  className?: string;
  label?: string;
}

export function FileUpload({
  onUpload,
  accept = "image/*,video/*",
  multiple = false,
  maxSize = 50,
  className = "",
  label = "ファイルをアップロード",
}: FileUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      if (!files || files.length === 0) return;

      setError(null);
      setUploading(true);

      const formData = new FormData();
      const filesToUpload = multiple ? Array.from(files) : [files[0]];

      // サイズチェック
      for (const file of filesToUpload) {
        if (file.size > maxSize * 1024 * 1024) {
          setError(`ファイルサイズは${maxSize}MB以下にしてください`);
          setUploading(false);
          return;
        }
      }

      try {
        const token = getAccessToken();
        const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

        if (multiple && filesToUpload.length > 1) {
          // 複数ファイルアップロード
          for (const file of filesToUpload) {
            formData.append("files", file);
          }

          const response = await fetch(`${baseUrl}/core/upload/multiple/`, {
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
          for (const file of data.files) {
            onUpload(file);
          }
        } else {
          // 単一ファイルアップロード
          formData.append("file", filesToUpload[0]);

          const response = await fetch(`${baseUrl}/core/upload/`, {
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
          onUpload(data);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "アップロードに失敗しました");
      } finally {
        setUploading(false);
        if (inputRef.current) {
          inputRef.current.value = "";
        }
      }
    },
    [multiple, maxSize, onUpload]
  );

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);
      handleFiles(e.dataTransfer.files);
    },
    [handleFiles]
  );

  return (
    <div className={className}>
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`
          border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors
          ${dragActive ? "border-blue-500 bg-blue-50" : "border-gray-300 hover:border-gray-400"}
          ${uploading ? "opacity-50 pointer-events-none" : ""}
        `}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={(e) => handleFiles(e.target.files)}
          className="hidden"
        />

        {uploading ? (
          <div className="flex flex-col items-center gap-2">
            <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
            <span className="text-sm text-gray-600">アップロード中...</span>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <div className="flex items-center gap-2 text-gray-400">
              <ImageIcon className="w-6 h-6" />
              <Film className="w-6 h-6" />
            </div>
            <Upload className="w-8 h-8 text-gray-400" />
            <span className="text-sm text-gray-600">{label}</span>
            <span className="text-xs text-gray-400">
              ドラッグ＆ドロップまたはクリック（最大{maxSize}MB）
            </span>
          </div>
        )}
      </div>

      {error && (
        <p className="mt-2 text-sm text-red-500">{error}</p>
      )}
    </div>
  );
}

interface FilePreviewProps {
  url: string;
  type: "image" | "video";
  filename?: string;
  onRemove?: () => void;
  className?: string;
}

export function FilePreview({
  url,
  type,
  filename,
  onRemove,
  className = "",
}: FilePreviewProps) {
  return (
    <div className={`relative inline-block ${className}`}>
      {type === "image" ? (
        <img
          src={url}
          alt={filename || "画像"}
          className="w-24 h-24 object-cover rounded border"
        />
      ) : (
        <video
          src={url}
          className="w-24 h-24 object-cover rounded border"
          controls={false}
        />
      )}
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 hover:bg-red-600"
        >
          <X className="w-3 h-3" />
        </button>
      )}
      {filename && (
        <p className="text-xs text-gray-500 truncate mt-1 max-w-24">{filename}</p>
      )}
    </div>
  );
}
