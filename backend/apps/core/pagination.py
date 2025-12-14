"""
Custom Pagination Classes
"""
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsSetPagination(PageNumberPagination):
    """標準ページネーション"""
    page_size = 20
    page_size_query_param = 'limit'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'data': data,
            'meta': {
                'total': self.page.paginator.count,
                'page': self.page.number,
                'limit': self.get_page_size(self.request),
                'total_pages': self.page.paginator.num_pages,
            },
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
            }
        })


class LargeResultsSetPagination(PageNumberPagination):
    """大量データ用ページネーション"""
    page_size = 100
    page_size_query_param = 'limit'
    max_page_size = 500

    def get_paginated_response(self, data):
        return Response({
            'data': data,
            'meta': {
                'total': self.page.paginator.count,
                'page': self.page.number,
                'limit': self.get_page_size(self.request),
                'total_pages': self.page.paginator.num_pages,
            },
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
            }
        })


class AdminResultsSetPagination(PageNumberPagination):
    """管理画面用ページネーション（大量データ対応）"""
    page_size = 100
    page_size_query_param = 'limit'
    max_page_size = 10000

    def get_paginated_response(self, data):
        return Response({
            'data': data,
            'meta': {
                'total': self.page.paginator.count,
                'page': self.page.number,
                'limit': self.get_page_size(self.request),
                'total_pages': self.page.paginator.num_pages,
            },
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
            }
        })
