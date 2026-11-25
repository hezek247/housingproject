from rest_framework import serializers
from .models import (
    CollectiveComplaint,
    MonthlyFeedback,
    PersonalComplaint,
    RentPayment,
    TenantProfile,
)


class TenantProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    full_name = serializers.CharField(
        source="user.get_full_name", read_only=True
    )

    class Meta:
        model = TenantProfile
        fields = [
            "id",
            "username",
            "full_name",
            "unit",
            "phone_number",
            "monthly_rent",
        ]


class RentPaymentSerializer(serializers.ModelSerializer):
    balance = serializers.IntegerField(read_only=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = RentPayment
        fields = [
            "id",
            "unit",
            "month",
            "rent_due",
            "amount_paid",
            "balance",
            "status",
            "mpesa_receipt",
            "payment_date",
        ]


class PersonalComplaintSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonalComplaint
        fields = [
            "id",
            "subject",
            "description",
            "status",
            "manager_reply",
            "created_at",
        ]
        read_only_fields = ["status", "manager_reply", "created_at"]


class CollectiveComplaintSerializer(serializers.ModelSerializer):
    class Meta:
        model = CollectiveComplaint
        fields = [
            "id",
            "issue_title",
            "category",
            "affected_units",
            "status",
            "created_at",
        ]
        read_only_fields = ["affected_units", "status", "created_at"]


class MonthlyFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthlyFeedback
        fields = [
            "id",
            "month",
            "rating",
            "cleanliness_rating",
            "security_rating",
            "comments",
            "submitted_at",
        ]
