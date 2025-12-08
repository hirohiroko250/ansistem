'use client';

import { MapPin } from 'lucide-react';

type School = {
  id: number;
  name: string;
  address: string;
  company: string;
  companyColor: string;
  position: { x: number; y: number };
};

type SchoolMapProps = {
  schools: School[];
  selectedSchool: number | null;
  onSchoolSelect: (schoolId: number) => void;
};

export function SchoolMap({ schools, selectedSchool, onSchoolSelect }: SchoolMapProps) {
  return (
    <div className="relative w-full aspect-square bg-gradient-to-br from-green-100 via-blue-50 to-green-100 rounded-2xl overflow-hidden shadow-lg border-4 border-gray-200">
      <svg className="absolute inset-0 w-full h-full opacity-20" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="gray" strokeWidth="0.5"/>
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />

        <path
          d="M50,150 Q100,100 150,120 T250,140"
          stroke="#4299e1"
          strokeWidth="3"
          fill="none"
          opacity="0.6"
        />
        <path
          d="M200,50 Q250,80 280,120"
          stroke="#4299e1"
          strokeWidth="3"
          fill="none"
          opacity="0.6"
        />

        <circle cx="80" cy="200" r="25" fill="#48bb78" opacity="0.3" />
        <circle cx="180" cy="180" r="30" fill="#48bb78" opacity="0.3" />
        <circle cx="260" cy="240" r="35" fill="#48bb78" opacity="0.3" />
        <circle cx="300" cy="100" r="20" fill="#48bb78" opacity="0.3" />
      </svg>

      <div className="absolute top-3 left-3 bg-white/90 backdrop-blur-sm px-3 py-1.5 rounded-lg shadow-md">
        <p className="text-xs font-semibold text-gray-700">エリアマップ</p>
      </div>

      {schools.map((school) => {
        const isSelected = selectedSchool === school.id;
        return (
          <div
            key={school.id}
            className="absolute transform -translate-x-1/2 -translate-y-1/2 cursor-pointer transition-all duration-200 hover:scale-110"
            style={{
              left: `${school.position.x}%`,
              top: `${school.position.y}%`,
            }}
            onClick={() => onSchoolSelect(school.id)}
          >
            <div className={`relative ${isSelected ? 'animate-bounce' : ''}`}>
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center shadow-lg transition-all ${
                  isSelected
                    ? 'ring-4 ring-blue-400 ring-offset-2 scale-125'
                    : 'hover:ring-2 hover:ring-gray-300'
                }`}
                style={{ backgroundColor: school.companyColor }}
              >
                <MapPin className="h-5 w-5 text-white" />
              </div>

              {isSelected && (
                <div className="absolute top-12 left-1/2 transform -translate-x-1/2 bg-white px-3 py-2 rounded-lg shadow-xl z-10 whitespace-nowrap min-w-[160px]">
                  <p className="text-xs font-bold text-gray-800 text-center">{school.name}</p>
                  <p className="text-[10px] text-gray-600 text-center mt-0.5">{school.company}</p>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
