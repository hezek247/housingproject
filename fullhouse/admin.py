from django.contrib import admin
from .models import CollectiveComplaint, ComplianceReport, RentPayment


@admin.register(RentPayment)
class RentPaymentAdmin(admin.ModelAdmin):
    list_display = (
        "unit",
        "tenant_name",
        "month",
        "rent_due",
        "amount_paid",
        "mpesa_receipt",
        "payment_date",
    )
    list_filter = ("month",)
    search_fields = ("unit", "tenant_name", "mpesa_receipt")


@admin.register(ComplianceReport)
class ComplianceReportAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "due_date", "status")
    list_filter = ("status", "category")


@admin.register(CollectiveComplaint)
class CollectiveComplaintAdmin(admin.ModelAdmin):
    list_display = (
        "issue_title",
        "category",
        "affected_units",
        "status",
        "created_at",
    )
    list_filter = ("status", "category")
