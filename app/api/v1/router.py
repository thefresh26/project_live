from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    auth,
    calificaciones,
    categorias,
    denuncias,
    servicios,
    solicitudes,
    trabajadores,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(trabajadores.router)
api_router.include_router(categorias.router)
api_router.include_router(servicios.router)
api_router.include_router(calificaciones.router)
api_router.include_router(solicitudes.router)
api_router.include_router(denuncias.router)
api_router.include_router(admin.router)
