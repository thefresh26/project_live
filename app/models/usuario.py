from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class Usuario(Base):
    __tablename__ = "usuario"

    id = Column(Integer, primary_key=True, index=True)
    correo = Column(String, unique=True, nullable=False, index=True)
    contrasena = Column(String, nullable=False)
    nombre = Column(String, nullable=False)
    apellido = Column(String, nullable=False)
    cedula = Column(String, unique=True, nullable=False, index=True)
    celular = Column(String, nullable=False)
    ciudad = Column(String, nullable=False)
    direccion = Column(String, nullable=False)
    latitud = Column(Float, nullable=True)
    longitud = Column(Float, nullable=True)
    foto_url = Column(String, nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
    # Cuentas creadas antes de este campo se tratan como ya verificadas
    # (ver la migracion ALTER TABLE en main.py); las nuevas empiezan en
    # False y se verifican con el enlace que llega por correo al registrarse.
    correo_verificado = Column(Boolean, nullable=False, default=False)
    # Numero de Nequi o llave Bancolombia (u otro dato equivalente) que el
    # propio trabajador escribe para que le paguen directo cuando complete
    # un servicio. Opcional: nadie esta obligado a llenarlo, y lo puede
    # cambiar cuando quiera desde "Mi cuenta".
    datos_pago = Column(String, nullable=True)
    id_rol = Column(Integer, ForeignKey("rol.id"), nullable=False)

    rol = relationship("Rol", back_populates="usuarios")
    servicios = relationship("Servicio", back_populates="usuario")
