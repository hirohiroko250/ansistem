'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { isAuthenticated, getMe } from '@/lib/api/auth';
import { qrCheckIn, qrCheckOut, QRCheckInResponse, QRCheckOutResponse } from '@/lib/api/lessons';
import { getSchools, School } from '@/lib/api/schools';
import {
  QrCode,
  CheckCircle,
  XCircle,
  LogIn,
  LogOut,
  Clock,
  User,
  Building2,
  RefreshCw,
} from 'lucide-react';
import { Html5QrcodeScanner, Html5QrcodeSupportedFormats } from 'html5-qrcode';
import { format } from 'date-fns';
import { ja } from 'date-fns/locale';

type ScanMode = 'check-in' | 'check-out';
type ScanResult = {
  success: boolean;
  message: string;
  studentName?: string;
  className?: string;
  time?: string;
};

export default function TabletCheckInPage() {
  const router = useRouter();
  const [authChecking, setAuthChecking] = useState(true);
  const [isStaff, setIsStaff] = useState(false);
  const [staffName, setStaffName] = useState<string>('');
  const [schools, setSchools] = useState<School[]>([]);
  const [selectedSchool, setSelectedSchool] = useState<School | null>(null);
  const [scanMode, setScanMode] = useState<ScanMode>('check-in');
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [lastScannedCode, setLastScannedCode] = useState<string | null>(null);
  const [cooldownUntil, setCooldownUntil] = useState<number | null>(null);
  const scannerRef = useRef<Html5QrcodeScanner | null>(null);
  const resultTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // 現在時刻を更新
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // 認証チェック
  useEffect(() => {
    const checkAuth = async () => {
      if (!isAuthenticated()) {
        router.push('/login');
        return;
      }

      try {
        const profile = await getMe();
        const userType = profile.userType;
        if (userType === 'staff' || userType === 'teacher') {
          setIsStaff(true);
          setStaffName(profile.fullName || profile.email || '');

          // 校舎一覧を取得
          const schoolsData = await getSchools();
          if (Array.isArray(schoolsData)) {
            setSchools(schoolsData);
            if (schoolsData.length === 1) {
              setSelectedSchool(schoolsData[0]);
            }
          }
        } else {
          // スタッフ以外はアクセス不可
          router.push('/feed');
          return;
        }
      } catch {
        router.push('/login');
        return;
      }

      setAuthChecking(false);
    };

    checkAuth();
  }, [router]);

  // QRスキャン成功時の処理
  const handleScanSuccess = useCallback(async (decodedText: string) => {
    // クールダウンチェック
    if (cooldownUntil && Date.now() < cooldownUntil) {
      return;
    }

    // 同じコードの連続スキャン防止
    if (lastScannedCode === decodedText) {
      return;
    }

    if (!selectedSchool) {
      setScanResult({
        success: false,
        message: '校舎を選択してください',
      });
      return;
    }

    setLastScannedCode(decodedText);
    setCooldownUntil(Date.now() + 3000); // 3秒のクールダウン

    try {
      let response: QRCheckInResponse | QRCheckOutResponse;

      if (scanMode === 'check-in') {
        response = await qrCheckIn(decodedText, selectedSchool.id);
        setScanResult({
          success: response.success,
          message: response.message,
          studentName: response.student_name,
          className: response.class_name,
          time: response.check_in_time,
        });
      } else {
        response = await qrCheckOut(decodedText, selectedSchool.id);
        setScanResult({
          success: response.success,
          message: response.message,
          studentName: response.student_name,
          className: response.class_name,
          time: (response as QRCheckOutResponse).check_out_time,
        });
      }

      // 成功音を再生（ブラウザ対応）
      if (response.success) {
        try {
          const audioContext = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
          const oscillator = audioContext.createOscillator();
          const gainNode = audioContext.createGain();
          oscillator.connect(gainNode);
          gainNode.connect(audioContext.destination);
          oscillator.frequency.value = 800;
          oscillator.type = 'sine';
          gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
          gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
          oscillator.start(audioContext.currentTime);
          oscillator.stop(audioContext.currentTime + 0.3);
        } catch {
          // オーディオ再生に失敗しても処理を続行
        }
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'エラーが発生しました';
      setScanResult({
        success: false,
        message: errorMessage,
      });
    }

    // 結果を3秒後にクリア
    if (resultTimeoutRef.current) {
      clearTimeout(resultTimeoutRef.current);
    }
    resultTimeoutRef.current = setTimeout(() => {
      setScanResult(null);
      setLastScannedCode(null);
    }, 3000);
  }, [scanMode, selectedSchool, lastScannedCode, cooldownUntil]);

  // QRスキャナー初期化
  useEffect(() => {
    if (!selectedSchool || !isStaff || authChecking) return;

    // 既存のスキャナーを停止
    if (scannerRef.current) {
      scannerRef.current.clear().catch(() => {});
    }

    const scanner = new Html5QrcodeScanner(
      'qr-reader',
      {
        fps: 10,
        qrbox: { width: 250, height: 250 },
        formatsToSupport: [Html5QrcodeSupportedFormats.QR_CODE],
        rememberLastUsedCamera: true,
      },
      false
    );

    scanner.render(
      handleScanSuccess,
      () => {} // エラーは無視（カメラが読み取り中の場合など）
    );

    scannerRef.current = scanner;
    setIsScanning(true);

    return () => {
      if (scannerRef.current) {
        scannerRef.current.clear().catch(() => {});
      }
    };
  }, [selectedSchool, isStaff, authChecking, handleScanSuccess]);

  // クリーンアップ
  useEffect(() => {
    return () => {
      if (resultTimeoutRef.current) {
        clearTimeout(resultTimeoutRef.current);
      }
    };
  }, []);

  if (authChecking) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-muted-foreground">読み込み中...</p>
        </div>
      </div>
    );
  }

  if (!isStaff) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="text-center">
          <p className="text-destructive">スタッフのみアクセス可能です</p>
          <Button onClick={() => router.push('/login')} className="mt-4">
            ログインに戻る
          </Button>
        </div>
      </div>
    );
  }

  // 校舎選択画面
  if (!selectedSchool) {
    return (
      <div className="min-h-screen bg-background p-4">
        <div className="max-w-md mx-auto space-y-6">
          <div className="text-center pt-8">
            <Building2 className="h-16 w-16 mx-auto text-primary" />
            <h1 className="text-2xl font-bold mt-4">校舎を選択</h1>
            <p className="text-muted-foreground mt-2">
              出席管理を行う校舎を選択してください
            </p>
          </div>

          <div className="space-y-3">
            {schools.map((school) => (
              <Button
                key={school.id}
                variant="outline"
                className="w-full h-16 text-lg justify-start"
                onClick={() => setSelectedSchool(school)}
              >
                <Building2 className="h-6 w-6 mr-3" />
                {school.school_name}
              </Button>
            ))}
          </div>

          {schools.length === 0 && (
            <p className="text-center text-muted-foreground">
              校舎が見つかりません
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* ヘッダー */}
      <header className="bg-primary text-primary-foreground px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <QrCode className="h-8 w-8" />
            <div>
              <h1 className="text-lg font-bold">出席管理</h1>
              <p className="text-sm opacity-90">{selectedSchool.school_name}</p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-2xl font-mono">
              {format(currentTime, 'HH:mm:ss')}
            </p>
            <p className="text-sm opacity-90">
              {format(currentTime, 'M月d日(E)', { locale: ja })}
            </p>
          </div>
        </div>
      </header>

      {/* モード切り替え */}
      <div className="p-4 border-b">
        <div className="flex gap-2">
          <Button
            variant={scanMode === 'check-in' ? 'default' : 'outline'}
            className="flex-1 h-12"
            onClick={() => setScanMode('check-in')}
          >
            <LogIn className="h-5 w-5 mr-2" />
            入室
          </Button>
          <Button
            variant={scanMode === 'check-out' ? 'default' : 'outline'}
            className="flex-1 h-12"
            onClick={() => setScanMode('check-out')}
          >
            <LogOut className="h-5 w-5 mr-2" />
            退出
          </Button>
        </div>
      </div>

      {/* メインコンテンツ */}
      <main className="flex-1 p-4 flex flex-col items-center justify-center">
        {/* スキャン結果表示 */}
        {scanResult && (
          <Card className={`w-full max-w-md mb-4 ${
            scanResult.success
              ? 'border-green-500 bg-green-50 dark:bg-green-950'
              : 'border-red-500 bg-red-50 dark:bg-red-950'
          }`}>
            <CardContent className="p-6 text-center">
              {scanResult.success ? (
                <CheckCircle className="h-16 w-16 mx-auto text-green-500" />
              ) : (
                <XCircle className="h-16 w-16 mx-auto text-red-500" />
              )}
              <p className="mt-4 text-2xl font-bold">
                {scanResult.studentName || (scanResult.success ? '成功' : 'エラー')}
              </p>
              {scanResult.className && (
                <p className="text-lg text-muted-foreground">
                  {scanResult.className}
                </p>
              )}
              <p className="mt-2 text-lg">
                {scanResult.message}
              </p>
              {scanResult.time && (
                <Badge variant="secondary" className="mt-2">
                  <Clock className="h-4 w-4 mr-1" />
                  {scanResult.time}
                </Badge>
              )}
            </CardContent>
          </Card>
        )}

        {/* QRスキャナー */}
        <div className="w-full max-w-md">
          <Card>
            <CardContent className="p-4">
              <div id="qr-reader" className="w-full" />
              {!isScanning && (
                <div className="text-center py-8">
                  <RefreshCw className="h-8 w-8 mx-auto animate-spin text-muted-foreground" />
                  <p className="mt-2 text-muted-foreground">
                    カメラを起動中...
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          <p className="mt-4 text-center text-muted-foreground">
            生徒のQRコードをカメラにかざしてください
          </p>
        </div>
      </main>

      {/* フッター */}
      <footer className="border-t p-4 bg-muted/50">
        <div className="flex items-center justify-between max-w-md mx-auto">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <User className="h-4 w-4" />
            <span>{staffName}</span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSelectedSchool(null)}
          >
            校舎変更
          </Button>
        </div>
      </footer>

      {/* html5-qrcodeのスタイル調整 */}
      <style jsx global>{`
        #qr-reader {
          border: none !important;
        }
        #qr-reader video {
          border-radius: 8px;
        }
        #qr-reader__scan_region {
          border-radius: 8px;
          overflow: hidden;
        }
        #qr-reader__dashboard_section_csr button {
          background-color: hsl(var(--primary)) !important;
          color: hsl(var(--primary-foreground)) !important;
          border-radius: 6px !important;
          padding: 8px 16px !important;
        }
        #qr-reader__dashboard_section_csr select {
          border-radius: 6px !important;
          padding: 8px !important;
        }
      `}</style>
    </div>
  );
}
