from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sqlalchemy.orm import Session

from app.api.deps import get_db, requerir_administrador
from app.crud import (
    crud_calificacion,
    crud_denuncia_trabajador,
    crud_error_log,
    crud_reporte_formulario,
    crud_servicio,
    crud_solicitud,
    crud_usuario,
)
from app.models.servicio import Servicio
from app.models.usuario import Usuario
from app.schemas.denuncia_trabajador import DenunciaTrabajador, DenunciaTrabajadorResolver
from app.schemas.error_log import ErrorLog as ErrorLogSchema
from app.schemas.estadisticas import EstadisticasAdmin
from app.schemas.reporte_formulario import ReporteFormulario, ReporteFormularioResolver
from app.schemas.servicio import RechazarServicio, ServicioConCategoria
from app.schemas.usuario import CrearUsuarioAdmin, UsuarioAdmin

router = APIRouter(prefix="/admin", tags=["admin"])


def _a_servicio_con_categoria(servicio: Servicio) -> ServicioConCategoria:
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
        nombre_trabajador=f"{servicio.usuario.nombre} {servicio.usuario.apellido}".strip()
        if servicio.usuario
        else None,
        ciudad_trabajador=servicio.usuario.ciudad if servicio.usuario else None,
    )


def _a_usuario_admin(usuario: Usuario) -> UsuarioAdmin:
    return UsuarioAdmin(
        id=usuario.id,
        nombre=usuario.nombre,
        apellido=usuario.apellido,
        correo=usuario.correo,
        cedula=usuario.cedula,
        celular=usuario.celular,
        ciudad=usuario.ciudad,
        direccion=usuario.direccion,
        activo=usuario.activo,
        id_rol=usuario.id_rol,
        nombre_rol=usuario.rol.nombre if usuario.rol else "",
    )


@router.get("/usuarios", response_model=list[UsuarioAdmin])
def listar_usuarios(
    db: Session = Depends(get_db),
    _admin: Usuario = Depends(requerir_administrador),
):
    """Lista completa de personas registradas (cualquier rol). Solo accesible
    con una sesión de un usuario con rol Administrador."""
    return [_a_usuario_admin(u) for u in crud_usuario.listar_todos(db)]


@router.post("/usuarios", response_model=UsuarioAdmin, status_code=201)
def crear_usuario(
    data: CrearUsuarioAdmin,
    db: Session = Depends(get_db),
    _admin: Usuario = Depends(requerir_administrador),
):
    """Crea una cuenta con el rol que el admin elija, incluido Administrador.
    A propósito no existe forma de hacer esto desde el registro público:
    solo se puede llegar aquí ya estando autenticado como Administrador."""
    if data.rol not in ("Cliente", "Trabajador", "Administrador"):
        raise HTTPException(status_code=400, detail="Rol no reconocido")
    if crud_usuario.get_by_correo(db, data.correo):
        raise HTTPException(status_code=400, detail="Ese correo ya está registrado")
    if crud_usuario.get_by_cedula(db, data.cedula):
        raise HTTPException(status_code=400, detail="Esa cédula ya está registrada")
    return _a_usuario_admin(crud_usuario.crear_con_rol(db, data))


@router.patch("/usuarios/{id_usuario}/desactivar", response_model=UsuarioAdmin)
def desactivar_usuario(
    id_usuario: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_administrador),
):
    """"Desecha" a una persona: desactiva su cuenta (no la borra), para que
    deje de aparecer en el mapa público y no pueda iniciar sesión."""
    if id_usuario == admin.id:
        raise HTTPException(status_code=400, detail="No puedes desactivar tu propia cuenta de administrador")
    usuario = crud_usuario.obtener(db, id_usuario)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return _a_usuario_admin(crud_usuario.desactivar(db, usuario))


@router.delete("/usuarios/{id_usuario}", status_code=204)
def eliminar_usuario(
    id_usuario: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requerir_administrador),
):
    """Borra la cuenta de forma real y permanente (a diferencia de
    desactivar): también borra en cascada sus servicios, calificaciones,
    solicitudes, denuncias y reportes. No se puede deshacer. Solo se
    bloquea que un administrador se borre a sí mismo (para que nadie se
    quede sin acceso al panel por accidente); borrar a otro administrador
    sí está permitido, porque solo alguien que ya es Administrador puede
    entrar a este panel."""
    if id_usuario == admin.id:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propia cuenta de administrador")
    usuario = crud_usuario.obtener(db, id_usuario)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    crud_usuario.eliminar(db, usuario)


class NuevaContrasena(BaseModel):
    contrasena: str = Field(min_length=8)


@router.patch("/usuarios/{id_usuario}/contrasena", status_code=204)
def cambiar_contrasena_usuario(
    id_usuario: int,
    data: NuevaContrasena,
    db: Session = Depends(get_db),
    _admin: Usuario = Depends(requerir_administrador),
):
    """Recuperación asistida: el administrador fija una contraseña nueva
    cuando el usuario no puede usar el correo de recuperación."""
    usuario = crud_usuario.obtener(db, id_usuario)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    crud_usuario.actualizar_contrasena(db, usuario, data.contrasena)


@router.patch("/usuarios/{id_usuario}/reactivar", response_model=UsuarioAdmin)
def reactivar_usuario(
    id_usuario: int,
    db: Session = Depends(get_db),
    _admin: Usuario = Depends(requerir_administrador),
):
    """Revierte una desactivación, por si fue un error."""
    usuario = crud_usuario.obtener(db, id_usuario)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return _a_usuario_admin(crud_usuario.reactivar(db, usuario))


@router.get("/estadisticas", response_model=EstadisticasAdmin)
def obtener_estadisticas(
    db: Session = Depends(get_db),
    _admin: Usuario = Depends(requerir_administrador),
):
    """Conteos para las tarjetas del panel de admin. Cuenta cuentas por rol
    (una persona nunca se cuenta dos veces, porque Cliente -> Trabajador es
    un ascenso de la misma cuenta) y formularios por estado."""
    por_rol = crud_usuario.contar_por_rol(db)
    por_estado_servicio = crud_servicio.contar_por_estado(db)
    solicitudes_totales, solicitudes_pendientes = crud_solicitud.contar_totales_y_pendientes(db)
    calificacion_promedio, calificaciones_totales = crud_calificacion.promedio_y_total_global(db)
    categoria_top_nombre, categoria_top_total = crud_servicio.categoria_mas_popular(db)
    errores_sin_revisar = crud_error_log.contar_no_vistos(db)
    return EstadisticasAdmin(
        total_clientes=por_rol.get("Cliente", 0),
        total_trabajadores=por_rol.get("Trabajador", 0),
        total_administradores=por_rol.get("Administrador", 0),
        formularios_pendientes=por_estado_servicio["pendiente"],
        formularios_aprobados=por_estado_servicio["aprobado"],
        formularios_rechazados=por_estado_servicio["rechazado"],
        denuncias_trabajador_pendientes=crud_denuncia_trabajador.contar_pendientes(db),
        reportes_formulario_pendientes=crud_reporte_formulario.contar_pendientes(db),
        solicitudes_totales=solicitudes_totales,
        solicitudes_pendientes=solicitudes_pendientes,
        calificaciones_totales=calificaciones_totales,
        calificacion_promedio=calificacion_promedio,
        categoria_top_nombre=categoria_top_nombre,
        categoria_top_total=categoria_top_total,
        servicios_nuevos_semana=crud_servicio.contar_nuevos_ultimos_dias(db, dias=7),
        errores_sin_revisar=errores_sin_revisar,
    )


@router.get("/servicios/pendientes", response_model=list[ServicioConCategoria])
def listar_servicios_pendientes(
    db: Session = Depends(get_db),
    _admin: Usuario = Depends(requerir_administrador),
):
    """Formularios de trabajo esperando aprobación."""
    return [_a_servicio_con_categoria(s) for s in crud_servicio.listar_pendientes(db)]


@router.patch("/servicios/{id_servicio}/aprobar", response_model=ServicioConCategoria)
def aprobar_servicio(
    id_servicio: int,
    db: Session = Depends(get_db),
    _admin: Usuario = Depends(requerir_administrador),
):
    """Aprueba un formulario: queda visible al público y, si el dueño todavía
    era Cliente, su cuenta asciende a Trabajador (misma cuenta, sin perder
    sus funciones de cliente)."""
    servicio = crud_servicio.obtener(db, id_servicio)
    if servicio is None:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")

    servicio = crud_servicio.aprobar(db, servicio)

    dueno = servicio.usuario
    if dueno is not None and dueno.rol is not None and dueno.rol.nombre == "Cliente":
        rol_trabajador = crud_usuario.obtener_o_crear_rol_trabajador(db)
        dueno.id_rol = rol_trabajador.id
        db.commit()
        db.refresh(servicio)

    return _a_servicio_con_categoria(servicio)


@router.patch("/servicios/{id_servicio}/rechazar", response_model=ServicioConCategoria)
def rechazar_servicio(
    id_servicio: int,
    data: RechazarServicio,
    db: Session = Depends(get_db),
    _admin: Usuario = Depends(requerir_administrador),
):
    """Rechaza un formulario. La cuenta del dueño no cambia de rol: sigue
    siendo Cliente (o Trabajador si ya tenía otro formulario aprobado antes)."""
    servicio = crud_servicio.obtener(db, id_servicio)
    if servicio is None:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    return _a_servicio_con_categoria(crud_servicio.rechazar(db, servicio, data.motivo))


def _a_denuncia_trabajador(d) -> DenunciaTrabajador:
    return DenunciaTrabajador(
        id=d.id,
        id_denunciante=d.id_denunciante,
        nombre_denunciante=f"{d.denunciante.nombre} {d.denunciante.apellido}".strip() if d.denunciante else "",
        id_trabajador=d.id_trabajador,
        nombre_trabajador=f"{d.trabajador.nombre} {d.trabajador.apellido}".strip() if d.trabajador else "",
        id_servicio=d.id_servicio,
        motivo=d.motivo,
        descripcion=d.descripcion,
        estado=d.estado,
        resolucion=d.resolucion,
        creado_en=d.creado_en,
    )


def _a_reporte_formulario(r) -> ReporteFormulario:
    return ReporteFormulario(
        id=r.id,
        id_trabajador=r.id_trabajador,
        nombre_trabajador=f"{r.trabajador.nombre} {r.trabajador.apellido}".strip() if r.trabajador else "",
        id_servicio=r.id_servicio,
        titulo_servicio=r.servicio.titulo if r.servicio else "",
        descripcion=r.descripcion,
        estado=r.estado,
        resolucion=r.resolucion,
        creado_en=r.creado_en,
    )


@router.get("/denuncias-trabajador", response_model=list[DenunciaTrabajador])
def listar_denuncias_trabajador(
    db: Session = Depends(get_db),
    _admin: Usuario = Depends(requerir_administrador),
):
    """Bandeja de quejas de clientes (o trabajadores actuando como clientes)
    contra un trabajador. Separada de los reportes de errores en formularios."""
    return [_a_denuncia_trabajador(d) for d in crud_denuncia_trabajador.listar_pendientes(db)]


@router.patch("/denuncias-trabajador/{id_denuncia}/resolver", response_model=DenunciaTrabajador)
def resolver_denuncia_trabajador(
    id_denuncia: int,
    data: DenunciaTrabajadorResolver,
    db: Session = Depends(get_db),
    _admin: Usuario = Depends(requerir_administrador),
):
    denuncia = crud_denuncia_trabajador.obtener(db, id_denuncia)
    if denuncia is None:
        raise HTTPException(status_code=404, detail="Denuncia no encontrada")

    if data.accion == "desactivar_trabajador":
        crud_usuario.desactivar(db, denuncia.trabajador)
    elif data.accion == "desactivar_servicio" and denuncia.servicio is not None:
        crud_servicio.desactivar(db, denuncia.servicio)
    elif data.accion not in ("ninguna", "desactivar_trabajador", "desactivar_servicio"):
        raise HTTPException(status_code=400, detail="Acción no reconocida")

    return _a_denuncia_trabajador(crud_denuncia_trabajador.resolver(db, denuncia, data.resolucion))


@router.get("/reportes-formulario", response_model=list[ReporteFormulario])
def listar_reportes_formulario(
    db: Session = Depends(get_db),
    _admin: Usuario = Depends(requerir_administrador),
):
    """Bandeja de errores que un trabajador reportó sobre su propio formulario."""
    return [_a_reporte_formulario(r) for r in crud_reporte_formulario.listar_pendientes(db)]


@router.patch("/reportes-formulario/{id_reporte}/resolver", response_model=ReporteFormulario)
def resolver_reporte_formulario(
    id_reporte: int,
    data: ReporteFormularioResolver,
    db: Session = Depends(get_db),
    _admin: Usuario = Depends(requerir_administrador),
):
    reporte = crud_reporte_formulario.obtener(db, id_reporte)
    if reporte is None:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    return _a_reporte_formulario(crud_reporte_formulario.resolver(db, reporte, data.resolucion))


@router.get("/errores", response_model=list[ErrorLogSchema])
def listar_errores(
    db: Session = Depends(get_db),
    _admin: Usuario = Depends(requerir_administrador),
):
    """Errores no controlados más recientes del backend (ver el middleware en
    app/main.py que los captura y guarda). Sirve para detectar fallas sin
    tener que entrar al dashboard de Render."""
    return crud_error_log.listar_recientes(db)


@router.patch("/errores/{id_error}/marcar-visto", response_model=ErrorLogSchema)
def marcar_error_visto(
    id_error: int,
    db: Session = Depends(get_db),
    _admin: Usuario = Depends(requerir_administrador),
):
    error = crud_error_log.obtener(db, id_error)
    if error is None:
        raise HTTPException(status_code=404, detail="Error no encontrado")
    return crud_error_log.marcar_visto(db, error)


@router.post("/errores/marcar-todos-vistos", status_code=204)
def marcar_todos_los_errores_vistos(
    db: Session = Depends(get_db),
    _admin: Usuario = Depends(requerir_administrador),
):
    crud_error_log.marcar_todos_vistos(db)
