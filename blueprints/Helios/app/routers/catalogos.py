from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import PERFIL_SOPORTE, get_current_user, require_perfil
from app.database import get_db
from app.models import Caso, Cliente, DatoComplementario, Documento, Flujo, TipoDato, TipoFlujo
from app.services.clientes import buscar_clientes, listar_clientes_recientes
from app.services.dato_formato import (
    TIPOS_CON_DECIMALES,
    resolve_formato,
    tipo_codigo,
)
from app.web import flash, render

router = APIRouter(prefix="/catalogos", dependencies=[Depends(get_current_user)])
admin_dep = Depends(require_perfil(PERFIL_SOPORTE))


# ------------------------------ Documentos --------------------------------


@router.get("/documentos")
def documentos(request: Request, db: Session = Depends(get_db)):
    return render(
        request,
        "catalogos/documentos.html",
        {"documentos": db.query(Documento).order_by(Documento.nombre).all()},
    )


@router.post("/documentos/crear", dependencies=[admin_dep])
def crear_documento(
    request: Request,
    nombre: str = Form(...),
    descripcion: str = Form(""),
    db: Session = Depends(get_db),
):
    if db.query(Documento).filter(Documento.nombre == nombre.strip()).first():
        flash(request, "Ya existe un documento con ese nombre.", "danger")
    else:
        db.add(Documento(nombre=nombre.strip(), descripcion=descripcion.strip() or None))
        db.commit()
        flash(request, f"Documento '{nombre}' creado.")
    return RedirectResponse("/catalogos/documentos", status_code=303)


@router.post("/documentos/{doc_id}/actualizar", dependencies=[admin_dep])
def actualizar_documento(
    request: Request,
    doc_id: int,
    nombre: str = Form(...),
    descripcion: str = Form(""),
    activo: str | None = Form(None),
    db: Session = Depends(get_db),
):
    d = db.get(Documento, doc_id)
    d.nombre = nombre.strip()
    d.descripcion = descripcion.strip() or None
    d.activo = activo == "1"
    db.commit()
    flash(request, "Documento actualizado.")
    return RedirectResponse("/catalogos/documentos", status_code=303)


# --------------------------- Datos complementarios ------------------------


@router.get("/datos")
def datos(request: Request, db: Session = Depends(get_db)):
    tipos = db.query(TipoDato).order_by(TipoDato.id).all()
    tipos_meta = [
        {
            "id": t.id,
            "nombre": t.nombre,
            "codigo": tipo_codigo(t),
            "permite_decimales": tipo_codigo(t) in TIPOS_CON_DECIMALES,
        }
        for t in tipos
    ]
    return render(
        request,
        "catalogos/datos.html",
        {
            "datos": db.query(DatoComplementario).order_by(DatoComplementario.nombre).all(),
            "tipos": tipos,
            "tipos_meta": tipos_meta,
        },
    )


@router.post("/datos/crear", dependencies=[admin_dep])
def crear_dato(
    request: Request,
    nombre: str = Form(...),
    descripcion: str = Form(""),
    tipo_dato_id: int = Form(...),
    opciones: str = Form(""),
    formato_visualizacion: str = Form(""),
    decimales: str = Form(""),
    db: Session = Depends(get_db),
):
    if db.query(DatoComplementario).filter(DatoComplementario.nombre == nombre.strip()).first():
        flash(request, "Ya existe un dato con ese nombre.", "danger")
    else:
        tipo = db.get(TipoDato, tipo_dato_id)
        codigo = tipo_codigo(tipo)
        fmt = (formato_visualizacion or "").strip() or resolve_formato(tipo_dato=tipo)
        prec = None
        if codigo in TIPOS_CON_DECIMALES:
            try:
                prec = int(decimales) if str(decimales).strip() else 2
            except ValueError:
                prec = 2
            prec = max(0, min(prec, 8))
        db.add(
            DatoComplementario(
                nombre=nombre.strip(),
                descripcion=descripcion.strip() or None,
                tipo_dato_id=tipo_dato_id,
                opciones=opciones.strip() or None,
                formato_visualizacion=fmt,
                decimales=prec,
            )
        )
        db.commit()
        flash(request, f"Dato '{nombre}' creado.")
    return RedirectResponse("/catalogos/datos", status_code=303)


@router.post("/datos/{dato_id}/actualizar", dependencies=[admin_dep])
def actualizar_dato(
    request: Request,
    dato_id: int,
    nombre: str = Form(...),
    descripcion: str = Form(""),
    tipo_dato_id: int = Form(...),
    opciones: str = Form(""),
    formato_visualizacion: str = Form(""),
    decimales: str = Form(""),
    activo: str | None = Form(None),
    db: Session = Depends(get_db),
):
    d = db.get(DatoComplementario, dato_id)
    tipo = db.get(TipoDato, tipo_dato_id)
    codigo = tipo_codigo(tipo)
    d.nombre = nombre.strip()
    d.descripcion = descripcion.strip() or None
    d.tipo_dato_id = tipo_dato_id
    d.opciones = opciones.strip() or None
    d.formato_visualizacion = (formato_visualizacion or "").strip() or resolve_formato(tipo_dato=tipo)
    if codigo in TIPOS_CON_DECIMALES:
        try:
            prec = int(decimales) if str(decimales).strip() else 2
        except ValueError:
            prec = 2
        d.decimales = max(0, min(prec, 8))
    else:
        d.decimales = None
    d.activo = activo == "1"
    db.commit()
    flash(request, "Dato actualizado.")
    return RedirectResponse("/catalogos/datos", status_code=303)


# ------------------------------ Tipos de flujo -----------------------------


@router.get("/tipos-flujo")
def tipos_flujo(request: Request, db: Session = Depends(get_db)):
    return render(
        request,
        "catalogos/tipos_flujo.html",
        {"tipos": db.query(TipoFlujo).order_by(TipoFlujo.nombre).all()},
    )


@router.post("/tipos-flujo/crear", dependencies=[admin_dep])
def crear_tipo_flujo(request: Request, nombre: str = Form(...), db: Session = Depends(get_db)):
    if db.query(TipoFlujo).filter(TipoFlujo.nombre == nombre.strip()).first():
        flash(request, "Ya existe ese tipo de flujo.", "danger")
    else:
        db.add(TipoFlujo(nombre=nombre.strip()))
        db.commit()
        flash(request, f"Tipo de flujo '{nombre}' creado.")
    return RedirectResponse("/catalogos/tipos-flujo", status_code=303)


# -------------------------------- Clientes --------------------------------


@router.get("/clientes")
def clientes(request: Request, q: str = "", db: Session = Depends(get_db)):
    if q.strip():
        resultado = buscar_clientes(db, q, page=1, page_size=25)
    else:
        resultado = listar_clientes_recientes(db, page=1, page_size=25)
    # No pasar clave "items" al template: en Jinja `resultado.items` es dict.items().
    return render(
        request,
        "catalogos/clientes.html",
        {
            "q": q,
            "clientes": resultado.get("items") or [],
            "clientes_total": int(resultado.get("total") or 0),
            "clientes_mode": resultado.get("mode") or ("busqueda" if q.strip() else "recientes"),
            "flujos": db.query(Flujo).filter(Flujo.activo).order_by(Flujo.nombre).all(),
        },
    )


@router.get("/api/clientes/buscar")
def api_buscar_clientes(
    q: str = "",
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    return JSONResponse(buscar_clientes(db, q, page=page, page_size=page_size))


@router.get("/clientes/{cliente_id}")
def cliente_detalle(request: Request, cliente_id: int, db: Session = Depends(get_db)):
    cliente = db.get(Cliente, cliente_id)
    if not cliente:
        flash(request, "Cliente no encontrado.", "danger")
        return RedirectResponse("/catalogos/clientes", status_code=303)
    casos = (
        db.query(Caso)
        .filter(Caso.cliente_id == cliente_id)
        .order_by(Caso.id.desc())
        .limit(100)
        .all()
    )
    return render(
        request,
        "catalogos/cliente_detalle.html",
        {
            "cliente": cliente,
            "casos": casos,
            "flujos": db.query(Flujo).filter(Flujo.activo).order_by(Flujo.nombre).all(),
        },
    )


@router.post("/clientes/crear")
def crear_cliente(
    request: Request,
    nombre_completo: str = Form(...),
    tipo_identificacion: str = Form(...),
    identificacion: str = Form(...),
    telefono: str = Form(""),
    correo: str = Form(""),
    db: Session = Depends(get_db),
):
    if db.query(Cliente).filter(Cliente.identificacion == identificacion.strip()).first():
        flash(request, "Ya existe un cliente con esa identificacion.", "danger")
        return RedirectResponse("/catalogos/clientes", status_code=303)
    c = Cliente(
        nombre_completo=nombre_completo.strip(),
        tipo_identificacion=tipo_identificacion,
        identificacion=identificacion.strip(),
        telefono=telefono.strip() or None,
        correo=correo.strip() or None,
    )
    db.add(c)
    db.commit()
    flash(request, f"Cliente '{nombre_completo}' creado.")
    return RedirectResponse(f"/catalogos/clientes/{c.id}", status_code=303)
