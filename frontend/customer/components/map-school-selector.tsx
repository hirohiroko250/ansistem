'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Loader2, Check } from 'lucide-react';
import type { BrandSchool } from '@/lib/api/schools';

interface MapSchoolSelectorProps {
  schools: BrandSchool[];
  selectedSchoolId: string | null;
  onSelectSchool: (schoolId: string) => void;
  brandColor?: string;
  isLoading?: boolean;
  initialSchoolId?: string | null;  // 初期表示時に中心にする校舎ID
}

export function MapSchoolSelector({
  schools,
  selectedSchoolId,
  onSelectSchool,
  isLoading = false,
  initialSchoolId,
}: MapSchoolSelectorProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [mapError, setMapError] = useState(false);

  // onSelectSchoolをrefで保持（useEffect内で最新の関数を使用するため）
  const onSelectSchoolRef = useRef(onSelectSchool);
  useEffect(() => {
    onSelectSchoolRef.current = onSelectSchool;
  }, [onSelectSchool]);

  // 初期表示時の中心校舎を取得
  const getInitialSchool = useCallback(() => {
    if (!initialSchoolId) return null;
    return schools.find(s => s.id === initialSchoolId && s.latitude && s.longitude);
  }, [schools, initialSchoolId]);

  // 校舎の境界を計算
  const getBounds = useCallback(() => {
    const schoolsWithLocation = schools.filter(s => s.latitude && s.longitude);
    if (schoolsWithLocation.length === 0) {
      // デフォルト: 愛知県・岐阜県あたり
      return {
        sw: [136.5, 34.9] as [number, number],  // 南西
        ne: [137.4, 35.5] as [number, number],  // 北東
      };
    }

    const lats = schoolsWithLocation.map(s => s.latitude!);
    const lngs = schoolsWithLocation.map(s => s.longitude!);

    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const minLng = Math.min(...lngs);
    const maxLng = Math.max(...lngs);

    // パディングを追加
    const latPadding = (maxLat - minLat) * 0.1 || 0.05;
    const lngPadding = (maxLng - minLng) * 0.1 || 0.05;

    return {
      sw: [minLng - lngPadding, minLat - latPadding] as [number, number],
      ne: [maxLng + lngPadding, maxLat + latPadding] as [number, number],
    };
  }, [schools]);

  // MapLibre GL JSを動的に読み込み
  useEffect(() => {
    if (!mapContainer.current || schools.length === 0) return;

    let mapInstance: any = null;
    let isMounted = true;

    const initMap = async () => {
      try {
        // MapLibre GL JSを動的インポート
        const maplibregl = (await import('maplibre-gl')).default;

        if (!isMounted || !mapContainer.current) return;

        // CSSを追加
        if (!document.querySelector('link[href*="maplibre-gl"]')) {
          const link = document.createElement('link');
          link.rel = 'stylesheet';
          link.href = 'https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css';
          document.head.appendChild(link);
        }

        const bounds = getBounds();
        const initialSchool = getInitialSchool();

        // 初期校舎がある場合はその位置を中心に、なければ全体を表示
        const mapOptions: any = {
          container: mapContainer.current!,
          style: {
            version: 8,
            sources: {
              osm: {
                type: 'raster',
                tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
                tileSize: 256,
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              }
            },
            layers: [
              {
                id: 'osm',
                type: 'raster',
                source: 'osm'
              }
            ]
          },
        };

        if (initialSchool) {
          // 初期校舎の位置を中心に表示
          mapOptions.center = [initialSchool.longitude!, initialSchool.latitude!];
          mapOptions.zoom = 14;
        } else {
          // 全校舎が収まるように表示
          mapOptions.bounds = [bounds.sw, bounds.ne];
          mapOptions.fitBoundsOptions = {
            padding: 40,
            maxZoom: 12,
          };
        }

        mapInstance = new maplibregl.Map(mapOptions);

        mapInstance.addControl(new maplibregl.NavigationControl(), 'top-right');

        mapRef.current = mapInstance;

        mapInstance.on('load', () => {
          if (!isMounted) return;
          setMapLoaded(true);

          // マーカーを追加
          const schoolsWithLocation = schools.filter(s => s.latitude && s.longitude);

          schoolsWithLocation.forEach((school) => {
            // カスタムマーカー要素を作成（柔らかい星型）
            const el = document.createElement('div');
            el.className = 'map-marker';
            el.style.width = '24px';
            el.style.height = '24px';
            el.style.cursor = 'pointer';
            el.style.filter = 'drop-shadow(0 1px 2px rgba(0,0,0,0.15))';
            el.style.transition = 'filter 0.2s ease';
            el.dataset.schoolId = school.id;

            // 柔らかい星型SVGを設定
            const isSelected = school.id === selectedSchoolId;
            const starColor = isSelected ? '#3B82F6' : '#10B981';  // 選択時: 青, 通常: 緑
            el.innerHTML = `
              <svg viewBox="0 0 24 24" fill="${starColor}" stroke="white" stroke-width="1" style="width: 100%; height: 100%;" opacity="0.85">
                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
              </svg>
            `;

            // hover時のスタイル変更（scaleを使わずshadowだけ変更）
            el.addEventListener('mouseenter', () => {
              el.style.filter = 'drop-shadow(0 2px 4px rgba(0,0,0,0.25))';
            });
            el.addEventListener('mouseleave', () => {
              el.style.filter = 'drop-shadow(0 1px 2px rgba(0,0,0,0.15))';
            });

            // ポップアップ（ボタンは別のIDで管理）
            const buttonId = `select-school-${school.id}`;
            const popup = new maplibregl.Popup({ offset: 25, closeButton: true })
              .setHTML(`
                <div style="min-width: 180px; padding: 4px;">
                  <h3 style="font-weight: bold; font-size: 14px; margin-bottom: 4px;">${school.name}</h3>
                  <p style="font-size: 12px; color: #666; margin-bottom: 8px;">${school.address}</p>
                  ${school.phone ? `<p style="font-size: 11px; color: #888;">TEL: ${school.phone}</p>` : ''}
                  <button
                    id="${buttonId}"
                    style="
                      margin-top: 8px;
                      width: 100%;
                      padding: 6px 12px;
                      background-color: #3B82F6;
                      color: white;
                      border: none;
                      border-radius: 4px;
                      cursor: pointer;
                      font-size: 12px;
                    "
                  >
                    この校舎を選択
                  </button>
                </div>
              `);

            // ポップアップが開いた時にボタンにイベントリスナーを追加
            popup.on('open', () => {
              setTimeout(() => {
                const btn = document.getElementById(buttonId);
                if (btn) {
                  btn.onclick = (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    // refから最新の関数を呼び出す
                    onSelectSchoolRef.current(school.id);
                    popup.remove();
                  };
                }
              }, 0);
            });

            const marker = new maplibregl.Marker({
              element: el,
              anchor: 'center'
            })
              .setLngLat([school.longitude!, school.latitude!])
              .setPopup(popup)
              .addTo(mapInstance);

            markersRef.current.push({ marker, schoolId: school.id, element: el });
          });
        });
      } catch (error) {
        console.error('Failed to load MapLibre GL:', error);
        if (isMounted) {
          setMapError(true);
        }
      }
    };

    initMap();

    return () => {
      isMounted = false;
      if (mapInstance) {
        mapInstance.remove();
      }
      markersRef.current = [];
    };
  }, [schools, getBounds, getInitialSchool]);

  // 選択された校舎が変わったらマーカーの色を更新
  useEffect(() => {
    markersRef.current.forEach(({ element, schoolId }) => {
      if (element) {
        const isSelected = schoolId === selectedSchoolId;
        const starColor = isSelected ? '#3B82F6' : '#10B981';
        const svg = element.querySelector('svg');
        if (svg) {
          svg.setAttribute('fill', starColor);
        }
      }
    });

    // 選択された校舎にパンする
    const selectedSchool = schools.find(s => s.id === selectedSchoolId);
    if (selectedSchool && mapRef.current && selectedSchool.latitude && selectedSchool.longitude) {
      mapRef.current.flyTo({
        center: [selectedSchool.longitude, selectedSchool.latitude],
        zoom: 14,
        duration: 800,
      });
    }
  }, [selectedSchoolId, schools]);

  // ローディング中
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500 mb-3" />
        <p className="text-sm text-gray-600">校舎を読み込み中...</p>
      </div>
    );
  }

  // 校舎がない場合
  if (schools.length === 0) {
    return (
      <p className="text-center text-gray-600 py-8">開講校舎がありません</p>
    );
  }

  // マップがエラーの場合はリスト表示
  if (mapError) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-gray-500 text-center">地図を読み込めませんでした。下のリストから校舎を選択してください。</p>
        {schools.map((school) => (
          <Card
            key={school.id}
            className={`rounded-xl shadow-md cursor-pointer transition-all ${
              selectedSchoolId === school.id
                ? 'border-2 border-green-500 bg-green-50'
                : 'hover:shadow-lg'
            }`}
            onClick={() => onSelectSchool(school.id)}
          >
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                {selectedSchoolId === school.id && (
                  <div className="w-6 h-6 bg-green-500 rounded-full flex items-center justify-center flex-shrink-0">
                    <Check className="h-4 w-4 text-white" />
                  </div>
                )}
                <div className="flex-1">
                  <h3 className="font-bold text-gray-800">{school.name}</h3>
                  <p className="text-sm text-gray-600">{school.address}</p>
                  {school.phone && (
                    <p className="text-xs text-gray-500 mt-1">TEL: {school.phone}</p>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* マップ */}
      <Card className="rounded-xl shadow-md overflow-hidden">
        <div className="relative">
          <div
            ref={mapContainer}
            className="w-full"
            style={{ height: '400px' }}
          />
          {!mapLoaded && (
            <div className="absolute inset-0 flex items-center justify-center bg-gray-100 z-10">
              <div className="text-center">
                <Loader2 className="h-8 w-8 animate-spin text-blue-500 mx-auto mb-2" />
                <p className="text-sm text-gray-600">地図を読み込み中...</p>
              </div>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
