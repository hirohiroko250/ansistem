"""
Bank Views - 金融機関関連
PublicBankTypesView, PublicBanksView, PublicBankDetailView, PublicBankBranchesView
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from django.db.models import Q

from ..models import BankType, Bank, BankBranch
from ..serializers import BankTypeSerializer, BankSerializer, BankDetailSerializer, BankBranchSerializer


class PublicBankTypesView(APIView):
    """金融機関種別一覧API（認証不要）"""
    permission_classes = [AllowAny]

    def get(self, request):
        """金融機関種別の一覧を返す"""
        bank_types = BankType.objects.filter(is_active=True).order_by('sort_order')
        serializer = BankTypeSerializer(bank_types, many=True)
        return Response(serializer.data)


class PublicBanksView(APIView):
    """金融機関一覧API（認証不要）

    フロントエンドのbank-selector.tsxから呼び出される。
    あいうえお行と金融機関種別でフィルタリング可能。
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """
        金融機関一覧を返す
        ?aiueo_row=あ (あいうえお行フィルター)
        ?bank_type_id=xxx (金融機関種別フィルター)
        """
        queryset = Bank.objects.filter(is_active=True).select_related('bank_type')

        # あいうえお行でフィルタリング（ひらがなの先頭文字で判定）
        aiueo_row = request.query_params.get('aiueo_row')
        if aiueo_row:
            # あいうえお行の範囲を定義
            aiueo_ranges = {
                'あ': ['あ', 'い', 'う', 'え', 'お'],
                'か': ['か', 'き', 'く', 'け', 'こ', 'が', 'ぎ', 'ぐ', 'げ', 'ご'],
                'さ': ['さ', 'し', 'す', 'せ', 'そ', 'ざ', 'じ', 'ず', 'ぜ', 'ぞ'],
                'た': ['た', 'ち', 'つ', 'て', 'と', 'だ', 'ぢ', 'づ', 'で', 'ど'],
                'な': ['な', 'に', 'ぬ', 'ね', 'の'],
                'は': ['は', 'ひ', 'ふ', 'へ', 'ほ', 'ば', 'び', 'ぶ', 'べ', 'ぼ', 'ぱ', 'ぴ', 'ぷ', 'ぺ', 'ぽ'],
                'ま': ['ま', 'み', 'む', 'め', 'も'],
                'や': ['や', 'ゆ', 'よ'],
                'ら': ['ら', 'り', 'る', 'れ', 'ろ'],
                'わ': ['わ', 'を', 'ん'],
            }
            # bank_name_hiraganaの先頭文字でフィルタリング
            chars = aiueo_ranges.get(aiueo_row, [])
            if chars:
                q_filter = Q()
                for char in chars:
                    q_filter |= Q(bank_name_hiragana__startswith=char)
                queryset = queryset.filter(q_filter)

        # 金融機関種別でフィルタリング
        bank_type_id = request.query_params.get('bank_type_id')
        if bank_type_id:
            queryset = queryset.filter(bank_type_id=bank_type_id)

        queryset = queryset.order_by('sort_order', 'bank_name_hiragana')
        serializer = BankSerializer(queryset, many=True)
        return Response(serializer.data)


class PublicBankDetailView(APIView):
    """金融機関詳細API（認証不要・支店一覧含む）"""
    permission_classes = [AllowAny]

    def get(self, request, bank_id):
        """
        金融機関の詳細と支店一覧を返す
        """
        try:
            bank = Bank.objects.select_related('bank_type').prefetch_related('branches').get(id=bank_id)
        except Bank.DoesNotExist:
            return Response({'error': 'Bank not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = BankDetailSerializer(bank)
        return Response(serializer.data)


class PublicBankBranchesView(APIView):
    """支店一覧API（認証不要）

    指定した金融機関の支店一覧を返す。
    あいうえお行でフィルタリング可能。
    """
    permission_classes = [AllowAny]

    def get(self, request, bank_id):
        """
        支店一覧を返す
        ?aiueo_row=あ (あいうえお行フィルター)
        """
        queryset = BankBranch.objects.filter(bank_id=bank_id, is_active=True)

        # あいうえお行でフィルタリング
        aiueo_row = request.query_params.get('aiueo_row')
        if aiueo_row:
            queryset = queryset.filter(aiueo_row=aiueo_row)

        queryset = queryset.order_by('sort_order', 'branch_name_hiragana')
        serializer = BankBranchSerializer(queryset, many=True)
        return Response(serializer.data)
