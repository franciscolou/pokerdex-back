from django.conf import settings
from django.contrib import admin
from django.shortcuts import render
from django.urls import path, include, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.views.decorators.csrf import csrf_exempt
schema_view = get_schema_view(
    openapi.Info(
        title="Pokerdex API",
        default_version="v1",
        description="API do backend (grupos, jogos, participações, auth, etc.)",
        terms_of_service="https://www.google.com/policies/terms/",  # opcional
        contact=openapi.Contact(email="teampokerdex@gmail.com"),    # opcional
        license=openapi.License(name="MIT License"),                # opcional
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

def redirect_root(request):
    return render(request, "index.html")


urlpatterns = [
    path("", redirect_root),
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    re_path(
        r"^docs/swagger(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    path(
        "docs/swagger/",
        name="schema-swagger-ui",
    ),
    path(
        "docs/redoc/",
        name="schema-redoc",
    ),
]

