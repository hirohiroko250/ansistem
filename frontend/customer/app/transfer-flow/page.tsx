'use client';

import { useState } from 'react';
import { ChevronLeft, MapPin, Calendar as CalendarIcon } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Calendar } from '@/components/ui/calendar';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import Link from 'next/link';
import { format } from 'date-fns';

type Region = {
  id: number;
  name: string;
  schoolCount: number;
};

type School = {
  id: number;
  name: string;
  address: string;
  region: string;
  availableSlots: { id: number; day: string; time: string; available: number }[];
};

const regions: Region[] = [
  { id: 1, name: '渋谷区', schoolCount: 3 },
  { id: 2, name: '新宿区', schoolCount: 2 },
  { id: 3, name: '世田谷区', schoolCount: 4 },
  { id: 4, name: '品川区', schoolCount: 2 },
];

const schools: School[] = [
  {
    id: 1,
    name: '○○そろばん教室 本校',
    address: '東京都渋谷区○○1-2-3',
    region: '渋谷区',
    availableSlots: [
      { id: 1, day: '月', time: '16:00-17:00', available: 5 },
      { id: 2, day: '火', time: '16:00-17:00', available: 3 },
      { id: 3, day: '木', time: '16:00-17:00', available: 8 },
    ],
  },
  {
    id: 2,
    name: '○○そろばん教室 駅前校',
    address: '東京都渋谷区△△2-3-4',
    region: '渋谷区',
    availableSlots: [
      { id: 4, day: '水', time: '15:00-16:00', available: 6 },
      { id: 5, day: '金', time: '16:00-17:00', available: 4 },
    ],
  },
  {
    id: 3,
    name: '○○そろばん教室 南口校',
    address: '東京都新宿区○○5-6-7',
    region: '新宿区',
    availableSlots: [
      { id: 6, day: '火', time: '17:00-18:00', available: 7 },
      { id: 7, day: '木', time: '17:00-18:00', available: 5 },
    ],
  },
];

export default function TransferFlowPage() {
  const [step, setStep] = useState<'region' | 'school' | 'date'>('region');
  const [selectedRegion, setSelectedRegion] = useState<Region | null>(null);
  const [selectedSchool, setSelectedSchool] = useState<School | null>(null);
  const [selectedSlot, setSelectedSlot] = useState<any>(null);
  const [selectedDate, setSelectedDate] = useState<Date>();

  const filteredSchools = selectedRegion
    ? schools.filter(s => s.region === selectedRegion.name)
    : schools;

  const handleRegionSelect = (region: Region) => {
    setSelectedRegion(region);
    setStep('school');
  };

  const handleSchoolSelect = (school: School) => {
    setSelectedSchool(school);
  };

  const handleSlotSelect = (slot: any) => {
    setSelectedSlot(slot);
    setStep('date');
  };

  const handleConfirm = () => {
    alert('振替予約が完了しました');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      <header className="sticky top-0 z-40 bg-white shadow-sm">
        <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center">
          <Link href="/class-registration" className="mr-3">
            <ChevronLeft className="h-6 w-6 text-gray-700" />
          </Link>
          <h1 className="text-xl font-bold text-gray-800">振替予約</h1>
        </div>
      </header>

      <main className="max-w-[390px] mx-auto px-4 py-6 pb-24">
        <div className="mb-6">
          <div className="flex items-center justify-center space-x-2">
            {['region', 'school', 'date'].map((s, index) => (
              <div
                key={s}
                className={`h-2 flex-1 rounded-full transition-colors ${
                  step === s || (s === 'school' && step === 'date') || (s === 'region' && (step === 'school' || step === 'date'))
                    ? 'bg-amber-500'
                    : 'bg-gray-200'
                }`}
              />
            ))}
          </div>
          <p className="text-center text-sm text-gray-600 mt-2">
            {step === 'region' && 'Step 1 / 3: 地域を選択'}
            {step === 'school' && 'Step 2 / 3: 教室を選択'}
            {step === 'date' && 'Step 3 / 3: 日時を選択'}
          </p>
        </div>

        {step === 'region' && (
          <section>
            <Card className="rounded-xl shadow-md bg-amber-50 border-amber-200 mb-6">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <MapPin className="h-6 w-6 text-amber-600" />
                  <div>
                    <h3 className="font-semibold text-gray-800 mb-1">地域を選択</h3>
                    <p className="text-sm text-gray-600">振替可能な教室がある地域を選んでください</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <h2 className="text-lg font-semibold text-gray-800 mb-4">地域一覧</h2>
            <div className="space-y-3">
              {regions.map((region) => (
                <Card
                  key={region.id}
                  className="rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer"
                  onClick={() => handleRegionSelect(region)}
                >
                  <CardContent className="p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-amber-100 rounded-full flex items-center justify-center">
                        <MapPin className="h-5 w-5 text-amber-600" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-800">{region.name}</h3>
                        <p className="text-sm text-gray-600">{region.schoolCount}校</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>
        )}

        {step === 'school' && (
          <section>
            <Button
              variant="ghost"
              className="mb-4"
              onClick={() => setStep('region')}
            >
              <ChevronLeft className="h-4 w-4 mr-2" />
              戻る
            </Button>

            <Card className="rounded-xl shadow-md bg-amber-50 border-amber-200 mb-6">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-amber-100 rounded-full flex items-center justify-center">
                    <MapPin className="h-5 w-5 text-amber-600" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">選択中の地域</p>
                    <p className="font-semibold text-gray-800">{selectedRegion?.name}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <h2 className="text-lg font-semibold text-gray-800 mb-4">教室一覧</h2>
            <div className="space-y-3">
              {filteredSchools.map((school) => (
                <Card
                  key={school.id}
                  className={`rounded-xl shadow-md hover:shadow-lg transition-shadow cursor-pointer ${
                    selectedSchool?.id === school.id ? 'border-2 border-amber-500' : ''
                  }`}
                  onClick={() => handleSchoolSelect(school)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3 mb-3">
                      <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center shrink-0">
                        <MapPin className="h-5 w-5 text-white" />
                      </div>
                      <div className="flex-1">
                        <h3 className="font-semibold text-gray-800 mb-1">{school.name}</h3>
                        <p className="text-sm text-gray-600">{school.address}</p>
                      </div>
                    </div>

                    {selectedSchool?.id === school.id && (
                      <div className="mt-4 pt-4 border-t">
                        <h4 className="font-semibold text-gray-800 mb-2 text-sm">空き時間</h4>
                        <div className="space-y-2">
                          {school.availableSlots.map((slot) => (
                            <button
                              key={slot.id}
                              onClick={(e) => {
                                e.stopPropagation();
                                handleSlotSelect(slot);
                              }}
                              className="w-full flex items-center justify-between p-3 rounded-lg bg-white hover:bg-amber-50 border border-gray-200 transition-colors"
                            >
                              <span className="font-medium text-gray-800">
                                {slot.day}曜日 {slot.time}
                              </span>
                              <Badge className="bg-green-100 text-green-700">
                                残{slot.available}枠
                              </Badge>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>
        )}

        {step === 'date' && (
          <section>
            <Button
              variant="ghost"
              className="mb-4"
              onClick={() => setStep('school')}
            >
              <ChevronLeft className="h-4 w-4 mr-2" />
              戻る
            </Button>

            <Card className="rounded-xl shadow-md bg-amber-50 border-amber-200 mb-6">
              <CardContent className="p-4 space-y-3">
                <div>
                  <p className="text-sm text-gray-600">教室</p>
                  <p className="font-semibold text-gray-800">{selectedSchool?.name}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">時間帯</p>
                  <p className="font-semibold text-gray-800">
                    {selectedSlot?.day}曜日 {selectedSlot?.time}
                  </p>
                </div>
              </CardContent>
            </Card>

            <h2 className="text-lg font-semibold text-gray-800 mb-4">日付を選択</h2>
            <Card className="rounded-xl shadow-md mb-6">
              <CardContent className="p-4">
                <div className="flex justify-center">
                  <Calendar
                    mode="single"
                    selected={selectedDate}
                    onSelect={setSelectedDate}
                    disabled={(date) => date < new Date()}
                    className="rounded-md border"
                  />
                </div>
              </CardContent>
            </Card>

            <Button
              onClick={handleConfirm}
              className="w-full h-14 rounded-full bg-amber-600 hover:bg-amber-700 text-white font-semibold text-lg"
              disabled={!selectedDate}
            >
              振替予約を確定する
            </Button>
          </section>
        )}
      </main>

      <BottomTabBar />
    </div>
  );
}
