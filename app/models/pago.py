from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class Pago(Base):
    """Cobro por un servicio ya prestado, con transferencia directa
    (Nequi / llave Bancolombia) al trabajador: la plataforma no procesa el
    dinero, solo le muestra al cliente el dato de pago del trabajador y
    lleva el registro de la confirmacion en dos pasos (cliente reporta que
    pago, trabajador confirma que le llego)."""

    __tablename__ = "pago"

    id = Column(Integer, primary_key=True, index=True)
    id_solicitud = Column(Integer, ForeignKey("solicitud.id"), nullable=False, unique=True)
    # Columnas heredadas de un intento anterior con pasarela de pago (Wompi).
    # Ya no se usan (nullable=True), se dejan solo por compatibilidad con la
    # tabla que ya existe en produccion; ver la migracion en main.py.
    referencia = Column(String, nullable=True, unique=True, index=True)
    monto = Column(Float, nullable=False)
    moneda = Column(String, nullable=False, default="COP")
    # pendiente: el trabajador completo el trabajo y esta esperando que el
    # cliente pague por su cuenta (Nequi/Bancolombia).
    # reportado: el cliente marco "ya pague", falta que el trabajador
    # confirme que de verdad le llego el dinero.
    # confirmado: el trabajador confirmo que recibio el pago.
    estado = Column(String, nullable=False, default="pendiente")
    creado_en = Column(DateTime, nullable=False, default=datetime.utcnow)
    actualizado_en = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    solicitud = relationship("Solicitud", back_populates="pago")
