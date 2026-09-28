from sqlalchemy.orm import Session

from app.models.pago import Pago


def obtener_por_solicitud(db: Session, id_solicitud: int) -> Pago | None:
    return db.query(Pago).filter(Pago.id_solicitud == id_solicitud).first()


def crear(db: Session, *, id_solicitud: int, monto: float) -> Pago:
    pago = Pago(id_solicitud=id_solicitud, monto=monto, moneda="COP", estado="pendiente")
    db.add(pago)
    db.commit()
    db.refresh(pago)
    return pago


def marcar_reportado(db: Session, pago: Pago) -> Pago:
    """El cliente dice que ya transfirio el dinero al trabajador."""
    pago.estado = "reportado"
    db.commit()
    db.refresh(pago)
    return pago


def marcar_confirmado(db: Session, pago: Pago) -> Pago:
    """El trabajador confirma que el dinero si le llego."""
    pago.estado = "confirmado"
    db.commit()
    db.refresh(pago)
    return pago
