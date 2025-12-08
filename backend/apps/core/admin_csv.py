"""CSV Import/Export mixin for Django Admin."""
import csv
import io
from django.contrib import admin, messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.html import format_html

from .csv_utils import CSVImporter, CSVExporter


class CSVImportExportMixin:
    """Mixin to add CSV import/export functionality to ModelAdmin."""

    # CSV Import settings
    csv_importer_class = CSVImporter
    csv_import_fields = {}
    csv_required_fields = []
    csv_unique_fields = []

    # CSV Export settings
    csv_exporter_class = CSVExporter
    csv_export_fields = []
    csv_export_headers = {}

    change_list_template = 'admin/csv_change_list.html'

    def get_urls(self):
        urls = super().get_urls()
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        custom_urls = [
            path(
                'import-csv/',
                self.admin_site.admin_view(self.import_csv_view),
                name=f'{app_label}_{model_name}_import_csv'
            ),
            path(
                'export-csv/',
                self.admin_site.admin_view(self.export_csv_view),
                name=f'{app_label}_{model_name}_export_csv'
            ),
            path(
                'download-template/',
                self.admin_site.admin_view(self.download_template_view),
                name=f'{app_label}_{model_name}_download_template'
            ),
        ]
        return custom_urls + urls

    def get_csv_importer(self, tenant_id=None):
        """Get configured CSV importer instance."""
        importer_class = getattr(self, 'csv_importer_class', CSVImporter)
        return importer_class(
            model=self.model,
            field_mapping=self.csv_import_fields,
            required_fields=self.csv_required_fields,
            unique_fields=self.csv_unique_fields,
            tenant_id=tenant_id
        )

    def get_csv_exporter(self):
        """Get configured CSV exporter instance."""
        return CSVExporter(
            model=self.model,
            export_fields=self.csv_export_fields,
            export_headers=self.csv_export_headers
        )

    def import_csv_view(self, request):
        """Handle CSV import."""
        if request.method == 'POST' and request.FILES.get('csv_file'):
            csv_file = request.FILES['csv_file']
            update_existing = request.POST.get('update_existing', 'on') == 'on'

            # Get tenant_id from request user if available
            tenant_id = None
            if hasattr(request.user, 'tenant_id'):
                tenant_id = request.user.tenant_id

            importer = self.get_csv_importer(tenant_id=tenant_id)
            result = importer.import_csv(csv_file, update_existing=update_existing)

            if result['success']:
                messages.success(
                    request,
                    f"インポート完了: {result['created']}件作成, "
                    f"{result['updated']}件更新, {result['skipped']}件スキップ"
                )
            else:
                messages.warning(
                    request,
                    f"インポート完了（エラーあり）: {result['created']}件作成, "
                    f"{result['updated']}件更新, {result['skipped']}件スキップ, "
                    f"{len(result['errors'])}件エラー"
                )
                for error in result['errors'][:10]:
                    messages.error(
                        request,
                        f"行{error['row']}: {error['message']}"
                    )

            return redirect(
                reverse(
                    f'admin:{self.model._meta.app_label}_{self.model._meta.model_name}_changelist'
                )
            )

        context = {
            **self.admin_site.each_context(request),
            'title': f'{self.model._meta.verbose_name} CSVインポート',
            'opts': self.model._meta,
            'csv_fields': self.csv_import_fields,
            'required_fields': self.csv_required_fields,
        }
        return render(request, 'admin/csv_import.html', context)

    def export_csv_view(self, request):
        """Handle CSV export."""
        exporter = self.get_csv_exporter()
        queryset = self.get_queryset(request)

        # Apply any filters from the changelist
        if hasattr(self, 'get_changelist_instance'):
            try:
                cl = self.get_changelist_instance(request)
                queryset = cl.get_queryset(request)
            except Exception:
                pass

        csv_content = exporter.export_csv(queryset)

        response = HttpResponse(csv_content, content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = (
            f'attachment; filename="{self.model._meta.model_name}_export.csv"'
        )
        # Add BOM for Excel compatibility
        response.content = b'\xef\xbb\xbf' + csv_content.encode('utf-8')
        return response

    def download_template_view(self, request):
        """Download CSV template file."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Write headers (Japanese field names)
        headers = list(self.csv_import_fields.keys())
        writer.writerow(headers)

        response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = (
            f'attachment; filename="{self.model._meta.model_name}_template.csv"'
        )
        response.content = b'\xef\xbb\xbf' + output.getvalue().encode('utf-8')
        return response

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['has_csv_import'] = bool(self.csv_import_fields)
        extra_context['has_csv_export'] = bool(self.csv_export_fields)
        return super().changelist_view(request, extra_context=extra_context)
