# apps/users/utils_invite.py
import secrets
from django.conf import settings
from django.core.mail import send_mail

def invite_user_and_email(user, source='creation'):
    """
    Genera contraseña temporal + invite_code, marca must_change_password=True
    y envía correo al usuario. Devuelve la contraseña temporal generada.
    """
    # Generar credenciales temporales
    temp_password = secrets.token_urlsafe(10)[:14]  # ~14 caracteres
    code = secrets.token_hex(4).upper()             # 8 hex (A-F/0-9)

    # Setear en el usuario
    user.set_password(temp_password)
    user.invite_code = code
    user.must_change_password = True
    user.save(update_fields=["password", "invite_code", "must_change_password"])

    # Preparar correo
    nombre = (getattr(user, "get_full_name", lambda: "")() or "").strip() or user.username

    if source == 'reset':
        asunto = "Reinicio de Contraseña - Dulcería Lilis ERP"
        cuerpo = (
            f"Hola {nombre},\n\n"
            f"Se ha pedido reiniciar tu contraseña para el sistema ERP de Dulcería Lilis.\n\n"
            f"Tus nuevas credenciales temporales son:\n"
            f"  - Usuario: {user.username}\n"
            f"  - Contraseña temporal: {temp_password}\n"
            f"  - Código de verificación: {code}\n\n"
            "Se te pedirá cambiar tu contraseña y deberás ingresar el código de verificación para completar el proceso..\n\n"
            "Saludos,\nEl equipo de Dulcería Lilis"
        )
    else:  # 'creation'
        asunto = "¡Bienvenido/a a Dulcería Lilis ERP!"
        cuerpo = (
            f"Hola {nombre},\n\n"
            f"Se ha creado una cuenta para ti en el sistema ERP de Dulcería Lilis.\n\n"
            f"Tus credenciales de acceso son:\n"
            f"  - Usuario: {user.username}\n"
            f"  - Contraseña temporal: {temp_password}\n"
            f"  - Código de verificación: {code}\n\n"
            "En tu primer inicio de sesión, se te pedirá cambiar tu contraseña y deberás ingresar el código de verificación para asegurar tu cuenta.\n\n"
            "Saludos,\nEl equipo de Dulcería Lilis"
        )

    send_mail(
        asunto,
        cuerpo,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )

    return temp_password
