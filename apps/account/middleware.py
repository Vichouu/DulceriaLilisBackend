# apps/account/middleware.py
from django.shortcuts import redirect
from django.urls import reverse

class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            if getattr(request.user, "must_change_password", False):
                allowed = {
                    reverse("password_change"),
                    reverse("password_change_done"),
                    reverse("logout"),
                }
                if request.path not in allowed:
                    return redirect("password_change")
        return self.get_response(request)
