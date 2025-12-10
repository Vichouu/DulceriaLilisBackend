from datetime import datetime
import json

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from lilis_erp.roles import require_roles

# Modelos correctos
from .models import MovimientoInventario, Producto, Proveedor, Bodega

# Serializers
from apps.api.serializers import (
    UsuarioSerializer,
    ProductoSerializer,
    ProveedorSerializer,
    MovimientoInventarioSerializer,
)

# Excel
try:
    from openpyxl import Workbook
    from openpyxl.utils import get_column_letter
except ImportError:
    Workbook = None


# ==============================================================
#                     BÚSQUEDA GLOBAL
# ==============================================================
def _build_transaction_q(q: str) -> Q:
    q = (q or "").strip()
    if not q:
        return Q()

    expr = (
        Q(producto__sku__icontains=q) |
        Q(producto__nombre__icontains=q) |
        Q(tipo__icontains=q) |
        Q(bodega_origen__nombre__icontains=q) |
        Q(bodega_destino__nombre__icontains=q) |
        Q(proveedor__razon_social__icontains=q) |
        Q(proveedor__rut_nif__icontains=q) |
        Q(creado_por__username__icontains=q) |
        Q(lote__icontains=q)
    )

    # cantidad
    try:
        expr |= Q(cantidad=float(q.replace(",", ".")))
    except:
        pass

    # id
    try:
        expr |= Q(id=int(q))
    except:
        pass

    return expr


# ==============================================================
#                   LISTADO DE TRANSACCIONES
# ==============================================================
@login_required
@require_roles("ADMIN", "PRODUCCION", "INVENTARIO", "VENTAS", "COMPRAS")
def gestion_transacciones(request):
    query = request.GET.get("q", "")
    sort_by = request.GET.get("sort", "sku")
    ver = request.GET.get("ver", "todos")
    export = request.GET.get("export", "")

    valid_sort_fields = [
        "id", "-id", "fecha", "-fecha",
        "producto__nombre", "-producto__nombre",
        "tipo", "-tipo"
    ]
    if sort_by not in valid_sort_fields:
        sort_by = "-id"
    if sort_by == "id":
        sort_by = "-id"

    qs = MovimientoInventario.objects.select_related(
        "producto", "proveedor",
        "bodega_origen", "bodega_destino",
        "creado_por"
    )

    filtro_tipos = {
        "ingreso": "INGRESO",
        "salida": "SALIDA",
        "ajuste": "AJUSTE",
        "devolucion": "DEVOLUCION",
        "transferencia": "TRANSFERENCIA",
    }
    if ver in filtro_tipos:
        qs = qs.filter(tipo=filtro_tipos[ver])

    if query:
        qs = qs.filter(_build_transaction_q(query))

    qs = qs.order_by(sort_by)

    # -------------------- EXPORTAR EXCEL --------------------
    if export == "xlsx":
        if Workbook is None:
            return HttpResponse("Falta instalar openpyxl", status=500)

        wb = Workbook()
        ws = wb.active
        ws.title = "Movimientos"

        headers = [
            "ID", "Fecha", "Tipo", "Producto", "SKU", "Cantidad",
            "Bodega Origen", "Bodega Destino", "Proveedor",
            "Lote", "Serie", "Vencimiento", "Usuario", "Observación"
        ]
        ws.append(headers)

        for m in qs:
            ws.append([
                m.id,
                m.fecha.strftime("%Y-%m-%d %H:%M") if m.fecha else "",
                m.tipo,
                m.producto.nombre,
                m.producto.sku,
                m.cantidad,
                m.bodega_origen.nombre if m.bodega_origen else "-",
                m.bodega_destino.nombre if m.bodega_destino else "-",
                m.proveedor.razon_social if m.proveedor else "-",
                m.lote or "-",
                m.serie or "-",
                m.fecha_vencimiento.strftime("%Y-%m-%d") if m.fecha_vencimiento else "-",
                m.creado_por.username if m.creado_por else "Sistema",
                m.observacion or ""
            ])

        # ajuste columnas
        for col in ws.columns:
            max_len = max((len(str(cell.value)) for cell in col if cell.value), default=0)
            ws.column_dimensions[get_column_letter(col[0].column)].width = min(max_len + 2, 50)

        filename = f"movimientos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        wb.save(response)
        return response

    # -------------------- FIX PAGINADOR --------------------
    paginator = Paginator(qs, 10)
    page_number = request.GET.get("page")

    if not page_number:
        page_obj = paginator.page(1)
    else:
        try:
            page_obj = paginator.page(page_number)
        except:
            page_obj = paginator.page(1)

    return render(request, "gestion_transacciones.html", {
        "movimientos": page_obj.object_list,
        "page_obj": page_obj,
        "query": query,
        "sort_by": sort_by,
        "ver": ver,
    })


# ==============================================================
#                     CREAR TRANSACCIÓN
# ==============================================================
@login_required
@require_roles("ADMIN", "PRODUCCION", "INVENTARIO")
@require_POST
def crear_transaccion(request):

    try:
        data = json.loads(request.body.decode("utf-8"))
    except:
        return JsonResponse({"ok": False, "error": "Payload inválido"}, status=400)

    errors = {}
    tipo = (data.get("tipo") or "").upper()
    cantidad_raw = data.get("cantidad")
    producto_text = (data.get("producto_text") or "").strip()
    proveedor_text = (data.get("proveedor_text") or "").strip()

    # Normalización
    map_tipos = {
        "INGRESO": "INGRESO",
        "SALIDA": "SALIDA",
        "AJUSTE": "AJUSTE",
        "DEVOLUCION": "DEVOLUCION",
        "DEVOLUCIÓN": "DEVOLUCION",
        "TRANSFERENCIA": "TRANSFERENCIA",
    }
    if tipo not in map_tipos:
        return JsonResponse({"ok": False, "error": "Tipo inválido"}, status=400)

    tipo = map_tipos[tipo]

    # Validaciones
    try:
        cantidad = float(cantidad_raw)
        if cantidad <= 0:
            raise ValueError
    except:
        errors["cantidad"] = "Cantidad inválida."

    if not producto_text:
        errors["producto_text"] = "Producto requerido."

    if tipo == "INGRESO" and not proveedor_text:
        errors["proveedor_text"] = "Proveedor requerido."

    if errors:
        return JsonResponse({"ok": False, "errors": errors}, status=400)

    # Producto
    producto = (
        Producto.objects.filter(sku=producto_text).first() or
        Producto.objects.filter(nombre__iexact=producto_text).first()
    )
    if not producto:
        return JsonResponse({"ok": False, "errors": {"producto_text": "Producto no encontrado"}}, status=400)

    # Proveedor
    proveedor = None
    if proveedor_text:
        proveedor = (
            Proveedor.objects.filter(rut_nif=proveedor_text).first() or
            Proveedor.objects.filter(razon_social__iexact=proveedor_text).first()
        )

    # Bodegas
    bodega_origen = None
    bodega_destino = None

    if data.get("bodega_origen"):
        bodega_origen = Bodega.objects.filter(id=data["bodega_origen"]).first()

    if data.get("bodega_destino"):
        bodega_destino = Bodega.objects.filter(id=data["bodega_destino"]).first()

    # Defaults
    if tipo in ("SALIDA", "AJUSTE", "TRANSFERENCIA") and not bodega_origen:
        bodega_origen = Bodega.objects.first()

    if tipo in ("INGRESO", "DEVOLUCION", "TRANSFERENCIA") and not bodega_destino:
        bodega_destino = Bodega.objects.first()

    # Crear movimiento
    try:
        with transaction.atomic():

            doc_ref = (data.get("doc_ref") or "").strip()
            motivo = (data.get("motivo") or "").strip()
            observ = (data.get("observaciones") or "").strip()

            extras = []
            if doc_ref:
                extras.append(f"Doc ref: {doc_ref}")
            if motivo:
                extras.append(f"Motivo: {motivo}")

            if extras:
                observ = (observ + " | " if observ else "") + " ".join(extras)

            mov = MovimientoInventario.objects.create(
                tipo=tipo,
                producto=producto,
                proveedor=proveedor,
                cantidad=cantidad,
                lote=data.get("lote") or "",
                serie=data.get("serie") or "",
                fecha_vencimiento=data.get("vencimiento") or None,
                observacion=observ,
                creado_por=request.user,
                bodega_origen=bodega_origen,
                bodega_destino=bodega_destino,
            )

            mov.aplicar_a_stock()

        return JsonResponse({"ok": True, "id": mov.id})

    except Exception as e:
        return JsonResponse({"ok": False, "errors": {"__all__": str(e)}}, status=500)


# ==============================================================
#                     EDITAR TRANSACCIÓN
# ==============================================================
@login_required
@require_roles("ADMIN", "PRODUCCION", "INVENTARIO")
def editar_transaccion(request, mov_id):
    try:
        mov = MovimientoInventario.objects.get(id=mov_id)
    except MovimientoInventario.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Movimiento no encontrado"}, status=404)

    if request.method == "GET":
        return JsonResponse({
            "ok": True,
            "movimiento": {
                "id": mov.id,
                "fecha": mov.fecha.isoformat(),
                "tipo": mov.tipo,
                "producto": mov.producto.id,
                "proveedor": mov.proveedor.id if mov.proveedor else None,
                "cantidad": mov.cantidad,
            }
        })

    return JsonResponse({"ok": False, "error": "Editar transacciones no permitido"}, status=400)


# ==============================================================
#                     ELIMINAR TRANSACCIÓN
# ==============================================================
@login_required
@require_roles("ADMIN", "PRODUCCION", "INVENTARIO")
@require_POST
def eliminar_transaccion(request, mov_id):
    return JsonResponse({"ok": False, "error": "No se pueden eliminar transacciones"}, status=400)
