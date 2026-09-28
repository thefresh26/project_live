from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.solicitud import Solicitud
from app.models.servicio import Servicio
from app.schemas.solicitud import SolicitudCrear


def crear(db: Session, data: SolicitudCrear, id_cliente: int, id_servicio: int) -> Solicitud:
    solicitud = Solicitud(id_cliente=id_cliente, id_servicio=id_servicio, mensaje=data.mensaje)
    db.add(solicitud)
    db.commit()
    db.refresh(solicitud)
    return solicitud


def listar_recibidas_por_trabajador(db: Session, id_trabajador: int) -> list[Solicitud]:
    """Solicitudes de servicios que le pertenecen a este trabajador."""
    return (
        db.query(Solicitud)
        .join(Servicio, Solicitud.id_servicio == Servicio.id)
        .options(
            joinedload(Solicitud.cliente),
            joinedload(Solicitud.servicio).joinedload(Servicio.usuario),
            joinedload(Solicitud.pago),
        )
        .filter(Servicio.id_usuario == id_trabajador)
        .order_by(Solicitud.creado_en.desc())
        .all()
    )


def obtener(db: Session, id_solicitud: int) -> Solicitud | None:
    return (
        db.query(Solicitud)
        .options(
            joinedload(Solicitud.cliente),
            joinedload(Solicitud.servicio).joinedload(Servicio.usuario),
            joinedload(Solicitud.pago),
        )
        .filter(Solicitud.id == id_solicitud)
        .first()
    )


def listar_hechas_por_cliente(db: Session, id_cliente: int) -> list[Solicitud]:
    """Solicitudes que este cliente ha hecho a servicios de otros
    trabajadores (para ver su estado y, si ya fueron completadas, pagar)."""
    return (
        db.query(Solicitud)
        .options(
            joinedload(Solicitud.cliente),
            joinedload(Solicitud.servicio).joinedload(Servicio.usuario),
            joinedload(Solicitud.pago),
        )
        .filter(Solicitud.id_cliente == id_cliente)
        .order_by(Solicitud.creado_en.desc())
        .all()
    )


def marcar_atendida(db: Session, solicitud: Solicitud) -> Solicitud:
    solicitud.atendida = True
    db.commit()
    db.refresh(solicitud)
    return solicitud


def marcar_completada(db: Session, solicitud: Solicitud) -> Solicitud:
    """El trabajador confirma que ya hizo el trabajo. Si todavía no la
    había marcado como atendida, también queda atendida (no tiene sentido
    completar algo que 'no había visto')."""
    solicitud.atendida = True
    solicitud.completada = True
    db.commit()
    db.refresh(solicitud)
    return solicitud

def contar_totales_y_pendientes(db: Session) -> tuple[int, int]:
    """Cuántas solicitudes de contacto se han hecho en toda la plataforma y
    cuántas siguen sin que el trabajador las marque como atendidas."""
    total = db.query(func.count(Solicitud.id)).scalar() or 0
    pendientes = (
        db.query(func.count(Solicitud.id)).filter(Solicitud.atendida.is_(False)).scalar() or 0
    )
    return total, pendientes

