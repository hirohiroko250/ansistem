"""
ボットFAQをアンイングリッシュGROUP向けに更新
"""
from django.core.management.base import BaseCommand
from apps.communications.models import BotConfig, BotFAQ

FAQ_DATA = [
    # 体験・基本
    {
        'category': '体験',
        'question': '体験授業を申し込みたい',
        'keywords': ['体験', '申込', '申し込み', '見学', 'お試し', '無料体験', 'トライアル'],
        'answer': '''体験レッスンにご興味いただきありがとうございます！

【体験レッスンの流れ】
1. Webまたはお電話でお申込み
2. ご希望の日時で体験レッスン参加
3. 入会ご検討

📝 お申込みはこちら
https://an-english.com/trial/

📞 お電話でのお申込み
0561-54-4449（受付10:00〜18:00）

体験レッスンは無料です！''',
        'next_action': 'trial_request',
        'sort_order': 1,
    },
    {
        'category': '授業',
        'question': '振替・欠席連絡について',
        'keywords': ['振替', '休み', '欠席', '変更', 'キャンセル', '休む'],
        'answer': '''【欠席のご連絡】
授業開始前までにアプリまたはお電話でご連絡ください。

【振替について】
・前日までにご連絡いただければ振替可能です
・アプリの「振替申請」から申請できます
・空き状況を確認後、振替日時をご案内します

※当日キャンセルの場合は振替ができない場合があります。''',
        'next_action': 'makeup_request',
        'sort_order': 2,
    },
    {
        'category': '料金',
        'question': '料金・月謝について',
        'keywords': ['料金', '月謝', '費用', 'いくら', '値段', '金額', '価格'],
        'answer': '''月謝は教室・コースにより異なります。

【主な料金目安】
・英会話: 週1回 8,800円〜/月
・そろばん: 週1回 5,500円〜/月
・習字: 週1回 4,400円〜/月
・プログラミング: 週1回 11,000円〜/月
・学習塾: 週1回 8,800円〜/月

※教室・学年により異なります

詳しい料金は体験レッスン時にご案内いたします。''',
        'sort_order': 3,
    },
    {
        'category': '授業',
        'question': '授業スケジュール・時間割について',
        'keywords': ['時間', '何時', 'スケジュール', '時間割', '曜日', 'いつ'],
        'answer': '''授業時間は教室・曜日により異なります。

【一般的な時間帯】
・平日: 15:00〜21:00
・土曜: 9:00〜18:00
・日曜: 一部教室で開講

お子様のスケジュールはアプリの「スケジュール」からご確認いただけます。

教室ごとの詳細は最寄りの教室にお問い合わせください。''',
        'sort_order': 4,
    },
    {
        'category': '教室',
        'question': '教室の場所を探している',
        'keywords': ['場所', '教室', 'どこ', '住所', 'アクセス', '近く', '最寄り'],
        'answer': '''愛知県・岐阜県を中心に80教室以上あります！

📍 教室検索はこちら
https://an-english.com/school/

【主なエリア】
・名古屋市内（守山区、名東区、緑区など）
・尾張旭市・瀬戸市
・春日井市・小牧市
・一宮市・稲沢市
・岐阜県

お住まいのエリアをお教えいただければ、最寄りの教室をご案内します！''',
        'sort_order': 5,
    },
    {
        'category': '検定',
        'question': '検定・資格試験について',
        'keywords': ['検定', '資格', '試験', '英検', 'そろばん検定', 'テスト'],
        'answer': '''各教室で検定・資格試験に対応しています！

【英語】
・英検対策（5級〜1級）
・TOEIC/TOEFL対策

【そろばん】
・日商珠算検定
・全珠連検定
・暗算検定

【習字】
・硬筆検定
・毛筆検定

検定対策コースや受験日程は各教室にお問い合わせください。''',
        'sort_order': 6,
    },
    # ブランド
    {
        'category': 'ブランド',
        'question': 'アンイングリッシュクラブについて',
        'keywords': ['イングリッシュ', '英会話', '英語', 'ネイティブ', 'English'],
        'answer': '''🇬🇧 アンイングリッシュクラブ

ネイティブ講師による本格英会話教室です！

【対象】年少〜高校生

【特徴】
・ネイティブ講師によるオールイングリッシュ授業
・楽しみながら自然に英語が身につく
・英検対策・受験対策にも対応
・愛知・岐阜に多数教室あり

📝 詳しくはこちら
https://an-english.com/brand/english/

無料体験レッスン受付中！''',
        'next_action': 'trial_request',
        'sort_order': 10,
    },
    {
        'category': 'ブランド',
        'question': 'アンそろばんクラブについて',
        'keywords': ['そろばん', '珠算', '暗算', '計算'],
        'answer': '''🧮 アンそろばんクラブ

「そろばんは頭が良くなる習い事」

【対象】年少〜小6生

【特徴】
・計算力・暗算力が飛躍的にアップ
・集中力・記憶力も向上
・右脳開発にも効果的
・検定取得でやる気アップ

📝 詳しくはこちら
https://an-english.com/brand/soroban/

無料体験レッスン受付中！''',
        'next_action': 'trial_request',
        'sort_order': 11,
    },
    {
        'category': 'ブランド',
        'question': 'アン美文字クラブについて',
        'keywords': ['美文字', '習字', '書道', '硬筆', '毛筆', '字', 'ペン字'],
        'answer': '''✏️ アン美文字クラブ

筆っこ式硬筆・毛筆の習字教室

【対象】年中〜小6生

【特徴】
・きれいな文字が書けるようになる
・硬筆と毛筆の両方を学べる
・姿勢・集中力も身につく
・段級位認定で達成感

📝 詳しくはこちら
https://an-english.com/brand/bimoji/

無料体験レッスン受付中！''',
        'next_action': 'trial_request',
        'sort_order': 12,
    },
    {
        'category': 'ブランド',
        'question': 'アンプログラミングクラブについて',
        'keywords': ['プログラミング', 'マイクラ', 'マインクラフト', 'IT', 'コード', 'ゲーム'],
        'answer': '''💻 アンプログラミングクラブ

マイクラで学ぶプログラミング教室

【対象】小1〜高校生

【特徴】
・大人気のマインクラフトで楽しく学習
・論理的思考力・問題解決力が身につく
・将来のIT人材育成に
・初心者でも安心のカリキュラム

📝 詳しくはこちら
https://an-english.com/brand/programming/

無料体験レッスン受付中！''',
        'next_action': 'trial_request',
        'sort_order': 13,
    },
    {
        'category': 'ブランド',
        'question': 'アン将棋クラブについて',
        'keywords': ['将棋', '囲碁', 'ボードゲーム'],
        'answer': '''♟️ アン将棋クラブ

今話題の将棋を楽しく学ぶ

【対象】小1〜小6生

【特徴】
・論理的思考力が身につく
・先を読む力・判断力を養う
・集中力アップ
・礼儀作法も学べる

📝 詳しくはこちら
https://an-english.com/brand/shogi/

無料体験レッスン受付中！''',
        'next_action': 'trial_request',
        'sort_order': 14,
    },
    {
        'category': 'ブランド',
        'question': 'アンさんこくキッズについて',
        'keywords': ['さんこく', '三国', 'キッズ', '幼児', '年長'],
        'answer': '''🌱 アンさんこくキッズ

スモールステップで算数・国語の基礎固め

【対象】年長〜小4生

【特徴】
・個別指導で一人ひとりのペースに合わせる
・算数と国語の基礎をしっかり身につける
・学習習慣を楽しく身につける
・小学校の学習に備える

📝 詳しくはこちら
https://an-english.com/brand/sankoku-kids/

無料体験レッスン受付中！''',
        'next_action': 'trial_request',
        'sort_order': 15,
    },
    {
        'category': 'ブランド',
        'question': 'アン算国クラブについて',
        'keywords': ['算国', '個別', '小学生', '算数', '国語'],
        'answer': '''📖 アン算国クラブ

先生1人に生徒4名の個別指導

【対象】小1〜小6生

【特徴】
・少人数制で一人ひとりに目が届く
・算数と国語をバランスよく学習
・学校の予習・復習にも対応
・定期テスト対策も充実

📝 詳しくはこちら
https://an-english.com/brand/sankoku/

無料体験レッスン受付中！''',
        'next_action': 'trial_request',
        'sort_order': 16,
    },
    {
        'category': 'ブランド',
        'question': 'アン進学ジムについて',
        'keywords': ['進学', 'ジム', '受験', '塾', '学習塾', '中学受験', '高校受験', '大学受験'],
        'answer': '''🎯 アン進学ジム

学力向上にこだわった本格個別指導塾

【対象】小4〜高校生

【特徴】
・一人ひとりに合わせた個別カリキュラム
・中学受験・高校受験・大学受験対応
・定期テスト対策も充実
・5教科対応

📝 詳しくはこちら
https://an-english.com/brand/shingaku/

無料体験レッスン受付中！''',
        'next_action': 'trial_request',
        'sort_order': 17,
    },
    {
        'category': 'ブランド',
        'question': 'アンインターナショナルスクールについて',
        'keywords': ['インターナショナル', '保育園', '幼稚園', '保育', '1歳', '2歳', '3歳'],
        'answer': '''🏫 アンインターナショナルスクール

遊びの中で楽しく英語を学ぶ保育園

【対象】1歳〜年長

【特徴】
・ネイティブ講師と過ごす毎日
・遊びを通じて自然に英語が身につく
・保育園としての機能も充実
・小学校入学準備もバッチリ

📝 詳しくはこちら
https://an-english.com/brand/international/

見学・入園相談受付中！''',
        'next_action': 'trial_request',
        'sort_order': 18,
    },
    {
        'category': 'ブランド',
        'question': 'アンまなびワールドについて',
        'keywords': ['まなび', '学童', '放課後', '預かり'],
        'answer': '''🏠 アンまなびワールド

12のまなびが学べる学童教室

【対象】小1〜小6生

【特徴】
・放課後を有効活用
・12種類の学びプログラム
・宿題サポートも充実
・安心・安全な環境

📝 詳しくはこちら
https://an-english.com/brand/manabi/

見学受付中！''',
        'next_action': 'trial_request',
        'sort_order': 19,
    },
    {
        'category': 'ブランド',
        'question': 'プラチナステージについて',
        'keywords': ['プラチナ', 'シニア', '大人', '生涯学習', '趣味'],
        'answer': '''🎓 プラチナステージ

大人の知的なまなびば

【対象】シニア・大人

【特徴】
・趣味として、脳トレとして楽しめる
・英会話、そろばん、習字など多彩なコース
・同世代の仲間と一緒に学べる
・生涯学習で充実した毎日を

📝 詳しくはこちら
https://an-english.com/brand/platinum/

体験受付中！''',
        'next_action': 'trial_request',
        'sort_order': 20,
    },
    # 年齢別
    {
        'category': '年齢',
        'question': '1〜3歳におすすめの教室',
        'keywords': ['1歳', '2歳', '3歳', '赤ちゃん', '乳児', '幼児'],
        'answer': '''1〜3歳のお子様におすすめ！

🏫 アンインターナショナルスクール
遊びの中で楽しく英語を学ぶ保育園です。
ネイティブ講師と一緒に、自然に英語が身につきます。

【特徴】
・1歳から入園可能
・ネイティブ講師との毎日
・保育園機能も充実

📝 詳しくはこちら
https://an-english.com/brand/international/

見学・入園相談受付中！''',
        'next_action': 'trial_request',
        'sort_order': 30,
    },
    {
        'category': '年齢',
        'question': '年少〜年長におすすめの習い事',
        'keywords': ['年少', '年中', '年長', '幼稚園', '園児', '4歳', '5歳', '6歳'],
        'answer': '''年少〜年長のお子様におすすめ！

🇬🇧 アンイングリッシュクラブ（年少〜）
ネイティブ講師の英会話

🧮 アンそろばんクラブ（年少〜）
計算力・集中力が身につくそろばん

✏️ アン美文字クラブ（年中〜）
きれいな字が書ける習字教室

📚 アンさんこくキッズ（年長〜）
算数・国語の基礎を楽しく学習

どの教室も無料体験レッスン受付中！

📝 お申込みはこちら
https://an-english.com/trial/''',
        'next_action': 'trial_request',
        'sort_order': 31,
    },
    {
        'category': '年齢',
        'question': '小学校低学年におすすめの習い事',
        'keywords': ['小学生', '小1', '小2', '小3', '低学年', '7歳', '8歳', '9歳'],
        'answer': '''小学1〜3年生のお子様におすすめ！

🇬🇧 アンイングリッシュクラブ
ネイティブ英会話で英検対策も！

🧮 アンそろばんクラブ
暗算力・集中力アップ

✏️ アン美文字クラブ
硬筆・毛筆で美しい文字を

💻 アンプログラミングクラブ（小1〜）
マイクラで楽しくプログラミング

♟️ アン将棋クラブ（小1〜）
論理的思考力を養う

📖 アン算国クラブ
1対4の個別指導

無料体験レッスン受付中！''',
        'next_action': 'trial_request',
        'sort_order': 32,
    },
    {
        'category': '年齢',
        'question': '小学校高学年におすすめの教室',
        'keywords': ['小4', '小5', '小6', '高学年', '10歳', '11歳', '12歳'],
        'answer': '''小学4〜6年生のお子様におすすめ！

🇬🇧 アンイングリッシュクラブ
英検対策・中学準備に最適

🧮 アンそろばんクラブ
計算スピード・正確性アップ

💻 アンプログラミングクラブ
本格的なプログラミングスキル

🎯 アン進学ジム（小4〜）
中学受験・学力向上の個別指導塾

📖 アン算国クラブ
1対4の個別指導

無料体験レッスン受付中！''',
        'next_action': 'trial_request',
        'sort_order': 33,
    },
    {
        'category': '年齢',
        'question': '中学生向けの学習塾や英会話',
        'keywords': ['中学生', '中学', '中1', '中2', '中3', '13歳', '14歳', '15歳'],
        'answer': '''中学生のお子様におすすめ！

🇬🇧 アンイングリッシュクラブ
英検対策・高校受験の英語強化

🎯 アン進学ジム
高校受験対策の個別指導塾
5教科対応・定期テスト対策も

💻 アンプログラミングクラブ
本格的なプログラミングスキル習得

無料体験レッスン受付中！

📝 お申込みはこちら
https://an-english.com/trial/''',
        'next_action': 'trial_request',
        'sort_order': 34,
    },
    {
        'category': '年齢',
        'question': '高校生向けの大学受験対策',
        'keywords': ['高校生', '高校', '高1', '高2', '高3', '大学受験', '16歳', '17歳', '18歳'],
        'answer': '''高校生のお子様におすすめ！

🇬🇧 アンイングリッシュクラブ
英検対策・大学受験の英語強化
TOEIC/TOEFL対策も

🎯 アン進学ジム
大学受験対策の個別指導塾
志望校に合わせたカリキュラム

💻 アンプログラミングクラブ
将来に役立つプログラミングスキル

無料体験レッスン受付中！

📝 お申込みはこちら
https://an-english.com/trial/''',
        'next_action': 'trial_request',
        'sort_order': 35,
    },
    # 連絡・その他
    {
        'category': '連絡',
        'question': 'スタッフと直接話したい',
        'keywords': ['スタッフ', '相談', '話したい', '電話', '人間', 'オペレーター', '直接', '連絡先'],
        'answer': '''スタッフにおつなぎします。

【お電話でのお問い合わせ】
📞 0561-54-4449

【受付時間】
平日: 10:00〜18:00
土曜: 10:00〜18:00
日祝: 休み

【Webからのお問い合わせ】
https://an-english.com/contact/

営業時間外の場合は、翌営業日にご連絡いたします。''',
        'next_action': 'escalate',
        'sort_order': 50,
    },
    {
        'category': 'その他',
        'question': '入会の流れについて',
        'keywords': ['入会', '入塾', '手続き', '流れ', '始める', 'スタート'],
        'answer': '''【入会までの流れ】

① 体験レッスンを申し込む
→ Webまたはお電話で

② 体験レッスンに参加
→ 実際の授業を体験！

③ 入会手続き
→ 気に入ったらその場でOK

④ レッスンスタート！

まずは無料体験からお気軽にどうぞ！

📝 お申込みはこちら
https://an-english.com/trial/''',
        'next_action': 'trial_request',
        'sort_order': 51,
    },
    {
        'category': '料金',
        'question': '支払い方法について',
        'keywords': ['支払い', '払い方', '引き落とし', '振込', 'クレジット', 'カード'],
        'answer': '''【お支払い方法】

以下からお選びいただけます：

1️⃣ 口座振替（毎月27日引き落とし）
2️⃣ クレジットカード
3️⃣ 銀行振込

口座振替・クレジットカードの登録変更はアプリの「お支払い設定」から行えます。

ご不明な点は各教室スタッフにお問い合わせください。''',
        'sort_order': 52,
    },
    {
        'category': 'その他',
        'question': '夏期講習・季節講習について',
        'keywords': ['夏期', '冬期', '春期', '講習', '夏休み', '冬休み', '特別'],
        'answer': '''【季節講習について】

各教室で季節講習を実施しています！

🌻 夏期講習（7月下旬〜8月下旬）
❄️ 冬期講習（12月下旬〜1月上旬）
🌸 春期講習（3月下旬〜4月上旬）

【内容】
・復習コース
・先取りコース
・受験対策コース

詳細は各季節の1〜2ヶ月前にお知らせします。
アプリの「お知らせ」をご確認ください。''',
        'sort_order': 53,
    },
    {
        'category': 'その他',
        'question': '駐車場について',
        'keywords': ['駐車場', '駐車', '車', '停める', 'パーキング'],
        'answer': '''【駐車場について】

駐車場の有無は校舎により異なります。

📍 各教室の詳細はこちら
https://an-english.com/school/

送迎の際は、近隣の方のご迷惑にならないようご協力をお願いいたします。

詳しくは最寄りの教室にお問い合わせください。''',
        'sort_order': 54,
    },
]


class Command(BaseCommand):
    help = 'ボットFAQをアンイングリッシュGROUP向けに更新'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant-id',
            type=str,
            help='対象のテナントID（デフォルト: 最初のアクティブなBotConfig）'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には更新せず、何が更新されるかを表示'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        tenant_id = options.get('tenant_id')

        # デフォルトのテナントID（アンイングリッシュグループ）
        default_tenant_id = '6603315b-f0d4-486a-97c9-dfe981d0bf53'

        # BotConfigを取得または作成
        if tenant_id:
            bot_config = BotConfig.objects.filter(
                tenant_id=tenant_id,
                is_active=True
            ).first()
        else:
            bot_config = BotConfig.objects.filter(is_active=True).first()
            if not bot_config:
                # デフォルトテナントで探す
                tenant_id = default_tenant_id
                bot_config = BotConfig.objects.filter(
                    tenant_id=tenant_id,
                    is_active=True
                ).first()

        if not bot_config:
            # BotConfigがなければ作成
            if dry_run:
                self.stdout.write('[DRY RUN] BotConfigを作成します')
            else:
                bot_config = BotConfig.objects.create(
                    tenant_id=tenant_id or default_tenant_id,
                    name='AIアシスタント',
                    bot_type='GENERAL',
                    welcome_message='こんにちは！',
                    fallback_message='申し訳ございません。',
                    is_active=True,
                )
                self.stdout.write(self.style.SUCCESS(f'BotConfigを作成しました: {bot_config.id}'))

        self.stdout.write(f"BotConfig: {bot_config.name} (tenant: {bot_config.tenant_id})")

        # BotConfigを更新
        if not dry_run:
            bot_config.name = 'AIアシスタント'
            bot_config.welcome_message = '''こんにちは！アンイングリッシュGROUPへようこそ！

英会話、そろばん、習字、プログラミング、学習塾など、お子様に最適な習い事をご案内します。

何でもお気軽にお聞きください！'''
            bot_config.fallback_message = '''申し訳ございません。ご質問の内容を理解できませんでした。

スタッフにお繋ぎしますか？「スタッフに相談」とお伝えください。

またはお電話でもお問い合わせいただけます。
📞 0561-54-4449'''
            bot_config.save()
            self.stdout.write(self.style.SUCCESS('BotConfigを更新しました'))
        else:
            self.stdout.write('[DRY RUN] BotConfigを更新します')

        # 既存FAQを削除して新規作成
        if not dry_run:
            deleted_count = BotFAQ.objects.filter(bot_config=bot_config).delete()[0]
            self.stdout.write(f"既存FAQ {deleted_count}件を削除しました")

        # 新規FAQ作成
        created_count = 0
        for faq_data in FAQ_DATA:
            if dry_run:
                self.stdout.write(
                    f"[DRY RUN] FAQ作成: [{faq_data['category']}] {faq_data['question']}"
                )
            else:
                BotFAQ.objects.create(
                    tenant_id=bot_config.tenant_id,
                    bot_config=bot_config,
                    category=faq_data['category'],
                    question=faq_data['question'],
                    keywords=faq_data['keywords'],
                    answer=faq_data['answer'],
                    next_action=faq_data.get('next_action'),
                    sort_order=faq_data['sort_order'],
                    is_active=True,
                )
            created_count += 1

        if dry_run:
            self.stdout.write(self.style.WARNING(f'[DRY RUN] {created_count}件のFAQが作成されます'))
        else:
            self.stdout.write(self.style.SUCCESS(f'{created_count}件のFAQを作成しました'))
