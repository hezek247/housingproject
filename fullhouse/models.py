from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class TenantProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="tenant_profile"
    )
    unit = models.CharField(
        max_length=20,
        unique=True,
        help_text="Used as Paybill Account Number (e.g. A-101)",
    )
    phone_number = models.CharField(
        max_length=15, help_text="Format: 2547XXXXXXXX"
    )
    monthly_rent = models.PositiveIntegerField(default=25000)

    def __str__(self):
        return f"{self.unit} - {self.user.get_full_name() or self.user.username}"


class RentPayment(models.Model):
    tenant = models.ForeignKey(
        TenantProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )
    unit = models.CharField(max_length=20)
    tenant_name = models.CharField(max_length=100)
    month = models.CharField(max_length=20)
    rent_due = models.PositiveIntegerField()
    amount_paid = models.PositiveIntegerField(default=0)
    mpesa_receipt = models.CharField(max_length=30, blank=True, default="-")
    checkout_request_id = models.CharField(max_length=100, blank=True, null=True)
    payment_date = models.DateField(auto_now_add=True)

    @property
    def balance(self):
        return max(self.rent_due - self.amount_paid, 0)

    @property
    def status(self):
        if self.amount_paid >= self.rent_due:
            return "Paid"
        elif self.amount_paid > 0:
            return "Partial"
        return "Overdue"

    def __str__(self):
        return f"{self.unit} - {self.month} ({self.mpesa_receipt})"


class ComplianceReport(models.Model):
    STATUS_CHOICES = [
        ("Compliant", "Compliant"),
        ("Pending", "Pending"),
        ("Action Required", "Action Required"),
    ]
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    due_date = models.DateField()
    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default="Pending"
    )
    notes = models.TextField(blank=True)


class CollectiveComplaint(models.Model):
    STATUS_CHOICES = [
        ("Open", "Open"),
        ("In Progress", "In Progress"),
        ("Resolved", "Resolved"),
    ]
    issue_title = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    affected_units = models.PositiveIntegerField(default=1)
    upvoted_by = models.ManyToManyField(
        User, blank=True, related_name="upvoted_complaints"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="Open"
    )
    created_at = models.DateField(auto_now_add=True)


class PersonalComplaint(models.Model):
    STATUS_CHOICES = [
        ("Open", "Open"),
        ("Technician Assigned", "Technician Assigned"),
        ("Resolved", "Resolved"),
    ]
    tenant = models.ForeignKey(
        TenantProfile,
        on_delete=models.CASCADE,
        related_name="personal_complaints",
    )
    subject = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default="Open"
    )
    manager_reply = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class MonthlyFeedback(models.Model):
    tenant = models.ForeignKey(
        TenantProfile, on_delete=models.CASCADE, related_name="feedbacks"
    )
    month = models.CharField(max_length=20)
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    cleanliness_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)], default=5
    )
    security_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)], default=5
    )
    comments = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("tenant", "month")  # One rating per unit per month
