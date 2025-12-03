from django.http import HttpResponseForbidden
from functools import wraps

def role_required(*allowed_roles):
    #EJEMPLO DE USO EN OTRAS APPS Y SU VISTA
    """
    Decorador para restringir acceso a usuarios con roles específicos.
    Ejemplo:
        @role_required('COMPRAS', 'ADMIN')
        def mi_vista(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated:
                if request.user.rol in allowed_roles or request.user.is_superuser:
                    return view_func(request, *args, **kwargs)
                else:
                    return HttpResponseForbidden("🚫 No tienes permiso para acceder a esta sección.")
            return HttpResponseForbidden("⚠️ Debes iniciar sesión para acceder.")
        return _wrapped_view
    return decorator
