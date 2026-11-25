from django.contrib.auth import views as auth_views
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from . import api_views, views

router = DefaultRouter()
router.register(r"rent", api_views.TenantRentViewSet, basename="api-rent")
router.register(
    r"personal-complaints",
    api_views.PersonalComplaintViewSet,
    basename="api-personal-complaints",
)
router.register(
    r"collective-complaints",
    api_views.CollectiveComplaintViewSet,
    basename="api-collective-complaints",
)
router.register(
    r"feedback", api_views.MonthlyFeedbackViewSet, basename="api-feedback"
)

urlpatterns = [
    # Authentication
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", views.role_router, name="home"),
    # Manager Dashboard & Tenant Room Portal
    path("manager/", views.dashboard, name="dashboard"),
    path("portal/", views.tenant_portal, name="tenant_portal"),
    path("portal/pay/", views.tenant_pay_rent, name="tenant_pay_rent"),
    path("add_payment/",views.add_payment,name="add_payment"),
    path("add_compliance/",views.add_compliance,name="add_compliance"),
    path("add_complaint/",views.add_complaint,name="add_complaint"),
    path(
        "portal/complaint/",
        views.submit_personal_complaint,
        name="submit_personal_complaint",
    ),
    path(
        "portal/feedback/",
        views.submit_monthly_feedback,
        name="submit_monthly_feedback",
    ),
    path(
        "complaints/<int:complaint_id>/upvote/",
        views.upvote_complaint,
        name="upvote_complaint",
    ),
    # Mobile App REST API & Daraja Webhooks
    path(
        "api/login/",
        api_views.CustomMobileLogin.as_view(),
        name="api_mobile_login",
    ),
    path(
        "api/mpesa/stk-push/",
        api_views.trigger_stk_push_api,
        name="api_stk_push",
    ),
    path(
        "api/mpesa/callback/",
        api_views.mpesa_stk_callback,
        name="api_mpesa_callback",
    ),
    path(
        "api/mpesa/c2b-confirm/",
        api_views.mpesa_c2b_confirmation,
        name="api_mpesa_c2b",
    ),
    path("api/", include(router.urls)),
]
