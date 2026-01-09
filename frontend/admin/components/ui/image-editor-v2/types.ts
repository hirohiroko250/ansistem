/**
 * ImageEditorV2 - Type Definitions
 */

// Main editor props
export interface ImageEditorV2Props {
  file?: File;
  initialImageUrl?: string;
  onSave: (editedFile: File) => void;
  onCancel: () => void;
  aspectRatio?: number;
  maxOutputSize?: number;
  enableFilters?: boolean;
  enableTextOverlay?: boolean;
}

// Crop state
export interface CropState {
  position: { x: number; y: number };
  scale: number;
}

// Filter state
export interface FilterState {
  brightness: number;  // 0-200, default 100
  contrast: number;    // 0-200, default 100
  saturation: number;  // 0-200, default 100
}

// Text overlay
export interface TextOverlay {
  id: string;
  text: string;
  position: { x: number; y: number };
  fontSize: number;
  fontFamily: string;
  color: string;
  textAlign: 'left' | 'center' | 'right';
  fontWeight: 'normal' | 'bold';
}

// Editor tab types
export type EditorTab = 'crop' | 'adjust' | 'text';

// Default values
export const DEFAULT_CROP_STATE: CropState = {
  position: { x: 0, y: 0 },
  scale: 1,
};

export const DEFAULT_FILTER_STATE: FilterState = {
  brightness: 100,
  contrast: 100,
  saturation: 100,
};

export const DEFAULT_TEXT_OVERLAY: Omit<TextOverlay, 'id'> = {
  text: 'テキスト',
  position: { x: 0.5, y: 0.5 },
  fontSize: 24,
  fontFamily: 'sans-serif',
  color: '#ffffff',
  textAlign: 'center',
  fontWeight: 'normal',
};
