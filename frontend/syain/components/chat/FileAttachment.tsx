'use client';

import { useState, useRef, useCallback, DragEvent, ChangeEvent } from 'react';
import { X, Upload, File, Image as ImageIcon, FileText, Loader2, Download } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  isAllowedFile,
  isImageFile,
  formatFileSize,
  MAX_FILE_SIZE,
  ALLOWED_FILE_EXTENSIONS,
  type FileUploadProgress,
} from '@/lib/api/chat';

interface FilePreview {
  file: File;
  previewUrl?: string;
  isImage: boolean;
}

interface FileAttachmentInputProps {
  onFileSelect: (file: File) => void;
  disabled?: boolean;
  className?: string;
}

/**
 * ファイル選択ボタン（+ボタンに統合用）
 */
export function FileAttachmentInput({
  onFileSelect,
  disabled = false,
  className = '',
}: FileAttachmentInputProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleClick = () => {
    inputRef.current?.click();
  };

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!isAllowedFile(file.name)) {
        alert(`許可されていないファイル形式です。\n対応形式: ${[...ALLOWED_FILE_EXTENSIONS.images, ...ALLOWED_FILE_EXTENSIONS.documents].join(', ')}`);
        return;
      }
      if (file.size > MAX_FILE_SIZE) {
        alert(`ファイルサイズが大きすぎます。最大${formatFileSize(MAX_FILE_SIZE)}までです。`);
        return;
      }
      onFileSelect(file);
    }
    // 同じファイルを再選択できるようにリセット
    e.target.value = '';
  };

  const acceptTypes = [...ALLOWED_FILE_EXTENSIONS.images, ...ALLOWED_FILE_EXTENSIONS.documents].join(',');

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept={acceptTypes}
        onChange={handleChange}
        className="hidden"
        disabled={disabled}
      />
      <button
        type="button"
        onClick={handleClick}
        disabled={disabled}
        className={`p-2 text-gray-500 hover:text-gray-700 disabled:opacity-50 ${className}`}
        title="ファイルを添付"
      >
        <Upload className="w-6 h-6" />
      </button>
    </>
  );
}

interface FilePreviewPanelProps {
  file: File;
  uploadProgress?: FileUploadProgress | null;
  onCancel: () => void;
  onUpload: () => void;
  isUploading: boolean;
}

/**
 * ファイルプレビューパネル（アップロード前確認用）
 */
export function FilePreviewPanel({
  file,
  uploadProgress,
  onCancel,
  onUpload,
  isUploading,
}: FilePreviewPanelProps) {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const isImage = isImageFile(file.name);

  // 画像プレビューを生成
  useState(() => {
    if (isImage) {
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
      return () => URL.revokeObjectURL(url);
    }
  });

  return (
    <div className="absolute bottom-full left-0 right-0 mb-2 mx-2 bg-white rounded-lg shadow-lg border border-gray-200 p-3">
      <div className="flex items-start gap-3">
        {/* プレビュー */}
        <div className="flex-shrink-0 w-16 h-16 bg-gray-100 rounded-lg overflow-hidden flex items-center justify-center">
          {isImage && previewUrl ? (
            <img
              src={previewUrl}
              alt={file.name}
              className="w-full h-full object-cover"
            />
          ) : (
            <FileText className="w-8 h-8 text-gray-400" />
          )}
        </div>

        {/* ファイル情報 */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate">{file.name}</p>
          <p className="text-xs text-gray-500">{formatFileSize(file.size)}</p>

          {/* アップロード進捗 */}
          {isUploading && uploadProgress && (
            <div className="mt-2">
              <div className="h-1.5 w-full bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-600 transition-all"
                  style={{ width: `${uploadProgress.percentage}%` }}
                />
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {uploadProgress.percentage}% アップロード中...
              </p>
            </div>
          )}
        </div>

        {/* アクションボタン */}
        <div className="flex-shrink-0 flex items-center gap-2">
          {!isUploading ? (
            <>
              <Button
                size="sm"
                variant="outline"
                onClick={onCancel}
              >
                <X className="w-4 h-4" />
              </Button>
              <Button
                size="sm"
                onClick={onUpload}
                className="bg-blue-600 hover:bg-blue-700"
              >
                送信
              </Button>
            </>
          ) : (
            <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
          )}
        </div>
      </div>
    </div>
  );
}

interface AttachmentDisplayProps {
  attachmentUrl: string;
  attachmentName: string;
  messageType: string;
  isOwnMessage?: boolean;
}

/**
 * メッセージ内の添付ファイル表示
 */
export function AttachmentDisplay({
  attachmentUrl,
  attachmentName,
  messageType,
  isOwnMessage = false,
}: AttachmentDisplayProps) {
  const isImage = messageType === 'IMAGE' || isImageFile(attachmentName);
  const [imageError, setImageError] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);

  // 画像の場合
  if (isImage && !imageError) {
    return (
      <div className="mt-2">
        <div
          className="relative cursor-pointer group"
          onClick={() => setIsExpanded(true)}
        >
          <img
            src={attachmentUrl}
            alt={attachmentName}
            className="max-w-[240px] max-h-[180px] rounded-lg object-cover"
            onError={() => setImageError(true)}
          />
          <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 rounded-lg transition-colors" />
        </div>

        {/* 拡大表示モーダル */}
        {isExpanded && (
          <div
            className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4"
            onClick={() => setIsExpanded(false)}
          >
            <div className="relative max-w-[90vw] max-h-[90vh]">
              <img
                src={attachmentUrl}
                alt={attachmentName}
                className="max-w-full max-h-[90vh] object-contain rounded-lg"
              />
              <button
                onClick={() => setIsExpanded(false)}
                className="absolute top-2 right-2 p-2 bg-black/50 hover:bg-black/70 rounded-full text-white"
              >
                <X className="w-5 h-5" />
              </button>
              <a
                href={attachmentUrl}
                download={attachmentName}
                onClick={(e) => e.stopPropagation()}
                className="absolute bottom-2 right-2 p-2 bg-black/50 hover:bg-black/70 rounded-full text-white"
              >
                <Download className="w-5 h-5" />
              </a>
            </div>
          </div>
        )}
      </div>
    );
  }

  // ファイルの場合
  return (
    <a
      href={attachmentUrl}
      download={attachmentName}
      className={`mt-2 flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
        isOwnMessage
          ? 'bg-green-600/20 hover:bg-green-600/30'
          : 'bg-gray-100 hover:bg-gray-200'
      }`}
      onClick={(e) => e.stopPropagation()}
    >
      <FileText className={`w-5 h-5 flex-shrink-0 ${isOwnMessage ? 'text-green-800' : 'text-gray-600'}`} />
      <span className={`text-sm truncate ${isOwnMessage ? 'text-green-900' : 'text-gray-700'}`}>
        {attachmentName}
      </span>
      <Download className={`w-4 h-4 flex-shrink-0 ml-auto ${isOwnMessage ? 'text-green-700' : 'text-gray-500'}`} />
    </a>
  );
}

interface DragDropZoneProps {
  onFileDrop: (file: File) => void;
  children: React.ReactNode;
  disabled?: boolean;
}

/**
 * ドラッグ&ドロップゾーン
 */
export function DragDropZone({
  onFileDrop,
  children,
  disabled = false,
}: DragDropZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (!disabled) {
      setIsDragOver(true);
    }
  }, [disabled]);

  const handleDragLeave = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);

    if (disabled) return;

    const file = e.dataTransfer.files?.[0];
    if (file) {
      if (!isAllowedFile(file.name)) {
        alert(`許可されていないファイル形式です。\n対応形式: ${[...ALLOWED_FILE_EXTENSIONS.images, ...ALLOWED_FILE_EXTENSIONS.documents].join(', ')}`);
        return;
      }
      if (file.size > MAX_FILE_SIZE) {
        alert(`ファイルサイズが大きすぎます。最大${formatFileSize(MAX_FILE_SIZE)}までです。`);
        return;
      }
      onFileDrop(file);
    }
  }, [disabled, onFileDrop]);

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className="relative"
    >
      {children}

      {/* ドラッグオーバー時のオーバーレイ */}
      {isDragOver && (
        <div className="absolute inset-0 bg-blue-500/20 border-2 border-dashed border-blue-500 rounded-lg flex items-center justify-center z-10">
          <div className="bg-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-2">
            <Upload className="w-5 h-5 text-blue-600" />
            <span className="text-blue-600 font-medium">ファイルをドロップ</span>
          </div>
        </div>
      )}
    </div>
  );
}
