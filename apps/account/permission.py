from functools import wraps
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required

def require_roles(*allowed_roles):
    """
    Restringe el acceso de la vista a los roles indicados.
    ADMIN siempre tiene acceso.
    Uso:
        @require_roles("COMPRAS", "INVENTARIO")
        def mi_vista(...):
            ...
    """
    def wrapper(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            rol = getattr(request.user, "rol", None)
            if rol == "ADMIN" or rol in allowed_roles:
                return view_func(request, *args, **kwargs)
            return HttpResponseForbidden("No tienes permisos para acceder a este módulo.")
        return _wrapped
    return wrapper
