'use client';

import { useState, useEffect } from 'react';
import { ChevronLeft, Copy, Share2, UserPlus, Users, Gift, Check, Loader2, Clock, CheckCircle, XCircle } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { isAuthenticated } from '@/lib/api/auth';
import {
  getMyReferralCode,
  registerFriend,
  getFriendsList,
  acceptFriendRequest,
  rejectFriendRequest,
  getFSDiscounts,
  type FriendsListResponse,
  type DiscountsResponse,
} from '@/lib/api/friendship';

export default function FriendReferralPage() {
  const router = useRouter();
  const [myCode, setMyCode] = useState<string>('');
  const [myName, setMyName] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [inputCode, setInputCode] = useState('');
  const [registering, setRegistering] = useState(false);
  const [registerResult, setRegisterResult] = useState<{ success: boolean; message: string } | null>(null);
  const [friendsData, setFriendsData] = useState<FriendsListResponse | null>(null);
  const [discountsData, setDiscountsData] = useState<DiscountsResponse | null>(null);
  const [activeTab, setActiveTab] = useState<'invite' | 'friends' | 'discounts'>('invite');
  const [processingId, setProcessingId] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login');
      return;
    }
    fetchData();
  }, [router]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [codeData, friendsList, discounts] = await Promise.all([
        getMyReferralCode(),
        getFriendsList(),
        getFSDiscounts(),
      ]);
      setMyCode(codeData.referral_code);
      setMyName(codeData.name);
      setFriendsData(friendsList);
      setDiscountsData(discounts);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCopyCode = async () => {
    try {
      await navigator.clipboard.writeText(myCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  };

  const handleShare = async () => {
    const shareText = `OZAスクールの友達紹介コードです！\n\n紹介コード: ${myCode}\n\nこのコードを使って登録すると、お互いに毎月500円割引が受けられます！`;

    if (navigator.share) {
      try {
        await navigator.share({
          title: 'OZA 友達紹介',
          text: shareText,
        });
      } catch (error) {
        if ((error as Error).name !== 'AbortError') {
          console.error('Share failed:', error);
        }
      }
    } else {
      await navigator.clipboard.writeText(shareText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleRegister = async () => {
    if (!inputCode.trim()) {
      setRegisterResult({ success: false, message: '紹介コードを入力してください' });
      return;
    }

    try {
      setRegistering(true);
      setRegisterResult(null);
      const result = await registerFriend(inputCode.trim());
      setRegisterResult({ success: true, message: result.message });
      setInputCode('');
      // 友達リストを更新
      const friendsList = await getFriendsList();
      setFriendsData(friendsList);
    } catch (error: unknown) {
      const errorMessage = error && typeof error === 'object' && 'message' in error
        ? (error as { message: string }).message
        : '登録に失敗しました';
      setRegisterResult({ success: false, message: errorMessage });
    } finally {
      setRegistering(false);
    }
  };

  const handleAccept = async (friendshipId: string) => {
    try {
      setProcessingId(friendshipId);
      await acceptFriendRequest(friendshipId);
      // データを更新
      const [friendsList, discounts] = await Promise.all([
        getFriendsList(),
        getFSDiscounts(),
      ]);
      setFriendsData(friendsList);
      setDiscountsData(discounts);
    } catch (error) {
      console.error('Failed to accept:', error);
    } finally {
      setProcessingId(null);
    }
  };

  const handleReject = async (friendshipId: string) => {
    try {
      setProcessingId(friendshipId);
      await rejectFriendRequest(friendshipId);
      // データを更新
      const friendsList = await getFriendsList();
      setFriendsData(friendsList);
    } catch (error) {
      console.error('Failed to reject:', error);
    } finally {
      setProcessingId(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-pink-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-purple-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-pink-50">
      <header className="sticky top-0 z-40 bg-white shadow-sm">
        <div className="max-w-[390px] mx-auto px-4 h-14 flex items-center">
          <Link href="/" className="mr-3">
            <ChevronLeft className="h-6 w-6 text-gray-700" />
          </Link>
          <h1 className="text-lg font-bold text-gray-800 flex-1 text-center">友達紹介</h1>
          <div className="w-9" />
        </div>
      </header>

      <main className="max-w-[390px] mx-auto px-4 py-6">
        {/* タブ切り替え */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setActiveTab('invite')}
            className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
              activeTab === 'invite'
                ? 'bg-purple-500 text-white'
                : 'bg-white text-gray-600 border border-gray-200'
            }`}
          >
            招待する
          </button>
          <button
            onClick={() => setActiveTab('friends')}
            className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors relative ${
              activeTab === 'friends'
                ? 'bg-purple-500 text-white'
                : 'bg-white text-gray-600 border border-gray-200'
            }`}
          >
            友達一覧
            {(friendsData?.pending_received?.length ?? 0) > 0 && (
              <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
                {friendsData?.pending_received?.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('discounts')}
            className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
              activeTab === 'discounts'
                ? 'bg-purple-500 text-white'
                : 'bg-white text-gray-600 border border-gray-200'
            }`}
          >
            割引情報
          </button>
        </div>

        {activeTab === 'invite' && (
          <>
            {/* 紹介特典説明 */}
            <Card className="rounded-2xl shadow-lg mb-6 overflow-hidden">
              <div className="bg-gradient-to-r from-purple-500 to-pink-500 p-4 text-white">
                <div className="flex items-center gap-3 mb-2">
                  <Gift className="h-8 w-8" />
                  <div>
                    <h2 className="text-lg font-bold">友達紹介特典</h2>
                    <p className="text-purple-100 text-sm">お互いに毎月500円割引！</p>
                  </div>
                </div>
              </div>
              <CardContent className="p-4">
                <ul className="space-y-2 text-sm text-gray-600">
                  <li className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
                    <span>紹介した方・された方、両方に毎月500円割引が適用されます</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
                    <span>お互いが受講している間、割引が継続されます</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
                    <span>どちらかが全退会した場合、割引は終了します</span>
                  </li>
                </ul>
              </CardContent>
            </Card>

            {/* 自分の紹介コード */}
            <Card className="rounded-2xl shadow-lg mb-6">
              <CardContent className="p-4">
                <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                  <Share2 className="h-5 w-5 text-purple-500" />
                  あなたの紹介コード
                </h3>
                <div className="bg-purple-50 rounded-xl p-4 mb-4">
                  <p className="text-3xl font-bold text-purple-600 text-center tracking-widest">
                    {myCode}
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button
                    onClick={handleCopyCode}
                    variant="outline"
                    className="flex-1 border-purple-200 text-purple-600 hover:bg-purple-50"
                  >
                    {copied ? (
                      <>
                        <Check className="h-4 w-4 mr-2" />
                        コピーしました
                      </>
                    ) : (
                      <>
                        <Copy className="h-4 w-4 mr-2" />
                        コピー
                      </>
                    )}
                  </Button>
                  <Button
                    onClick={handleShare}
                    className="flex-1 bg-purple-500 hover:bg-purple-600 text-white"
                  >
                    <Share2 className="h-4 w-4 mr-2" />
                    シェア
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* 紹介コード入力 */}
            <Card className="rounded-2xl shadow-lg">
              <CardContent className="p-4">
                <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                  <UserPlus className="h-5 w-5 text-pink-500" />
                  紹介コードを入力
                </h3>
                <p className="text-sm text-gray-500 mb-3">
                  友達から受け取った紹介コードを入力してください
                </p>
                <div className="flex gap-2 mb-3">
                  <Input
                    type="text"
                    placeholder="紹介コードを入力"
                    value={inputCode}
                    onChange={(e) => setInputCode(e.target.value)}
                    className="flex-1"
                    maxLength={20}
                  />
                  <Button
                    onClick={handleRegister}
                    disabled={registering || !inputCode.trim()}
                    className="bg-pink-500 hover:bg-pink-600 text-white"
                  >
                    {registering ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      '登録'
                    )}
                  </Button>
                </div>
                {registerResult && (
                  <div className={`p-3 rounded-lg text-sm ${
                    registerResult.success
                      ? 'bg-green-50 text-green-700'
                      : 'bg-red-50 text-red-700'
                  }`}>
                    {registerResult.message}
                  </div>
                )}
              </CardContent>
            </Card>
          </>
        )}

        {activeTab === 'friends' && friendsData && (
          <>
            {/* 承認待ちの申請 */}
            {(friendsData.pending_received?.length ?? 0) > 0 && (
              <Card className="rounded-2xl shadow-lg mb-4">
                <CardContent className="p-4">
                  <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                    <Clock className="h-5 w-5 text-orange-500" />
                    承認待ち
                    <span className="ml-auto bg-orange-100 text-orange-600 text-xs px-2 py-1 rounded-full">
                      {friendsData.pending_received?.length ?? 0}件
                    </span>
                  </h3>
                  <div className="space-y-3">
                    {friendsData.pending_received?.map((request) => (
                      <div key={request.id} className="flex items-center justify-between p-3 bg-orange-50 rounded-lg">
                        <div>
                          <p className="font-medium text-gray-800">{request.name}</p>
                          <p className="text-xs text-gray-500">
                            {new Date(request.requested_at).toLocaleDateString('ja-JP')}
                          </p>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            onClick={() => handleAccept(request.id)}
                            disabled={processingId === request.id}
                            className="bg-green-500 hover:bg-green-600 text-white"
                          >
                            {processingId === request.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <CheckCircle className="h-4 w-4" />
                            )}
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleReject(request.id)}
                            disabled={processingId === request.id}
                            className="border-red-200 text-red-500 hover:bg-red-50"
                          >
                            <XCircle className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* 申請中 */}
            {(friendsData.pending_sent?.length ?? 0) > 0 && (
              <Card className="rounded-2xl shadow-lg mb-4">
                <CardContent className="p-4">
                  <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                    <Clock className="h-5 w-5 text-blue-500" />
                    申請中
                  </h3>
                  <div className="space-y-2">
                    {friendsData.pending_sent?.map((request) => (
                      <div key={request.id} className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
                        <div>
                          <p className="font-medium text-gray-800">{request.name}</p>
                          <p className="text-xs text-gray-500">
                            {new Date(request.requested_at).toLocaleDateString('ja-JP')}に申請
                          </p>
                        </div>
                        <span className="text-xs text-blue-600 bg-blue-100 px-2 py-1 rounded-full">
                          承認待ち
                        </span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* 友達一覧 */}
            <Card className="rounded-2xl shadow-lg">
              <CardContent className="p-4">
                <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                  <Users className="h-5 w-5 text-purple-500" />
                  友達一覧
                  <span className="ml-auto text-sm text-gray-500">
                    {friendsData.friends?.length ?? 0}人
                  </span>
                </h3>
                {(friendsData.friends?.length ?? 0) > 0 ? (
                  <div className="space-y-2">
                    {friendsData.friends?.map((friend) => (
                      <div key={friend.id} className="flex items-center gap-3 p-3 bg-purple-50 rounded-lg">
                        <div className="w-10 h-10 bg-purple-200 rounded-full flex items-center justify-center">
                          <Users className="h-5 w-5 text-purple-600" />
                        </div>
                        <div>
                          <p className="font-medium text-gray-800">{friend.name}</p>
                          <p className="text-xs text-gray-500">毎月500円割引中</p>
                        </div>
                        <CheckCircle className="h-5 w-5 text-green-500 ml-auto" />
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-center text-gray-500 py-4">
                    まだ友達がいません。<br />
                    紹介コードを共有して友達を招待しましょう！
                  </p>
                )}
              </CardContent>
            </Card>
          </>
        )}

        {activeTab === 'discounts' && discountsData && (
          <Card className="rounded-2xl shadow-lg">
            <CardContent className="p-4">
              <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                <Gift className="h-5 w-5 text-green-500" />
                友達紹介割引
              </h3>

              {/* 合計割引額 */}
              <div className="bg-gradient-to-r from-green-500 to-emerald-500 rounded-xl p-4 mb-4 text-white">
                <p className="text-sm opacity-90">毎月の割引額</p>
                <p className="text-3xl font-bold">
                  ¥{(discountsData.total_discount ?? 0).toLocaleString()}
                </p>
              </div>

              {(discountsData.discounts?.length ?? 0) > 0 ? (
                <div className="space-y-3">
                  {discountsData.discounts?.map((discount) => (
                    <div key={discount.id} className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                      <div>
                        <p className="font-medium text-gray-800">{discount.friend_name}さんとの紹介割引</p>
                        <p className="text-xs text-gray-500">
                          {discount.valid_until
                            ? `${discount.valid_until}まで有効`
                            : '継続中'}
                        </p>
                      </div>
                      <span className="text-lg font-bold text-green-600">
                        -¥{discount.discount_value.toLocaleString()}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-center text-gray-500 py-4">
                  現在適用中の友達紹介割引はありません。<br />
                  友達を紹介すると毎月500円割引が適用されます！
                </p>
              )}
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}
