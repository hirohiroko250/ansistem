'use client';

import { Slider } from '@/components/ui/slider';
import { Button } from '@/components/ui/button';
import { RotateCcw, Sun, Contrast, Droplets } from 'lucide-react';
import { FilterState, DEFAULT_FILTER_STATE } from './types';

interface FilterPanelProps {
  filterState: FilterState;
  onChange: (state: FilterState) => void;
}

export function FilterPanel({ filterState, onChange }: FilterPanelProps) {
  const handleBrightnessChange = (value: number[]) => {
    onChange({ ...filterState, brightness: value[0] });
  };

  const handleContrastChange = (value: number[]) => {
    onChange({ ...filterState, contrast: value[0] });
  };

  const handleSaturationChange = (value: number[]) => {
    onChange({ ...filterState, saturation: value[0] });
  };

  const handleReset = () => {
    onChange(DEFAULT_FILTER_STATE);
  };

  return (
    <div className="space-y-5">
      {/* Brightness */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sun className="h-4 w-4 text-yellow-500" />
            <span className="text-sm font-medium">明るさ</span>
          </div>
          <span className="text-sm text-gray-500">{filterState.brightness - 100}</span>
        </div>
        <Slider
          value={[filterState.brightness]}
          onValueChange={handleBrightnessChange}
          min={0}
          max={200}
          step={1}
        />
      </div>

      {/* Contrast */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Contrast className="h-4 w-4 text-gray-500" />
            <span className="text-sm font-medium">コントラスト</span>
          </div>
          <span className="text-sm text-gray-500">{filterState.contrast - 100}</span>
        </div>
        <Slider
          value={[filterState.contrast]}
          onValueChange={handleContrastChange}
          min={0}
          max={200}
          step={1}
        />
      </div>

      {/* Saturation */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Droplets className="h-4 w-4 text-blue-500" />
            <span className="text-sm font-medium">彩度</span>
          </div>
          <span className="text-sm text-gray-500">{filterState.saturation - 100}</span>
        </div>
        <Slider
          value={[filterState.saturation]}
          onValueChange={handleSaturationChange}
          min={0}
          max={200}
          step={1}
        />
      </div>

      <div className="flex justify-center pt-2">
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
