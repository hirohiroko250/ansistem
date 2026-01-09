'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Crop, Sliders, Type, Loader2 } from 'lucide-react';
import { CropTool } from './CropTool';
import { FilterPanel } from './FilterPanel';
import { TextOverlayTool } from './TextOverlayTool';
import {
  ImageEditorV2Props,
  EditorTab,
  CropState,
  FilterState,
  TextOverlay,
  DEFAULT_CROP_STATE,
  DEFAULT_FILTER_STATE,
  DEFAULT_TEXT_OVERLAY,
} from './types';

const PREVIEW_SIZE = 400;
const OUTPUT_SIZE = 1200;

export function ImageEditorV2({
  file,
  initialImageUrl,
  onSave,
  onCancel,
  maxOutputSize = OUTPUT_SIZE,
}: ImageEditorV2Props) {
  const [activeTab, setActiveTab] = useState<EditorTab>('crop');
  const [cropState, setCropState] = useState<CropState>(DEFAULT_CROP_STATE);
  const [filterState, setFilterState] = useState<FilterState>(DEFAULT_FILTER_STATE);
  const [textOverlays, setTextOverlays] = useState<TextOverlay[]>([]);
  const [selectedTextId, setSelectedTextId] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [imageLoaded, setImageLoaded] = useState(false);

  const previewCanvasRef = useRef<HTMLCanvasElement>(null);
  const outputCanvasRef = useRef<HTMLCanvasElement>(null);
  const imageRef = useRef<HTMLImageElement | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Drag state
  const isDraggingRef = useRef(false);
  const dragStartRef = useRef({ x: 0, y: 0 });
  const dragTargetRef = useRef<'image' | 'text' | null>(null);

  // Load image
  useEffect(() => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      imageRef.current = img;
      setImageLoaded(true);

      // Initialize crop position to center the image
      const imgAspect = img.width / img.height;
      let initialScale = 1;

      if (imgAspect > 1) {
        // Landscape - fit height
        initialScale = PREVIEW_SIZE / img.height;
      } else {
        // Portrait - fit width
        initialScale = PREVIEW_SIZE / img.width;
      }

      const scaledWidth = img.width * initialScale;
      const scaledHeight = img.height * initialScale;

      setCropState({
        position: {
          x: (PREVIEW_SIZE - scaledWidth) / 2,
          y: (PREVIEW_SIZE - scaledHeight) / 2,
        },
        scale: initialScale,
      });
    };
    img.onerror = () => {
      console.error('Failed to load image');
    };

    // Use initialImageUrl if provided, otherwise create blob URL from file
    const imageSource = initialImageUrl || (file ? URL.createObjectURL(file) : null);
    if (!imageSource) {
      console.error('No image source provided');
      return;
    }
    img.src = imageSource;

    return () => {
      if (!initialImageUrl && file && img.src) {
        URL.revokeObjectURL(img.src);
      }
    };
  }, [file, initialImageUrl]);

  // Render preview
  const renderPreview = useCallback(() => {
    const canvas = previewCanvasRef.current;
    const img = imageRef.current;
    if (!canvas || !img) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, PREVIEW_SIZE, PREVIEW_SIZE);

    // Apply filters
    ctx.filter = `
      brightness(${filterState.brightness}%)
      contrast(${filterState.contrast}%)
      saturate(${filterState.saturation}%)
    `;

    // Draw image with crop
    const { position, scale } = cropState;
    const scaledWidth = img.width * scale;
    const scaledHeight = img.height * scale;

    ctx.drawImage(img, position.x, position.y, scaledWidth, scaledHeight);

    // Reset filter for text
    ctx.filter = 'none';

    // Draw text overlays
    textOverlays.forEach((overlay) => {
      const x = overlay.position.x * PREVIEW_SIZE;
      const y = overlay.position.y * PREVIEW_SIZE;

      ctx.save();
      ctx.font = `${overlay.fontWeight} ${overlay.fontSize}px ${overlay.fontFamily}`;
      ctx.fillStyle = overlay.color;
      ctx.textAlign = overlay.textAlign;
      ctx.textBaseline = 'middle';

      // Text shadow for better visibility
      ctx.shadowColor = 'rgba(0, 0, 0, 0.5)';
      ctx.shadowBlur = 4;
      ctx.shadowOffsetX = 1;
      ctx.shadowOffsetY = 1;

      ctx.fillText(overlay.text, x, y);
      ctx.restore();

      // Draw selection box if selected
      if (overlay.id === selectedTextId) {
        const metrics = ctx.measureText(overlay.text);
        const textWidth = metrics.width;
        const textHeight = overlay.fontSize;

        let boxX = x;
        if (overlay.textAlign === 'center') boxX = x - textWidth / 2;
        else if (overlay.textAlign === 'right') boxX = x - textWidth;

        ctx.strokeStyle = '#3b82f6';
        ctx.lineWidth = 2;
        ctx.setLineDash([4, 4]);
        ctx.strokeRect(boxX - 4, y - textHeight / 2 - 4, textWidth + 8, textHeight + 8);
        ctx.setLineDash([]);
      }
    });
  }, [cropState, filterState, textOverlays, selectedTextId]);

  // Re-render on state change
  useEffect(() => {
    if (imageLoaded) {
      renderPreview();
    }
  }, [imageLoaded, renderPreview]);

  // Handle mouse/touch events for dragging
  const handlePointerDown = (e: React.PointerEvent) => {
    const canvas = previewCanvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) * (PREVIEW_SIZE / rect.width);
    const y = (e.clientY - rect.top) * (PREVIEW_SIZE / rect.height);

    // Check if clicking on text (only in text tab)
    if (activeTab === 'text') {
      const clickedText = textOverlays.find((overlay) => {
        const ctx = canvas.getContext('2d');
        if (!ctx) return false;

        ctx.font = `${overlay.fontWeight} ${overlay.fontSize}px ${overlay.fontFamily}`;
        const metrics = ctx.measureText(overlay.text);
        const textWidth = metrics.width;
        const textHeight = overlay.fontSize;

        const textX = overlay.position.x * PREVIEW_SIZE;
        const textY = overlay.position.y * PREVIEW_SIZE;

        let boxX = textX;
        if (overlay.textAlign === 'center') boxX = textX - textWidth / 2;
        else if (overlay.textAlign === 'right') boxX = textX - textWidth;

        return (
          x >= boxX - 4 &&
          x <= boxX + textWidth + 4 &&
          y >= textY - textHeight / 2 - 4 &&
          y <= textY + textHeight / 2 + 4
        );
      });

      if (clickedText) {
        setSelectedTextId(clickedText.id);
        dragTargetRef.current = 'text';
        isDraggingRef.current = true;
        dragStartRef.current = { x, y };
        canvas.setPointerCapture(e.pointerId);
        return;
      }
    }

    // Drag image in crop mode
    if (activeTab === 'crop') {
      dragTargetRef.current = 'image';
      isDraggingRef.current = true;
      dragStartRef.current = { x, y };
      canvas.setPointerCapture(e.pointerId);
    }
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!isDraggingRef.current) return;

    const canvas = previewCanvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) * (PREVIEW_SIZE / rect.width);
    const y = (e.clientY - rect.top) * (PREVIEW_SIZE / rect.height);

    const deltaX = x - dragStartRef.current.x;
    const deltaY = y - dragStartRef.current.y;

    if (dragTargetRef.current === 'image') {
      setCropState((prev) => ({
        ...prev,
        position: {
          x: prev.position.x + deltaX,
          y: prev.position.y + deltaY,
        },
      }));
    } else if (dragTargetRef.current === 'text' && selectedTextId) {
      setTextOverlays((prev) =>
        prev.map((overlay) =>
          overlay.id === selectedTextId
            ? {
                ...overlay,
                position: {
                  x: Math.max(0, Math.min(1, overlay.position.x + deltaX / PREVIEW_SIZE)),
                  y: Math.max(0, Math.min(1, overlay.position.y + deltaY / PREVIEW_SIZE)),
                },
              }
            : overlay
        )
      );
    }

    dragStartRef.current = { x, y };
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    isDraggingRef.current = false;
    dragTargetRef.current = null;
    previewCanvasRef.current?.releasePointerCapture(e.pointerId);
  };

  // Add text overlay
  const handleAddText = () => {
    const newOverlay: TextOverlay = {
      ...DEFAULT_TEXT_OVERLAY,
      id: `text-${Date.now()}`,
    };
    setTextOverlays((prev) => [...prev, newOverlay]);
    setSelectedTextId(newOverlay.id);
  };

  // Update text overlay
  const handleUpdateText = (id: string, updates: Partial<TextOverlay>) => {
    setTextOverlays((prev) =>
      prev.map((overlay) => (overlay.id === id ? { ...overlay, ...updates } : overlay))
    );
  };

  // Remove text overlay
  const handleRemoveText = (id: string) => {
    setTextOverlays((prev) => prev.filter((overlay) => overlay.id !== id));
    if (selectedTextId === id) {
      setSelectedTextId(null);
    }
  };

  // Export to file
  const handleSave = async () => {
    const canvas = outputCanvasRef.current;
    const img = imageRef.current;
    if (!canvas || !img) return;

    setIsProcessing(true);

    try {
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      // Set output size
      canvas.width = maxOutputSize;
      canvas.height = maxOutputSize;

      // Calculate scale factor for output
      const outputScale = maxOutputSize / PREVIEW_SIZE;

      // Clear canvas
      ctx.clearRect(0, 0, maxOutputSize, maxOutputSize);

      // Apply filters
      ctx.filter = `
        brightness(${filterState.brightness}%)
        contrast(${filterState.contrast}%)
        saturate(${filterState.saturation}%)
      `;

      // Draw image scaled for output
      const { position, scale } = cropState;
      ctx.drawImage(
        img,
        position.x * outputScale,
        position.y * outputScale,
        img.width * scale * outputScale,
        img.height * scale * outputScale
      );

      // Reset filter for text
      ctx.filter = 'none';

      // Draw text overlays scaled for output
      textOverlays.forEach((overlay) => {
        const x = overlay.position.x * maxOutputSize;
        const y = overlay.position.y * maxOutputSize;
        const fontSize = overlay.fontSize * outputScale;

        ctx.save();
        ctx.font = `${overlay.fontWeight} ${fontSize}px ${overlay.fontFamily}`;
        ctx.fillStyle = overlay.color;
        ctx.textAlign = overlay.textAlign;
        ctx.textBaseline = 'middle';

        // Text shadow
        ctx.shadowColor = 'rgba(0, 0, 0, 0.5)';
        ctx.shadowBlur = 4 * outputScale;
        ctx.shadowOffsetX = 1 * outputScale;
        ctx.shadowOffsetY = 1 * outputScale;

        ctx.fillText(overlay.text, x, y);
        ctx.restore();
      });

      // Convert to blob
      canvas.toBlob(
        (blob) => {
          if (blob) {
            const fileName = file?.name || 'edited-image.jpg';
            const editedFile = new File([blob], fileName.replace(/\.[^.]+$/, '.jpg'), {
              type: 'image/jpeg',
            });
            onSave(editedFile);
          }
          setIsProcessing(false);
        },
        'image/jpeg',
        0.9
      );
    } catch (error) {
      console.error('Failed to process image:', error);
      setIsProcessing(false);
    }
  };

  return (
    <Dialog open={true} onOpenChange={() => onCancel()}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>画像を編集</DialogTitle>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as EditorTab)}>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="crop" className="gap-2">
              <Crop className="h-4 w-4" />
              切り抜き
            </TabsTrigger>
            <TabsTrigger value="adjust" className="gap-2">
              <Sliders className="h-4 w-4" />
              調整
            </TabsTrigger>
            <TabsTrigger value="text" className="gap-2">
              <Type className="h-4 w-4" />
              テキスト
            </TabsTrigger>
          </TabsList>

          {/* Preview Canvas */}
          <div
            ref={containerRef}
            className="relative aspect-square bg-gray-900 rounded-lg overflow-hidden my-4"
          >
            {!imageLoaded && (
              <div className="absolute inset-0 flex items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-white" />
              </div>
            )}
            <canvas
              ref={previewCanvasRef}
              width={PREVIEW_SIZE}
              height={PREVIEW_SIZE}
              className="w-full h-full cursor-move"
              onPointerDown={handlePointerDown}
              onPointerMove={handlePointerMove}
              onPointerUp={handlePointerUp}
              onPointerLeave={handlePointerUp}
            />
          </div>

          <TabsContent value="crop" className="mt-0">
            <CropTool cropState={cropState} onChange={setCropState} />
          </TabsContent>

          <TabsContent value="adjust" className="mt-0">
            <FilterPanel filterState={filterState} onChange={setFilterState} />
          </TabsContent>

          <TabsContent value="text" className="mt-0">
            <TextOverlayTool
              overlays={textOverlays}
              selectedId={selectedTextId}
              onAdd={handleAddText}
              onUpdate={handleUpdateText}
              onRemove={handleRemoveText}
              onSelect={setSelectedTextId}
            />
          </TabsContent>
        </Tabs>

        <DialogFooter>
          <Button variant="outline" onClick={onCancel} disabled={isProcessing}>
            キャンセル
          </Button>
          <Button onClick={handleSave} disabled={isProcessing || !imageLoaded}>
            {isProcessing ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                処理中...
              </>
            ) : (
              '適用'
            )}
          </Button>
        </DialogFooter>

        {/* Hidden output canvas */}
        <canvas ref={outputCanvasRef} style={{ display: 'none' }} />
      </DialogContent>
    </Dialog>
  );
}
