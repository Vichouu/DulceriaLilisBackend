from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from apps.account.views import get_redirect_for_role

@login_required(login_url='login')
def dashboard_page(request):
    user = request.user
    if not (user.is_superuser or getattr(user, "rol", "") == "ADMIN"):
        return redirect(get_redirect_for_role(user))
    return render(request, "dashboard.html")

def handler403(request, exception=None):
    return render(request, "403.html", status=403)
