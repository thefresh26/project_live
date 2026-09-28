from datetime import datetime

from pydantic import BaseModel


class SolicitudCrear(BaseModel):
    mensaje: str | None = None


class Solicitud(BaseModel):
    """Lo que ve el trabajador cuando un cliente lo solicita (datos de
    contacto del cliente) y lo que ve el cliente en 'Mis solicitudes'
    (nombre del trabajador y, una vez completada, su dato de pago)."""

    id: int
    id_servicio: int
    titulo_servicio: str
    nombre_cliente: str
    correo_cliente: str
    celular_cliente: str
    nombre_trabajador: str
    celular_trabajador: str
    mensaje: str | None = None
    atendida: bool
    completada: bool
    # None si el trabajador todavia no la marca como completada (no hay
    # cobro creado todavia). Una vez existe: pendiente (esperando que el
    # cliente pague), reportado (el cliente dice que ya pago, falta que el
    # trabajador confirme) o confirmado (el trabajador confirmo que le
    # llego el dinero).
    estado_pago: str | None = None
    monto_pago: float | None = None
    # El numero de Nequi o llave Bancolombia del trabajador, para que el
    # cliente le transfiera. Solo se llena una vez la solicitud esta
    # completada; puede ser None si el trabajador nunca lo configuro.
    datos_pago_trabajador: str | None = None
    creado_en: datetime

    class Config:
        from_attributes = True
