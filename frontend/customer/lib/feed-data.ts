/**
 * フィードデータ（ダミー）
 */

export interface Post {
  id: number;
  type: '新着' | 'お知らせ' | 'イベント';
  caption: string;
  date: string;
  imageUrl?: string;
}

export const posts: Post[] = [
  {
    id: 1,
    type: '新着',
    caption: '冬期講習の受付を開始しました。お早めにお申し込みください。',
    date: '2024年12月1日',
  },
  {
    id: 2,
    type: 'お知らせ',
    caption: '年末年始の休校日程についてのお知らせ',
    date: '2024年11月28日',
  },
  {
    id: 3,
    type: 'イベント',
    caption: '保護者説明会のご案内 - 12月15日開催',
    date: '2024年11月25日',
  },
  {
    id: 4,
    type: '新着',
    caption: '新しい英会話コースが開講します',
    date: '2024年11月20日',
  },
];
