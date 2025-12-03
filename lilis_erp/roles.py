# lilis_erp/roles.py
from functools import wraps
from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponseForbidden

def require_roles(*allowed_roles):
    """
    Decorador para restringir vistas según el atributo user.rol.
    - Si no está autenticado: lo manda a 'login' con next=...
    - Si está autenticado pero su rol no está permitido: responde 403.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                login_url = reverse("login")
                return redirect(f"{login_url}?next={request.get_full_path()}")

            user_role = getattr(request.user, "rol", None)
            if user_role in allowed_roles or "ANY" in allowed_roles:
                return view_func(request, *args, **kwargs)

            # 403 (usará tu handler403)
            return HttpResponseForbidden()
        return _wrapped
    return decorator
