from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db  # re-exported for convenience
from app.models.usuario import Usuario

__all__ = ["get_db", "get_current_usuario", "requerir_administrador"]

seguridad_bearer = HTTPBearer()


def get_current_usuario(
    credenciales: HTTPAuthorizationCredentials = Depends(seguridad_bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    credenciales_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar la sesión",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(credenciales.credentials)
        id_usuario = payload.get("sub")
        if id_usuario is None:
            raise credenciales_invalidas
    except Exception:
        raise credenciales_invalidas

    usuario = db.query(Usuario).filter(Usuario.id == int(id_usuario)).first()
    if usuario is None or not usuario.activo:
        raise credenciales_invalidas
    return usuario


def requerir_administrador(usuario: Usuario = Depends(get_current_usuario)) -> Usuario:
    """Para endpoints del panel de admin: solo pasa si el usuario tiene el rol Administrador."""
    if usuario.rol is None or usuario.rol.nombre != "Administrador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos de administrador",
        )
    return usuario
