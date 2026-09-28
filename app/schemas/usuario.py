from pydantic import BaseModel, EmailStr, Field


class RegistroTrabajador(BaseModel):
    nombre: str
    apellido: str
    correo: EmailStr
    # Minimo 8 caracteres: evita contrasenas como "1" o "abc", sin exigir
    # mayusculas/simbolos para no complicar el registro de un proyecto academico.
    contrasena: str = Field(min_length=8)
    cedula: str
    celular: str
    ciudad: str
    direccion: str
    latitud: float | None = None
    longitud: float | None = None


class Usuario(BaseModel):
    id: int
    nombre: str
    apellido: str
    correo: EmailStr
    cedula: str
    celular: str
    ciudad: str
    direccion: str
    latitud: float | None = None
    longitud: float | None = None
    foto_url: str | None = None
    id_rol: int
    correo_verificado: bool = True
    datos_pago: str | None = None

    class Config:
        from_attributes = True


class ActualizarDatosPago(BaseModel):
    """Numero de Nequi o llave Bancolombia del trabajador. Se puede dejar
    vacio (None) para borrarlo: no es obligatorio tener uno."""

    datos_pago: str | None = None


class TrabajadorMapa(BaseModel):
    """Datos públicos de un trabajador para pintarlo en el mapa de la landing page.
    Nunca expone correo, cédula, celular ni dirección exacta."""

    id: int
    nombre: str
    apellido: str
    ciudad: str
    latitud: float
    longitud: float
    foto_url: str | None = None

    class Config:
        from_attributes = True


class TrabajadorDestacado(BaseModel):
    """Trabajador con al menos un servicio activo publicado, para la sección
    "Trabajadores destacados" de la landing page. Datos siempre reales,
    nunca de ejemplo."""

    id: int
    nombre: str
    apellido: str
    ciudad: str
    foto_url: str | None = None
    oficio: str
    bio: str | None = None
    total_calificaciones: int = 0
    calificacion_promedio: float | None = None


class UsuarioAdmin(BaseModel):
    """Vista completa de un usuario, solo para el panel de administrador.
    Nunca se expone en ningún endpoint público."""

    id: int
    nombre: str
    apellido: str
    correo: EmailStr
    cedula: str
    celular: str
    ciudad: str
    direccion: str
    activo: bool
    id_rol: int
    nombre_rol: str

    class Config:
        from_attributes = True


class CrearUsuarioAdmin(BaseModel):
    """Para crear una cuenta desde el panel de administrador, con el rol que
    el propio admin elija (incluido Administrador). A diferencia del
    registro público, aquí no hay restricción de rol: quien usa este
    endpoint ya es un Administrador autenticado, así que no hay riesgo en
    dejarlo elegir el rol directamente."""

    nombre: str
    apellido: str
    correo: EmailStr
    contrasena: str = Field(min_length=8)
    cedula: str
    celular: str
    ciudad: str
    direccion: str = ""
    rol: str  # "Cliente" | "Trabajador" | "Administrador"


class LoginRequest(BaseModel):
    correo: EmailStr
    contrasena: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
