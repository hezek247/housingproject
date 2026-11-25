from datetime import datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import F, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .models import (
    CollectiveComplaint,
    ComplianceReport,
    MonthlyFeedback,
    PersonalComplaint,
    RentPayment,
)
from .mpesa import initiate_paybill_stk_push


def is_manager(user):
    return user.is_staff or user.is_superuser


@login_required
def role_router(request):
    """Redirects staff to Manager Dashboard and tenants to their Room Portal."""
    if is_manager(request.user):
        return redirect("dashboard")
    return redirect("tenant_portal")


@login_required
@user_passes_test(is_manager)
def dashboard(request):
    payments = RentPayment.objects.all().order_by("unit")
    compliance = ComplianceReport.objects.all().order_by("due_date")
    complaints = CollectiveComplaint.objects.all().order_by("-affected_units")
    personal_issues = PersonalComplaint.objects.all().order_by("-created_at")
    feedbacks = MonthlyFeedback.objects.all().order_by("-submitted_at")

    totals = payments.aggregate(
        expected=Sum("rent_due"), collected=Sum("amount_paid")
    )
    total_expected = totals["expected"] or 0
    total_collected = totals["collected"] or 0

    return render(
        request,
        "fullhouse/index.html",
        {
            "payments": payments,
            "compliance": compliance,
            "complaints": complaints,
            "personal_issues": personal_issues,
            "feedbacks": feedbacks,
            "total_expected": total_expected,
            "total_collected": total_collected,
            "total_arrears": total_expected - total_collected,
            "pending_compliance": compliance.exclude(status="Compliant").count(),
            "open_complaints": complaints.exclude(status="Resolved").count(),
        },
    )


@login_required
def tenant_portal(request):
    """Dedicated Room Portal for logged-in tenants."""
    profile = getattr(request.user, "tenant_profile", None)
    if not profile:
        return render(
            request,
            "fullhouse/tenant_portal.html",
            {"error": "No unit assigned to your account. Contact management."},
        )

    current_month = datetime.now().strftime("%b %Y")
    payments = RentPayment.objects.filter(unit=profile.unit).order_by(
        "-payment_date"
    )
    personal_complaints = PersonalComplaint.objects.filter(
        tenant=profile
    ).order_by("-created_at")
    collective_complaints = CollectiveComplaint.objects.exclude(
        status="Resolved"
    ).order_by("-affected_units")
    feedback_history = MonthlyFeedback.objects.filter(tenant=profile).order_by(
        "-submitted_at"
    )

    return render(
        request,
        "fullhouse/tenant_portal.html",
        {
            "profile": profile,
            "current_month": current_month,
            "payments": payments,
            "personal_complaints": personal_complaints,
            "collective_complaints": collective_complaints,
            "feedback_history": feedback_history,
        },
    )


@login_required
@require_POST
def tenant_pay_rent(request):
    profile = request.user.tenant_profile
    amount = int(request.POST.get("amount", profile.monthly_rent))
    phone = request.POST.get("phone", profile.phone_number)
    res = initiate_paybill_stk_push(
        phone=phone, amount=amount, account_number=profile.unit
    )
    if res.get("ResponseCode") == "0":
        messages.success(
            request,
            f"M-Pesa STK Push sent to {phone} for Account {profile.unit}. Enter your PIN.",
        )
    else:
        messages.error(
            request,
            f"M-Pesa error: {res.get('errorMessage', 'Could not send prompt.')}",
        )
    return redirect("tenant_portal")


@login_required
@require_POST
def submit_personal_complaint(request):
    PersonalComplaint.objects.create(
        tenant=request.user.tenant_profile,
        subject=request.POST["subject"],
        description=request.POST["description"],
    )
    messages.success(request, "Room maintenance request submitted.")
    return redirect("tenant_portal")


@login_required
@require_POST
def submit_monthly_feedback(request):
    profile = request.user.tenant_profile
    month = request.POST["month"]
    MonthlyFeedback.objects.update_or_create(
        tenant=profile,
        month=month,
        defaults={
            "rating": int(request.POST["rating"]),
            "cleanliness_rating": int(request.POST["cleanliness_rating"]),
            "security_rating": int(request.POST["security_rating"]),
            "comments": request.POST.get("comments", ""),
        },
    )
    messages.success(request, f"Thank you! Rating saved for {month}.")
    return redirect("tenant_portal")


@login_required
@require_POST
def upvote_complaint(request, complaint_id):
    complaint = get_object_or_404(CollectiveComplaint, id=complaint_id)
    if request.user not in complaint.upvoted_by.all():
        complaint.upvoted_by.add(request.user)
        CollectiveComplaint.objects.filter(id=complaint_id).update(
            affected_units=F("affected_units") + 1
        )
    return redirect(
        "tenant_portal" if not is_manager(request.user) else "dashboard"
    )

@require_POST
def add_payment(request):
    RentPayment.objects.create(
        unit=request.POST["unit"],
        tenant_name=request.POST["tenant_name"],
        month=request.POST["month"],
        rent_due=int(request.POST["rent_due"]),
        amount_paid=int(request.POST["amount_paid"]),
        mpesa_receipt=request.POST.get("mpesa_receipt") or "-",
    )
    return redirect("dashboard")

@require_POST
def add_compliance(request):
    ComplianceReport.objects.create(
        title=request.POST["title"],
        category=request.POST["category"],
        due_date=request.POST["due_date"],
        status=request.POST["status"],
        notes=request.POST.get("notes", ""),
    )
    return redirect("dashboard")

@require_POST
def update_compliance_status(request, report_id):
    report = get_object_or_404(ComplianceReport, id=report_id)
    report.status = request.POST["status"]
    report.save()
    return redirect("dashboard")

@require_POST
def add_complaint(request):
    CollectiveComplaint.objects.create(
        issue_title=request.POST["issue_title"],
        category=request.POST["category"],
    )
    return redirect("dashboard")

@require_POST
def resolve_complaint(request, complaint_id):
    complaint = get_object_or_404(CollectiveComplaint, id=complaint_id)
    complaint.status = "Resolved"
    complaint.save()
    return redirect("dashboard")