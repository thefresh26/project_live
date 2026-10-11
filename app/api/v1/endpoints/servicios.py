from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.deps import get_current_usuario, get_db
from app.core.uploads import guardar_foto_perfil
from app.crud import crud_calificacion, crud_categoria, crud_servicio
from app.models.servicio import Servicio
from app.models.usuario import Usuario
from app.schemas.servicio import ServicioConCategoria, ServicioCrear

router = APIRouter(prefix="/servicios", tags=["servicios"])


def _a_servicio_con_categoria(db: Session, servicio: Servicio) -> ServicioConCategoria:
    promedio, total = crud_calificacion.promedio_y_total(db, servicio.id)
    return ServicioConCategoria(
        id=servicio.id,
        id_usuario=servicio.id_usuario,
        id_categoria=servicio.id_categoria,
        titulo=servicio.titulo,
        descripcion=servicio.descripcion,
        precio_desde=servicio.precio_desde,
        disponibilidad=servicio.disponibilidad,
        foto_url=servicio.foto_url,
        activo=servicio.activo,
        estado=servicio.estado,
        motivo_rechazo=servicio.motivo_rechazo,
        creado_en=servicio.creado_en,
        categoria=servicio.categoria,
        calificacion_promedio=promedio,
        total_calificaciones=total,
        nombre_trabajador=f"{servicio.usuario.nombre} {servicio.usuario.apellido}".strip()
        if servicio.usuario
        else None,
        ciudad_trabajador=servicio.usuario.ciudad if servicio.usuario else None,
    )


@router.get("", response_model=list[ServicioConCategoria])
def listar_servicios(id_categoria: int | None = None, db: Session = Depends(get_db)):
    servicios = crud_servicio.listar_activos(db, id_categoria=id_categoria)
    return [_a_servicio_con_categoria(db, s) for s in servicios]


@router.get("/mios", response_model=list[ServicioConCategoria])
def mis_servicios(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_usuario),
):
    servicios = crud_servicio.listar_por_usuario(db, usuario.id)
    return [_a_servicio_con_categoria(db, s) for s in servicios]


@router.get("/{id_servicio}", response_model=ServicioConCategoria)
def obtener_servicio(id_servicio: int, db: Session = Depends(get_db)):
    servicio = crud_servicio.obtener(db, id_servicio)
    if servicio is None:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    return _a_servicio_con_categoria(db, servicio)


@router.post("", response_model=ServicioConCategoria, status_code=status.HTTP_201_CREATED)
async def crear_servicio(
    id_categoria: int = Form(...),
    titulo: str = Form(...),
    descripcion: str | None = Form(None),
    precio_desde: float | None = Form(None),
    disponibilidad: str | None = Form(None),
    foto: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_usuario),
):
    try:
        data = ServicioCrear(
            id_categoria=id_categoria,
            titulo=titulo,
            descripcion=descripcion,
            precio_desde=precio_desde,
            disponibilidad=disponibilidad,
        )
    except ValidationError as exc:
        primero = exc.errors()[0]
        campo = primero["loc"][-1] if primero.get("loc") else "datos"
        raise HTTPException(status_code=422, detail=f"Dato inválido ({campo}): {primero['msg']}")
    if crud_categoria.obtener(db, data.id_categoria) is None:
        raise HTTPException(status_code=400, detail="La categoría elegida no existe")
    foto_url = await guardar_foto_perfil(foto)
    servicio = crud_servicio.crear(db, data, id_usuario=usuario.id, foto_url=foto_url)
    return _a_servicio_con_categoria(db, servicio)


@router.delete("/{id_servicio}", status_code=status.HTTP_204_NO_CONTENT)
def desactivar_servicio(
    id_servicio: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_usuario),
):
    """"Elimina" un servicio publicado (en realidad lo desactiva, no lo borra,
    para no perder el historial de calificaciones)."""
    servicio = crud_servicio.obtener(db, id_servicio)
    if servicio is None:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    if servicio.id_usuario != usuario.id:
        raise HTTPException(status_code=403, detail="No puedes eliminar un servicio que no es tuyo")
    crud_servicio.desactivar(db, servicio)
