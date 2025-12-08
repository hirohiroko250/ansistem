'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { MapPin, Loader2 } from 'lucide-react';
import type { BrandSchool } from '@/lib/api/schools';

// Google Maps APIキーを環境変数から取得
const GOOGLE_MAPS_API_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || '';

interface GoogleMapSchoolSelectorProps {
  schools: BrandSchool[];
  selectedSchoolId: string | null;
  onSelectSchool: (schoolId: string) => void;
  brandColor?: string;
  isLoading?: boolean;
}

// Google Maps APIを動的に読み込む
let googleMapsPromise: Promise<void> | null = null;

function loadGoogleMapsAPI(): Promise<void> {
  if (googleMapsPromise) return googleMapsPromise;

  if (!GOOGLE_MAPS_API_KEY) {
    return Promise.reject(new Error('Google Maps API key is not configured'));
  }

  googleMapsPromise = new Promise((resolve, reject) => {
    if (window.google?.maps) {
      resolve();
      return;
    }

    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=${GOOGLE_MAPS_API_KEY}&libraries=places`;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Failed to load Google Maps API'));
    document.head.appendChild(script);
  });

  return googleMapsPromise;
}

declare global {
  interface Window {
    google?: {
      maps: typeof google.maps;
    };
  }
}

export function GoogleMapSchoolSelector({
  schools,
  selectedSchoolId,
  onSelectSchool,
  brandColor = '#3B82F6',
  isLoading = false,
}: GoogleMapSchoolSelectorProps) {
  const [mapLoaded, setMapLoaded] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);
  const [map, setMap] = useState<google.maps.Map | null>(null);
  const [markers, setMarkers] = useState<google.maps.Marker[]>([]);
  const [infoWindow, setInfoWindow] = useState<google.maps.InfoWindow | null>(null);

  // 校舎の中心位置を計算
  const getCenter = useCallback(() => {
    const schoolsWithLocation = schools.filter(s => s.latitude && s.longitude);
    if (schoolsWithLocation.length === 0) {
      // デフォルト: 名古屋市中心
      return { lat: 35.1815, lng: 136.9066 };
    }

    const avgLat = schoolsWithLocation.reduce((sum, s) => sum + (s.latitude || 0), 0) / schoolsWithLocation.length;
    const avgLng = schoolsWithLocation.reduce((sum, s) => sum + (s.longitude || 0), 0) / schoolsWithLocation.length;
    return { lat: avgLat, lng: avgLng };
  }, [schools]);

  // Google Maps APIを読み込む
  useEffect(() => {
    if (!GOOGLE_MAPS_API_KEY) {
      setMapError('Google Maps APIキーが設定されていません');
      return;
    }

    loadGoogleMapsAPI()
      .then(() => setMapLoaded(true))
      .catch((err) => setMapError(err.message));
  }, []);

  // マップを初期化
  useEffect(() => {
    if (!mapLoaded || !window.google?.maps) return;

    const mapElement = document.getElementById('school-map');
    if (!mapElement) return;

    const newMap = new window.google.maps.Map(mapElement, {
      center: getCenter(),
      zoom: 11,
      styles: [
        {
          featureType: 'poi',
          elementType: 'labels',
          stylers: [{ visibility: 'off' }],
        },
      ],
      mapTypeControl: false,
      streetViewControl: false,
      fullscreenControl: false,
    });

    const newInfoWindow = new window.google.maps.InfoWindow();
    setMap(newMap);
    setInfoWindow(newInfoWindow);

    return () => {
      newInfoWindow.close();
    };
  }, [mapLoaded, getCenter]);

  // マーカーを配置
  useEffect(() => {
    if (!map || !window.google?.maps || !infoWindow) return;

    // 既存のマーカーをクリア
    markers.forEach(marker => marker.setMap(null));

    const newMarkers: google.maps.Marker[] = [];

    schools.forEach((school) => {
      if (!school.latitude || !school.longitude) return;

      const isSelected = school.id === selectedSchoolId;

      const marker = new window.google.maps.Marker({
        position: { lat: school.latitude, lng: school.longitude },
        map,
        title: school.name,
        icon: {
          path: window.google.maps.SymbolPath.CIRCLE,
          fillColor: isSelected ? '#EF4444' : brandColor,
          fillOpacity: 1,
          strokeColor: '#FFFFFF',
          strokeWeight: 3,
          scale: isSelected ? 14 : 10,
        },
        animation: isSelected ? window.google.maps.Animation.BOUNCE : undefined,
      });

      marker.addListener('click', () => {
        onSelectSchool(school.id);

        const content = `
          <div style="padding: 8px; min-width: 200px;">
            <h3 style="font-weight: bold; font-size: 16px; margin-bottom: 4px;">${school.name}</h3>
            <p style="color: #666; font-size: 12px; margin-bottom: 4px;">${school.address}</p>
            ${school.phone ? `<p style="color: #666; font-size: 12px;">TEL: ${school.phone}</p>` : ''}
          </div>
        `;

        infoWindow.setContent(content);
        infoWindow.open(map, marker);
      });

      newMarkers.push(marker);
    });

    setMarkers(newMarkers);

    // マップを校舎に合わせてフィット
    if (newMarkers.length > 0) {
      const bounds = new window.google.maps.LatLngBounds();
      newMarkers.forEach(marker => {
        const pos = marker.getPosition();
        if (pos) bounds.extend(pos);
      });
      map.fitBounds(bounds);

      // ズームを適度に調整
      const listener = window.google.maps.event.addListener(map, 'idle', () => {
        const currentZoom = map.getZoom();
        if (currentZoom && currentZoom > 15) map.setZoom(15);
        window.google.maps.event.removeListener(listener);
      });
    }

    return () => {
      newMarkers.forEach(marker => marker.setMap(null));
    };
  }, [map, schools, selectedSchoolId, brandColor, infoWindow, onSelectSchool]);

  // ローディング中
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500 mb-3" />
        <p className="text-sm text-gray-600">校舎を読み込み中...</p>
      </div>
    );
  }

  // マップエラー時はリスト表示にフォールバック
  if (mapError || !GOOGLE_MAPS_API_KEY) {
    return (
      <div className="space-y-3">
        {schools.length === 0 ? (
          <p className="text-center text-gray-600 py-8">開講校舎がありません</p>
        ) : (
          schools.map((school) => (
            <Card
              key={school.id}
              className={`rounded-xl shadow-md cursor-pointer transition-all ${
                selectedSchoolId === school.id
                  ? 'border-2 border-blue-500 bg-blue-50'
                  : 'hover:shadow-lg'
              }`}
              onClick={() => onSelectSchool(school.id)}
            >
              <CardContent className="p-4">
                <div className="flex items-start gap-3">
                  <div
                    className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
                    style={{ backgroundColor: `${brandColor}20` }}
                  >
                    <MapPin className="h-5 w-5" style={{ color: brandColor }} />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-bold text-gray-800 mb-1">{school.name}</h3>
                    <p className="text-sm text-gray-600">{school.address}</p>
                    {school.phone && (
                      <p className="text-xs text-gray-500 mt-1">TEL: {school.phone}</p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    );
  }

  const selectedSchool = schools.find(s => s.id === selectedSchoolId);

  return (
    <div className="space-y-4">
      {/* マップ */}
      <Card className="rounded-xl shadow-md overflow-hidden">
        <div
          id="school-map"
          className="w-full h-64 md:h-80 bg-gray-100"
          style={{ minHeight: '256px' }}
        />
      </Card>

      {/* 選択中の校舎 */}
      {selectedSchool && (
        <Card className="rounded-xl shadow-md border-2 border-green-500 bg-green-50">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
                <MapPin className="h-5 w-5 text-green-600" />
              </div>
              <div className="flex-1">
                <p className="text-xs text-green-600 mb-1">選択中の校舎</p>
                <h3 className="font-bold text-gray-800">{selectedSchool.name}</h3>
                <p className="text-sm text-gray-600">{selectedSchool.address}</p>
                {selectedSchool.phone && (
                  <p className="text-xs text-gray-500 mt-1">TEL: {selectedSchool.phone}</p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 校舎リスト */}
      <div className="space-y-2">
        <p className="text-sm text-gray-600">校舎一覧（タップで選択）</p>
        {schools.map((school) => (
          <Card
            key={school.id}
            className={`rounded-xl shadow-sm cursor-pointer transition-all ${
              selectedSchoolId === school.id
                ? 'border-2 border-blue-500'
                : 'hover:shadow-md border border-gray-200'
            }`}
            onClick={() => {
              onSelectSchool(school.id);
              // マップの中心を移動
              if (map && school.latitude && school.longitude) {
                map.panTo({ lat: school.latitude, lng: school.longitude });
                map.setZoom(15);
              }
            }}
          >
            <CardContent className="p-3">
              <div className="flex items-center gap-2">
                <MapPin
                  className="h-4 w-4 flex-shrink-0"
                  style={{ color: selectedSchoolId === school.id ? '#3B82F6' : '#9CA3AF' }}
                />
                <span className={`text-sm ${selectedSchoolId === school.id ? 'font-semibold text-blue-700' : 'text-gray-700'}`}>
                  {school.name}
                </span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
