"""
Receipt Service - 領収書PDF生成サービス
"""
import io
from datetime import date
from decimal import Decimal
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
import os


def _register_japanese_font():
    """日本語フォントを登録"""
    # macOS のヒラギノフォント
    font_paths = [
        '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc',
        '/System/Library/Fonts/Hiragino Sans GB.ttc',
        '/Library/Fonts/Arial Unicode.ttf',
        # Linux
        '/usr/share/fonts/truetype/fonts-japanese-gothic.ttf',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    ]

    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('JapaneseFont', font_path))
                return 'JapaneseFont'
            except Exception:
                continue

    # フォントが見つからない場合はデフォルトフォントを使用
    return 'Helvetica'


def _format_currency(amount) -> str:
    """金額をフォーマット"""
    if isinstance(amount, Decimal):
        amount = int(amount)
    return f"¥{amount:,}"


def generate_receipt_pdf(confirmed_billing) -> bytes:
    """領収書PDFを生成

    Args:
        confirmed_billing: ConfirmedBillingインスタンス

    Returns:
        bytes: PDF バイナリデータ
    """
    buffer = io.BytesIO()

    # PDFドキュメントを作成
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )

    # 日本語フォントを登録
    font_name = _register_japanese_font()

    # スタイルを定義
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'Title',
        parent=styles['Title'],
        fontName=font_name,
        fontSize=24,
        alignment=TA_CENTER,
        spaceAfter=20*mm,
    )

    header_style = ParagraphStyle(
        'Header',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=12,
        alignment=TA_RIGHT,
    )

    name_style = ParagraphStyle(
        'Name',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=14,
        alignment=TA_LEFT,
    )

    amount_style = ParagraphStyle(
        'Amount',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=18,
        alignment=TA_CENTER,
    )

    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=11,
        alignment=TA_LEFT,
    )

    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        alignment=TA_RIGHT,
    )

    # コンテンツを構築
    elements = []

    # 領収書番号と発行日
    receipt_no = f"No. R{confirmed_billing.billing_no.replace('CB', '')}" if confirmed_billing.billing_no else f"No. R{confirmed_billing.id.hex[:8].upper()}"
    issue_date = date.today().strftime('%Y年%m月%d日')

    elements.append(Paragraph(f"領収書番号: {receipt_no}", header_style))
    elements.append(Paragraph(f"発行日: {issue_date}", header_style))
    elements.append(Spacer(1, 15*mm))

    # タイトル
    elements.append(Paragraph("領　収　書", title_style))
    elements.append(Spacer(1, 10*mm))

    # 宛名
    guardian = confirmed_billing.guardian
    guardian_name = f"{guardian.last_name} {guardian.first_name}" if guardian else "様"
    elements.append(Paragraph(f"{guardian_name}　様", name_style))
    elements.append(Spacer(1, 5*mm))

    # 下線
    line_data = [['', '']]
    line_table = Table(line_data, colWidths=[150*mm, 0])
    line_table.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (0, 0), 1, colors.black),
    ]))
    elements.append(line_table)
    elements.append(Spacer(1, 15*mm))

    # 金額
    total_amount = int(confirmed_billing.total_amount) if confirmed_billing.total_amount else 0
    amount_text = _format_currency(total_amount)

    # 金額テーブル
    amount_data = [[f"金額　{amount_text}　（税込）"]]
    amount_table = Table(amount_data, colWidths=[170*mm])
    amount_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 18),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOX', (0, 0), (-1, -1), 2, colors.black),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(amount_table)
    elements.append(Spacer(1, 15*mm))

    # 但し書き
    billing_period = f"{confirmed_billing.year}年{confirmed_billing.month}月分"
    elements.append(Paragraph(f"但し　{billing_period}授業料として", normal_style))
    elements.append(Spacer(1, 5*mm))

    # 下線
    elements.append(line_table)
    elements.append(Spacer(1, 10*mm))

    # 明細
    elements.append(Paragraph("【明細】", normal_style))
    elements.append(Spacer(1, 3*mm))

    # 明細テーブル
    items_snapshot = confirmed_billing.items_snapshot or []
    detail_data = [['品目', '数量', '単価', '金額']]

    for item in items_snapshot:
        item_name = item.get('product_name', item.get('item_name', '授業料'))
        quantity = item.get('quantity', 1)
        unit_price = item.get('unit_price', 0)
        final_price = item.get('final_price', 0)
        detail_data.append([
            item_name[:20],  # 長すぎる場合は切り詰め
            str(quantity),
            _format_currency(unit_price),
            _format_currency(final_price),
        ])

    # 合計行
    detail_data.append(['', '', '合計', _format_currency(total_amount)])

    detail_table = Table(detail_data, colWidths=[80*mm, 20*mm, 35*mm, 35*mm])
    detail_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
    ]))
    elements.append(detail_table)
    elements.append(Spacer(1, 20*mm))

    # 上記の金額を領収いたしました
    elements.append(Paragraph("上記の金額を正に領収いたしました。", normal_style))
    elements.append(Spacer(1, 20*mm))

    # 発行元情報
    # テナント情報から取得（または固定値）
    tenant = getattr(confirmed_billing, 'tenant', None)
    if tenant:
        company_name = getattr(tenant, 'name', 'OZAシステム')
        address = getattr(tenant, 'address', '')
    else:
        company_name = 'OZAシステム'
        address = ''

    elements.append(Paragraph(company_name, footer_style))
    if address:
        elements.append(Paragraph(address, footer_style))

    # PDFを生成
    doc.build(elements)

    return buffer.getvalue()


def generate_receipt_response(confirmed_billing) -> HttpResponse:
    """領収書PDFのHTTPレスポンスを生成

    Args:
        confirmed_billing: ConfirmedBillingインスタンス

    Returns:
        HttpResponse: PDF添付ファイルとしてのレスポンス
    """
    pdf_data = generate_receipt_pdf(confirmed_billing)

    # ファイル名を生成
    guardian = confirmed_billing.guardian
    guardian_name = f"{guardian.last_name}{guardian.first_name}" if guardian else "receipt"
    filename = f"receipt_{confirmed_billing.year}{str(confirmed_billing.month).zfill(2)}_{guardian_name}.pdf"

    response = HttpResponse(pdf_data, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response
