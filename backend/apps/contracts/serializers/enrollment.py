"""
Enrollment Serializers - 講習・検定申込シリアライザ
SeminarEnrollmentListSerializer, SeminarEnrollmentDetailSerializer,
CertificationEnrollmentListSerializer, CertificationEnrollmentDetailSerializer
"""
from rest_framework import serializers
from ..models import SeminarEnrollment, CertificationEnrollment


class SeminarEnrollmentListSerializer(serializers.ModelSerializer):
    """講習申込一覧"""
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    seminar_name = serializers.CharField(source='seminar.seminar_name', read_only=True)

    class Meta:
        model = SeminarEnrollment
        fields = [
            'id', 'student', 'student_name',
            'seminar', 'seminar_name',
            'status', 'unit_price', 'final_price', 'applied_at'
        ]


class SeminarEnrollmentDetailSerializer(serializers.ModelSerializer):
    """講習申込詳細"""
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    seminar_name = serializers.CharField(source='seminar.seminar_name', read_only=True)

    class Meta:
        model = SeminarEnrollment
        fields = [
            'id', 'student', 'student_name',
            'seminar', 'seminar_name',
            'status', 'applied_at',
            'unit_price', 'discount_amount', 'final_price',
            'billing_month', 'is_required', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CertificationEnrollmentListSerializer(serializers.ModelSerializer):
    """検定申込一覧"""
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    certification_name = serializers.CharField(source='certification.certification_name', read_only=True)

    class Meta:
        model = CertificationEnrollment
        fields = [
            'id', 'student', 'student_name',
            'certification', 'certification_name',
            'status', 'exam_fee', 'final_price', 'score', 'applied_at'
        ]


class CertificationEnrollmentDetailSerializer(serializers.ModelSerializer):
    """検定申込詳細"""
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    certification_name = serializers.CharField(source='certification.certification_name', read_only=True)

    class Meta:
        model = CertificationEnrollment
        fields = [
            'id', 'student', 'student_name',
            'certification', 'certification_name',
            'status', 'applied_at',
            'exam_fee', 'discount_amount', 'final_price',
            'billing_month', 'score', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
