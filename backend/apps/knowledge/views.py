"""
Knowledge Views
"""
import os
import uuid
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
from django.conf import settings
from django.core.files.storage import default_storage

from .models import ManualCategory, Manual, TemplateCategory, ChatTemplate
from .serializers import (
    ManualCategorySerializer,
    ManualListSerializer, ManualDetailSerializer, ManualCreateUpdateSerializer,
    TemplateCategorySerializer,
    ChatTemplateListSerializer, ChatTemplateDetailSerializer,
    ChatTemplateCreateUpdateSerializer, ChatTemplateRenderSerializer,
)


class ManualCategoryViewSet(viewsets.ModelViewSet):
    """マニュアルカテゴリViewSet"""
    serializer_class = ManualCategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ManualCategory.objects.filter(
            tenant_ref_id=self.request.user.tenant_id,
            is_active=True
        ).order_by('sort_order', 'name')

    def perform_create(self, serializer):
        serializer.save(tenant_ref_id=self.request.user.tenant_id)


class ManualViewSet(viewsets.ModelViewSet):
    """マニュアルViewSet"""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Manual.objects.filter(
            tenant_ref_id=self.request.user.tenant_id
        ).select_related('category', 'author').order_by('-is_pinned', '-updated_at')

        # フィルター
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category_id=category)

        is_published = self.request.query_params.get('is_published')
        if is_published is not None:
            queryset = queryset.filter(is_published=is_published.lower() == 'true')

        # 検索
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(content__icontains=search) |
                Q(summary__icontains=search) |
                Q(tags__icontains=search)
            )

        # タグフィルター
        tag = self.request.query_params.get('tag')
        if tag:
            queryset = queryset.filter(tags__contains=[tag])

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return ManualListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ManualCreateUpdateSerializer
        return ManualDetailSerializer

    def perform_create(self, serializer):
        serializer.save(tenant_ref_id=self.request.user.tenant_id)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # 閲覧数をインクリメント
        instance.increment_view_count()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def pinned(self, request):
        """ピン留めされたマニュアル一覧"""
        queryset = self.get_queryset().filter(is_pinned=True, is_published=True)
        serializer = ManualListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """最近更新されたマニュアル"""
        queryset = self.get_queryset().filter(is_published=True)[:10]
        serializer = ManualListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def popular(self, request):
        """よく閲覧されるマニュアル"""
        queryset = self.get_queryset().filter(is_published=True).order_by('-view_count')[:10]
        serializer = ManualListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_image(self, request):
        """マニュアル用の画像をアップロード

        画像をアップロードしてURLを返す。
        マニュアルのcontent内でMarkdown形式で参照可能:
        ![説明](返されたURL)
        """
        file = request.FILES.get('image') or request.FILES.get('file')
        if not file:
            return Response(
                {'error': '画像ファイルを指定してください'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 拡張子チェック
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        _, ext = os.path.splitext(file.name.lower())
        if ext not in allowed_extensions:
            return Response(
                {'error': f'許可されていないファイル形式です。対応形式: {", ".join(allowed_extensions)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ファイルサイズチェック（10MB）
        max_size = 10 * 1024 * 1024
        if file.size > max_size:
            return Response(
                {'error': 'ファイルサイズが大きすぎます。最大10MBまでです'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ユニークなファイル名を生成
        unique_id = uuid.uuid4().hex[:12]
        new_filename = f"{unique_id}{ext}"
        file_path = f"manual_images/{new_filename}"

        try:
            # ファイルを保存
            saved_path = default_storage.save(file_path, file)

            # URLを生成
            file_url = default_storage.url(saved_path)

            # 相対パスの場合は絶対パスに変換
            if not file_url.startswith('http'):
                file_url = f"/{settings.MEDIA_URL}{saved_path}"

            return Response({
                'url': file_url,
                'filename': file.name,
                'markdown': f'![{file.name}]({file_url})',
            })
        except Exception as e:
            return Response(
                {'error': f'ファイルの保存に失敗しました: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TemplateCategoryViewSet(viewsets.ModelViewSet):
    """テンプレートカテゴリViewSet"""
    serializer_class = TemplateCategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TemplateCategory.objects.filter(
            tenant_ref_id=self.request.user.tenant_id,
            is_active=True
        ).order_by('sort_order', 'name')

    def perform_create(self, serializer):
        serializer.save(tenant_ref_id=self.request.user.tenant_id)


class ChatTemplateViewSet(viewsets.ModelViewSet):
    """チャットテンプレートViewSet"""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = ChatTemplate.objects.filter(
            tenant_ref_id=self.request.user.tenant_id
        ).select_related('category').order_by('-is_default', '-use_count', 'title')

        # フィルター
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category_id=category)

        template_type = self.request.query_params.get('type')
        if template_type:
            queryset = queryset.filter(template_type=template_type)

        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        # 検索
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(content__icontains=search) |
                Q(scene__icontains=search) |
                Q(tags__icontains=search)
            )

        # 場面フィルター
        scene = self.request.query_params.get('scene')
        if scene:
            queryset = queryset.filter(scene__icontains=scene)

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return ChatTemplateListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ChatTemplateCreateUpdateSerializer
        return ChatTemplateDetailSerializer

    def perform_create(self, serializer):
        serializer.save(tenant_ref_id=self.request.user.tenant_id)

    @action(detail=True, methods=['post'])
    def render(self, request, pk=None):
        """テンプレートをレンダリング"""
        template = self.get_object()
        serializer = ChatTemplateRenderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        rendered = template.render(serializer.validated_data['context'])
        return Response({
            'rendered': rendered,
            'subject': template.subject,
        })

    @action(detail=True, methods=['post'])
    def use(self, request, pk=None):
        """テンプレート使用をカウント"""
        template = self.get_object()
        template.increment_use_count()
        return Response({'use_count': template.use_count})

    @action(detail=False, methods=['get'])
    def popular(self, request):
        """よく使われるテンプレート"""
        queryset = self.get_queryset().filter(is_active=True).order_by('-use_count')[:10]
        serializer = ChatTemplateListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_scene(self, request):
        """場面別テンプレート一覧"""
        queryset = self.get_queryset().filter(is_active=True)
        scenes = queryset.values_list('scene', flat=True).distinct()

        result = {}
        for scene in scenes:
            if scene:
                templates = queryset.filter(scene=scene)
                result[scene] = ChatTemplateListSerializer(templates, many=True).data

        return Response(result)
