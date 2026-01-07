"""
Message Views - メッセージ管理Views
MessageViewSet
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.db.models.functions import Coalesce
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.utils import timezone
from datetime import datetime
import re

from apps.core.permissions import IsTenantUser
from ..models import Channel, Message, ChatLog, MessageReaction
from ..serializers import MessageSerializer, MessageCreateSerializer
from ..services import notify_new_message, notify_message_edited, notify_message_deleted, notify_thread_reply, notify_reaction_added, notify_reaction_removed
from ..services.mention import process_message_mentions
from ..services.file_upload import save_uploaded_file, get_file_type, FileUploadError, get_file_info


class SearchResultPagination(PageNumberPagination):
    """検索結果用のページネーション"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class MessageViewSet(viewsets.ModelViewSet):
    """メッセージビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]

    def get_tenant_id(self):
        """tenant_idを取得（request.tenant_idまたはユーザーの保護者プロファイルから）"""
        tenant_id = getattr(self.request, 'tenant_id', None)
        if not tenant_id and hasattr(self.request.user, 'guardian_profile') and self.request.user.guardian_profile:
            tenant_id = self.request.user.guardian_profile.tenant_id
        return tenant_id

    def get_queryset(self):
        from apps.core.permissions import is_admin_user
        tenant_id = self.get_tenant_id()
        queryset = Message.objects.filter(
            is_deleted=False
        ).select_related('channel', 'sender', 'sender_guardian', 'reply_to', 'channel__guardian', 'channel__school')

        # 管理者以外はテナントでフィルタ
        if not is_admin_user(self.request.user):
            queryset = queryset.filter(tenant_id=tenant_id)

        # channel_id でフィルタ
        channel_id = self.request.query_params.get('channel_id')
        if channel_id:
            queryset = queryset.filter(channel_id=channel_id)

        # guardian_id でフィルタ（チャンネルの保護者または送信者保護者）
        guardian_id = self.request.query_params.get('guardian_id')
        if guardian_id:
            queryset = queryset.filter(
                Q(channel__guardian_id=guardian_id) | Q(sender_guardian_id=guardian_id)
            )

        # 作成日時の昇順（古いメッセージが先）
        return queryset.order_by('created_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return MessageCreateSerializer
        return MessageSerializer

    def perform_create(self, serializer):
        # 保護者の場合は sender_guardian も設定
        sender_guardian = None
        if hasattr(self.request.user, 'guardian_profile') and self.request.user.guardian_profile:
            sender_guardian = self.request.user.guardian_profile

        tenant_id = self.get_tenant_id()

        # tenant_idがない場合（管理者等）、チャンネルから取得
        if not tenant_id:
            channel_id = serializer.validated_data.get('channel')
            if channel_id:
                channel = Channel.objects.filter(id=channel_id.id if hasattr(channel_id, 'id') else channel_id).first()
                if channel:
                    tenant_id = channel.tenant_id

        serializer.save(
            tenant_id=tenant_id,
            sender=self.request.user,
            sender_guardian=sender_guardian
        )

    def create(self, request, *args, **kwargs):
        """メッセージ作成（レスポンスは詳細シリアライザーを使用）"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[MessageViewSet.create] Received data: {request.data}")

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"[MessageViewSet.create] Validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        self.perform_create(serializer)
        message = serializer.instance

        # チャットログを作成
        try:
            tenant_id = self.get_tenant_id()
            chat_log = ChatLog.create_from_message(message, tenant_id)
            logger.info(f"[MessageViewSet.create] ChatLog created: {chat_log.id}")
        except Exception as e:
            logger.error(f"[MessageViewSet.create] Failed to create ChatLog: {e}")

        # WebSocket通知を送信
        try:
            notify_new_message(str(message.channel_id), message)
            logger.info(f"[MessageViewSet.create] WebSocket notification sent for message {message.id}")

            # スレッド返信の場合は追加通知
            if message.reply_to:
                notify_thread_reply(str(message.channel_id), message.reply_to, message)
                logger.info(f"[MessageViewSet.create] Thread reply notification sent for message {message.id}")
        except Exception as e:
            logger.error(f"[MessageViewSet.create] Failed to send WebSocket notification: {e}")

        # メンション処理
        try:
            mentions = process_message_mentions(message)
            if mentions:
                logger.info(f"[MessageViewSet.create] Processed {len(mentions)} mentions for message {message.id}")
        except Exception as e:
            logger.error(f"[MessageViewSet.create] Failed to process mentions: {e}")

        # レスポンスは詳細シリアライザーを使用
        response_serializer = MessageSerializer(message)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def edit(self, request, pk=None):
        """メッセージ編集"""
        message = self.get_object()
        if message.sender != request.user:
            return Response(
                {'error': '自分のメッセージのみ編集できます'},
                status=status.HTTP_403_FORBIDDEN
            )

        message.content = request.data.get('content', message.content)
        message.is_edited = True
        message.edited_at = timezone.now()
        message.save()

        # WebSocket通知を送信
        try:
            notify_message_edited(str(message.channel_id), message)
        except Exception:
            pass  # 通知失敗は無視

        return Response(MessageSerializer(message).data)

    @action(detail=True, methods=['post'])
    def delete_message(self, request, pk=None):
        """メッセージ削除（論理削除）"""
        message = self.get_object()
        if message.sender != request.user:
            return Response(
                {'error': '自分のメッセージのみ削除できます'},
                status=status.HTTP_403_FORBIDDEN
            )

        channel_id = str(message.channel_id)
        message_id = str(message.id)

        message.is_deleted = True
        message.save(update_fields=['is_deleted'])

        # WebSocket通知を送信
        try:
            notify_message_deleted(channel_id, message_id)
        except Exception:
            pass  # 通知失敗は無視

        return Response({'status': 'deleted'})

    @action(detail=True, methods=['get'])
    def thread(self, request, pk=None):
        """スレッド（返信）メッセージ一覧取得"""
        parent_message = self.get_object()

        # 返信メッセージを取得
        replies = Message.objects.filter(
            reply_to=parent_message,
            is_deleted=False
        ).select_related(
            'sender', 'sender_guardian'
        ).order_by('created_at')

        serializer = MessageSerializer(replies, many=True)

        return Response({
            'parent': MessageSerializer(parent_message).data,
            'replies': serializer.data,
            'total_count': replies.count()
        })

    @action(detail=True, methods=['post'], url_path='reactions')
    def add_reaction(self, request, pk=None):
        """リアクション（絵文字）を追加"""
        message = self.get_object()
        emoji = request.data.get('emoji', '').strip()

        if not emoji:
            return Response(
                {'error': '絵文字を指定してください'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 既存のリアクションをチェック
        reaction, created = MessageReaction.objects.get_or_create(
            message=message,
            user=request.user,
            emoji=emoji,
        )

        if not created:
            return Response(
                {'error': '既にリアクション済みです'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # WebSocket通知
        try:
            notify_reaction_added(
                str(message.channel_id),
                str(message.id),
                emoji,
                str(request.user.id),
                request.user.full_name or request.user.email
            )
        except Exception:
            pass

        return Response({
            'id': str(reaction.id),
            'emoji': emoji,
            'message_id': str(message.id),
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path='reactions/(?P<emoji>[^/]+)')
    def remove_reaction(self, request, pk=None, emoji=None):
        """リアクション（絵文字）を削除"""
        message = self.get_object()

        if not emoji:
            return Response(
                {'error': '絵文字を指定してください'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # URLデコード（絵文字がエンコードされている場合）
        import urllib.parse
        emoji = urllib.parse.unquote(emoji)

        # リアクションを取得して削除
        try:
            reaction = MessageReaction.objects.get(
                message=message,
                user=request.user,
                emoji=emoji,
            )
            reaction.delete()

            # WebSocket通知
            try:
                notify_reaction_removed(
                    str(message.channel_id),
                    str(message.id),
                    emoji,
                    str(request.user.id)
                )
            except Exception:
                pass

            return Response({'status': 'removed'})

        except MessageReaction.DoesNotExist:
            return Response(
                {'error': 'リアクションが見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload(self, request):
        """
        ファイルをアップロードしてメッセージを作成

        リクエストパラメータ:
        - file: アップロードするファイル（必須）
        - channel_id: チャンネルID（必須）
        - content: テキスト内容（任意）
        - reply_to: 返信先メッセージID（任意）
        """
        import logging
        logger = logging.getLogger(__name__)

        file = request.FILES.get('file')
        channel_id = request.data.get('channel_id')
        content = request.data.get('content', '')
        reply_to_id = request.data.get('reply_to')

        # バリデーション
        if not file:
            return Response(
                {'error': 'ファイルが選択されていません'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not channel_id:
            return Response(
                {'error': 'チャンネルIDが必要です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # チャンネルの存在確認と権限チェック
        try:
            channel = Channel.objects.get(id=channel_id)
        except Channel.DoesNotExist:
            return Response(
                {'error': 'チャンネルが見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        # ファイル情報を取得
        try:
            file_info = get_file_info(file)
            logger.info(f"[MessageViewSet.upload] File info: {file_info}")
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ファイルをアップロード
        try:
            file_url, original_name = save_uploaded_file(file, channel_id)
            logger.info(f"[MessageViewSet.upload] File saved: {file_url}")
        except FileUploadError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        # メッセージタイプを決定
        message_type = get_file_type(file.name)

        # 返信先メッセージの取得
        reply_to = None
        if reply_to_id:
            try:
                reply_to = Message.objects.get(id=reply_to_id, channel=channel, is_deleted=False)
            except Message.DoesNotExist:
                pass

        # 保護者情報の取得
        sender_guardian = None
        if hasattr(request.user, 'guardian_profile') and request.user.guardian_profile:
            sender_guardian = request.user.guardian_profile

        # tenant_idの取得
        tenant_id = getattr(request, 'tenant_id', None)
        if not tenant_id and sender_guardian:
            tenant_id = sender_guardian.tenant_id
        if not tenant_id:
            tenant_id = channel.tenant_id

        # メッセージを作成
        message = Message.objects.create(
            tenant_id=tenant_id,
            channel=channel,
            message_type=message_type,
            sender=request.user,
            sender_guardian=sender_guardian,
            content=content or original_name,  # 内容がなければファイル名を使用
            attachment_url=file_url,
            attachment_name=original_name,
            reply_to=reply_to,
        )

        # チャットログを作成
        try:
            chat_log = ChatLog.create_from_message(message, tenant_id)
            logger.info(f"[MessageViewSet.upload] ChatLog created: {chat_log.id}")
        except Exception as e:
            logger.error(f"[MessageViewSet.upload] Failed to create ChatLog: {e}")

        # WebSocket通知を送信
        try:
            notify_new_message(str(message.channel_id), message)
            logger.info(f"[MessageViewSet.upload] WebSocket notification sent for message {message.id}")

            # スレッド返信の場合は追加通知
            if message.reply_to:
                notify_thread_reply(str(message.channel_id), message.reply_to, message)
        except Exception as e:
            logger.error(f"[MessageViewSet.upload] Failed to send WebSocket notification: {e}")

        # メンション処理
        try:
            mentions = process_message_mentions(message)
            if mentions:
                logger.info(f"[MessageViewSet.upload] Processed {len(mentions)} mentions")
        except Exception as e:
            logger.error(f"[MessageViewSet.upload] Failed to process mentions: {e}")

        # レスポンス
        response_serializer = MessageSerializer(message)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        メッセージを検索

        クエリパラメータ:
        - q: 検索キーワード（必須）
        - channel_id: チャンネルIDでフィルタ（任意）
        - sender_id: 送信者IDでフィルタ（任意）
        - date_from: 開始日（YYYY-MM-DD）（任意）
        - date_to: 終了日（YYYY-MM-DD）（任意）
        - page: ページ番号（任意、デフォルト1）
        - page_size: 1ページあたりの件数（任意、デフォルト20、最大100）
        """
        import logging
        logger = logging.getLogger(__name__)

        query = request.query_params.get('q', '').strip()

        if not query:
            return Response(
                {'error': '検索キーワードを入力してください'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(query) < 2:
            return Response(
                {'error': '検索キーワードは2文字以上入力してください'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ベースクエリ
        from apps.core.permissions import is_admin_user
        tenant_id = self.get_tenant_id()

        queryset = Message.objects.filter(
            is_deleted=False
        ).select_related(
            'channel', 'sender', 'sender_guardian',
            'channel__guardian', 'channel__school'
        )

        # 管理者以外はテナントでフィルタ
        if not is_admin_user(request.user):
            queryset = queryset.filter(tenant_id=tenant_id)

        # ユーザーがアクセス可能なチャンネルのみ
        # スタッフはINTERNAL、ADMINは全て
        if not is_admin_user(request.user):
            # ユーザーが参加しているチャンネルのみ
            from ..models import ChannelMember
            user_channels = ChannelMember.objects.filter(
                user=request.user
            ).values_list('channel_id', flat=True)
            queryset = queryset.filter(channel_id__in=user_channels)

        # チャンネルIDでフィルタ
        channel_id = request.query_params.get('channel_id')
        if channel_id:
            queryset = queryset.filter(channel_id=channel_id)

        # 送信者IDでフィルタ
        sender_id = request.query_params.get('sender_id')
        if sender_id:
            queryset = queryset.filter(sender_id=sender_id)

        # 日付範囲でフィルタ
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        if date_from:
            try:
                date_from_dt = datetime.strptime(date_from, '%Y-%m-%d')
                queryset = queryset.filter(created_at__date__gte=date_from_dt.date())
            except ValueError:
                pass

        if date_to:
            try:
                date_to_dt = datetime.strptime(date_to, '%Y-%m-%d')
                queryset = queryset.filter(created_at__date__lte=date_to_dt.date())
            except ValueError:
                pass

        # PostgreSQL全文検索を試行、失敗時はicontainsにフォールバック
        try:
            # 日本語対応のため、simple設定で検索ベクトルを作成
            search_vector = SearchVector('content', config='simple')
            search_query = SearchQuery(query, config='simple')

            queryset = queryset.annotate(
                search=search_vector,
                rank=SearchRank(search_vector, search_query)
            ).filter(
                Q(search=search_query) | Q(content__icontains=query)
            ).order_by('-rank', '-created_at')
        except Exception as e:
            # 全文検索が使えない場合はicontainsでフォールバック
            logger.warning(f"[MessageViewSet.search] Full-text search failed, using icontains: {e}")
            queryset = queryset.filter(
                content__icontains=query
            ).order_by('-created_at')

        # ページネーション
        paginator = SearchResultPagination()
        page = paginator.paginate_queryset(queryset, request)

        if page is not None:
            serializer = MessageSerializer(page, many=True)
            results = serializer.data

            # 検索結果にハイライト情報を追加
            for result in results:
                result['highlight'] = self._highlight_text(result.get('content', ''), query)

            return paginator.get_paginated_response(results)

        serializer = MessageSerializer(queryset[:100], many=True)
        results = serializer.data

        for result in results:
            result['highlight'] = self._highlight_text(result.get('content', ''), query)

        return Response({
            'count': len(results),
            'results': results
        })

    def _highlight_text(self, text: str, query: str, context_length: int = 50) -> str:
        """
        検索キーワードをハイライトした抜粋を生成

        Args:
            text: 元のテキスト
            query: 検索キーワード
            context_length: キーワード前後の文字数

        Returns:
            ハイライト付きの抜粋テキスト
        """
        if not text or not query:
            return text[:100] + '...' if len(text) > 100 else text

        # 大文字小文字を無視してマッチ位置を検索
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        match = pattern.search(text)

        if not match:
            return text[:100] + '...' if len(text) > 100 else text

        start_pos = match.start()
        end_pos = match.end()

        # 抜粋の開始位置と終了位置を計算
        excerpt_start = max(0, start_pos - context_length)
        excerpt_end = min(len(text), end_pos + context_length)

        # 抜粋を作成
        excerpt = text[excerpt_start:excerpt_end]

        # プレフィックスとサフィックスを追加
        if excerpt_start > 0:
            excerpt = '...' + excerpt
        if excerpt_end < len(text):
            excerpt = excerpt + '...'

        # ハイライト用のマーカーを追加（フロントエンドで<mark>タグに変換）
        highlighted = pattern.sub(r'[[HIGHLIGHT]]\g<0>[[/HIGHLIGHT]]', excerpt)

        return highlighted
