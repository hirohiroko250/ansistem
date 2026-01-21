'use client';

import { useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { BottomTabBar } from '@/components/bottom-tab-bar';
import { useUser } from '@/lib/hooks/use-user';
import { useMyQRCode } from '@/lib/hooks/use-students';
import { Download, Printer, QrCode, User } from 'lucide-react';
import { QRCodeCanvas } from 'qrcode.react';

export default function MyQRPage() {
  const router = useRouter();
  const qrRef = useRef<HTMLDivElement>(null);

  // React Queryフック
  const { data: profile, isLoading: isUserLoading } = useUser();
  const { data: qrInfo, isLoading: isQRLoading, error: qrError } = useMyQRCode();

  // 生徒アカウントのみアクセス可能（ユーザー情報読み込み後にチェック）
  if (!isUserLoading && profile && profile.userType !== 'student') {
    router.push('/feed');
  }

  const loading = isUserLoading || isQRLoading;
  const error = qrError ? 'QRコードの取得に失敗しました' : null;

  const handleDownload = () => {
    if (!qrRef.current) return;

    const canvas = qrRef.current.querySelector('canvas');
    if (!canvas) return;

    const link = document.createElement('a');
    link.download = `qrcode_${qrInfo?.student_no || 'student'}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  };

  const handlePrint = () => {
    window.print();
  };

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
          <p className="mt-2 text-muted-foreground">読み込み中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <p className="text-destructive">{error}</p>
          <Button onClick={() => router.push('/feed')} className="mt-4">
            ホームに戻る
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background pb-20">
      {/* ヘッダー */}
      <header className="sticky top-0 z-10 bg-background border-b px-4 py-3">
        <div className="flex items-center gap-3">
          <QrCode className="h-6 w-6 text-primary" />
          <h1 className="text-lg font-semibold">マイQRコード</h1>
        </div>
      </header>

      <main className="p-4 space-y-4">
        {/* 生徒情報カード */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <User className="h-4 w-4" />
              生徒情報
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              <p className="text-lg font-semibold">{qrInfo?.student_name}</p>
              <p className="text-sm text-muted-foreground">
                生徒番号: {qrInfo?.student_no}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* QRコード表示カード */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base text-center">出席用QRコード</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col items-center">
            <div
              ref={qrRef}
              className="bg-white p-4 rounded-lg shadow-sm print:shadow-none"
            >
              {qrInfo && (
                <QRCodeCanvas
                  value={qrInfo.qr_code}
                  size={200}
                  level="H"
                  includeMargin
                />
              )}
            </div>

            <p className="mt-4 text-sm text-muted-foreground text-center">
              校舎のタブレットにこのQRコードをかざして
              <br />
              出席を記録してください
            </p>

            {/* 印刷用情報（画面では非表示） */}
            <div className="hidden print:block mt-4 text-center">
              <p className="text-lg font-semibold">{qrInfo?.student_name}</p>
              <p className="text-sm">生徒番号: {qrInfo?.student_no}</p>
            </div>
          </CardContent>
        </Card>

        {/* アクションボタン */}
        <div className="grid grid-cols-2 gap-3 print:hidden">
          <Button
            variant="outline"
            onClick={handleDownload}
            className="w-full"
          >
            <Download className="h-4 w-4 mr-2" />
            ダウンロード
          </Button>
          <Button
            variant="outline"
            onClick={handlePrint}
            className="w-full"
          >
            <Printer className="h-4 w-4 mr-2" />
            印刷
          </Button>
        </div>

        {/* 注意事項 */}
        <Card className="print:hidden">
          <CardContent className="pt-4">
            <div className="text-sm text-muted-foreground space-y-2">
              <p className="font-medium text-foreground">ご注意</p>
              <ul className="list-disc list-inside space-y-1">
                <li>このQRコードは出席記録専用です</li>
                <li>他の人に見せたり共有しないでください</li>
                <li>QRコードを紛失した場合は再発行できます</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </main>

      <BottomTabBar />

      {/* 印刷用スタイル */}
      <style jsx global>{`
        @media print {
          body * {
            visibility: hidden;
          }
          .print\\:block,
          .print\\:block * {
            visibility: visible !important;
          }
          main {
            position: absolute;
            left: 0;
            top: 0;
            visibility: visible !important;
          }
          main * {
            visibility: visible !important;
          }
          header,
          nav,
          .print\\:hidden {
            display: none !important;
          }
        }
      `}</style>
    </div>
  );
}
