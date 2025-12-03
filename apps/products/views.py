from datetime import datetime
import json
import traceback
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction, models, IntegrityError
from django.db.models import Q, CharField, DecimalField, Value
from django.db.models.functions import Cast, Coalesce
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.forms.models import model_to_dict
from django.core.exceptions import FieldError, ValidationError
from django.apps import apps  # <- para cargar Bodega de forma segura
from django.db.models.deletion import ProtectedError, RestrictedError  # 👈 NUEVO

from lilis_erp.roles import require_roles

# Excel opcional
try:
    from openpyxl import Workbook
except ImportError:
    Workbook = None

# Modelos locales
from .models import Producto as Product
from .models import Categoria
from .forms import ProductoForm


# -------------------------- Constantes / helpers --------------------------

ALLOWED_SORT_FIELDS = {
    "id", "-id",
    "sku", "-sku",
    "nombre", "-nombre",
    "categoria", "-categoria",
    "stock", "-stock",
}

# Campo decimal único para todas las anotaciones de stock
DEC = DecimalField(max_digits=14, decimal_places=3)


def _display_categoria(obj):
    cat = getattr(obj, "categoria", None)
    return getattr(cat, "nombre", "") if cat else ""


def _qs_to_dicts(qs):
    out = []
    for p in qs:
        st = getattr(p, "stock_total", Decimal("0"))
        out.append({
            "id": p.id,
            "sku": p.sku or "",
            "nombre": p.nombre or "",
            "categoria": _display_categoria(p),
            "stock": int(st or 0),
        })
    return out


def _base_queryset():
    """
    - id_text para buscar por ID (icontains)
    - stock_total por JOIN + SUM sobre related_name='stocks'
    - Tipado como Decimal para evitar 'mixed types'
    """
    return (
        Product.objects.select_related("categoria")
        .annotate(
            id_text=Cast("id", output_field=CharField()),
            stock_total=Coalesce(
                models.Sum("stocks__cantidad", output_field=DEC),
                Value(Decimal("0"), output_field=DEC),
                output_field=DEC,
            ),
        )
    )


def _build_search_q(q: str):
    q = (q or "").strip()
    if not q:
        return Q()
    expr = (
        Q(sku__icontains=q) |
        Q(nombre__icontains=q) |
        Q(categoria__nombre__icontains=q) |
        Q(id_text__icontains=q)
    )
    if q.isdigit():
        expr |= Q(id=int(q))
    return expr


def _apply_filters(qs, request):
    """
    Filtros ligeros SIN romper nada de lo tuyo.
    - categoría: ?categoria=<id>  (o ?cat=<id>)
    - estado/activo: ?estado=activos | inactivos   (si el modelo tiene 'activo')
    """
    cat = (request.GET.get("categoria") or request.GET.get("cat") or "").strip()
    if cat.isdigit():
        qs = qs.filter(categoria_id=int(cat))

    estado = (request.GET.get("estado") or "").strip().lower()
    if estado in {"activos", "inactivos"} and hasattr(Product, "activo"):
        qs = qs.filter(activo=(estado == "activos"))

    return qs


def _apply_sort(qs, sort_by: str):
    sort_by = (sort_by or "").strip()
    if sort_by not in ALLOWED_SORT_FIELDS:
        sort_by = "sku"

    reverse = sort_by.startswith("-")
    key = sort_by.lstrip("-")

    sort_field = {
        "categoria": "categoria__nombre",
        "stock": "stock_total",
    }.get(key, key)

    try:
        ordered = qs.order_by(f"-{sort_field}" if reverse else sort_field, "id")
        list(ordered[:1])  # evalúa 1 fila para cazar errores
        return ordered
    except FieldError as e:
        print("[productos] FieldError en order_by:", e)
        traceback.print_exc()
        try:
            ordered = qs.order_by("-sku" if reverse else "sku", "id")
            list(ordered[:1])
            return ordered
        except Exception as e2:
            print("[productos] Fallback a sku también falló, usando id:", e2)
            traceback.print_exc()
            return qs.order_by("-id" if reverse else "id")


def _load_bodegas_safe():
    """Devuelve queryset de Bodega si existe; [] si no existe el modelo."""
    try:
        Bodega = apps.get_model("transactional", "Bodega")
        return Bodega.objects.all() if Bodega is not None else []
    except Exception:
        return []


def _json_or_empty(request):
    """Devuelve el cuerpo JSON o {} sin romper si llega vacío o HTML."""
    try:
        raw = request.body.decode("utf-8") if request.body else ""
        return json.loads(raw) if raw else {}
    except Exception:
        return {}


# Helper: convierte a Decimal o devuelve None si viene vacío / inválido
def _to_decimal_or_none(val):
    if val in (None, "", "None"):
        return None
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError):
        return None


# ---------------- LISTADO ----------------
@login_required
@require_roles("ADMIN", "INVENTARIO", "PRODUCCION", "VENTAS")
def product_list_view(request):
    """
    GET /productos/?q=...&sort=...&page=...&categoria=...&estado=...
    Renderiza productos.html (compatible con AJAX).
    """
    query = (request.GET.get("q") or "").strip()
    sort_by = (request.GET.get("sort") or "id").strip()
    export = (request.GET.get("export") or "").strip()

    try:
        qs = _base_queryset()
        if query:
            qs = qs.filter(_build_search_q(query))
        qs = _apply_filters(qs, request)  # <- aplica filtros si vienen
        qs = _apply_sort(qs, sort_by)
    except Exception as e:
        print("[productos] ERROR construyendo queryset:", e)
        traceback.print_exc()
        qs = Product.objects.none()

    # Exportación a XLSX
    if export == "xlsx":
        if Workbook is None:
            return HttpResponse("Falta dependencia: pip install openpyxl", status=500)
        wb = Workbook()
        ws = wb.active
        ws.title = "Productos"
        ws.append(["ID", "SKU", "Nombre", "Categoría", "Stock"])
        for p in _qs_to_dicts(qs):
            ws.append([p["id"], p["sku"], p["nombre"], p["categoria"], p["stock"]])
        resp = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        resp["Content-Disposition"] = f'attachment; filename="productos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        wb.save(resp)
        return resp

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    ctx = {
        "productos": _qs_to_dicts(page_obj.object_list),
        "page_obj": page_obj,
        "query": query,
        "sort_by": sort_by,
        "categorias": Categoria.objects.all(),
        "uom_choices": getattr(Product, "UOMS", []),
        "bodegas": _load_bodegas_safe(),
    }
    ctx["query"] = query
    ctx["sort_by"] = sort_by

    # 🔧 Si la solicitud viene por AJAX (live-search), devolvemos solo el fragmento HTML necesario
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render(request, "partials/_productos_table.html", ctx)

    return render(request, "productos.html", ctx)


# ---------------- BÚSQUEDA (autocompletar / ajax ligero) ----------------
@login_required
@require_roles("ADMIN", "INVENTARIO", "PRODUCCION", "VENTAS")
def search_products(request):
    q = (request.GET.get("q") or "").strip()
    try:
        qs = _base_queryset()
        if q:
            qs = qs.filter(_build_search_q(q))
        qs = _apply_sort(qs, "id")[:10]
        data = _qs_to_dicts(qs)
    except Exception as e:
        print("[productos.search] ERROR:", e)
        traceback.print_exc()
        data = []
    return JsonResponse({"results": data})


# ---------------- CRUD ----------------

@login_required
@require_roles("ADMIN", "INVENTARIO", "PRODUCCION", "VENTAS")
@transaction.atomic
def crear_producto(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Método no permitido."}, status=405)

    is_json = "application/json" in request.headers.get("Content-Type", "")
    data = _json_or_empty(request) if is_json else request.POST
    form = ProductoForm(data)

    if form.is_valid():
        try:
            producto = form.save(commit=False)

            # --- INICIO DE LA MODIFICACIÓN ---
            # Asignar precio_compra (del front) a costo_estandar (del modelo)
            precio_compra = data.get("precio_compra")
            producto.costo_estandar = _to_decimal_or_none(precio_compra)

            # Aseguramos que los valores vacíos se manejen correctamente
            if not producto.ean_upc:
                producto.ean_upc = ""  # Asignar un valor vacío en lugar de None
            if not producto.stock_minimo:
                producto.stock_minimo = 0  # Asignar 0 si está vacío
            if not producto.stock_maximo:
                producto.stock_maximo = 0  # Asignar 0 si está vacío
            # --- FIN DE LA MODIFICACIÓN ---

            producto.save()  # Guardamos el producto

            return JsonResponse({"ok": True, "id": producto.id})

        except Exception as e:
            return JsonResponse({"ok": False, "error": f"Error inesperado al guardar: {str(e)}"}, status=500)
    else:
        errores = []
        for field, field_errors in form.errors.items():
            errores.append(f"{field}: {', '.join(field_errors)}")
        error_str = " | ".join(errores)
        return JsonResponse({"ok": False, "error": f"Datos inválidos: {error_str}"}, status=400)

@login_required
@require_roles("ADMIN", "INVENTARIO", "PRODUCCION", "VENTAS")
@transaction.atomic
def editar_producto(request, prod_id: int):
    producto = get_object_or_404(Product, id=prod_id)

    # GET -> devuelve JSON para cargar modal/form por AJAX
    if request.method == "GET":
        data = model_to_dict(
            producto,
            fields=[
                "id", "sku", "nombre", "descripcion", "marca", "modelo",
                "ean_upc", "stock_minimo", "stock_maximo", "punto_reorden", "categoria",
                "url_imagen", "url_ficha_tecnica"
            ]
        )
        data["categoria_nombre"] = getattr(producto.categoria, "nombre", "")
        data["categorias"] = list(Categoria.objects.values("id", "nombre").order_by("nombre"))
        return JsonResponse({"ok": True, "data": data})

    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Método no permitido."}, status=405)

    # --- POST (actualización robusta) ---
    try:
        # Acepta JSON o form; evita excepciones si llega vacío/HTML
        is_json = (request.headers.get("Content-Type", "") or "").startswith("application/json")
        data = _json_or_empty(request) if is_json else request.POST

        # Campos básicos (los que envías desde el front)
        nombre = (data.get("nombre") or "").strip()
        marca = (data.get("marca") or "").strip()
        descripcion = (data.get("descripcion") or "").strip()
        categoria_raw = data.get("categoria", None)

        if not nombre:
            return JsonResponse({"ok": False, "error": "El nombre es obligatorio."}, status=400)

        # categoria: "", None -> None ; si viene id, validar que exista
        if categoria_raw in ("", None):
            producto.categoria = None
            categoria_changed = True
        else:
            try:
                categoria_id = int(categoria_raw)
                # valida que exista
                Categoria.objects.get(pk=categoria_id)
                producto.categoria_id = categoria_id
                categoria_changed = True
            except (ValueError, Categoria.DoesNotExist):
                return JsonResponse({"ok": False, "error": "La categoría seleccionada no existe."}, status=400)

        # Actualiza campos de texto que llegaron (sin forzar los que no envías)
        update_fields = []
        if "nombre" in data:
            producto.nombre = nombre
            update_fields.append("nombre")
        if "marca" in data:
            producto.marca = marca
            update_fields.append("marca")
        if "descripcion" in data:
            producto.descripcion = descripcion
            update_fields.append("descripcion")
        if "categoria" in data and categoria_changed:
            update_fields.append("categoria")

        # ean / código de barras
        if "codigo_barras" in data or "ean_upc" in data:
            ean = (data.get("codigo_barras") or data.get("ean_upc") or "").strip()
            producto.ean_upc = ean or None
            update_fields.append("ean_upc")

        # urls
        if "url_imagen" in data:
            img = (data.get("url_imagen") or "").strip() or None
            producto.url_imagen = img
            update_fields.append("url_imagen")
        if "url_ficha_tecnica" in data:
            ficha = (data.get("url_ficha_tecnica") or "").strip() or None
            producto.url_ficha_tecnica = ficha
            update_fields.append("url_ficha_tecnica")

        # numéricos: stock_minimo, stock_maximo, punto_reorden (seguro)
        for f in ("stock_minimo", "stock_maximo", "punto_reorden"):
            if f in data and hasattr(producto, f):
                val = data.get(f)
                try:
                    if val in ("", None):
                        # Para stock_minimo no forzamos None (tiene default y no admite null), 
                        # para los otros (nullable) sí permitimos limpiar a None
                        if f == "stock_minimo":
                            # si viene vacío, no tocar stock_minimo (mantener valor actual)
                            continue
                        else:
                            setattr(producto, f, None)
                            update_fields.append(f)
                    else:
                        # convertir a Decimal o None si inválido
                        converted = _to_decimal_or_none(val)
                        setattr(producto, f, converted)
                        update_fields.append(f)
                except Exception:
                    # no corta el flujo si viene sucio
                    pass

        if update_fields:
            producto.save(update_fields=update_fields)
        else:
            # si no vino ningún campo actualizable, igual asegura persistencia
            producto.save()

        return JsonResponse({"ok": True, "message": "Producto actualizado."})

    except Exception as e:
        # Devuelve JSON (no HTML) si algo inesperado ocurre
        return JsonResponse({"ok": False, "error": f"Error al actualizar: {e}"}, status=500)


@login_required
@require_roles("ADMIN", "INVENTARIO", "PRODUCCION", "VENTAS")
@transaction.atomic
@require_POST
def eliminar_producto(request, prod_id: int):
    """
    Elimina un producto de forma segura:
    - Si no existe -> 404 JSON
    - Si tiene relaciones protegidas (stocks, movimientos, etc.) -> error legible
    - Si elimina bien -> status=ok
    Siempre responde JSON (nunca HTML 500) para que el front no reviente con r.json().
    """
    try:
        producto = Product.objects.get(id=prod_id)
    except Product.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Producto no encontrado."},
            status=404
        )

    try:
        producto.delete()
        return JsonResponse(
            {"status": "ok", "message": "Producto eliminado correctamente."}
        )

    except ProtectedError:
        # FK con on_delete=PROTECT
        return JsonResponse(
            {
                "status": "error",
                "message": (
                    "No se puede eliminar el producto porque tiene movimientos, "
                    "stock u otras relaciones asociadas."
                ),
            },
            status=400,
        )

    except RestrictedError:
        # Django 3.1+ on_delete=RESTRICT
        return JsonResponse(
            {
                "status": "error",
                "message": (
                    "No se puede eliminar el producto debido a restricciones de integridad "
                    "en la base de datos (registros relacionados)."
                ),
            },
            status=400,
        )

    except IntegrityError:
        # Cualquier otra violación de integridad
        return JsonResponse(
            {
                "status": "error",
                "message": (
                    "No se pudo eliminar el producto por un problema de integridad de datos."
                ),
            },
            status=400,
        )

    except Exception as e:
        # Fallback: nunca devolvemos HTML, siempre JSON
        return JsonResponse(
            {
                "status": "error",
                "message": f"Error inesperado al eliminar el producto: {e}",
            },
            status=500,
        )