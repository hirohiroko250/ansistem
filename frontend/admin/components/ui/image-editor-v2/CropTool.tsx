'use client';

import { Slider } from '@/components/ui/slider';
import { Button } from '@/components/ui/button';
import { RotateCcw, ZoomIn, ZoomOut } from 'lucide-react';
import { CropState, DEFAULT_CROP_STATE } from './types';

interface CropToolProps {
  cropState: CropState;
  onChange: (state: CropState) => void;
}

export function CropTool({ cropState, onChange }: CropToolProps) {
  const handleScaleChange = (value: number[]) => {
    onChange({ ...cropState, scale: value[0] });
  };

  const handleReset = () => {
    onChange(DEFAULT_CROP_STATE);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <ZoomOut className="h-4 w-4 text-gray-500" />
        <Slider
          value={[cropState.scale]}
          onValueChange={handleScaleChange}
          min={0.5}
          max={3}
          step={0.1}
          className="flex-1"
        />
        <ZoomIn className="h-4 w-4 text-gray-500" />
        <span className="text-sm text-gray-600 w-12 text-right">
          {Math.round(cropState.scale * 100)}%
        </span>
      </div>

      <p className="text-sm text-gray-500 text-center">
        画像をドラッグして位置を調整できます
      </p>

      <div className="flex justify-center">
        <Button
          variant="outline"
          size="sm"
          onClick={handleReset}
          className="gap-2"
        >
          <RotateCcw className="h-4 w-4" />
          リセット
        </Button>
      </div>
    </div>
  );
}
