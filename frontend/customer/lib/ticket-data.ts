import { Calculator, GraduationCap, Users, MessageCircle, PenTool, Ticket, Globe } from 'lucide-react';

export const brands = [
  { id: 'AEC', name: 'アンイングリッシュ', icon: MessageCircle, color: 'bg-orange-100 text-orange-600' },
  { id: 'SOR', name: 'そろばん', icon: Calculator, color: 'bg-blue-100 text-blue-600' },
  { id: 'KID', name: 'さんこくキッズ', icon: GraduationCap, color: 'bg-green-100 text-green-600' },
  { id: 'PRO', name: 'プログラミング', icon: Users, color: 'bg-purple-100 text-purple-600' },
  { id: 'BMC', name: '習字', icon: PenTool, color: 'bg-pink-100 text-pink-600' },
  { id: 'INT', name: 'インターナショナル', icon: Globe, color: 'bg-cyan-100 text-cyan-600' },
  { id: 'SHO', name: '将棋', icon: Ticket, color: 'bg-red-100 text-red-600' },
];

export const regions = [
  { id: 'nagoya', name: '名古屋市', area: '愛知県' },
  { id: 'aichi-west', name: '尾張地方', area: '愛知県' },
  { id: 'aichi-east', name: '三河地方', area: '愛知県' },
  { id: 'gifu-city', name: '岐阜市周辺', area: '岐阜県' },
  { id: 'gifu-west', name: '西濃地方', area: '岐阜県' },
];

export type Company = {
  id: number;
  name: string;
  region: string;
  brand: string;
  schoolCount: number;
  color: string;
  schools: {
    id: number;
    name: string;
    address: string;
    position?: { x: number; y: number };
  }[];
  courses: {
    id: number;
    name: string;
    tickets: number;
    price: number;
    description: string;
    popular?: boolean;
    isMonthly: boolean;
    type?: string;
    eventDate?: string;
  }[];
};

export const companies: Company[] = [
  {
    id: 1,
    name: 'ABC教育グループ',
    region: 'nagoya',
    brand: 'soroban',
    schoolCount: 5,
    color: '#3B82F6',
    schools: [
      { id: 1, name: '○○そろばん教室 栄校', address: '愛知県名古屋市中区栄1-2-3', position: { x: 30, y: 40 } },
      { id: 2, name: '○○そろばん教室 金山校', address: '愛知県名古屋市中区金山4-5-6', position: { x: 55, y: 70 } },
    ],
    courses: [
      { id: 1, name: '週1コース', tickets: 4, price: 6000, description: '月4回のレッスン', isMonthly: true },
      { id: 2, name: '週2コース', tickets: 8, price: 12000, description: '月8回のレッスン', popular: true, isMonthly: true },
      { id: 3, name: '回数券（1回）', tickets: 1, price: 1500, description: '都度利用', isMonthly: false },
      { id: 4, name: '入会金', tickets: 0, price: 10000, description: '初回のみ', type: 'fee', isMonthly: false },
    ]
  },
  {
    id: 2,
    name: 'XYZ教育株式会社',
    region: 'nagoya',
    brand: 'soroban',
    schoolCount: 3,
    color: '#10B981',
    schools: [
      { id: 3, name: '○○そろばん教室 名駅校', address: '愛知県名古屋市中村区名駅2-3-4', position: { x: 70, y: 30 } },
    ],
    courses: [
      { id: 1, name: '週1コース', tickets: 4, price: 7000, description: '月4回のレッスン', isMonthly: true },
      { id: 2, name: '週2コース', tickets: 8, price: 13500, description: '月8回のレッスン', popular: true, isMonthly: true },
      { id: 3, name: '週3コース', tickets: 12, price: 18000, description: '月12回のレッスン', isMonthly: true },
      { id: 4, name: '回数券（1回）', tickets: 1, price: 2000, description: '都度利用', isMonthly: false },
      { id: 5, name: '入会金', tickets: 0, price: 15000, description: '初回のみ', type: 'fee', isMonthly: false },
    ]
  },
  {
    id: 3,
    name: '進学塾ABCグループ',
    region: 'nagoya',
    brand: 'juku',
    schoolCount: 8,
    color: '#8B5CF6',
    schools: [
      { id: 4, name: '進学塾ABC 千種校', address: '愛知県名古屋市千種区5-6-7', position: { x: 40, y: 55 } },
      { id: 5, name: '進学塾ABC 星ヶ丘校', address: '愛知県名古屋市千種区星が丘8-9-10', position: { x: 65, y: 60 } },
    ],
    courses: [
      { id: 1, name: '週1コース', tickets: 4, price: 8000, description: '月4回の授業', isMonthly: true },
      { id: 2, name: '週2コース', tickets: 8, price: 15000, description: '月8回の授業', popular: true, isMonthly: true },
      { id: 3, name: '回数券（1回）', tickets: 1, price: 2500, description: '都度利用', isMonthly: false },
      { id: 4, name: '入会金', tickets: 0, price: 20000, description: '初回のみ', type: 'fee', isMonthly: false },
    ]
  },
  {
    id: 4,
    name: '学童クラブ○○運営会社',
    region: 'nagoya',
    brand: 'gakudo',
    schoolCount: 2,
    color: '#F59E0B',
    schools: [
      { id: 6, name: '学童クラブ○○', address: '愛知県名古屋市昭和区8-9-10', position: { x: 50, y: 45 } },
    ],
    courses: [
      { id: 1, name: '週5コース', tickets: 20, price: 25000, description: '月20回（平日毎日）', isMonthly: true, popular: true },
      { id: 2, name: '週3コース', tickets: 12, price: 18000, description: '月12回', isMonthly: true },
      { id: 3, name: '回数券（1回）', tickets: 1, price: 2000, description: '都度利用', isMonthly: false },
      { id: 4, name: '入会金', tickets: 0, price: 10000, description: '初回のみ', type: 'fee', isMonthly: false },
    ]
  },
  {
    id: 5,
    name: 'English Education Co.',
    region: 'gifu-city',
    brand: 'eikaiwa',
    schoolCount: 4,
    color: '#EF4444',
    schools: [
      { id: 7, name: 'イングリッシュスクール○○', address: '岐阜県岐阜市長住町11-12-13', position: { x: 25, y: 65 } },
    ],
    courses: [
      { id: 1, name: '週1コース', tickets: 4, price: 9000, description: '月4回のレッスン', isMonthly: true },
      { id: 2, name: '週2コース', tickets: 8, price: 16000, description: '月8回のレッスン', popular: true, isMonthly: true },
      { id: 3, name: 'プライベートレッスン（1回）', tickets: 1, price: 5000, description: 'マンツーマン', isMonthly: false },
      { id: 4, name: '入会金', tickets: 0, price: 12000, description: '初回のみ', type: 'fee', isMonthly: false },
    ]
  },
  {
    id: 6,
    name: '書道教室○○',
    region: 'aichi-west',
    brand: 'shodo',
    schoolCount: 1,
    color: '#EC4899',
    schools: [
      { id: 8, name: '書道教室○○', address: '愛知県一宮市○○14-15-16', position: { x: 45, y: 50 } },
    ],
    courses: [
      { id: 1, name: '週1コース', tickets: 4, price: 5000, description: '月4回のお稽古', isMonthly: true },
      { id: 2, name: '週2コース', tickets: 8, price: 9000, description: '月8回のお稽古', popular: true, isMonthly: true },
      { id: 3, name: '回数券（1回）', tickets: 1, price: 1500, description: '都度利用', isMonthly: false },
      { id: 4, name: '入会金', tickets: 0, price: 5000, description: '初回のみ', type: 'fee', isMonthly: false },
    ]
  },
  {
    id: 7,
    name: 'MyLesson運営',
    region: 'nagoya',
    brand: 'event',
    schoolCount: 1,
    color: '#6366F1',
    schools: [
      { id: 9, name: 'イベントチケット', address: '各教室で開催', position: { x: 60, y: 50 } },
    ],
    courses: [
      { id: 1, name: '夏祭りイベント', tickets: 1, price: 2000, description: '2025年8月10日開催', isMonthly: false, eventDate: '2025-08-10' },
      { id: 2, name: 'そろばん大会', tickets: 1, price: 3000, description: '2025年9月15日開催', isMonthly: false, eventDate: '2025-09-15', popular: true },
      { id: 3, name: '英語スピーチコンテスト', tickets: 1, price: 2500, description: '2025年10月20日開催', isMonthly: false, eventDate: '2025-10-20' },
      { id: 4, name: '無料体験会', tickets: 1, price: 0, description: '随時開催', isMonthly: false, type: 'free' },
    ]
  },
];

export const calculateAdditionalTickets = (course: any) => {
  const today = new Date();
  const currentDay = today.getDate();
  const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0).getDate();

  if (currentDay <= 5) {
    return { needed: false, tickets: 0, price: 0 };
  }

  const remainingDays = lastDay - currentDay;
  const ratio = remainingDays / lastDay;
  const additionalTickets = Math.ceil(course.tickets * ratio);
  const ticketPrice = course.price / course.tickets;
  const additionalPrice = Math.ceil(additionalTickets * ticketPrice);

  return {
    needed: true,
    tickets: additionalTickets,
    price: additionalPrice,
    currentDay,
    lastDay,
  };
};

export type ClassSchedule = {
  id: number;
  schoolId: number;
  dayOfWeek: string;
  startTime: string;
  endTime: string;
  maxSeats: number;
  currentSeats: number;
  instructor: string;
};

export const classSchedules: ClassSchedule[] = [
  { id: 1, schoolId: 1, dayOfWeek: '月曜日', startTime: '16:00', endTime: '17:00', maxSeats: 10, currentSeats: 7, instructor: '佐藤先生' },
  { id: 2, schoolId: 1, dayOfWeek: '月曜日', startTime: '17:00', endTime: '18:00', maxSeats: 10, currentSeats: 9, instructor: '佐藤先生' },
  { id: 3, schoolId: 1, dayOfWeek: '火曜日', startTime: '16:00', endTime: '17:00', maxSeats: 10, currentSeats: 5, instructor: '田中先生' },
  { id: 4, schoolId: 1, dayOfWeek: '水曜日', startTime: '16:00', endTime: '17:00', maxSeats: 10, currentSeats: 3, instructor: '佐藤先生' },
  { id: 5, schoolId: 1, dayOfWeek: '木曜日', startTime: '16:00', endTime: '17:00', maxSeats: 10, currentSeats: 8, instructor: '田中先生' },
  { id: 6, schoolId: 1, dayOfWeek: '金曜日', startTime: '16:00', endTime: '17:00', maxSeats: 10, currentSeats: 10, instructor: '佐藤先生' },
  { id: 7, schoolId: 2, dayOfWeek: '月曜日', startTime: '15:00', endTime: '16:00', maxSeats: 12, currentSeats: 6, instructor: '山田先生' },
  { id: 8, schoolId: 2, dayOfWeek: '水曜日', startTime: '15:00', endTime: '16:00', maxSeats: 12, currentSeats: 4, instructor: '山田先生' },
  { id: 9, schoolId: 2, dayOfWeek: '金曜日', startTime: '15:00', endTime: '16:00', maxSeats: 12, currentSeats: 11, instructor: '鈴木先生' },
];
