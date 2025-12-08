'use client';

import { useState } from 'react';
import { ChevronLeft, MapPin, Clock, X } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Calendar } from '@/components/ui/calendar';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import Link from 'next/link';
import { format } from 'date-fns';

type School = {
  id: number;
  name: string;
  address: string;
  lat: number;
  lng: number;
  brand: string;
  brandColor: string;
  classes: {
    id: number;
    day: string;
    time: string;
    available: number;
  }[];
};

const schools: School[] = [
  {
    id: 1,
    name: '○○そろばん教室 本校',
    address: '東京都渋谷区○○1-2-3',
    lat: 35.6628,
    lng: 139.7034,
    brand: 'そろばん',
    brandColor: 'bg-blue-500',
    classes: [
      { id: 1, day: '月', time: '16:00-17:00', available: 8 },
      { id: 2, day: '火', time: '16:00-17:00', available: 5 },
      { id: 3, day: '木', time: '16:00-17:00', available: 12 },
    ],
  },
  {
    id: 2,
    name: '○○そろばん教室 駅前校',
    address: '東京都新宿区△△2-3-4',
    lat: 35.6897,
    lng: 139.7001,
    brand: 'そろばん',
    brandColor: 'bg-blue-500',
    classes: [
      { id: 4, day: '月', time: '17:00-18:00', available: 3 },
      { id: 5, day: '水', time: '16:00-17:00', available: 7 },
      { id: 6, day: '金', time: '16:00-17:00', available: 4 },
    ],
  },
  {
    id: 3,
    name: 'イングリッシュスクール○○',
    address: '東京都世田谷区○○11-12-13',
    lat: 35.6464,
    lng: 139.6531,
    brand: '英会話',
    brandColor: 'bg-orange-500',
    classes: [
      { id: 7, day: '火', time: '15:00-16:00', available: 6 },
      { id: 8, day: '木', time: '15:00-16:00', available: 5 },
      { id: 9, day: '土', time: '10:00-11:00', available: 10 },
    ],
  },
  {
    id: 4,
    name: '進学塾ABC 渋谷校',
    address: '東京都渋谷区○○5-6-7',
    lat: 35.6619,
    lng: 139.7047,
    brand: '塾',
    brandColor: 'bg-green-500',
    classes: [
      { id: 10, day: '月', time: '18:00-19:30', available: 8 },
      { id: 11, day: '水', time: '18:00-19:30', available: 6 },
      { id: 12, day: '金', time: '18:00-19:30', available: 9 },
    ],
  },
];

export default function MapPage() {
  const [selectedSchool, setSelectedSchool] = useState<School | null>(null);
  const [selectedClass, setSelectedClass] = useState<any>(null);
  const [showCalendar, setShowCalendar] = useState(false);
  const [selectedDate, setSelectedDate] = useState<Date>();

  const handleSchoolClick = (school: School) => {
    setSelectedSchool(school);
    setSelectedClass(null);
    setSelectedDate(undefined);
  };

  const handleClassSelect = (classItem: any) => {
    setSelectedClass(classItem);
    setShowCalendar(true);
  };

  const handleBookClass = () => {
    setSelectedSchool(null);
    setSelectedClass(null);
    setShowCalendar(false);
    setSelectedDate(undefined);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      <header className="sticky top-0 z-40 bg-white shadow-sm">
        <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center">
          <Link href="/" className="mr-3">
            <ChevronLeft className="h-6 w-6 text-gray-700" />
          </Link>
          <h1 className="text-xl font-bold text-gray-800">地図から探す</h1>
        </div>
      </header>

      <main className="max-w-[390px] mx-auto pb-24">
        <div className="relative h-[400px] bg-gray-200 overflow-hidden">
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-gray-500 text-center">
              <MapPin className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p className="text-sm">マップビュー</p>
              <p className="text-xs mt-1">(デモ用プレースホルダー)</p>
            </div>
          </div>

          {schools.map((school) => (
            <div
              key={school.id}
              className="absolute cursor-pointer transform -translate-x-1/2 -translate-y-1/2 hover:scale-110 transition-transform"
              style={{
                left: `${((school.lng - 139.65) / 0.06) * 100}%`,
                top: `${((35.69 - school.lat) / 0.05) * 100}%`,
              }}
              onClick={() => handleSchoolClick(school)}
            >
              <div className="relative">
                <div className={`w-10 h-10 ${school.brandColor} rounded-full shadow-lg flex items-center justify-center border-2 border-white`}>
                  <MapPin className="h-6 w-6 text-white" />
                </div>
                <div className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full border-2 border-white" />
              </div>
            </div>
          ))}
        </div>

        <div className="px-4 py-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">付近の教室</h2>
          <div className="space-y-3">
            {schools.map((school) => (
              <Card
                key={school.id}
                className="rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer"
                onClick={() => handleSchoolClick(school)}
              >
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    <div className={`w-10 h-10 ${school.brandColor} rounded-full flex items-center justify-center shrink-0`}>
                      <MapPin className="h-6 w-6 text-white" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <Badge className={`${school.brandColor} text-white text-xs mb-1`}>
                        {school.brand}
                      </Badge>
                      <h3 className="font-semibold text-gray-800 mb-1">{school.name}</h3>
                      <p className="text-sm text-gray-600">{school.address}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </main>

      <Dialog open={selectedSchool !== null && !showCalendar} onOpenChange={() => setSelectedSchool(null)}>
        <DialogContent className="max-w-[340px] rounded-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{selectedSchool?.name}</DialogTitle>
            <p className="text-sm text-gray-600">{selectedSchool?.address}</p>
          </DialogHeader>
          {selectedSchool && (
            <div className="space-y-3">
              <div>
                <h3 className="font-semibold text-gray-800 mb-2 flex items-center gap-2">
                  <Clock className="h-4 w-4" />
                  開講クラス
                </h3>
                <div className="space-y-2">
                  {selectedSchool.classes.map((classItem) => (
                    <Card
                      key={classItem.id}
                      className="rounded-xl cursor-pointer hover:shadow-md transition-shadow"
                      onClick={() => handleClassSelect(classItem)}
                    >
                      <CardContent className="p-3">
                        <div className="flex justify-between items-center">
                          <div>
                            <p className="font-semibold text-gray-800">
                              {classItem.day}曜日 {classItem.time}
                            </p>
                          </div>
                          <Badge className="bg-green-100 text-green-700">
                            残{classItem.available}席
                          </Badge>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={showCalendar} onOpenChange={setShowCalendar}>
        <DialogContent className="max-w-[340px] rounded-2xl">
          <DialogHeader>
            <DialogTitle>授業日を選択</DialogTitle>
            <p className="text-sm text-gray-600">
              {selectedClass && `${selectedClass.day}曜日 ${selectedClass.time}`}
            </p>
          </DialogHeader>
          <div className="flex justify-center">
            <Calendar
              mode="single"
              selected={selectedDate}
              onSelect={setSelectedDate}
              disabled={(date) => date < new Date()}
              className="rounded-md border"
            />
          </div>
          {selectedDate && (
            <div className="bg-blue-50 rounded-xl p-3 text-sm">
              <p className="text-gray-700">
                <span className="font-semibold">選択日時:</span> {format(selectedDate, 'yyyy年MM月dd日')} {selectedClass?.time}
              </p>
            </div>
          )}
          <div className="flex gap-2">
            <Button
              variant="outline"
              className="flex-1 rounded-xl"
              onClick={() => {
                setShowCalendar(false);
                setSelectedDate(undefined);
              }}
            >
              キャンセル
            </Button>
            <Button
              className="flex-1 rounded-xl bg-blue-600 hover:bg-blue-700"
              onClick={handleBookClass}
              disabled={!selectedDate}
            >
              予約する
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <BottomTabBar />
    </div>
  );
}
