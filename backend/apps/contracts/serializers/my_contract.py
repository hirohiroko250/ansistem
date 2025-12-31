"""
My Contract Serializers - 顧客用契約シリアライザ（保護者向け）
MyContractSerializer, MyStudentItemSerializer
"""
from rest_framework import serializers
from ..models import Contract, StudentItem


class MyContractStudentSerializer(serializers.Serializer):
    """顧客用生徒シリアライザー"""
    id = serializers.UUIDField()
    studentNo = serializers.CharField(source='student_no')
    fullName = serializers.CharField(source='full_name')
    grade = serializers.CharField(source='grade.grade_name', allow_null=True)


class MyContractSchoolSerializer(serializers.Serializer):
    """顧客用校舎シリアライザー"""
    id = serializers.UUIDField()
    schoolCode = serializers.CharField(source='school_code')
    schoolName = serializers.CharField(source='school_name')


class MyContractBrandSerializer(serializers.Serializer):
    """顧客用ブランドシリアライザー"""
    id = serializers.UUIDField()
    brandCode = serializers.CharField(source='brand_code')
    brandName = serializers.CharField(source='brand_name')


class MyContractCourseSerializer(serializers.Serializer):
    """顧客用コースシリアライザー"""
    id = serializers.UUIDField()
    courseCode = serializers.CharField(source='course_code')
    courseName = serializers.CharField(source='course_name')


class MyContractSerializer(serializers.ModelSerializer):
    """顧客用契約シリアライザー（保護者向け）"""
    contractNo = serializers.CharField(source='contract_no')
    student = MyContractStudentSerializer(read_only=True)
    school = MyContractSchoolSerializer(read_only=True)
    brand = MyContractBrandSerializer(read_only=True)
    course = MyContractCourseSerializer(read_only=True, allow_null=True)
    contractDate = serializers.DateField(source='contract_date')
    startDate = serializers.DateField(source='start_date')
    endDate = serializers.DateField(source='end_date', allow_null=True)
    monthlyTotal = serializers.DecimalField(source='monthly_total', max_digits=10, decimal_places=0)
    dayOfWeek = serializers.IntegerField(source='day_of_week', allow_null=True)
    startTime = serializers.TimeField(source='start_time', allow_null=True)
    endTime = serializers.TimeField(source='end_time', allow_null=True)

    class Meta:
        model = Contract
        fields = [
            'id', 'contractNo', 'student', 'school', 'brand', 'course',
            'status', 'contractDate', 'startDate', 'endDate',
            'monthlyTotal', 'dayOfWeek', 'startTime', 'endTime'
        ]


class MyStudentItemStudentSerializer(serializers.Serializer):
    """顧客用生徒シリアライザー（StudentItem用）"""
    id = serializers.UUIDField()
    studentNo = serializers.CharField(source='student_no')
    fullName = serializers.SerializerMethodField()
    grade = serializers.CharField(source='grade.grade_name', allow_null=True)

    def get_fullName(self, obj):
        return f"{obj.last_name} {obj.first_name}"


class MyStudentItemSchoolSerializer(serializers.Serializer):
    """顧客用校舎シリアライザー（StudentItem用）"""
    id = serializers.UUIDField()
    schoolCode = serializers.CharField(source='school_code')
    schoolName = serializers.CharField(source='school_name')


class MyStudentItemBrandSerializer(serializers.Serializer):
    """顧客用ブランドシリアライザー（StudentItem用）"""
    id = serializers.UUIDField()
    brandCode = serializers.CharField(source='brand_code')
    brandName = serializers.CharField(source='brand_name')


class MyStudentItemCourseSerializer(serializers.Serializer):
    """顧客用コースシリアライザー（StudentItem用）"""
    id = serializers.UUIDField()
    courseCode = serializers.CharField(source='course_code')
    courseName = serializers.CharField(source='course_name')


class MyStudentItemTicketSerializer(serializers.Serializer):
    """顧客用チケットシリアライザー（StudentItem用）"""
    id = serializers.UUIDField()
    ticketCode = serializers.CharField(source='ticket_code')
    ticketName = serializers.CharField(source='ticket_name')
    ticketType = serializers.CharField(source='ticket_type', allow_null=True)
    ticketCategory = serializers.CharField(source='ticket_category', allow_null=True)
    durationMinutes = serializers.IntegerField(source='duration_minutes', allow_null=True)


class MyStudentItemSerializer(serializers.ModelSerializer):
    """顧客用受講コースシリアライザー（保護者向け、StudentItemベース）"""
    contractNo = serializers.SerializerMethodField()
    student = MyStudentItemStudentSerializer(read_only=True)
    school = MyStudentItemSchoolSerializer(read_only=True)
    brand = MyStudentItemBrandSerializer(read_only=True)
    course = MyStudentItemCourseSerializer(read_only=True, allow_null=True)
    ticket = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    contractDate = serializers.DateField(source='start_date', allow_null=True)
    startDate = serializers.DateField(source='start_date', allow_null=True)
    endDate = serializers.SerializerMethodField()
    monthlyTotal = serializers.DecimalField(source='final_price', max_digits=10, decimal_places=0, allow_null=True, default=0)
    dayOfWeek = serializers.SerializerMethodField()
    startTime = serializers.SerializerMethodField()
    endTime = serializers.SerializerMethodField()

    class Meta:
        model = StudentItem
        fields = [
            'id', 'contractNo', 'student', 'school', 'brand', 'course', 'ticket',
            'status', 'contractDate', 'startDate', 'endDate',
            'monthlyTotal', 'dayOfWeek', 'startTime', 'endTime'
        ]

    def get_contractNo(self, obj):
        return str(obj.id)[:8].upper()

    def get_ticket(self, obj):
        """StudentItemまたはコースに紐づくチケットを取得"""
        if hasattr(obj, 'ticket') and obj.ticket:
            return MyStudentItemTicketSerializer(obj.ticket).data

        if obj.course:
            from ..models import CourseTicket
            course_ticket = CourseTicket.objects.filter(
                course=obj.course,
                deleted_at__isnull=True
            ).select_related('ticket').first()
            if course_ticket and course_ticket.ticket:
                return MyStudentItemTicketSerializer(course_ticket.ticket).data
        return None

    def get_status(self, obj):
        return 'active'

    def get_endDate(self, obj):
        return None

    def get_dayOfWeek(self, obj):
        if obj.day_of_week is not None:
            return obj.day_of_week
        if obj.contract and obj.contract.day_of_week is not None:
            return obj.contract.day_of_week
        return None

    def get_startTime(self, obj):
        if obj.start_time:
            return obj.start_time.strftime('%H:%M:%S')
        if obj.contract and obj.contract.start_time:
            return obj.contract.start_time.strftime('%H:%M:%S')
        return None

    def get_endTime(self, obj):
        if obj.end_time:
            return obj.end_time.strftime('%H:%M:%S')
        if obj.contract and obj.contract.end_time:
            return obj.contract.end_time.strftime('%H:%M:%S')
        return None
