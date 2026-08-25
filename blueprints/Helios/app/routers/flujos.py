from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import PERFIL_SOPORTE, require_perfil
from app.database import get_db
from app.models import Estado, Etapa, Flujo, TipoFlujo
from app.services.flujo_completo import (
    cargar_flujo_completo,
    catalogos_editor,
    guardar_flujo_completo,
    serializar_flujo,
)
from app.web import flash, render

router = APIRouter(prefix="/flujos", dependencies=[Depends(require_perfil(PERFIL_SOPORTE))])


@router.get("")
def lista(request: Request, db: Session = Depends(get_db)):
    return render(
        request,
        "flujos/lista.html",
        {
            "flujos": db.query(Flujo).order_by(Flujo.nombre).all(),
            "tipos": db.query(TipoFlujo).order_by(TipoFlujo.nombre).all(),
        },
    )


@router.post("/crear")
def crear(
    request: Request,
    nombre: str = Form(...),
    tipo_flujo_id: int = Form(...),
    descripcion: str = Form(""),
    db: Session = Depends(get_db),
):
    flujo = Flujo(
        nombre=nombre.strip(),
        tipo_flujo_id=tipo_flujo_id,
        descripcion=descripcion.strip() or None,
    )
    db.add(flujo)
    db.commit()
    flash(
        request,
        f"Flujo '{nombre}' creado. Configure el diseño y pulse Guardar Cambios.",
    )
    return RedirectResponse(f"/flujos/{flujo.id}/editar", status_code=303)


@router.get("/{flujo_id}")
def detalle(flujo_id: int, db: Session = Depends(get_db)):
    flujo = db.get(Flujo, flujo_id)
    if not flujo:
        return RedirectResponse("/flujos", status_code=303)
    return RedirectResponse(f"/flujos/{flujo_id}/editar", status_code=303)


@router.get("/{flujo_id}/editar")
def editor(request: Request, flujo_id: int, db: Session = Depends(get_db)):
    flujo = cargar_flujo_completo(db, flujo_id)
    if not flujo:
        flash(request, "Flujo no encontrado.", "danger")
        return RedirectResponse("/flujos", status_code=303)
    return render(
        request,
        "flujos/editor.html",
        {
            "flujo": flujo,
            "snapshot": serializar_flujo(flujo),
            "catalogos": catalogos_editor(db),
        },
    )


@router.get("/{flujo_id}/completo")
def obtener_completo(flujo_id: int, db: Session = Depends(get_db)):
    flujo = cargar_flujo_completo(db, flujo_id)
    if not flujo:
        return JSONResponse({"ok": False, "error": "Flujo no encontrado."}, status_code=404)
    return JSONResponse(
        {"ok": True, "data": serializar_flujo(flujo), "catalogos": catalogos_editor(db)}
    )


@router.post("/{flujo_id}/guardar-completo")
async def guardar_completo(request: Request, flujo_id: int, db: Session = Depends(get_db)):
    if not db.get(Flujo, flujo_id):
        return JSONResponse({"ok": False, "error": "Flujo no encontrado."}, status_code=404)
    try:
        payload = await request.json()
    except Exception:  # noqa: BLE001
        return JSONResponse({"ok": False, "error": "JSON inválido."}, status_code=400)
    try:
        data = guardar_flujo_completo(db, flujo_id, payload)
        return JSONResponse({"ok": True, "message": "Cambios guardados.", "data": data})
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@router.get("/{flujo_id}/etapas/{etapa_id}")
def etapa_detalle(flujo_id: int, etapa_id: int):
    """Compatibilidad: las URLs antiguas abren el editor en la etapa."""
    return RedirectResponse(f"/flujos/{flujo_id}/editar#etapa-{etapa_id}", status_code=303)


@router.post("/{flujo_id}/etapas/crear")
def crear_etapa_legacy(
    request: Request,
    flujo_id: int,
    nombre: str = Form(...),
    descripcion: str = Form(""),
    permite_retroceso: str | None = Form(None),
    es_final: str | None = Form(None),
    solicita_documentacion: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """Legacy: crear etapa rápida (el editor preferido usa guardar-completo)."""
    flujo = db.get(Flujo, flujo_id)
    orden = max((e.orden for e in flujo.etapas), default=0) + 1
    etapa = Etapa(
        flujo_id=flujo_id,
        nombre=nombre.strip(),
        descripcion=descripcion.strip() or None,
        orden=orden,
        permite_retroceso=permite_retroceso == "1",
        es_final=es_final == "1",
        solicita_documentacion=solicita_documentacion == "1",
    )
    db.add(etapa)
    db.flush()
    db.add(Estado(etapa_id=etapa.id, nombre="Pendiente", es_inicial=True))
    db.commit()
    return RedirectResponse(f"/flujos/{flujo_id}/editar#etapa-{etapa.id}", status_code=303)
