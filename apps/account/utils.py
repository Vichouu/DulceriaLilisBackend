import logging

audit_logger = logging.getLogger('audit')

def registrar_auditoria(usuario, accion, objeto):
    """
    Registra operaciones CRUD sin exponer datos sensibles.
    """
    username = usuario.username if usuario else "desconocido"

    mensaje = (
        f"Usuario={username} | "
        f"Accion={accion} | "
        f"Objeto={objeto}"
    )

    audit_logger.info(mensaje)
