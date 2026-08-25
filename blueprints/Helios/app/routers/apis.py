import json

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import PERFIL_SOPORTE, require_perfil
from app.database import get_db
from app.models import ApiCall, ApiOutput, ApiParametro, DatoComplementario
from app.services.api_mapeo import CAMPOS_CASO
from app.web import flash, render

router = APIRouter(prefix="/apis", dependencies=[Depends(require_perfil(PERFIL_SOPORTE))])


@router.get("")
def lista(request: Request, db: Session = Depends(get_db)):
    return render(request, "apis/lista.html", {"apis": db.query(ApiCall).order_by(ApiCall.nombre).all()})


@router.post("/crear")
def crear(
    request: Request,
    nombre: str = Form(...),
    descripcion: str = Form(""),
    metodo: str = Form("POST"),
    url: str = Form(...),
    db: Session = Depends(get_db),
):
    if db.query(ApiCall).filter(ApiCall.nombre == nombre.strip()).first():
        flash(request, "Ya existe un API con ese nombre.", "danger")
        return RedirectResponse("/apis", status_code=303)
    api = ApiCall(nombre=nombre.strip(), descripcion=descripcion.strip() or None, metodo=metodo, url=url.strip())
    db.add(api)
    db.commit()
    flash(request, f"API '{nombre}' creado. Configure parametros y outputs.")
    return RedirectResponse(f"/apis/{api.id}", status_code=303)


@router.get("/{api_id}")
def detalle(request: Request, api_id: int, db: Session = Depends(get_db)):
    api = db.get(ApiCall, api_id)
    if not api:
        flash(request, "API no encontrado.", "danger")
        return RedirectResponse("/apis", status_code=303)
    return render(
        request,
        "apis/detalle.html",
        {
            "api": api,
            "datos": db.query(DatoComplementario).filter(DatoComplementario.activo).order_by(DatoComplementario.nombre).all(),
            "campos_caso": CAMPOS_CASO,
        },
    )


@router.post("/{api_id}/actualizar")
def actualizar(
    request: Request,
    api_id: int,
    nombre: str = Form(...),
    descripcion: str = Form(""),
    metodo: str = Form(...),
    url: str = Form(...),
    headers_json: str = Form(""),
    timeout_seg: int = Form(30),
    activo: str | None = Form(None),
    db: Session = Depends(get_db),
):
    api = db.get(ApiCall, api_id)
    if headers_json.strip():
        try:
            json.loads(headers_json)
        except json.JSONDecodeError:
            flash(request, "Los headers deben ser JSON valido.", "danger")
            return RedirectResponse(f"/apis/{api_id}", status_code=303)
    api.nombre = nombre.strip()
    api.descripcion = descripcion.strip() or None
    api.metodo = metodo
    api.url = url.strip()
    api.headers_json = headers_json.strip() or None
    api.timeout_seg = timeout_seg
    api.activo = activo == "1"
    db.commit()
    flash(request, "API actualizado.")
    return RedirectResponse(f"/apis/{api_id}", status_code=303)


# ------------------------------- Parametros -------------------------------


@router.post("/{api_id}/parametros/crear")
def crear_parametro(
    request: Request,
    api_id: int,
    nombre: str = Form(...),
    ubicacion: str = Form(...),
    origen: str = Form(...),
    valor_fijo: str = Form(""),
    dato_id: str = Form(""),
    campo_caso: str = Form(""),
    db: Session = Depends(get_db),
):
    db.add(
        ApiParametro(
            api_id=api_id,
            nombre=nombre.strip(),
            ubicacion=ubicacion,
            origen=origen,
            valor_fijo=valor_fijo.strip() or None if origen == "fijo" else None,
            dato_id=int(dato_id) if origen == "dato" and dato_id else None,
            campo_caso=campo_caso if origen == "caso" else None,
        )
    )
    db.commit()
    flash(request, f"Parametro '{nombre}' agregado.")
    return RedirectResponse(f"/apis/{api_id}", status_code=303)


@router.post("/{api_id}/parametros/{param_id}/eliminar")
def eliminar_parametro(request: Request, api_id: int, param_id: int, db: Session = Depends(get_db)):
    p = db.get(ApiParametro, param_id)
    if p and p.api_id == api_id:
        db.delete(p)
        db.commit()
        flash(request, "Parametro eliminado.")
    return RedirectResponse(f"/apis/{api_id}", status_code=303)


# --------------------------------- Outputs --------------------------------


@router.post("/{api_id}/outputs/crear")
def crear_output(
    request: Request,
    api_id: int,
    nombre: str = Form(...),
    json_path: str = Form(...),
    formato: str = Form("texto"),
    db: Session = Depends(get_db),
):
    db.add(ApiOutput(api_id=api_id, nombre=nombre.strip(), json_path=json_path.strip(), formato=formato))
    db.commit()
    flash(request, f"Output '{nombre}' agregado.")
    return RedirectResponse(f"/apis/{api_id}", status_code=303)


@router.post("/{api_id}/outputs/{output_id}/eliminar")
def eliminar_output(request: Request, api_id: int, output_id: int, db: Session = Depends(get_db)):
    o = db.get(ApiOutput, output_id)
    if o and o.api_id == api_id:
        try:
            db.delete(o)
            db.commit()
            flash(request, "Output eliminado.")
        except Exception:
            db.rollback()
            flash(request, "No se pudo eliminar: el output se usa en reglas o mapeos de flujo.", "danger")
    return RedirectResponse(f"/apis/{api_id}", status_code=303)


@router.post("/{api_id}/probar")
def probar_api(
    request: Request,
    api_id: int,
    caso_id: int = Form(...),
    db: Session = Depends(get_db),
):
    """Bonus: preview + ejecución de prueba contra un caso real (loguea en CasoApiLog)."""
    from fastapi.responses import JSONResponse

    from app.models import Caso
    from app.services.api_engine import ejecutar_api, preview_request
    from sqlalchemy.orm import selectinload

    api = (
        db.query(ApiCall)
        .options(selectinload(ApiCall.parametros), selectinload(ApiCall.outputs))
        .filter(ApiCall.id == api_id)
        .first()
    )
    caso = db.get(Caso, caso_id)
    if not api or not caso:
        return JSONResponse({"ok": False, "error": "API o caso no encontrado."}, status_code=404)

    preview = preview_request(api, caso, db)
    resultado = ejecutar_api(api, caso, db)
    db.commit()
    return JSONResponse(
        {
            "ok": resultado.exito,
            "preview_request": preview,
            "http_status": resultado.http_status,
            "outputs": resultado.outputs,
            "error": resultado.error,
            "response_preview": (resultado.response_json or "")[:2000],
        }
    )
