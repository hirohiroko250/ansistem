/**
 * Friendship API - 友達紹介
 */
import api from './client';

// APIレスポンスのラッパー型
type ApiResponse<T> = {
  success: boolean;
  data: T;
};

// 自分の紹介コード取得
export type MyCodeResponse = {
  referral_code: string;
  name: string;
};

export async function getMyReferralCode(): Promise<MyCodeResponse> {
  const response = await api.get<ApiResponse<MyCodeResponse>>('/students/friendship/my_code/');
  console.log('API raw response:', JSON.stringify(response));
  console.log('response.data:', JSON.stringify(response.data));
  return response.data;
}

// 友達コードで登録
export type RegisterFriendResponse = {
  message: string;
  status: 'pending' | 'accepted';
  friend_name: string;
  friendship_id?: string;
};

export async function registerFriend(referralCode: string): Promise<RegisterFriendResponse> {
  const response = await api.post<ApiResponse<RegisterFriendResponse>>('/students/friendship/register/', {
    referral_code: referralCode,
  });
  return response.data;
}

// 友達一覧取得
export type Friend = {
  id: string;
  name: string;
  guardian_no: string;
};

export type PendingRequest = {
  id: string;
  name: string;
  requested_at: string;
};

export type FriendsListResponse = {
  friends: Friend[];
  pending_sent: PendingRequest[];
  pending_received: PendingRequest[];
};

export async function getFriendsList(): Promise<FriendsListResponse> {
  const response = await api.get<ApiResponse<FriendsListResponse>>('/students/friendship/list_friends/');
  return response.data;
}

// 友達申請を承認
export async function acceptFriendRequest(friendshipId: string): Promise<{ message: string; friend_name: string }> {
  const response = await api.post<ApiResponse<{ message: string; friend_name: string }>>(`/students/friendship/${friendshipId}/accept/`);
  return response.data;
}

// 友達申請を拒否
export async function rejectFriendRequest(friendshipId: string): Promise<{ message: string }> {
  const response = await api.post<ApiResponse<{ message: string }>>(`/students/friendship/${friendshipId}/reject/`);
  return response.data;
}

// 割引一覧取得
export type FSDiscountInfo = {
  id: string;
  discount_type: string;
  discount_value: number;
  status: string;
  valid_from: string | null;
  valid_until: string | null;
  friend_name: string;
};

export type DiscountsResponse = {
  discounts: FSDiscountInfo[];
  total_discount: number;
};

export async function getFSDiscounts(): Promise<DiscountsResponse> {
  const response = await api.get<ApiResponse<DiscountsResponse>>('/students/friendship/discounts/');
  return response.data;
}
