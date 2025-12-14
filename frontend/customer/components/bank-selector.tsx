'use client';

import { useState, useEffect } from 'react';
import { Loader2, Search } from 'lucide-react';
import {
  getBanksByAiueo,
  getBranches,
  searchBanks,
  filterBranchesByAiueo,
  AIUEO_ROWS,
  type Bank,
  type Branch,
} from '@/lib/api/bank-api';

// 全角カタカナ→半角カタカナ変換
function toHalfWidthKatakana(str: string): string {
  const kanaMap: Record<string, string> = {
    'ア': 'ｱ', 'イ': 'ｲ', 'ウ': 'ｳ', 'エ': 'ｴ', 'オ': 'ｵ',
    'カ': 'ｶ', 'キ': 'ｷ', 'ク': 'ｸ', 'ケ': 'ｹ', 'コ': 'ｺ',
    'サ': 'ｻ', 'シ': 'ｼ', 'ス': 'ｽ', 'セ': 'ｾ', 'ソ': 'ｿ',
    'タ': 'ﾀ', 'チ': 'ﾁ', 'ツ': 'ﾂ', 'テ': 'ﾃ', 'ト': 'ﾄ',
    'ナ': 'ﾅ', 'ニ': 'ﾆ', 'ヌ': 'ﾇ', 'ネ': 'ﾈ', 'ノ': 'ﾉ',
    'ハ': 'ﾊ', 'ヒ': 'ﾋ', 'フ': 'ﾌ', 'ヘ': 'ﾍ', 'ホ': 'ﾎ',
    'マ': 'ﾏ', 'ミ': 'ﾐ', 'ム': 'ﾑ', 'メ': 'ﾒ', 'モ': 'ﾓ',
    'ヤ': 'ﾔ', 'ユ': 'ﾕ', 'ヨ': 'ﾖ',
    'ラ': 'ﾗ', 'リ': 'ﾘ', 'ル': 'ﾙ', 'レ': 'ﾚ', 'ロ': 'ﾛ',
    'ワ': 'ﾜ', 'ヲ': 'ｦ', 'ン': 'ﾝ',
    'ァ': 'ｧ', 'ィ': 'ｨ', 'ゥ': 'ｩ', 'ェ': 'ｪ', 'ォ': 'ｫ',
    'ッ': 'ｯ', 'ャ': 'ｬ', 'ュ': 'ｭ', 'ョ': 'ｮ',
    'ガ': 'ｶﾞ', 'ギ': 'ｷﾞ', 'グ': 'ｸﾞ', 'ゲ': 'ｹﾞ', 'ゴ': 'ｺﾞ',
    'ザ': 'ｻﾞ', 'ジ': 'ｼﾞ', 'ズ': 'ｽﾞ', 'ゼ': 'ｾﾞ', 'ゾ': 'ｿﾞ',
    'ダ': 'ﾀﾞ', 'ヂ': 'ﾁﾞ', 'ヅ': 'ﾂﾞ', 'デ': 'ﾃﾞ', 'ド': 'ﾄﾞ',
    'バ': 'ﾊﾞ', 'ビ': 'ﾋﾞ', 'ブ': 'ﾌﾞ', 'ベ': 'ﾍﾞ', 'ボ': 'ﾎﾞ',
    'パ': 'ﾊﾟ', 'ピ': 'ﾋﾟ', 'プ': 'ﾌﾟ', 'ペ': 'ﾍﾟ', 'ポ': 'ﾎﾟ',
    'ヴ': 'ｳﾞ',
    'ー': 'ｰ', '・': '･', '「': '｢', '」': '｣', '。': '｡', '、': '､',
  };

  return str.split('').map(char => kanaMap[char] || char).join('');
}

interface BankSelectorProps {
  onSelect: (data: {
    bankName: string;
    bankCode: string;
    branchName: string;
    branchCode: string;
    bankNameKana: string;      // 半角カタカナ
    branchNameKana: string;    // 半角カタカナ
  }) => void;
  initialBank?: { name: string; code: string };
  initialBranch?: { name: string; code: string };
}

export function BankSelector({ onSelect, initialBank, initialBranch }: BankSelectorProps) {
  // ステップ管理（aiueo → bank → branch）
  const [step, setStep] = useState<'aiueo' | 'bank' | 'branch'>('aiueo');

  // 選択状態
  const [selectedAiueo, setSelectedAiueo] = useState<string>('');
  const [selectedBank, setSelectedBank] = useState<Bank | null>(null);
  const [selectedBranch, setSelectedBranch] = useState<Branch | null>(null);

  // データ
  const [banks, setBanks] = useState<Bank[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [filteredBranches, setFilteredBranches] = useState<Branch[]>([]);

  // 検索
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Bank[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // ローディング
  const [loadingBanks, setLoadingBanks] = useState(false);
  const [loadingBranches, setLoadingBranches] = useState(false);

  // 支店のあいうえお
  const [branchAiueo, setBranchAiueo] = useState<string>('');

  // 検索処理
  useEffect(() => {
    if (!searchQuery || searchQuery.length < 2) {
      setSearchResults([]);
      return;
    }

    const timer = setTimeout(async () => {
      setIsSearching(true);
      const results = await searchBanks(searchQuery);
      setSearchResults(results);
      setIsSearching(false);
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // あいうえお選択時
  const handleAiueoSelect = async (row: string) => {
    setSelectedAiueo(row);
    setLoadingBanks(true);

    const fetchedBanks = await getBanksByAiueo(row);
    setBanks(fetchedBanks);
    setLoadingBanks(false);
    setStep('bank');
  };

  // 銀行選択時
  const handleBankSelect = async (bank: Bank) => {
    setSelectedBank(bank);
    setLoadingBranches(true);

    const fetchedBranches = await getBranches(bank.code);
    setBranches(fetchedBranches);
    setFilteredBranches(fetchedBranches);
    setLoadingBranches(false);
    setBranchAiueo('');
    setStep('branch');
  };

  // 検索結果から銀行選択
  const handleSearchBankSelect = async (bank: Bank) => {
    setSearchQuery('');
    setSearchResults([]);
    await handleBankSelect(bank);
  };

  // 支店のあいうえおフィルター
  const handleBranchAiueoSelect = (row: string) => {
    setBranchAiueo(row);
    if (row) {
      setFilteredBranches(filterBranchesByAiueo(branches, row));
    } else {
      setFilteredBranches(branches);
    }
  };

  // 支店選択時
  const handleBranchSelect = (branch: Branch) => {
    setSelectedBranch(branch);

    if (selectedBank) {
      onSelect({
        bankName: selectedBank.name,
        bankCode: selectedBank.code,
        branchName: branch.name,
        branchCode: branch.code,
        bankNameKana: toHalfWidthKatakana(selectedBank.katakana),
        branchNameKana: toHalfWidthKatakana(branch.katakana),
      });
    }
  };

  // 戻る処理
  const handleBack = () => {
    if (step === 'branch') {
      setStep('bank');
      setSelectedBranch(null);
    } else if (step === 'bank') {
      setStep('aiueo');
      setSelectedBank(null);
      setBanks([]);
    }
  };

  // リセット
  const handleReset = () => {
    setStep('aiueo');
    setSelectedAiueo('');
    setSelectedBank(null);
    setSelectedBranch(null);
    setBanks([]);
    setBranches([]);
    setSearchQuery('');
    setSearchResults([]);
  };

  return (
    <div className="space-y-4">
      {/* 検索ボックス */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="金融機関名で検索（例：愛知信用）"
          className="w-full h-11 pl-10 pr-4 rounded-xl border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        {isSearching && (
          <Loader2 className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 animate-spin text-blue-500" />
        )}
      </div>

      {/* 検索結果 */}
      {searchResults.length > 0 && (
        <div className="border border-gray-200 rounded-xl bg-white max-h-48 overflow-y-auto">
          {searchResults.map((bank) => (
            <button
              key={bank.code}
              onClick={() => handleSearchBankSelect(bank)}
              className="w-full px-4 py-3 text-left text-sm hover:bg-blue-50 border-b border-gray-100 last:border-b-0"
            >
              <span className="font-medium">{bank.name}</span>
              <span className="text-gray-400 ml-2">({bank.code})</span>
            </button>
          ))}
        </div>
      )}

      {/* 選択状況表示 */}
      {(selectedBank || selectedBranch) && (
        <div className="bg-blue-50 rounded-xl p-3 space-y-1">
          {selectedBank && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">金融機関:</span>
              <span className="font-medium">{selectedBank.name}</span>
            </div>
          )}
          {selectedBranch && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">支店:</span>
              <span className="font-medium">{selectedBranch.name}</span>
            </div>
          )}
          {step !== 'aiueo' && (
            <button
              onClick={handleReset}
              className="text-xs text-blue-600 underline mt-1"
            >
              最初からやり直す
            </button>
          )}
        </div>
      )}

      {/* ステップ1: あいうえお選択 */}
      {step === 'aiueo' && !searchResults.length && (
        <div>
          <label className="text-sm font-medium text-gray-700 mb-2 block">
            金融機関の頭文字を選択 <span className="text-red-500">*</span>
          </label>
          <div className="flex flex-wrap gap-2">
            {AIUEO_ROWS.map((item) => (
              <button
                key={item.row}
                onClick={() => handleAiueoSelect(item.row)}
                className={`w-10 h-10 rounded-lg border text-sm font-medium transition-colors ${
                  selectedAiueo === item.row
                    ? 'bg-blue-500 text-white border-blue-500'
                    : 'border-gray-200 bg-white hover:bg-blue-50'
                }`}
              >
                {item.row}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ステップ2: 銀行選択 */}
      {step === 'bank' && !searchResults.length && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-gray-700">
              金融機関を選択 <span className="text-red-500">*</span>
            </label>
            <button onClick={handleBack} className="text-xs text-blue-600">
              戻る
            </button>
          </div>

          {loadingBanks ? (
            <div className="flex items-center justify-center h-24 bg-gray-50 rounded-xl border border-gray-200">
              <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
              <span className="ml-2 text-sm text-gray-500">読み込み中...</span>
            </div>
          ) : banks.length === 0 ? (
            <div className="flex items-center justify-center h-24 bg-gray-50 rounded-xl border border-gray-200">
              <span className="text-sm text-gray-500">該当する金融機関がありません</span>
            </div>
          ) : (
            <div className="border border-gray-200 rounded-xl bg-white max-h-48 overflow-y-auto">
              {banks.map((bank) => (
                <button
                  key={bank.code}
                  onClick={() => handleBankSelect(bank)}
                  className="w-full px-4 py-3 text-left text-sm hover:bg-blue-50 border-b border-gray-100 last:border-b-0"
                >
                  <span className="font-medium">{bank.name}</span>
                  <span className="text-gray-400 ml-2">({bank.code})</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ステップ3: 支店選択 */}
      {step === 'branch' && !searchResults.length && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-gray-700">
              支店を選択 <span className="text-red-500">*</span>
            </label>
            <button onClick={handleBack} className="text-xs text-blue-600">
              戻る
            </button>
          </div>

          {/* 支店のあいうえおフィルター */}
          <div className="flex flex-wrap gap-1 mb-2">
            <button
              onClick={() => handleBranchAiueoSelect('')}
              className={`px-2 py-1 rounded text-xs transition-colors ${
                branchAiueo === ''
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              全て
            </button>
            {AIUEO_ROWS.map((item) => (
              <button
                key={item.row}
                onClick={() => handleBranchAiueoSelect(item.row)}
                className={`px-2 py-1 rounded text-xs transition-colors ${
                  branchAiueo === item.row
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {item.row}
              </button>
            ))}
          </div>

          {loadingBranches ? (
            <div className="flex items-center justify-center h-24 bg-gray-50 rounded-xl border border-gray-200">
              <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
              <span className="ml-2 text-sm text-gray-500">支店を読み込み中...</span>
            </div>
          ) : filteredBranches.length === 0 ? (
            <div className="flex items-center justify-center h-24 bg-gray-50 rounded-xl border border-gray-200">
              <span className="text-sm text-gray-500">該当する支店がありません</span>
            </div>
          ) : (
            <div className="border border-gray-200 rounded-xl bg-white max-h-48 overflow-y-auto">
              {filteredBranches.map((branch) => (
                <button
                  key={branch.code}
                  onClick={() => handleBranchSelect(branch)}
                  className={`w-full px-4 py-3 text-left text-sm hover:bg-blue-50 border-b border-gray-100 last:border-b-0 ${
                    selectedBranch?.code === branch.code ? 'bg-blue-50' : ''
                  }`}
                >
                  <span className="font-medium">{branch.name}</span>
                  <span className="text-gray-400 ml-2">({branch.code})</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
