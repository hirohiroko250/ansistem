"""
Student CSV Importer - 生徒用カスタムCSVインポーター
"""
from apps.core.csv_utils import CSVImporter


class StudentCSVImporter(CSVImporter):
    """生徒用カスタムCSVインポーター（FK名前解決付き）"""

    def resolve_foreign_keys(self, data: dict) -> dict:
        """名前からForeignKeyを解決"""
        from apps.schools.models import School, Brand, Grade

        # 主所属校舎
        school_name = data.pop('primary_school_name', None)
        if school_name:
            try:
                school = School.objects.filter(school_name=school_name).first()
                if school:
                    data['primary_school'] = school
            except Exception:
                pass

        # 主所属ブランド
        brand_name = data.pop('primary_brand_name', None)
        if brand_name:
            try:
                brand = Brand.objects.filter(brand_name=brand_name).first()
                if brand:
                    data['primary_brand'] = brand
            except Exception:
                pass

        # 学年
        grade_name = data.pop('grade_name', None)
        if grade_name:
            try:
                grade = Grade.objects.filter(grade_name=grade_name).first()
                if grade:
                    data['grade'] = grade
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

                # データ変換
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
