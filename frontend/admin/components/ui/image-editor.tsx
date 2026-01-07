"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Label } from "@/components/ui/label";
import { X, RotateCw, ZoomIn, ZoomOut, Check } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";

interface ImageEditorProps {
  file: File;
  onSave: (editedFile: File) => void;
  onCancel: () => void;
  aspectRatio?: number; // 例: 1 = 正方形, 16/9 = ワイド
  maxWidth?: number;
  maxHeight?: number;
}

export function ImageEditor({
  file,
  onSave,
  onCancel,
  aspectRatio,
  maxWidth = 1200,
  maxHeight = 1200,
}: ImageEditorProps) {
  const [imageUrl, setImageUrl] = useState<string>("");
  const [scale, setScale] = useState(100);
  const [rotation, setRotation] = useState(0);
  const [processing, setProcessing] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imageRef = useRef<HTMLImageElement | null>(null);

  useEffect(() => {
    const url = URL.createObjectURL(file);
    setImageUrl(url);

    const img = new Image();
    img.onload = () => {
      imageRef.current = img;
    };
    img.src = url;

    return () => {
      URL.revokeObjectURL(url);
    };
  }, [file]);

  const handleRotate = () => {
    setRotation((prev) => (prev + 90) % 360);
  };

  const processImage = useCallback(async () => {
    if (!imageRef.current || !canvasRef.current) return null;

    setProcessing(true);

    const img = imageRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;

    // 回転を考慮したサイズ計算
    const isRotated = rotation === 90 || rotation === 270;
    let srcWidth = img.width;
    let srcHeight = img.height;

    if (isRotated) {
      [srcWidth, srcHeight] = [srcHeight, srcWidth];
    }

    // スケールを適用
    let targetWidth = Math.round(srcWidth * (scale / 100));
    let targetHeight = Math.round(srcHeight * (scale / 100));

    // 最大サイズを超えないように調整
    if (targetWidth > maxWidth) {
      const ratio = maxWidth / targetWidth;
      targetWidth = maxWidth;
      targetHeight = Math.round(targetHeight * ratio);
    }
    if (targetHeight > maxHeight) {
      const ratio = maxHeight / targetHeight;
      targetHeight = maxHeight;
      targetWidth = Math.round(targetWidth * ratio);
    }

    // アスペクト比が指定されている場合
    if (aspectRatio) {
      const currentRatio = targetWidth / targetHeight;
      if (currentRatio > aspectRatio) {
        targetWidth = Math.round(targetHeight * aspectRatio);
      } else {
        targetHeight = Math.round(targetWidth / aspectRatio);
      }
    }

    canvas.width = targetWidth;
    canvas.height = targetHeight;

    // キャンバスをクリア
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, targetWidth, targetHeight);

    // 回転の中心を設定
    ctx.save();
    ctx.translate(targetWidth / 2, targetHeight / 2);
    ctx.rotate((rotation * Math.PI) / 180);

    // 回転後の描画サイズ
    let drawWidth = targetWidth;
    let drawHeight = targetHeight;
    if (isRotated) {
      [drawWidth, drawHeight] = [drawHeight, drawWidth];
    }

    ctx.drawImage(img, -drawWidth / 2, -drawHeight / 2, drawWidth, drawHeight);
    ctx.restore();

    return new Promise<File>((resolve) => {
      canvas.toBlob(
        (blob) => {
          if (blob) {
            const editedFile = new File([blob], file.name, {
              type: "image/jpeg",
              lastModified: Date.now(),
            });
            resolve(editedFile);
          }
        },
        "image/jpeg",
        0.9
      );
    });
  }, [scale, rotation, aspectRatio, maxWidth, maxHeight, file.name]);

  const handleSave = async () => {
    const editedFile = await processImage();
    if (editedFile) {
      onSave(editedFile);
    }
    setProcessing(false);
  };

  return (
    <Dialog open={true} onOpenChange={() => onCancel()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>画像を編集</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* プレビュー */}
          <div className="flex justify-center bg-gray-100 rounded-lg p-4 min-h-[300px] items-center">
            {imageUrl && (
              <img
                src={imageUrl}
                alt="プレビュー"
                style={{
                  maxWidth: "100%",
                  maxHeight: "300px",
                  transform: `scale(${scale / 100}) rotate(${rotation}deg)`,
                  transition: "transform 0.2s",
                }}
              />
            )}
          </div>

          {/* 非表示のキャンバス（処理用） */}
          <canvas ref={canvasRef} style={{ display: "none" }} />

          {/* コントロール */}
          <div className="space-y-4">
            {/* サイズ調整 */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>サイズ: {scale}%</Label>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setScale((s) => Math.max(10, s - 10))}
                  >
                    <ZoomOut className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setScale((s) => Math.min(200, s + 10))}
                  >
                    <ZoomIn className="w-4 h-4" />
                  </Button>
                </div>
              </div>
              <Slider
                value={[scale]}
                onValueChange={([v]) => setScale(v)}
                min={10}
                max={200}
                step={5}
              />
            </div>

            {/* 回転 */}
            <div className="flex items-center justify-between">
              <Label>回転: {rotation}°</Label>
              <Button variant="outline" size="sm" onClick={handleRotate}>
                <RotateCw className="w-4 h-4 mr-1" />
                90°回転
              </Button>
            </div>

            {/* プリセットサイズ */}
            <div className="flex gap-2 flex-wrap">
              <Label className="w-full text-sm text-gray-500">クイックサイズ:</Label>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setScale(100)}
              >
                原寸
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setScale(75)}
              >
                75%
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setScale(50)}
              >
                50%
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setScale(25)}
              >
                25%
              </Button>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onCancel}>
            <X className="w-4 h-4 mr-1" />
            キャンセル
          </Button>
          <Button onClick={handleSave} disabled={processing}>
            <Check className="w-4 h-4 mr-1" />
            {processing ? "処理中..." : "適用"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
