/**
 * Friendship API - 友達紹介
 */
import { apiClient } from './client';

// 自分の紹介コード取得
export type MyCodeResponse = {
  referral_code: string;
  name: string;
};

export async function getMyReferralCode(): Promise<MyCodeResponse> {
  const response = await apiClient.get('/students/friendship/my_code/');
  return response.data.data;
}

// 友達コードで登録
export type RegisterFriendResponse = {
  message: string;
  status: 'pending' | 'accepted';
  friend_name: string;
  friendship_id?: string;
};

export async function registerFriend(referralCode: string): Promise<RegisterFriendResponse> {
  const response = await apiClient.post('/students/friendship/register/', {
    referral_code: referralCode,
  });
  return response.data.data;
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
  const response = await apiClient.get('/students/friendship/list_friends/');
  return response.data.data;
}

// 友達申請を承認
export async function acceptFriendRequest(friendshipId: string): Promise<{ message: string; friend_name: string }> {
  const response = await apiClient.post(`/students/friendship/${friendshipId}/accept/`);
  return response.data.data;
}

// 友達申請を拒否
export async function rejectFriendRequest(friendshipId: string): Promise<{ message: string }> {
  const response = await apiClient.post(`/students/friendship/${friendshipId}/reject/`);
  return response.data.data;
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
  const response = await apiClient.get('/students/friendship/discounts/');
  return response.data.data;
}
