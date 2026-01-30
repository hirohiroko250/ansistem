"""
Feed Views - フィード（投稿・コメント・ブックマーク）管理Views
FeedPostViewSet, FeedCommentViewSet, FeedBookmarkViewSet
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.utils import timezone

from apps.core.permissions import IsTenantUser, IsTenantAdmin
from ..models import FeedPost, FeedComment, FeedLike, FeedCommentLike, FeedBookmark
from ..serializers import (
    FeedPostListSerializer, FeedPostDetailSerializer, FeedPostCreateSerializer,
    FeedCommentSerializer, FeedCommentCreateSerializer,
    FeedLikeSerializer, FeedBookmarkSerializer,
)


class FeedPostViewSet(viewsets.ModelViewSet):
    """フィード投稿ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]

    def _is_admin_user(self):
        """リクエストユーザーがADMIN/SUPER_ADMINかを判定"""
        user = self.request.user
        return user and user.is_authenticated and getattr(user, 'role', None) in ('ADMIN', 'SUPER_ADMIN')

    def get_queryset(self):
        # tenant_idを取得（リクエストから、またはユーザーから）
        tenant_id = getattr(self.request, 'tenant_id', None)
        if not tenant_id and self.request.user and hasattr(self.request.user, 'tenant_id'):
            tenant_id = self.request.user.tenant_id

        queryset = FeedPost.objects.filter(
            is_deleted=False,
        ).select_related('author', 'school', 'approved_by').prefetch_related('media', 'target_schools', 'target_grades')

        # 管理者は全ステータス表示可能、一般ユーザーは承認済＋公開のみ
        if self._is_admin_user():
            # 承認ステータスフィルター（管理画面用）
            approval_status = self.request.query_params.get('approval_status')
            if approval_status:
                queryset = queryset.filter(approval_status=approval_status)
        else:
            queryset = queryset.filter(
                is_published=True,
                approval_status=FeedPost.ApprovalStatus.APPROVED,
            )

        # tenant_idがある場合のみフィルタ
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        # 公開範囲フィルター
        visibility = self.request.query_params.get('visibility')
        if visibility:
            queryset = queryset.filter(visibility=visibility)

        # 校舎フィルター
        school_id = self.request.query_params.get('school_id')
        if school_id:
            queryset = queryset.filter(
                Q(school_id=school_id) |
                Q(target_schools__id=school_id) |
                Q(visibility=FeedPost.Visibility.PUBLIC)
            ).distinct()

        # ハッシュタグフィルター
        hashtag = self.request.query_params.get('hashtag')
        if hashtag:
            queryset = queryset.filter(hashtags__contains=[hashtag])

        # 投稿者フィルター
        author_id = self.request.query_params.get('author_id')
        if author_id:
            queryset = queryset.filter(author_id=author_id)

        # 固定投稿を先頭に
        return queryset.order_by('-is_pinned', '-created_at')

    def get_serializer_class(self):
        if self.action == 'list':
            return FeedPostListSerializer
        elif self.action == 'create':
            return FeedPostCreateSerializer
        return FeedPostDetailSerializer

    def get_permissions(self):
        # 承認・却下は管理者のみ
        if self.action in ['approve', 'reject']:
            return [IsAuthenticated(), IsTenantAdmin()]
        # 作成・更新・削除・ピン操作は管理者のみ
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'pin', 'unpin']:
            return [IsAuthenticated(), IsTenantAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        from django.utils import timezone as tz
        # tenant_idを取得（リクエストから、またはユーザーから）
        tenant_id = getattr(self.request, 'tenant_id', None)
        if not tenant_id and self.request.user:
            tenant_id = getattr(self.request.user, 'tenant_id', None)

        # 管理者の投稿は自動承認、それ以外は申請中
        is_admin = self._is_admin_user()
        extra_kwargs = dict(
            tenant_id=tenant_id,
            author=self.request.user,
        )
        if is_admin:
            extra_kwargs['approval_status'] = FeedPost.ApprovalStatus.APPROVED
            extra_kwargs['approved_by'] = self.request.user
            extra_kwargs['approved_at'] = tz.now()
            extra_kwargs['published_at'] = tz.now() if serializer.validated_data.get('is_published', True) else None
        else:
            extra_kwargs['approval_status'] = FeedPost.ApprovalStatus.PENDING
            extra_kwargs['is_published'] = False
            extra_kwargs['published_at'] = None

        serializer.save(**extra_kwargs)

    def retrieve(self, request, *args, **kwargs):
        """詳細取得時に閲覧数をインクリメント"""
        instance = self.get_object()
        instance.view_count += 1
        instance.save(update_fields=['view_count'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """論理削除"""
        instance = self.get_object()
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.save(update_fields=['is_deleted', 'deleted_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        """いいね"""
        post = self.get_object()
        if not post.allow_likes:
            return Response(
                {'error': 'この投稿にはいいねできません'},
                status=status.HTTP_400_BAD_REQUEST
            )

        like, created = FeedLike.objects.get_or_create(
            post=post,
            user=request.user
        )

        if created:
            post.like_count += 1
            post.save(update_fields=['like_count'])
            return Response({'status': 'liked', 'like_count': post.like_count})
        else:
            return Response({'status': 'already_liked', 'like_count': post.like_count})

    @action(detail=True, methods=['post'])
    def unlike(self, request, pk=None):
        """いいね解除"""
        post = self.get_object()
        deleted, _ = FeedLike.objects.filter(
            post=post,
            user=request.user
        ).delete()

        if deleted:
            post.like_count = max(0, post.like_count - 1)
            post.save(update_fields=['like_count'])

        return Response({'status': 'unliked', 'like_count': post.like_count})

    @action(detail=True, methods=['get'])
    def likes(self, request, pk=None):
        """いいね一覧"""
        post = self.get_object()
        likes = post.likes.select_related('user', 'guardian').all()
        page = self.paginate_queryset(likes)
        if page is not None:
            serializer = FeedLikeSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = FeedLikeSerializer(likes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def bookmark(self, request, pk=None):
        """ブックマーク"""
        post = self.get_object()
        bookmark, created = FeedBookmark.objects.get_or_create(
            post=post,
            user=request.user
        )

        if created:
            return Response({'status': 'bookmarked'})
        else:
            return Response({'status': 'already_bookmarked'})

    @action(detail=True, methods=['post'])
    def unbookmark(self, request, pk=None):
        """ブックマーク解除"""
        post = self.get_object()
        FeedBookmark.objects.filter(
            post=post,
            user=request.user
        ).delete()
        return Response({'status': 'unbookmarked'})

    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        """コメント一覧・追加"""
        post = self.get_object()

        if request.method == 'GET':
            comments = post.comments.filter(
                is_deleted=False,
                parent__isnull=True  # トップレベルのみ
            ).select_related('user', 'guardian')
            page = self.paginate_queryset(comments)
            if page is not None:
                serializer = FeedCommentSerializer(page, many=True, context={'request': request})
                return self.get_paginated_response(serializer.data)
            serializer = FeedCommentSerializer(comments, many=True, context={'request': request})
            return Response(serializer.data)

        elif request.method == 'POST':
            if not post.allow_comments:
                return Response(
                    {'error': 'この投稿にはコメントできません'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = FeedCommentCreateSerializer(data={
                **request.data,
                'post': post.id
            })
            serializer.is_valid(raise_exception=True)
            comment = serializer.save(user=request.user)

            # コメント数更新
            post.comment_count += 1
            post.save(update_fields=['comment_count'])

            return Response(
                FeedCommentSerializer(comment, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )

    @action(detail=True, methods=['post'])
    def pin(self, request, pk=None):
        """固定表示"""
        post = self.get_object()
        post.is_pinned = True
        post.pinned_at = timezone.now()
        post.save(update_fields=['is_pinned', 'pinned_at'])
        return Response(FeedPostDetailSerializer(post, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def unpin(self, request, pk=None):
        """固定表示解除"""
        post = self.get_object()
        post.is_pinned = False
        post.pinned_at = None
        post.save(update_fields=['is_pinned', 'pinned_at'])
        return Response(FeedPostDetailSerializer(post, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """投稿を承認"""
        post = self.get_object()
        if post.approval_status != FeedPost.ApprovalStatus.PENDING:
            return Response(
                {'error': '申請中の投稿のみ承認できます'},
                status=status.HTTP_400_BAD_REQUEST
            )
        post.approval_status = FeedPost.ApprovalStatus.APPROVED
        post.is_published = True
        post.approved_by = request.user
        post.approved_at = timezone.now()
        post.published_at = timezone.now()
        post.save(update_fields=[
            'approval_status', 'is_published', 'approved_by',
            'approved_at', 'published_at',
        ])
        return Response(FeedPostDetailSerializer(post, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """投稿を却下"""
        post = self.get_object()
        if post.approval_status != FeedPost.ApprovalStatus.PENDING:
            return Response(
                {'error': '申請中の投稿のみ却下できます'},
                status=status.HTTP_400_BAD_REQUEST
            )
        post.approval_status = FeedPost.ApprovalStatus.REJECTED
        post.save(update_fields=['approval_status'])
        return Response(FeedPostDetailSerializer(post, context={'request': request}).data)


class FeedCommentViewSet(viewsets.ModelViewSet):
    """フィードコメントビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    serializer_class = FeedCommentSerializer

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        return FeedComment.objects.filter(
            post__tenant_id=tenant_id,
            is_deleted=False
        ).select_related('user', 'guardian', 'parent')

    @action(detail=True, methods=['get'])
    def replies(self, request, pk=None):
        """返信一覧"""
        comment = self.get_object()
        replies = comment.replies.filter(is_deleted=False).select_related('user', 'guardian')
        serializer = FeedCommentSerializer(replies, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        """コメントいいね"""
        comment = self.get_object()
        like, created = FeedCommentLike.objects.get_or_create(
            comment=comment,
            user=request.user
        )

        if created:
            comment.like_count += 1
            comment.save(update_fields=['like_count'])
            return Response({'status': 'liked', 'like_count': comment.like_count})
        return Response({'status': 'already_liked', 'like_count': comment.like_count})

    @action(detail=True, methods=['post'])
    def unlike(self, request, pk=None):
        """コメントいいね解除"""
        comment = self.get_object()
        deleted, _ = FeedCommentLike.objects.filter(
            comment=comment,
            user=request.user
        ).delete()

        if deleted:
            comment.like_count = max(0, comment.like_count - 1)
            comment.save(update_fields=['like_count'])

        return Response({'status': 'unliked', 'like_count': comment.like_count})

    def destroy(self, request, *args, **kwargs):
        """論理削除"""
        comment = self.get_object()
        # 自分のコメントのみ削除可能
        if comment.user != request.user:
            return Response(
                {'error': '自分のコメントのみ削除できます'},
                status=status.HTTP_403_FORBIDDEN
            )

        comment.is_deleted = True
        comment.save(update_fields=['is_deleted'])

        # 投稿のコメント数を減らす
        comment.post.comment_count = max(0, comment.post.comment_count - 1)
        comment.post.save(update_fields=['comment_count'])

        return Response(status=status.HTTP_204_NO_CONTENT)


class FeedBookmarkViewSet(viewsets.ReadOnlyModelViewSet):
    """フィードブックマークビューセット（自分のブックマーク一覧）"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    serializer_class = FeedBookmarkSerializer

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        return FeedBookmark.objects.filter(
            post__tenant_id=tenant_id,
            user=self.request.user,
            post__is_deleted=False
        ).select_related('post__author', 'post__school').order_by('-created_at')
