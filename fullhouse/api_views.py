from django.db.models import F
from rest_framework import permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import (
    CollectiveComplaint,
    MonthlyFeedback,
    PersonalComplaint,
    RentPayment,
)
from .mpesa import initiate_paybill_stk_push, record_mpesa_reconciliation
from .serializers import (
    CollectiveComplaintSerializer,
    MonthlyFeedbackSerializer,
    PersonalComplaintSerializer,
    RentPaymentSerializer,
    TenantProfileSerializer,
)


class CustomMobileLogin(ObtainAuthToken):
    """Returns Auth Token + Tenant Room Profile for mobile app login."""

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        profile_data = (
            TenantProfileSerializer(user.tenant_profile).data
            if hasattr(user, "tenant_profile")
            else None
        )
        return Response({
            "token": token.key,
            "is_staff": user.is_staff,
            "profile": profile_data,
        })


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def trigger_stk_push_api(request):
    """Mobile or web endpoint to initiate Paybill STK push for the logged-in tenant's unit."""
    profile = getattr(request.user, "tenant_profile", None)
    unit = request.data.get("unit") or (profile.unit if profile else None)
    phone = request.data.get("phone") or (
        profile.phone_number if profile else None
    )
    amount = request.data.get("amount") or (
        profile.monthly_rent if profile else 10
    )

    if not unit or not phone:
        return Response(
            {"error": "Unit account number and phone number are required."},
            status=400,
        )

    daraja_res = initiate_paybill_stk_push(
        phone=phone, amount=int(amount), account_number=unit
    )
    return Response(daraja_res)


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def mpesa_stk_callback(request):
    """Safaricom Daraja STK Push Callback."""
    stk_callback = request.data.get("Body", {}).get("stkCallback", {})
    if stk_callback.get("ResultCode") == 0:
        items = stk_callback.get("CallbackMetadata", {}).get("Item", [])
        meta = {item["Name"]: item.get("Value") for item in items}
        amount = meta.get("Amount", 0)
        receipt = meta.get("MpesaReceiptNumber", "UNKNOWN")
        # Note: Store CheckoutRequestID -> AccountReference mapping in production
        account_ref = request.GET.get("account", "A-101")
        record_mpesa_reconciliation(
            account_ref, amount, receipt, stk_callback.get("CheckoutRequestID")
        )
    return Response({"ResultCode": 0, "ResultDesc": "Accepted"})


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def mpesa_c2b_confirmation(request):
    """Safaricom Daraja C2B Paybill Confirmation URL (when tenant pays manually via M-Pesa menu)."""
    data = request.data
    receipt = data.get("TransID")
    amount = float(data.get("TransAmount", 0))
    account_ref = data.get(
        "BillRefNumber", ""
    )  # Customer enters their Unit Number here!
    if receipt and account_ref:
        record_mpesa_reconciliation(account_ref, int(amount), receipt)
    return Response({"ResultCode": 0, "ResultDesc": "Confirmation Received"})


class TenantRentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RentPaymentSerializer

    def get_queryset(self):
        if self.request.user.is_staff:
            return RentPayment.objects.all()
        return RentPayment.objects.filter(
            unit=self.request.user.tenant_profile.unit
        )


class PersonalComplaintViewSet(viewsets.ModelViewSet):
    serializer_class = PersonalComplaintSerializer

    def get_queryset(self):
        if self.request.user.is_staff:
            return PersonalComplaint.objects.all()
        return PersonalComplaint.objects.filter(
            tenant=self.request.user.tenant_profile
        )

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant_profile)


class CollectiveComplaintViewSet(viewsets.ModelViewSet):
    queryset = CollectiveComplaint.objects.all().order_by("-affected_units")
    serializer_class = CollectiveComplaintSerializer


class MonthlyFeedbackViewSet(viewsets.ModelViewSet):
    serializer_class = MonthlyFeedbackSerializer

    def get_queryset(self):
        if self.request.user.is_staff:
            return MonthlyFeedback.objects.all()
        return MonthlyFeedback.objects.filter(
            tenant=self.request.user.tenant_profile
        )

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant_profile)
