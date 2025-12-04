# apps/account/middleware.py

from django.shortcuts import redirect
from django.urls import reverse

# Rutas que NO deben ser bloqueadas
EXCLUDED_PATHS = [
    "/swagger/",
    "/redoc/",
    "/api/",
    "/api/token/",
    "/api/token/refresh/",
    "/static/",
    "/admin/",
]

class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # Evitar interferir con la API, Swagger y estáticos
        for path in EXCLUDED_PATHS:
            if request.path.startswith(path):
                return self.get_response(request)

        # Lógica principal
        user = request.user
        if user.is_authenticated and getattr(user, "must_change_password", False):
            allowed = {
                reverse("password_change"),
                reverse("password_change_done"),
                reverse("logout"),
            }
            if request.path not in allowed:
                return redirect("password_change")

        return self.get_response(request)
