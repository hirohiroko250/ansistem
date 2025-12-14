/**
 * 金融機関選択API
 * Django APIを使用して金融機関・支店データを取得
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

// 金融機関種別（Django BankTypeモデルと連携）
export const BUSINESS_TYPES = [
  { code: 'city', name: '都市銀行', label: '都市銀行' },
  { code: 'regional', name: '地方銀行', label: '地方銀行' },
  { code: 'second_regional', name: '第二地方銀行', label: '第二地銀' },
  { code: 'shinkin', name: '信用金庫', label: '信用金庫' },
  { code: 'credit_union', name: '信用組合', label: '信用組合' },
  { code: 'net', name: 'ネット銀行', label: 'ネット銀行' },
  { code: 'yucho', name: 'ゆうちょ銀行', label: 'ゆうちょ' },
  { code: 'trust', name: '信託銀行', label: '信託銀行' },
  { code: 'rokin', name: '労働金庫', label: '労働金庫' },
  { code: 'ja', name: '農業協同組合', label: '農協(JA)' },
] as const;

export type BusinessType = typeof BUSINESS_TYPES[number];

// あいうえお行
export const AIUEO_ROWS = [
  { row: 'あ', start: 'あ', end: 'お' },
  { row: 'か', start: 'か', end: 'こ' },
  { row: 'さ', start: 'さ', end: 'そ' },
  { row: 'た', start: 'た', end: 'と' },
  { row: 'な', start: 'な', end: 'の' },
  { row: 'は', start: 'は', end: 'ほ' },
  { row: 'ま', start: 'ま', end: 'も' },
  { row: 'や', start: 'や', end: 'よ' },
  { row: 'ら', start: 'ら', end: 'ろ' },
  { row: 'わ', start: 'わ', end: 'を' },
] as const;

export interface Bank {
  code: string;
  name: string;
  hiragana: string;
  katakana: string;
  businessTypeCode?: string;
}

export interface Branch {
  code: string;
  name: string;
  hiragana: string;
  katakana: string;
}

// APIレスポンス型（Django APIはcamelCaseで返す）
interface ApiBankType {
  id: string;
  typeCode: string;
  typeName: string;
  typeLabel: string;
  sortOrder: number;
  isActive: boolean;
}

interface ApiBank {
  id: string;
  bankCode: string;
  bankName: string;
  bankNameKana: string;
  bankNameHalfKana: string;
  bankNameHiragana: string;
  aiueoRow: string;
  bankType: string | null;
  bankTypeName: string | null;
  sortOrder: number;
  isActive: boolean;
  branchCount?: number;
}

interface ApiBranch {
  id: string;
  branchCode: string;
  branchName: string;
  branchNameKana: string;
  branchNameHalfKana: string;
  branchNameHiragana: string;
  aiueoRow: string;
  sortOrder: number;
  isActive: boolean;
}

// BankType IDをキャッシュ
let bankTypeCache: ApiBankType[] | null = null;

/**
 * 金融機関種別一覧を取得
 */
async function fetchBankTypes(): Promise<ApiBankType[]> {
  if (bankTypeCache) {
    return bankTypeCache;
  }

  try {
    const response = await fetch(`${API_BASE}/schools/public/bank-types/`);
    if (!response.ok) {
      console.error('Failed to fetch bank types:', response.status);
      return [];
    }
    const data = await response.json();
    bankTypeCache = data;
    return data;
  } catch (error) {
    console.error('Failed to fetch bank types:', error);
    return [];
  }
}

/**
 * 金融機関種別コードからBankType IDを取得
 */
async function getBankTypeId(typeCode: string): Promise<string | null> {
  const bankTypes = await fetchBankTypes();
  const bankType = bankTypes.find(t => t.typeCode === typeCode);
  return bankType?.id || null;
}

/**
 * あいうえお行で銀行一覧を取得（種別を問わず全銀行）
 */
export async function getBanksByAiueo(aiueoRow: string): Promise<Bank[]> {
  try {
    const params = new URLSearchParams();
    params.append('aiueo_row', aiueoRow);

    const url = `${API_BASE}/schools/public/banks/?${params.toString()}`;
    const response = await fetch(url);

    if (!response.ok) {
      console.error('Failed to fetch banks by aiueo:', response.status);
      return [];
    }

    const data: ApiBank[] = await response.json();

    return data.map(bank => ({
      code: bank.bankCode,
      name: bank.bankName,
      hiragana: bank.bankNameHiragana || '',
      katakana: bank.bankNameKana || '',
      businessTypeCode: bank.bankType || undefined,
    }));
  } catch (error) {
    console.error('Failed to fetch banks by aiueo:', error);
    return [];
  }
}

/**
 * 金融機関種別で銀行一覧を取得（Django API使用）
 */
export async function getBanksByType(
  businessTypeCode: string,
  aiueoRow?: string
): Promise<Bank[]> {
  try {
    // BankType IDを取得
    const bankTypeId = await getBankTypeId(businessTypeCode);

    // クエリパラメータを構築
    const params = new URLSearchParams();
    if (bankTypeId) {
      params.append('bank_type_id', bankTypeId);
    }
    if (aiueoRow) {
      params.append('aiueo_row', aiueoRow);
    }

    const url = `${API_BASE}/schools/public/banks/?${params.toString()}`;
    const response = await fetch(url);

    if (!response.ok) {
      console.error('Failed to fetch banks:', response.status);
      return [];
    }

    const data: ApiBank[] = await response.json();

    // APIレスポンスをBank型に変換
    return data.map(bank => ({
      code: bank.bankCode,
      name: bank.bankName,
      hiragana: bank.bankNameHiragana || '',
      katakana: bank.bankNameKana || '',
      businessTypeCode: bank.bankType || undefined,
    }));
  } catch (error) {
    console.error('Failed to fetch banks by type:', error);
    return [];
  }
}

/**
 * 金融機関名で検索（Django API使用）
 */
export async function searchBanks(
  query: string,
  businessTypeCode?: string
): Promise<Bank[]> {
  if (!query || query.length < 1) {
    return [];
  }

  try {
    // 全銀行を取得してフロントエンドでフィルタリング
    const params = new URLSearchParams();
    if (businessTypeCode) {
      const bankTypeId = await getBankTypeId(businessTypeCode);
      if (bankTypeId) {
        params.append('bank_type_id', bankTypeId);
      }
    }

    const url = `${API_BASE}/schools/public/banks/?${params.toString()}`;
    const response = await fetch(url);

    if (!response.ok) {
      console.error('Failed to fetch banks for search:', response.status);
      return [];
    }

    const data: ApiBank[] = await response.json();

    // 検索フィルタリング
    const queryLower = query.toLowerCase();
    const filteredData = data.filter(bank =>
      bank.bankName.includes(query) ||
      (bank.bankNameHiragana && bank.bankNameHiragana.includes(queryLower)) ||
      (bank.bankNameKana && bank.bankNameKana.includes(query))
    );

    // Bank型に変換
    return filteredData.map(bank => ({
      code: bank.bankCode,
      name: bank.bankName,
      hiragana: bank.bankNameHiragana || '',
      katakana: bank.bankNameKana || '',
      businessTypeCode: bank.bankType || undefined,
    }));
  } catch (error) {
    console.error('Failed to search banks:', error);
    return [];
  }
}

/**
 * 特定の銀行の支店一覧を取得（Django API使用）
 */
export async function getBranches(bankCode: string): Promise<Branch[]> {
  try {
    // まず銀行IDを取得（bank_codeから）
    const banksResponse = await fetch(`${API_BASE}/schools/public/banks/`);
    if (!banksResponse.ok) {
      console.error('Failed to fetch banks for branch lookup:', banksResponse.status);
      return [];
    }

    const banks: ApiBank[] = await banksResponse.json();
    const bank = banks.find(b => b.bankCode === bankCode);

    if (!bank) {
      console.error('Bank not found:', bankCode);
      return [];
    }

    // 支店一覧を取得
    const response = await fetch(`${API_BASE}/schools/public/banks/${bank.id}/branches/`);

    if (!response.ok) {
      console.error('Failed to fetch branches:', response.status);
      return [];
    }

    const data: ApiBranch[] = await response.json();

    // Branch型に変換
    return data.map(branch => ({
      code: branch.branchCode,
      name: branch.branchName,
      hiragana: branch.branchNameHiragana || '',
      katakana: branch.branchNameKana || '',
    }));
  } catch (error) {
    console.error('Failed to fetch branches:', error);
    return [];
  }
}

/**
 * 支店をあいうえお行でフィルタリング
 */
export function filterBranchesByAiueo(
  branches: Branch[],
  aiueoRow: string
): Branch[] {
  const row = AIUEO_ROWS.find((r) => r.row === aiueoRow);
  if (!row) return branches;

  return branches.filter((branch) => {
    const firstChar = branch.hiragana.charAt(0);
    // 濁音・半濁音の対応
    const baseChar = firstChar
      .replace(/[がぎぐげご]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 1))
      .replace(/[ざじずぜぞ]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 1))
      .replace(/[だぢづでど]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 1))
      .replace(/[ばびぶべぼ]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 1))
      .replace(/[ぱぴぷぺぽ]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 2));

    return baseChar >= row.start && baseChar <= row.end;
  });
}

// 後方互換性のため
export type { Bank as OldBank, Branch as OldBranch };

/**
 * 旧API互換
 * @deprecated 新しいgetBanksByType()を使用してください
 */
export async function getBanks(): Promise<Bank[]> {
  try {
    const response = await fetch(`${API_BASE}/schools/public/banks/`);
    if (!response.ok) {
      console.error('Failed to fetch all banks:', response.status);
      return [];
    }

    const data: ApiBank[] = await response.json();

    return data.map(bank => ({
      code: bank.bankCode,
      name: bank.bankName,
      hiragana: bank.bankNameHiragana || '',
      katakana: bank.bankNameKana || '',
      businessTypeCode: bank.bankType || undefined,
    }));
  } catch (error) {
    console.error('Failed to fetch banks:', error);
    return [];
  }
}
