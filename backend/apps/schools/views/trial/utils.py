"""
Trial Utils - 体験授業関連ユーティリティ
get_school_year_from_birth_date
"""
from datetime import date

from ...models import SchoolYear


def get_school_year_from_birth_date(birth_date, tenant_id=None):
    """生年月日から単一学年（SchoolYear）を取得する

    日本の学年制度：4月2日〜翌年4月1日生まれが同学年

    学年コード:
    - 1Y, 2Y, 3Y: 1〜3歳
    - NS, NC, NL: 年少、年中、年長
    - E1〜E6: 小1〜小6
    - J1〜J3: 中1〜中3
    - H1〜H3: 高1〜高3
    """
    today = date.today()

    # 学年計算の基準日（4月1日）
    current_year = today.year
    fiscal_year_start = date(current_year, 4, 1)

    # 今日が4月1日より前なら前年度
    fiscal_year = current_year if today >= fiscal_year_start else current_year - 1

    # 生まれた年度を計算（4月2日〜翌年4月1日が同年度）
    birth_year = birth_date.year
    birth_month = birth_date.month
    birth_day = birth_date.day
    # 4月1日以前に生まれた場合は前年度扱い
    if birth_month < 4 or (birth_month == 4 and birth_day <= 1):
        birth_fiscal_year = birth_year - 1
    else:
        birth_fiscal_year = birth_year

    # 学年オフセット
    age_in_fiscal_year = fiscal_year - birth_fiscal_year

    # 学年コードを決定（DBの実際のコードに合わせる）
    year_code = None
    if age_in_fiscal_year <= 1:
        year_code = '1Y'
    elif age_in_fiscal_year == 2:
        year_code = '2Y'
    elif age_in_fiscal_year == 3:
        year_code = '3Y'
    elif age_in_fiscal_year == 4:
        year_code = 'NS'  # 年少
    elif age_in_fiscal_year == 5:
        year_code = 'NC'  # 年中
    elif age_in_fiscal_year == 6:
        year_code = 'NL'  # 年長
    elif 7 <= age_in_fiscal_year <= 12:
        year_code = f'E{age_in_fiscal_year - 6}'  # E1〜E6
    elif 13 <= age_in_fiscal_year <= 15:
        year_code = f'J{age_in_fiscal_year - 12}'  # J1〜J3
    elif 16 <= age_in_fiscal_year <= 18:
        year_code = f'H{age_in_fiscal_year - 15}'  # H1〜H3
    else:
        year_code = 'AD'  # 社会人

    # SchoolYearを取得
    filters = {'year_code': year_code}
    if tenant_id:
        filters['tenant_id'] = tenant_id

    school_year = SchoolYear.objects.filter(**filters).first()
    return school_year
