'use client';

import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import { Card } from '@/components/ui/card';
import { Loader2 } from 'lucide-react';
import type { BrandSchool } from '@/lib/api/schools';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Leafletのデフォルトアイコンを修正
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

interface LeafletMapProps {
  schools: BrandSchool[];
  selectedSchoolId: string | null;
  onSelectSchool: (schoolId: string) => void;
}

export function LeafletMap({
  schools,
  selectedSchoolId,
  onSelectSchool,
}: LeafletMapProps) {
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  // 校舎の中心位置を計算
  const getCenter = (): [number, number] => {
    const schoolsWithLocation = schools.filter(s => s.latitude && s.longitude);
    if (schoolsWithLocation.length === 0) {
      // デフォルト: 名古屋市中心
      return [35.1815, 136.9066];
    }

    const avgLat = schoolsWithLocation.reduce((sum, s) => sum + (s.latitude || 0), 0) / schoolsWithLocation.length;
    const avgLng = schoolsWithLocation.reduce((sum, s) => sum + (s.longitude || 0), 0) / schoolsWithLocation.length;
    return [avgLat, avgLng];
  };

  if (!isClient) {
    return (
      <Card className="rounded-xl shadow-md">
        <div className="w-full h-64 md:h-80 flex items-center justify-center bg-gray-100">
          <div className="text-center">
            <Loader2 className="h-8 w-8 animate-spin text-blue-500 mx-auto mb-2" />
            <p className="text-sm text-gray-600">地図を読み込み中...</p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card className="rounded-xl shadow-md overflow-hidden">
      <div className="w-full h-64 md:h-80">
        <MapContainer
          center={getCenter()}
          zoom={10}
          style={{ height: '100%', width: '100%' }}
          scrollWheelZoom={false}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {schools.map((school) => {
            if (!school.latitude || !school.longitude) return null;

            return (
              <Marker
                key={school.id}
                position={[school.latitude, school.longitude]}
                eventHandlers={{
                  click: () => onSelectSchool(school.id),
                }}
              >
                <Popup>
                  <div className="min-w-[180px]">
                    <h3 className="font-bold text-sm mb-1">{school.name}</h3>
                    <p className="text-xs text-gray-600 mb-2">{school.address}</p>
                    {school.phone && (
                      <p className="text-xs text-gray-500">TEL: {school.phone}</p>
                    )}
                    <button
                      onClick={() => onSelectSchool(school.id)}
                      className="mt-2 w-full text-xs py-1 px-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                    >
                      この校舎を選択
                    </button>
                  </div>
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>
      </div>
    </Card>
  );
}
