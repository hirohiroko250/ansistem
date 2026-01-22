'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { Html5Qrcode } from 'html5-qrcode';
import { format } from 'date-fns';
import { ja } from 'date-fns/locale';
import { MapPin, QrCode, CheckCircle2, XCircle, Clock, Users, Loader2, RefreshCw } from 'lucide-react';
import api from '../lib/api/client';

interface School {
  id: string;
  schoolName: string;
  latitude?: number;
  longitude?: number;
  geofenceRange?: number;
}

interface CheckInResult {
  success: boolean;
  message: string;
  studentName?: string;
  type?: 'check_in' | 'check_out';
  timestamp?: string;
}

interface RecentCheckIn {
  studentName: string;
  type: 'check_in' | 'check_out';
  timestamp: Date;
}

export default function KioskPage() {
  const [schools, setSchools] = useState<School[]>([]);
  const [selectedSchool, setSelectedSchool] = useState<School | null>(null);
  const [isDetectingLocation, setIsDetectingLocation] = useState(false);
  const [locationError, setLocationError] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [isScanning, setIsScanning] = useState(false);
  const [scanResult, setScanResult] = useState<CheckInResult | null>(null);
  const [recentCheckIns, setRecentCheckIns] = useState<RecentCheckIn[]>([]);
  const scannerRef = useRef<Html5Qrcode | null>(null);
  const resultTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // 時計更新
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // 校舎一覧取得（キオスク用公開API）
  useEffect(() => {
    const fetchSchools = async () => {
      try {
        const response = await api.get<{ schools: School[] }>('/lessons/kiosk/schools/');
        setSchools(response.schools || []);
      } catch (err) {
        console.error('Failed to fetch schools:', err);
      }
    };
    fetchSchools();
  }, []);

  // GPS位置から最も近い校舎を検出
  const detectNearestSchool = useCallback(() => {
    if (!navigator.geolocation) {
      setLocationError('このデバイスはGPSに対応していません');
      return;
    }

    setIsDetectingLocation(true);
    setLocationError(null);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;

        // 緯度経度を持つ校舎のみフィルタ
        const schoolsWithLocation = schools.filter(s => s.latitude && s.longitude);

        if (schoolsWithLocation.length === 0) {
          setLocationError('位置情報が設定された校舎がありません');
          setIsDetectingLocation(false);
          return;
        }

        // 最も近い校舎を計算（Haversine formula）
        let nearestSchool: School | null = null;
        let minDistance = Infinity;

        schoolsWithLocation.forEach((school) => {
          const distance = calculateDistance(
            latitude,
            longitude,
            school.latitude!,
            school.longitude!
          );
          if (distance < minDistance) {
            minDistance = distance;
            nearestSchool = school;
          }
        });

        if (nearestSchool && minDistance < 1) { // 1km以内
          setSelectedSchool(nearestSchool);
        } else {
          setLocationError('近くに校舎が見つかりません（1km以内）');
        }
        setIsDetectingLocation(false);
      },
      (error) => {
        let message = 'GPS位置の取得に失敗しました';
        if (error.code === error.PERMISSION_DENIED) {
          message = 'GPSの使用が許可されていません。設定を確認してください。';
        } else if (error.code === error.POSITION_UNAVAILABLE) {
          message = 'GPS位置情報を取得できません';
        } else if (error.code === error.TIMEOUT) {
          message = 'GPS位置取得がタイムアウトしました';
        }
        setLocationError(message);
        setIsDetectingLocation(false);
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      }
    );
  }, [schools]);

  // 距離計算（Haversine formula）
  const calculateDistance = (lat1: number, lon1: number, lat2: number, lon2: number): number => {
    const R = 6371; // 地球の半径（km）
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  };

  const toRad = (deg: number) => deg * (Math.PI / 180);

  // QRスキャン開始
  const startScanning = useCallback(async () => {
    if (!selectedSchool) return;

    try {
      if (scannerRef.current) {
        await scannerRef.current.stop();
      }

      const scanner = new Html5Qrcode('qr-reader');
      scannerRef.current = scanner;

      await scanner.start(
        { facingMode: 'environment' },
        {
          fps: 10,
          qrbox: { width: 300, height: 300 },
        },
        async (decodedText) => {
          // スキャン成功時
          await handleQRCode(decodedText);
        },
        () => {
          // スキャンエラー（QRが検出されない）は無視
        }
      );

      setIsScanning(true);
    } catch (err) {
      console.error('Failed to start scanner:', err);
      setLocationError('カメラの起動に失敗しました');
    }
  }, [selectedSchool]);

  // QRコード処理
  const handleQRCode = async (qrData: string) => {
    if (resultTimeoutRef.current) {
      clearTimeout(resultTimeoutRef.current);
    }

    try {
      // キオスク用公開APIで入退室を自動判定
      const response = await api.post<{
        success: boolean;
        message: string;
        student_name?: string;
        type?: 'check_in' | 'check_out';
      }>('/lessons/kiosk/attendance/', {
        qr_code: qrData,
        school_id: selectedSchool?.id,
      });

      const result: CheckInResult = {
        success: response.success,
        message: response.message,
        studentName: response.student_name,
        type: response.type,
        timestamp: new Date().toISOString(),
      };

      setScanResult(result);

      if (result.success && result.studentName) {
        setRecentCheckIns((prev) => [
          {
            studentName: result.studentName!,
            type: result.type || 'check_in',
            timestamp: new Date(),
          },
          ...prev.slice(0, 4),
        ]);
      }
    } catch (err: any) {
      setScanResult({
        success: false,
        message: err.message || 'チェックインに失敗しました',
      });
    }

    // 3秒後に結果をクリア
    resultTimeoutRef.current = setTimeout(() => {
      setScanResult(null);
    }, 3000);
  };

  // スキャン停止
  const stopScanning = useCallback(async () => {
    if (scannerRef.current) {
      try {
        await scannerRef.current.stop();
      } catch (err) {
        console.error('Failed to stop scanner:', err);
      }
      scannerRef.current = null;
    }
    setIsScanning(false);
  }, []);

  // 校舎選択後にスキャン開始
  useEffect(() => {
    if (selectedSchool) {
      startScanning();
    }
    return () => {
      stopScanning();
    };
  }, [selectedSchool, startScanning, stopScanning]);

  // 校舎選択画面
  if (!selectedSchool) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-600 to-blue-800 flex flex-col items-center justify-center p-8">
        <div className="text-white text-center mb-12">
          <h1 className="text-4xl font-bold mb-2">OZ Academy</h1>
          <p className="text-xl text-blue-200">教室チェックインシステム</p>
        </div>

        <div className="w-full max-w-md space-y-6">
          {/* GPS検出ボタン */}
          <button
            onClick={detectNearestSchool}
            disabled={isDetectingLocation}
            className="w-full bg-white text-blue-600 font-bold text-xl py-6 px-8 rounded-2xl shadow-lg hover:bg-blue-50 transition-all flex items-center justify-center gap-3 disabled:opacity-50"
          >
            {isDetectingLocation ? (
              <>
                <Loader2 className="h-8 w-8 animate-spin" />
                <span>位置を検出中...</span>
              </>
            ) : (
              <>
                <MapPin className="h-8 w-8" />
                <span>現在地から校舎を検出</span>
              </>
            )}
          </button>

          {locationError && (
            <div className="bg-red-100 border border-red-300 text-red-700 px-4 py-3 rounded-xl text-center">
              {locationError}
            </div>
          )}

          <div className="text-center text-blue-200 text-sm">または校舎を選択</div>

          {/* 校舎一覧 */}
          <div className="space-y-3 max-h-64 overflow-y-auto">
            {schools.map((school) => (
              <button
                key={school.id}
                onClick={() => setSelectedSchool(school)}
                className="w-full bg-white/20 backdrop-blur text-white font-semibold text-lg py-4 px-6 rounded-xl hover:bg-white/30 transition-all text-left"
              >
                {school.schoolName}
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // メインのスキャン画面
  return (
    <div className="min-h-screen bg-gray-900 flex flex-col">
      {/* ヘッダー */}
      <div className="bg-blue-600 text-white px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <MapPin className="h-6 w-6" />
          <span className="font-bold text-xl">{selectedSchool.schoolName}</span>
        </div>
        <div className="flex items-center gap-2 text-2xl font-mono">
          <Clock className="h-6 w-6" />
          {format(currentTime, 'HH:mm:ss')}
        </div>
      </div>

      {/* メインコンテンツ */}
      <div className="flex-1 flex flex-col lg:flex-row">
        {/* QRスキャンエリア */}
        <div className="flex-1 flex flex-col items-center justify-center p-8">
          <div className="text-center mb-6">
            <QrCode className="h-16 w-16 text-blue-400 mx-auto mb-4" />
            <h2 className="text-white text-2xl font-bold mb-2">QRコードをかざしてください</h2>
            <p className="text-gray-400">生徒証のQRコードをカメラに向けてください</p>
          </div>

          {/* QRリーダー */}
          <div className="relative w-full max-w-md aspect-square bg-black rounded-2xl overflow-hidden">
            <div id="qr-reader" className="w-full h-full" />

            {/* スキャン結果オーバーレイ */}
            {scanResult && (
              <div
                className={`absolute inset-0 flex flex-col items-center justify-center ${
                  scanResult.success ? 'bg-green-500/90' : 'bg-red-500/90'
                }`}
              >
                {scanResult.success ? (
                  <CheckCircle2 className="h-24 w-24 text-white mb-4" />
                ) : (
                  <XCircle className="h-24 w-24 text-white mb-4" />
                )}
                <p className="text-white text-3xl font-bold mb-2">
                  {scanResult.studentName || (scanResult.success ? '成功' : 'エラー')}
                </p>
                <p className="text-white/80 text-xl">
                  {scanResult.type === 'check_out' ? '退室しました' : '入室しました'}
                </p>
              </div>
            )}
          </div>

          <button
            onClick={() => setSelectedSchool(null)}
            className="mt-8 text-gray-500 hover:text-white flex items-center gap-2 transition-colors"
          >
            <RefreshCw className="h-5 w-5" />
            校舎を変更
          </button>
        </div>

        {/* 最近のチェックイン */}
        <div className="lg:w-80 bg-gray-800 p-6">
          <div className="flex items-center gap-2 text-white mb-4">
            <Users className="h-5 w-5" />
            <h3 className="font-semibold">最近のチェックイン</h3>
          </div>
          <div className="space-y-3">
            {recentCheckIns.length === 0 ? (
              <p className="text-gray-500 text-sm text-center py-8">
                まだチェックインはありません
              </p>
            ) : (
              recentCheckIns.map((checkIn, index) => (
                <div
                  key={index}
                  className={`p-3 rounded-lg ${
                    checkIn.type === 'check_out' ? 'bg-orange-900/30' : 'bg-green-900/30'
                  }`}
                >
                  <p className="text-white font-semibold">{checkIn.studentName}</p>
                  <p className="text-gray-400 text-sm flex items-center gap-1">
                    <span className={checkIn.type === 'check_out' ? 'text-orange-400' : 'text-green-400'}>
                      {checkIn.type === 'check_out' ? '退室' : '入室'}
                    </span>
                    <span>・</span>
                    <span>{format(checkIn.timestamp, 'HH:mm', { locale: ja })}</span>
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* フッター */}
      <div className="bg-gray-800 text-gray-500 text-center py-3 text-sm">
        {format(currentTime, 'yyyy年MM月dd日（E）', { locale: ja })}
      </div>
    </div>
  );
}
