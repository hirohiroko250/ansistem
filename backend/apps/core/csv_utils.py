"""CSV Import/Export utilities for Django models."""
import csv
import io
from typing import Any, Dict, List, Optional, Type


class CSVImporter:
    """Base CSV importer class."""

    model = None
    field_mapping: Dict[str, str] = {}
    required_fields: List[str] = []
    unique_fields: List[str] = []

    def __init__(self, model=None, field_mapping=None, required_fields=None,
                 unique_fields=None, tenant_id=None):
        self.model = model or self.model
        self.field_mapping = field_mapping or self.field_mapping
        self.required_fields = required_fields or self.required_fields
        self.unique_fields = unique_fields or self.unique_fields
        self.tenant_id = tenant_id
        self.errors = []
        self.created_count = 0
        self.updated_count = 0
        self.skipped_count = 0

    def parse_csv(self, csv_file) -> List[Dict[str, str]]:
        """Parse CSV file and return list of row dictionaries."""
        if hasattr(csv_file, 'read'):
            content = csv_file.read()
            if isinstance(content, bytes):
                content = content.decode('utf-8-sig')
        else:
            content = csv_file

        reader = csv.DictReader(io.StringIO(content))
        return list(reader)

    def validate_row(self, row: Dict[str, str], row_num: int) -> bool:
        """Validate a single row."""
        for field in self.required_fields:
            if field not in row or not row[field]:
                self.errors.append({
                    'row': row_num,
                    'field': field,
                    'message': f'必須フィールド "{field}" が空です'
                })
                return False
        return True

    def convert_value(self, field_name: str, value: str, field_type=None) -> Any:
        """Convert string value to appropriate type."""
        if value is None or value == '':
            return None

        value = value.strip()

        # Boolean conversion
        if value.lower() in ('true', '1', 'yes', 'はい', 'o', '○'):
            return True
        if value.lower() in ('false', '0', 'no', 'いいえ', 'x', '×'):
            return False

        # Try numeric conversion
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        return value

    def get_or_create_instance(self, data: Dict[str, Any]) -> tuple:
        """Get or create model instance based on unique fields."""
        lookup = {}
        for field in self.unique_fields:
            if field in data:
                lookup[field] = data[field]

        if lookup:
            try:
                instance = self.model.objects.get(**lookup)
                return instance, False
            except self.model.DoesNotExist:
                pass

        return self.model(), True

    def resolve_foreign_keys(self, data: dict) -> dict:
        """Override this to resolve foreign key relationships."""
        return data

    def import_csv(self, csv_file, update_existing: bool = True) -> Dict[str, Any]:
        """Import CSV data into the model."""
        from django.db import transaction

        self.errors = []
        self.created_count = 0
        self.updated_count = 0
        self.skipped_count = 0

        rows = self.parse_csv(csv_file)

        with transaction.atomic():
            for row_num, row in enumerate(rows, start=2):
                if not self.validate_row(row, row_num):
                    self.skipped_count += 1
                    continue

                data = {}
                for csv_field, model_field in self.field_mapping.items():
                    if csv_field in row:
                        value = row[csv_field]
                        data[model_field] = self.convert_value(model_field, value)

                # FK resolution
                data = self.resolve_foreign_keys(data)

                # Tenant ID
                if self.tenant_id and hasattr(self.model, 'tenant_id'):
                    data['tenant_id'] = self.tenant_id

                try:
                    instance, is_new = self.get_or_create_instance(data)

                    if not is_new and not update_existing:
                        self.skipped_count += 1
                        continue

                    for field_name, value in data.items():
                        if value is not None:
                            setattr(instance, field_name, value)

                    instance.save()

                    if is_new:
                        self.created_count += 1
                    else:
                        self.updated_count += 1

                except Exception as e:
                    self.errors.append({
                        'row': row_num,
                        'field': None,
                        'message': str(e)
                    })
                    self.skipped_count += 1

        return {
            'success': len(self.errors) == 0,
            'created': self.created_count,
            'updated': self.updated_count,
            'skipped': self.skipped_count,
            'errors': self.errors
        }


class CSVExporter:
    """Base CSV exporter class."""

    model = None
    export_fields: List[str] = []
    export_headers: Dict[str, str] = {}

    def __init__(self, model=None, export_fields=None, export_headers=None):
        self.model = model or self.model
        self.export_fields = export_fields or self.export_fields
        self.export_headers = export_headers or self.export_headers

    def get_value(self, obj, field_name: str) -> str:
        """Get field value, supporting dotted notation for related fields."""
        parts = field_name.split('.')
        value = obj
        for part in parts:
            if value is None:
                return ''
            value = getattr(value, part, None)
        return str(value) if value is not None else ''

    def export_csv(self, queryset=None) -> str:
        """Export queryset to CSV string."""
        if queryset is None:
            queryset = self.model.objects.all()

        output = io.StringIO()
        writer = csv.writer(output)

        # Write headers
        headers = [self.export_headers.get(f, f) for f in self.export_fields]
        writer.writerow(headers)

        # Write data
        for obj in queryset:
            row = [self.get_value(obj, field) for field in self.export_fields]
            writer.writerow(row)

        return output.getvalue()


class CSVMixin:
    """Mixin for views that need CSV import/export."""

    csv_importer_class = CSVImporter
    csv_exporter_class = CSVExporter
    csv_import_fields = {}
    csv_required_fields = []
    csv_unique_fields = []
    csv_export_fields = []
    csv_export_headers = {}

    def get_csv_importer(self):
        """Get configured CSV importer instance."""
        return self.csv_importer_class(
            model=self.get_queryset().model,
            field_mapping=self.csv_import_fields,
            required_fields=self.csv_required_fields,
            unique_fields=self.csv_unique_fields
        )

    def get_csv_exporter(self):
        """Get configured CSV exporter instance."""
        return self.csv_exporter_class(
            model=self.get_queryset().model,
            export_fields=self.csv_export_fields,
            export_headers=self.csv_export_headers
        )
