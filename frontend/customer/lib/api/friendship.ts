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
  referral_code?: string;
  referralCode?: string;
  name: string;
};

export async function getMyReferralCode(): Promise<MyCodeResponse> {
  const response = await api.get<ApiResponse<MyCodeResponse>>('/students/friendship/my_code/');

  // Handle different response structures
  const resp = response as unknown as Record<string, unknown>;

  // If response has data property
  if (resp.data && typeof resp.data === 'object') {
    const data = resp.data as Record<string, unknown>;
    // Check for both camelCase and snake_case
    if ('referralCode' in data || 'referral_code' in data) {
      return resp.data as MyCodeResponse;
    }
  }

  // If response directly contains referralCode or referral_code (already unwrapped)
  if ('referralCode' in resp || 'referral_code' in resp) {
    return resp as unknown as MyCodeResponse;
  }

  throw new Error('Invalid API response format for referral code');
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
  const resp = response as unknown as Record<string, unknown>;
  if (resp.data && typeof resp.data === 'object') {
    return resp.data as RegisterFriendResponse;
  }
  if ('message' in resp) {
    return resp as unknown as RegisterFriendResponse;
  }
  throw new Error('Invalid API response format');
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
  const resp = response as unknown as Record<string, unknown>;
  if (resp.data && typeof resp.data === 'object') {
    return resp.data as FriendsListResponse;
  }
  if ('friends' in resp) {
    return resp as unknown as FriendsListResponse;
  }
  throw new Error('Invalid API response format');
}

// 友達申請を承認
export async function acceptFriendRequest(friendshipId: string): Promise<{ message: string; friend_name: string }> {
  const response = await api.post<ApiResponse<{ message: string; friend_name: string }>>(`/students/friendship/${friendshipId}/accept/`);
  const resp = response as unknown as Record<string, unknown>;
  if (resp.data && typeof resp.data === 'object') {
    return resp.data as { message: string; friend_name: string };
  }
  if ('message' in resp) {
    return resp as unknown as { message: string; friend_name: string };
  }
  throw new Error('Invalid API response format');
}

// 友達申請を拒否
export async function rejectFriendRequest(friendshipId: string): Promise<{ message: string }> {
  const response = await api.post<ApiResponse<{ message: string }>>(`/students/friendship/${friendshipId}/reject/`);
  const resp = response as unknown as Record<string, unknown>;
  if (resp.data && typeof resp.data === 'object') {
    return resp.data as { message: string };
  }
  if ('message' in resp) {
    return resp as unknown as { message: string };
  }
  throw new Error('Invalid API response format');
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
  const resp = response as unknown as Record<string, unknown>;
  if (resp.data && typeof resp.data === 'object') {
    return resp.data as DiscountsResponse;
  }
  if ('discounts' in resp) {
    return resp as unknown as DiscountsResponse;
  }
  throw new Error('Invalid API response format');
}
