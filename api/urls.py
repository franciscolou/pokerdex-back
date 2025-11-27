from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .auth_views import SignupView, LoginView, LogoutView, MeView

from .views import (
    GroupViewSet,
    GroupRequestViewSet,
    GameViewSet,
    GameParticipationViewSet,
    request_password_reset,
    confirm_password_reset
)

router = DefaultRouter()

router.register(r"groups", GroupViewSet, basename="groups")
router.register(r"group-requests", GroupRequestViewSet, basename="group-requests")

router.register(r"games", GameViewSet, basename="games")
router.register(r"participations", GameParticipationViewSet, basename="participations")

urlpatterns = [
    path("", include(router.urls)),
    path("auth/signup/", SignupView.as_view()),
    path("auth/login/", LoginView.as_view()),
    path("auth/logout/", LogoutView.as_view()),
    path("auth/me/", MeView.as_view()),
    path("password_reset/", request_password_reset),
    path("password_reset/confirm/", confirm_password_reset),
]
