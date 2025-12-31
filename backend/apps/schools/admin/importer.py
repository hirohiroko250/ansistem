"""
Schools CSV Importers - CSVインポーター
SchoolCSVImporter, ClassroomCSVImporter, LessonCalendarCSVImporter
"""
from apps.core.csv_utils import CSVImporter
from ..models import Brand, School


class SchoolCSVImporter(CSVImporter):
    """校舎用カスタムCSVインポーター（FK名前解決付き）"""

    def resolve_foreign_keys(self, data: dict) -> dict:
        """名前からForeignKeyを解決"""
        # ブランド（ブランド名で検索）
        brand_name = data.pop('brand_name', None)
        if brand_name:
            try:
                brand = Brand.objects.filter(brand_name=brand_name).first()
                if brand:
                    data['brand'] = brand
            except Exception:
                pass
        return data

    def import_csv(self, csv_file, update_existing: bool = True):
        """CSVインポート（FK解決付き）"""
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
                        try:
                            field = self.model._meta.get_field(model_field)
                            field_type = type(field)
                        except Exception:
                            field_type = str
                        data[model_field] = self.convert_value(model_field, value, field_type)

                # FK解決
                data = self.resolve_foreign_keys(data)

                # テナントID設定
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


class ClassroomCSVImporter(CSVImporter):
    """教室用カスタムCSVインポーター（FK名前解決付き）"""

    def resolve_foreign_keys(self, data: dict) -> dict:
        """名前からForeignKeyを解決"""
        # 校舎（校舎名で検索）
        school_name = data.pop('school_name', None)
        if school_name:
            try:
                school = School.objects.filter(school_name=school_name).first()
                if school:
                    data['school'] = school
            except Exception:
                pass
        return data

    def import_csv(self, csv_file, update_existing: bool = True):
        """CSVインポート（FK解決付き）"""
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
                        try:
                            field = self.model._meta.get_field(model_field)
                            field_type = type(field)
                        except Exception:
                            field_type = str
                        data[model_field] = self.convert_value(model_field, value, field_type)

                # FK解決
                data = self.resolve_foreign_keys(data)

                # テナントID設定
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


class LessonCalendarCSVImporter(CSVImporter):
    """開講カレンダー用カスタムCSVインポーター（カレンダーIDからブランド・校舎自動解析）"""

    def resolve_foreign_keys(self, data: dict) -> dict:
        """カレンダーIDからブランド・校舎を自動解析してForeignKeyを解決

        カレンダーID形式: 1001_SKAEC_A = 校舎コード_ブランドコード_タイプ
        例: 1001_SKAEC_A → 校舎コード=1001, ブランドコード=SKAEC
        """
        calendar_code = data.get('calendar_code', '')

        if calendar_code and '_' in calendar_code:
            parts = calendar_code.split('_')
            if len(parts) >= 2:
                school_code = parts[0]  # 1001
                brand_code = parts[1]   # SKAEC

                # ブランド検索
                try:
                    brand = Brand.objects.filter(brand_code=brand_code).first()
                    if brand:
                        data['brand'] = brand
                except Exception:
                    pass

                # 校舎検索
                try:
                    school = School.objects.filter(school_code=school_code).first()
                    if school:
                        data['school'] = school
                except Exception:
                    pass

        return data

    def import_csv(self, csv_file, update_existing: bool = True):
        """CSVインポート（FK解決付き）"""
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
                        try:
                            field = self.model._meta.get_field(model_field)
                            field_type = type(field)
                        except Exception:
                            field_type = str
                        data[model_field] = self.convert_value(model_field, value, field_type)

                # FK解決
                data = self.resolve_foreign_keys(data)

                # テナントID設定
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
