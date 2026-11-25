import base64
from datetime import datetime
from django.conf import settings
import requests
from .models import RentPayment, TenantProfile


def normalize_phone(phone: str) -> str:
    phone = phone.strip().replace("+", "")
    if phone.startswith("0"):
        return "254" + phone[1:]
    return phone


def get_daraja_token() -> str:
    url = f"{settings.MPESA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials"
    res = requests.get(
        url,
        auth=(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET),
        timeout=15,
    )
    res.raise_for_status()
    return res.json()["access_token"]


def initiate_paybill_stk_push(
    phone: str, amount: int, account_number: str, desc="Rent Payment"
):
    """Triggers an STK Push to a Paybill where AccountReference = Unit Number (e.g., A-101)."""
    token = get_daraja_token()
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    shortcode = settings.MPESA_PAYBILL_SHORTCODE
    raw_password = f"{shortcode}{settings.MPESA_PASSKEY}{timestamp}"
    password = base64.b64encode(raw_password.encode()).decode("utf-8")

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": normalize_phone(phone),
        "PartyB": shortcode,
        "PhoneNumber": normalize_phone(phone),
        "CallBackURL": settings.MPESA_CALLBACK_URL,
        "AccountReference": account_number.upper().strip(),
        "TransactionDesc": desc,
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    res = requests.post(
        f"{settings.MPESA_BASE_URL}/mpesa/stkpush/v1/processrequest",
        json=payload,
        headers=headers,
        timeout=20,
    )
    return res.json()


def record_mpesa_reconciliation(
    account_ref: str, amount: int, receipt_no: str, checkout_id: str = None
):
    """Matches Paybill AccountReference (unit number) to a TenantProfile and logs/updates rent."""
    unit_code = account_ref.upper().strip()
    current_month = datetime.now().strftime("%b %Y")
    profile = TenantProfile.objects.filter(unit__iexact=unit_code).first()

    # Check if a rent record already exists for this unit & month
    payment = RentPayment.objects.filter(
        unit__iexact=unit_code, month=current_month
    ).first()
    if payment:
        payment.amount_paid += int(amount)
        payment.mpesa_receipt = receipt_no
        if checkout_id:
            payment.checkout_request_id = checkout_id
        payment.save()
    else:
        RentPayment.objects.create(
            tenant=profile,
            unit=profile.unit if profile else unit_code,
            tenant_name=(
                profile.user.get_full_name() or profile.user.username
                if profile
                else "Unassigned Tenant"
            ),
            month=current_month,
            rent_due=profile.monthly_rent if profile else int(amount),
            amount_paid=int(amount),
            mpesa_receipt=receipt_no,
            checkout_request_id=checkout_id,
        )
