"""
Communications Services
後方互換性のためのリダイレクト
実際の実装は services/ ディレクトリを参照
"""
from .services import BotService, NotificationService

__all__ = ['BotService', 'NotificationService']
