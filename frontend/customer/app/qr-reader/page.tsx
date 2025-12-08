'use client';

import { useState } from 'react';
import { ChevronLeft, Camera, CheckCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import Link from 'next/link';

export default function QRReaderPage() {
  const [isScanning, setIsScanning] = useState(false);
  const [scanResult, setScanResult] = useState<string | null>(null);

  const handleScan = () => {
    setIsScanning(true);
    setTimeout(() => {
      setScanResult('チェックイン完了：○○そろばん教室 本校 / 2025-01-27 14:30');
      setIsScanning(false);
    }, 2000);
  };

  const handleReset = () => {
    setScanResult(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      <header className="sticky top-0 z-40 bg-white shadow-sm">
        <div className="max-w-[390px] mx-auto px-4 h-16 flex items-center">
          <Link href="/" className="mr-3">
            <ChevronLeft className="h-6 w-6 text-gray-700" />
          </Link>
          <h1 className="text-xl font-bold text-gray-800">QR読み取り</h1>
        </div>
      </header>

      <main className="max-w-[390px] mx-auto px-4 py-6 pb-24">
        {!scanResult ? (
          <div>
            <Card className="rounded-xl shadow-md mb-6 overflow-hidden">
              <CardContent className="p-0">
                <div className="aspect-square bg-gray-900 flex items-center justify-center relative">
                  {isScanning ? (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="w-64 h-64 border-4 border-blue-500 rounded-xl animate-pulse" />
                      <div className="absolute text-white font-semibold">スキャン中...</div>
                    </div>
                  ) : (
                    <Camera className="h-24 w-24 text-gray-600" />
                  )}
                </div>
              </CardContent>
            </Card>

            <div className="space-y-4">
              <Card className="rounded-xl shadow-md">
                <CardContent className="p-4">
                  <h3 className="font-semibold text-gray-800 mb-2">使い方</h3>
                  <ul className="text-sm text-gray-600 space-y-1">
                    <li>• 教室のQRコードをカメラで読み取ってください</li>
                    <li>• チェックインが自動で完了します</li>
                    <li>• チケットが1枚消費されます</li>
                  </ul>
                </CardContent>
              </Card>

              <Button
                onClick={handleScan}
                disabled={isScanning}
                className="w-full h-14 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-semibold text-lg"
              >
                {isScanning ? 'スキャン中...' : 'QRコードを読み取る'}
              </Button>
            </div>
          </div>
        ) : (
          <div className="text-center py-12">
            <div className="w-20 h-20 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-6">
              <CheckCircle className="h-12 w-12 text-green-600" />
            </div>
            <h2 className="text-2xl font-bold text-gray-800 mb-3">チェックイン完了</h2>
            <Card className="rounded-xl shadow-md mb-6 text-left">
              <CardContent className="p-6">
                <p className="text-gray-800">{scanResult}</p>
              </CardContent>
            </Card>
            <div className="space-y-3">
              <Link href="/" className="block">
                <Button className="w-full h-14 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-semibold text-lg">
                  トップへ戻る
                </Button>
              </Link>
              <Button
                onClick={handleReset}
                variant="outline"
                className="w-full h-14 rounded-full border-2 font-semibold text-lg"
              >
                もう一度読み取る
              </Button>
            </div>
          </div>
        )}
      </main>

      <BottomTabBar />
    </div>
  );
}
