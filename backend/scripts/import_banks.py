"""
金融機関マスターデータインポートスクリプト
Django shellで実行: python manage.py shell < scripts/import_banks.py
"""

from apps.schools.models import BankType, Bank, BankBranch

# テナントID（既存データから取得またはデフォルト）
TENANT_ID = 100000

print("=== 金融機関マスターデータ インポート ===\n")

# ========================================
# 1. 金融機関種別（BankType）
# ========================================
print("1. 金融機関種別をインポート中...")

BANK_TYPES = [
    {'type_code': 'city', 'type_name': '都市銀行', 'type_label': '都市銀行', 'sort_order': 1},
    {'type_code': 'regional', 'type_name': '地方銀行', 'type_label': '地方銀行', 'sort_order': 2},
    {'type_code': 'second_regional', 'type_name': '第二地方銀行', 'type_label': '第二地銀', 'sort_order': 3},
    {'type_code': 'shinkin', 'type_name': '信用金庫', 'type_label': '信用金庫', 'sort_order': 4},
    {'type_code': 'credit_union', 'type_name': '信用組合', 'type_label': '信用組合', 'sort_order': 5},
    {'type_code': 'net', 'type_name': 'ネット銀行', 'type_label': 'ネット銀行', 'sort_order': 6},
    {'type_code': 'yucho', 'type_name': 'ゆうちょ銀行', 'type_label': 'ゆうちょ', 'sort_order': 7},
    {'type_code': 'trust', 'type_name': '信託銀行', 'type_label': '信託銀行', 'sort_order': 8},
    {'type_code': 'rokin', 'type_name': '労働金庫', 'type_label': '労働金庫', 'sort_order': 9},
    {'type_code': 'ja', 'type_name': '農業協同組合', 'type_label': '農協(JA)', 'sort_order': 10},
]

bank_type_map = {}
for bt_data in BANK_TYPES:
    bt, created = BankType.objects.update_or_create(
        tenant_id=TENANT_ID,
        type_code=bt_data['type_code'],
        defaults={
            'type_name': bt_data['type_name'],
            'type_label': bt_data['type_label'],
            'sort_order': bt_data['sort_order'],
            'is_active': True,
        }
    )
    bank_type_map[bt_data['type_code']] = bt
    print(f"  {'作成' if created else '更新'}: {bt.type_name}")

print(f"  金融機関種別: {BankType.objects.count()} 件\n")

# ========================================
# 2. 金融機関（Bank）
# ========================================
print("2. 金融機関をインポート中...")

BANKS = [
    # 都市銀行
    {'code': '0001', 'name': 'みずほ銀行', 'hiragana': 'みずほぎんこう', 'kana': 'ミズホギンコウ', 'type': 'city'},
    {'code': '0005', 'name': '三菱UFJ銀行', 'hiragana': 'みつびしゆーえふじぇいぎんこう', 'kana': 'ミツビシユーエフジェイギンコウ', 'type': 'city'},
    {'code': '0009', 'name': '三井住友銀行', 'hiragana': 'みついすみともぎんこう', 'kana': 'ミツイスミトモギンコウ', 'type': 'city'},
    {'code': '0010', 'name': 'りそな銀行', 'hiragana': 'りそなぎんこう', 'kana': 'リソナギンコウ', 'type': 'city'},
    {'code': '0017', 'name': '埼玉りそな銀行', 'hiragana': 'さいたまりそなぎんこう', 'kana': 'サイタマリソナギンコウ', 'type': 'city'},

    # 地方銀行（愛知県中心）
    {'code': '0532', 'name': '名古屋銀行', 'hiragana': 'なごやぎんこう', 'kana': 'ナゴヤギンコウ', 'type': 'regional'},
    {'code': '0533', 'name': '中京銀行', 'hiragana': 'ちゅうきょうぎんこう', 'kana': 'チュウキョウギンコウ', 'type': 'regional'},
    {'code': '0534', 'name': '愛知銀行', 'hiragana': 'あいちぎんこう', 'kana': 'アイチギンコウ', 'type': 'regional'},
    {'code': '0150', 'name': '静岡銀行', 'hiragana': 'しずおかぎんこう', 'kana': 'シズオカギンコウ', 'type': 'regional'},
    {'code': '0153', 'name': '大垣共立銀行', 'hiragana': 'おおがききょうりつぎんこう', 'kana': 'オオガキキョウリツギンコウ', 'type': 'regional'},
    {'code': '0154', 'name': '十六銀行', 'hiragana': 'じゅうろくぎんこう', 'kana': 'ジュウロクギンコウ', 'type': 'regional'},
    {'code': '0155', 'name': '三十三銀行', 'hiragana': 'さんじゅうさんぎんこう', 'kana': 'サンジュウサンギンコウ', 'type': 'regional'},
    {'code': '0157', 'name': '百五銀行', 'hiragana': 'ひゃくごぎんこう', 'kana': 'ヒャクゴギンコウ', 'type': 'regional'},

    # 信用金庫（愛知県中心）
    {'code': '1550', 'name': '愛知信用金庫', 'hiragana': 'あいちしんようきんこ', 'kana': 'アイチシンヨウキンコ', 'type': 'shinkin'},
    {'code': '1551', 'name': '豊橋信用金庫', 'hiragana': 'とよはししんようきんこ', 'kana': 'トヨハシシンヨウキンコ', 'type': 'shinkin'},
    {'code': '1552', 'name': '岡崎信用金庫', 'hiragana': 'おかざきしんようきんこ', 'kana': 'オカザキシンヨウキンコ', 'type': 'shinkin'},
    {'code': '1553', 'name': 'いちい信用金庫', 'hiragana': 'いちいしんようきんこ', 'kana': 'イチイシンヨウキンコ', 'type': 'shinkin'},
    {'code': '1554', 'name': '瀬戸信用金庫', 'hiragana': 'せとしんようきんこ', 'kana': 'セトシンヨウキンコ', 'type': 'shinkin'},
    {'code': '1555', 'name': '半田信用金庫', 'hiragana': 'はんだしんようきんこ', 'kana': 'ハンダシンヨウキンコ', 'type': 'shinkin'},
    {'code': '1556', 'name': '知多信用金庫', 'hiragana': 'ちたしんようきんこ', 'kana': 'チタシンヨウキンコ', 'type': 'shinkin'},
    {'code': '1557', 'name': '豊川信用金庫', 'hiragana': 'とよかわしんようきんこ', 'kana': 'トヨカワシンヨウキンコ', 'type': 'shinkin'},
    {'code': '1559', 'name': '豊田信用金庫', 'hiragana': 'とよたしんようきんこ', 'kana': 'トヨタシンヨウキンコ', 'type': 'shinkin'},
    {'code': '1560', 'name': '碧海信用金庫', 'hiragana': 'へきかいしんようきんこ', 'kana': 'ヘキカイシンヨウキンコ', 'type': 'shinkin'},
    {'code': '1561', 'name': '西尾信用金庫', 'hiragana': 'にしおしんようきんこ', 'kana': 'ニシオシンヨウキンコ', 'type': 'shinkin'},
    {'code': '1562', 'name': '蒲郡信用金庫', 'hiragana': 'がまごおりしんようきんこ', 'kana': 'ガマゴオリシンヨウキンコ', 'type': 'shinkin'},
    {'code': '1563', 'name': '尾西信用金庫', 'hiragana': 'びさいしんようきんこ', 'kana': 'ビサイシンヨウキンコ', 'type': 'shinkin'},
    {'code': '1565', 'name': '中日信用金庫', 'hiragana': 'ちゅうにちしんようきんこ', 'kana': 'チュウニチシンヨウキンコ', 'type': 'shinkin'},
    {'code': '1566', 'name': '東春信用金庫', 'hiragana': 'とうしゅんしんようきんこ', 'kana': 'トウシュンシンヨウキンコ', 'type': 'shinkin'},

    # ネット銀行
    {'code': '0033', 'name': 'PayPay銀行', 'hiragana': 'ぺいぺいぎんこう', 'kana': 'ペイペイギンコウ', 'type': 'net'},
    {'code': '0034', 'name': 'セブン銀行', 'hiragana': 'せぶんぎんこう', 'kana': 'セブンギンコウ', 'type': 'net'},
    {'code': '0035', 'name': 'ソニー銀行', 'hiragana': 'そにーぎんこう', 'kana': 'ソニーギンコウ', 'type': 'net'},
    {'code': '0036', 'name': '楽天銀行', 'hiragana': 'らくてんぎんこう', 'kana': 'ラクテンギンコウ', 'type': 'net'},
    {'code': '0038', 'name': '住信SBIネット銀行', 'hiragana': 'すみしんえすびーあいねっとぎんこう', 'kana': 'スミシンエスビーアイネットギンコウ', 'type': 'net'},
    {'code': '0039', 'name': 'auじぶん銀行', 'hiragana': 'えーゆーじぶんぎんこう', 'kana': 'エーユージブンギンコウ', 'type': 'net'},
    {'code': '0040', 'name': 'イオン銀行', 'hiragana': 'いおんぎんこう', 'kana': 'イオンギンコウ', 'type': 'net'},
    {'code': '0042', 'name': 'GMOあおぞらネット銀行', 'hiragana': 'じーえむおーあおぞらねっとぎんこう', 'kana': 'ジーエムオーアオゾラネットギンコウ', 'type': 'net'},
    {'code': '0043', 'name': 'みんなの銀行', 'hiragana': 'みんなのぎんこう', 'kana': 'ミンナノギンコウ', 'type': 'net'},
    {'code': '0044', 'name': 'UI銀行', 'hiragana': 'ゆーあいぎんこう', 'kana': 'ユーアイギンコウ', 'type': 'net'},

    # ゆうちょ銀行
    {'code': '9900', 'name': 'ゆうちょ銀行', 'hiragana': 'ゆうちょぎんこう', 'kana': 'ユウチョギンコウ', 'type': 'yucho'},

    # 労働金庫
    {'code': '2011', 'name': '東海労働金庫', 'hiragana': 'とうかいろうどうきんこ', 'kana': 'トウカイロウドウキンコ', 'type': 'rokin'},
]

bank_map = {}
for idx, bank_data in enumerate(BANKS):
    bank_type = bank_type_map.get(bank_data['type'])
    bank, created = Bank.objects.update_or_create(
        tenant_id=TENANT_ID,
        bank_code=bank_data['code'],
        defaults={
            'bank_name': bank_data['name'],
            'bank_name_kana': bank_data['kana'],
            'bank_name_hiragana': bank_data['hiragana'],
            'bank_type': bank_type,
            'sort_order': idx,
            'is_active': True,
        }
    )
    bank_map[bank_data['code']] = bank
    if idx < 10:
        print(f"  {'作成' if created else '更新'}: {bank.bank_name}")

print(f"  ... 他{max(0, len(BANKS) - 10)}件")
print(f"  金融機関: {Bank.objects.count()} 件\n")

# ========================================
# 3. 支店（BankBranch）
# ========================================
print("3. 支店をインポート中...")

# 愛知信用金庫の支店
AICHI_SHINKIN_BRANCHES = [
    {'code': '001', 'name': '本店営業部', 'hiragana': 'ほんてんえいぎょうぶ', 'kana': 'ホンテンエイギョウブ'},
    {'code': '002', 'name': '大曽根支店', 'hiragana': 'おおぞねしてん', 'kana': 'オオゾネシテン'},
    {'code': '003', 'name': '千種支店', 'hiragana': 'ちくさしてん', 'kana': 'チクサシテン'},
    {'code': '004', 'name': '東支店', 'hiragana': 'ひがししてん', 'kana': 'ヒガシシテン'},
    {'code': '005', 'name': '高岳支店', 'hiragana': 'たかおかしてん', 'kana': 'タカオカシテン'},
    {'code': '006', 'name': '上飯田支店', 'hiragana': 'かみいいだしてん', 'kana': 'カミイイダシテン'},
    {'code': '007', 'name': '大幸支店', 'hiragana': 'だいこうしてん', 'kana': 'ダイコウシテン'},
    {'code': '008', 'name': '矢田支店', 'hiragana': 'やだしてん', 'kana': 'ヤダシテン'},
    {'code': '009', 'name': '庄内支店', 'hiragana': 'しょうないしてん', 'kana': 'ショウナイシテン'},
    {'code': '010', 'name': '大津橋支店', 'hiragana': 'おおつばししてん', 'kana': 'オオツバシシテン'},
    {'code': '011', 'name': '金山支店', 'hiragana': 'かなやましてん', 'kana': 'カナヤマシテン'},
    {'code': '012', 'name': '熱田支店', 'hiragana': 'あつたしてん', 'kana': 'アツタシテン'},
    {'code': '013', 'name': '港支店', 'hiragana': 'みなとしてん', 'kana': 'ミナトシテン'},
    {'code': '014', 'name': '中川支店', 'hiragana': 'なかがわしてん', 'kana': 'ナカガワシテン'},
    {'code': '015', 'name': '守山支店', 'hiragana': 'もりやましてん', 'kana': 'モリヤマシテン'},
    {'code': '016', 'name': '名東支店', 'hiragana': 'めいとうしてん', 'kana': 'メイトウシテン'},
    {'code': '017', 'name': '天白支店', 'hiragana': 'てんぱくしてん', 'kana': 'テンパクシテン'},
    {'code': '018', 'name': '緑支店', 'hiragana': 'みどりしてん', 'kana': 'ミドリシテン'},
    {'code': '019', 'name': '春日井支店', 'hiragana': 'かすがいしてん', 'kana': 'カスガイシテン'},
    {'code': '020', 'name': '小牧支店', 'hiragana': 'こまきしてん', 'kana': 'コマキシテン'},
    {'code': '021', 'name': '瀬戸支店', 'hiragana': 'せとしてん', 'kana': 'セトシテン'},
    {'code': '022', 'name': '尾張旭支店', 'hiragana': 'おわりあさひしてん', 'kana': 'オワリアサヒシテン'},
    {'code': '023', 'name': '長久手支店', 'hiragana': 'ながくてしてん', 'kana': 'ナガクテシテン'},
    {'code': '024', 'name': '日進支店', 'hiragana': 'にっしんしてん', 'kana': 'ニッシンシテン'},
]

# ゆうちょ銀行の支店
YUCHO_BRANCHES = [
    {'code': '008', 'name': '〇〇八店', 'hiragana': 'ぜろぜろはちてん', 'kana': 'ゼロゼロハチテン'},
    {'code': '018', 'name': '〇一八店', 'hiragana': 'ぜろいちはちてん', 'kana': 'ゼロイチハチテン'},
    {'code': '028', 'name': '〇二八店', 'hiragana': 'ぜろにはちてん', 'kana': 'ゼロニハチテン'},
    {'code': '038', 'name': '〇三八店', 'hiragana': 'ぜろさんはちてん', 'kana': 'ゼロサンハチテン'},
    {'code': '048', 'name': '〇四八店', 'hiragana': 'ぜろよんはちてん', 'kana': 'ゼロヨンハチテン'},
    {'code': '058', 'name': '〇五八店', 'hiragana': 'ぜろごはちてん', 'kana': 'ゼロゴハチテン'},
    {'code': '068', 'name': '〇六八店', 'hiragana': 'ぜろろくはちてん', 'kana': 'ゼロロクハチテン'},
    {'code': '078', 'name': '〇七八店', 'hiragana': 'ぜろななはちてん', 'kana': 'ゼロナナハチテン'},
    {'code': '088', 'name': '〇八八店', 'hiragana': 'ぜろはちはちてん', 'kana': 'ゼロハチハチテン'},
    {'code': '098', 'name': '〇九八店', 'hiragana': 'ぜろきゅうはちてん', 'kana': 'ゼロキュウハチテン'},
    {'code': '108', 'name': '一〇八店', 'hiragana': 'いちぜろはちてん', 'kana': 'イチゼロハチテン'},
    {'code': '118', 'name': '一一八店', 'hiragana': 'いちいちはちてん', 'kana': 'イチイチハチテン'},
    {'code': '128', 'name': '一二八店', 'hiragana': 'いちにはちてん', 'kana': 'イチニハチテン'},
    {'code': '218', 'name': '二一八店', 'hiragana': 'にいちはちてん', 'kana': 'ニイチハチテン'},
    {'code': '238', 'name': '二三八店', 'hiragana': 'にさんはちてん', 'kana': 'ニサンハチテン'},
    {'code': '318', 'name': '三一八店', 'hiragana': 'さんいちはちてん', 'kana': 'サンイチハチテン'},
    {'code': '408', 'name': '四〇八店', 'hiragana': 'よんぜろはちてん', 'kana': 'ヨンゼロハチテン'},
    {'code': '418', 'name': '四一八店', 'hiragana': 'よんいちはちてん', 'kana': 'ヨンイチハチテン'},
    {'code': '458', 'name': '四五八店', 'hiragana': 'よんごはちてん', 'kana': 'ヨンゴハチテン'},
]

# 都市銀行の主要支店
CITY_BANK_BRANCHES = {
    '0001': [  # みずほ銀行
        {'code': '001', 'name': '本店', 'hiragana': 'ほんてん', 'kana': 'ホンテン'},
        {'code': '004', 'name': '丸の内支店', 'hiragana': 'まるのうちしてん', 'kana': 'マルノウチシテン'},
        {'code': '006', 'name': '銀座支店', 'hiragana': 'ぎんざしてん', 'kana': 'ギンザシテン'},
        {'code': '009', 'name': '新宿支店', 'hiragana': 'しんじゅくしてん', 'kana': 'シンジュクシテン'},
        {'code': '016', 'name': '渋谷支店', 'hiragana': 'しぶやしてん', 'kana': 'シブヤシテン'},
        {'code': '110', 'name': '名古屋支店', 'hiragana': 'なごやしてん', 'kana': 'ナゴヤシテン'},
    ],
    '0005': [  # 三菱UFJ銀行
        {'code': '001', 'name': '本店', 'hiragana': 'ほんてん', 'kana': 'ホンテン'},
        {'code': '002', 'name': '丸の内支店', 'hiragana': 'まるのうちしてん', 'kana': 'マルノウチシテン'},
        {'code': '009', 'name': '新宿支店', 'hiragana': 'しんじゅくしてん', 'kana': 'シンジュクシテン'},
        {'code': '150', 'name': '名古屋営業部', 'hiragana': 'なごやえいぎょうぶ', 'kana': 'ナゴヤエイギョウブ'},
    ],
    '0009': [  # 三井住友銀行
        {'code': '210', 'name': '東京営業部', 'hiragana': 'とうきょうえいぎょうぶ', 'kana': 'トウキョウエイギョウブ'},
        {'code': '220', 'name': '銀座支店', 'hiragana': 'ぎんざしてん', 'kana': 'ギンザシテン'},
        {'code': '229', 'name': '新宿支店', 'hiragana': 'しんじゅくしてん', 'kana': 'シンジュクシテン'},
        {'code': '340', 'name': '名古屋営業部', 'hiragana': 'なごやえいぎょうぶ', 'kana': 'ナゴヤエイギョウブ'},
    ],
}

branch_count = 0

# 愛知信用金庫の支店
aichi_shinkin = bank_map.get('1550')
if aichi_shinkin:
    for idx, branch_data in enumerate(AICHI_SHINKIN_BRANCHES):
        branch, created = BankBranch.objects.update_or_create(
            tenant_id=TENANT_ID,
            bank=aichi_shinkin,
            branch_code=branch_data['code'],
            defaults={
                'branch_name': branch_data['name'],
                'branch_name_kana': branch_data['kana'],
                'branch_name_hiragana': branch_data['hiragana'],
                'sort_order': idx,
                'is_active': True,
            }
        )
        branch_count += 1
    print(f"  愛知信用金庫: {len(AICHI_SHINKIN_BRANCHES)} 支店")

# ゆうちょ銀行の支店
yucho = bank_map.get('9900')
if yucho:
    for idx, branch_data in enumerate(YUCHO_BRANCHES):
        branch, created = BankBranch.objects.update_or_create(
            tenant_id=TENANT_ID,
            bank=yucho,
            branch_code=branch_data['code'],
            defaults={
                'branch_name': branch_data['name'],
                'branch_name_kana': branch_data['kana'],
                'branch_name_hiragana': branch_data['hiragana'],
                'sort_order': idx,
                'is_active': True,
            }
        )
        branch_count += 1
    print(f"  ゆうちょ銀行: {len(YUCHO_BRANCHES)} 支店")

# 都市銀行の支店
for bank_code, branches in CITY_BANK_BRANCHES.items():
    bank = bank_map.get(bank_code)
    if bank:
        for idx, branch_data in enumerate(branches):
            branch, created = BankBranch.objects.update_or_create(
                tenant_id=TENANT_ID,
                bank=bank,
                branch_code=branch_data['code'],
                defaults={
                    'branch_name': branch_data['name'],
                    'branch_name_kana': branch_data['kana'],
                    'branch_name_hiragana': branch_data['hiragana'],
                    'sort_order': idx,
                    'is_active': True,
                }
            )
            branch_count += 1
        print(f"  {bank.bank_name}: {len(branches)} 支店")

print(f"  支店合計: {BankBranch.objects.count()} 件\n")

print("=== インポート完了 ===")
print(f"金融機関種別: {BankType.objects.count()} 件")
print(f"金融機関: {Bank.objects.count()} 件")
print(f"支店: {BankBranch.objects.count()} 件")
