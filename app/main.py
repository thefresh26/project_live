import traceback as traceback_module
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.crud import crud_error_log
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import (  # noqa: F401
    calificacion,
    denuncia_trabajador,
    email_verification_token,
    error_log,
    modulo,
    modulo_por_rol,
    pago,
    password_reset_token,
    reporte_formulario,
    rol,
    servicio,
    solicitud,
    usuario,
)
from app.models.categoria import Categoria

app = FastAPI(title="Plataforma de Servicios - API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origenes_permitidos,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def capturar_errores_no_controlados(request: Request, call_next):
    """Registra en la base de datos cualquier excepción no controlada que se
    escape de un endpoint, para que el administrador la vea en el panel
    (pestaña "Errores") sin depender de entrar al dashboard de Render. Si
    guardar el error también falla (por ejemplo la base de datos está caída),
    no deja que eso tumbe la respuesta original al cliente."""
    try:
        return await call_next(request)
    except Exception as exc:
        db = SessionLocal()
        try:
            crud_error_log.registrar(
                db,
                metodo=request.method,
                ruta=request.url.path,
                tipo_error=type(exc).__name__,
                mensaje=str(exc) or "(sin mensaje)",
                traceback=traceback_module.format_exc(),
            )
        except Exception:
            pass
        finally:
            db.close()
        return JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})

# Fotos de perfil subidas en el registro (ver app/core/uploads.py).
DIRECTORIO_STATIC = Path(__file__).resolve().parent / "static"
DIRECTORIO_STATIC.mkdir(parents=True, exist_ok=True)
(DIRECTORIO_STATIC / "fotos").mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=DIRECTORIO_STATIC), name="static")

# Frontend ya compilado (SvelteKit + adapter-static), copiado aquí como
# archivos estáticos listos. Así el backend sirve tanto la API como las
# páginas del sitio, en un solo servidor y un solo servicio en Render.
# Si esta carpeta no existe (por ejemplo, en desarrollo local si aún no se
# ha compilado el frontend), el backend sigue funcionando solo como API.
DIRECTORIO_FRONTEND = Path(__file__).resolve().parent / "frontend_dist"
FRONTEND_DISPONIBLE = (DIRECTORIO_FRONTEND / "index.html").is_file()

if FRONTEND_DISPONIBLE:
    # Los archivos compilados (JS/CSS con nombres únicos) que SvelteKit
    # referencia con rutas absolutas como "/_app/immutable/...".
    app.mount(
        "/_app",
        StaticFiles(directory=DIRECTORIO_FRONTEND / "_app"),
        name="frontend_assets",
    )


CATEGORIAS_INICIALES = [
    {"nombre": "Plomería", "icono": "plomeria", "descripcion": "Reparación de fugas, instalaciones y destape de tuberías"},
    {"nombre": "Electricidad", "icono": "electricidad", "descripcion": "Instalaciones y reparaciones eléctricas residenciales"},
    {"nombre": "Aseo y limpieza", "icono": "limpieza", "descripcion": "Limpieza de hogares, apartamentos y oficinas"},
    {"nombre": "Jardinería", "icono": "jardineria", "descripcion": "Mantenimiento de jardines y zonas verdes"},
    {"nombre": "Pintura", "icono": "pintura", "descripcion": "Pintura de interiores y exteriores"},
    {"nombre": "Mudanzas", "icono": "mudanzas", "descripcion": "Transporte y mudanzas de hogares y oficinas"},
    {"nombre": "Carpintería", "icono": "carpinteria", "descripcion": "Fabricación y reparación de muebles y estructuras en madera"},
    {"nombre": "Cerrajería", "icono": "cerrajeria", "descripcion": "Apertura, cambio e instalación de cerraduras y llaves"},
    {"nombre": "Albañilería", "icono": "albanileria", "descripcion": "Construcción, reparaciones y acabados en obra"},
    {"nombre": "Mecánica automotriz", "icono": "mecanica_auto", "descripcion": "Reparación y mantenimiento de automóviles"},
    {"nombre": "Mecánica de motos", "icono": "mecanica_motos", "descripcion": "Reparación y mantenimiento de motocicletas"},
    {"nombre": "Neveras y aires acondicionados", "icono": "refrigeracion", "descripcion": "Instalación y reparación de neveras y aires acondicionados"},
    {"nombre": "Instalación de gas", "icono": "gas", "descripcion": "Instalación y revisión de redes de gas domiciliario"},
    {"nombre": "Fumigación y control de plagas", "icono": "fumigacion", "descripcion": "Control de plagas en hogares y negocios"},
    {"nombre": "Niñera y cuidado infantil", "icono": "ninera", "descripcion": "Cuidado de niños en el hogar"},
    {"nombre": "Cuidado de adultos mayores", "icono": "cuidado_adultos", "descripcion": "Acompañamiento y cuidado de personas mayores"},
    {"nombre": "Cocina y catering", "icono": "cocina", "descripcion": "Preparación de alimentos para eventos y hogares"},
    {"nombre": "Costura y modistería", "icono": "costura", "descripcion": "Arreglos y confección de ropa"},
    {"nombre": "Peluquería y belleza a domicilio", "icono": "belleza", "descripcion": "Cortes, peinados y tratamientos de belleza a domicilio"},
    {"nombre": "Manicure y pedicure", "icono": "manicure", "descripcion": "Cuidado de uñas a domicilio"},
    {"nombre": "Masajes y spa a domicilio", "icono": "masajes", "descripcion": "Masajes y tratamientos de relajación a domicilio"},
    {"nombre": "Fotografía y video", "icono": "fotografia", "descripcion": "Cobertura fotográfica y de video para eventos"},
    {"nombre": "Diseño gráfico", "icono": "diseno_grafico", "descripcion": "Diseño de piezas gráficas y branding"},
    {"nombre": "Desarrollo web y software", "icono": "desarrollo_web", "descripcion": "Creación y mantenimiento de páginas web y aplicaciones"},
    {"nombre": "Clases particulares y tutorías", "icono": "tutorias", "descripcion": "Clases de refuerzo y tutorías personalizadas"},
    {"nombre": "Entrenador personal", "icono": "entrenador", "descripcion": "Rutinas de ejercicio y acompañamiento fitness"},
    {"nombre": "Paseador de mascotas", "icono": "paseador_mascotas", "descripcion": "Paseo y cuidado de mascotas"},
    {"nombre": "Peluquería canina", "icono": "peluqueria_canina", "descripcion": "Baño y corte de pelo para mascotas"},
    {"nombre": "Lavado de autos a domicilio", "icono": "lavado_autos", "descripcion": "Lavado y detallado de vehículos a domicilio"},
    {"nombre": "Instalación de pisos y cerámica", "icono": "pisos", "descripcion": "Instalación de pisos, baldosas y cerámica"},
    {"nombre": "Tapicería", "icono": "tapiceria", "descripcion": "Reparación y forrado de muebles"},
    {"nombre": "Vidriería y aluminio", "icono": "vidrieria", "descripcion": "Instalación de vidrios, ventanas y estructuras de aluminio"},
    {"nombre": "Techos e impermeabilización", "icono": "techos", "descripcion": "Reparación de techos y goteras"},
    {"nombre": "Soldadura y estructuras metálicas", "icono": "soldadura", "descripcion": "Trabajos en metal y estructuras soldadas"},
    {"nombre": "Instalación de cámaras de seguridad", "icono": "camaras_seguridad", "descripcion": "Instalación y configuración de cámaras de seguridad"},
    {"nombre": "Redes y cableado estructurado", "icono": "redes", "descripcion": "Instalación de redes de internet y cableado"},
    {"nombre": "Domicilios y mensajería", "icono": "mensajeria", "descripcion": "Entrega de paquetes y encargos"},
    {"nombre": "Transporte de carga", "icono": "transporte_carga", "descripcion": "Transporte de mercancía y mudanzas pequeñas"},
    {"nombre": "Eventos y decoración", "icono": "eventos", "descripcion": "Decoración y organización de eventos"},
    {"nombre": "Sonido e iluminación para eventos", "icono": "sonido", "descripcion": "Equipos de sonido e iluminación para fiestas y eventos"},
    {"nombre": "Reparación de electrodomésticos", "icono": "electrodomesticos", "descripcion": "Reparación de lavadoras, estufas y otros electrodomésticos"},
    {"nombre": "Reparación de celulares y computadores", "icono": "tecnologia", "descripcion": "Reparación de celulares, tablets y computadores"},
    {"nombre": "Traducción e idiomas", "icono": "traduccion", "descripcion": "Traducción de documentos y clases de idiomas"},
    {"nombre": "Trámites y contabilidad", "icono": "contabilidad", "descripcion": "Asesoría contable y gestión de trámites"},
    {"nombre": "Asesoría legal", "icono": "asesoria_legal", "descripcion": "Consultas y trámites legales"},
    {"nombre": "Arquitectura y diseño de interiores", "icono": "arquitectura", "descripcion": "Diseño y remodelación de espacios"},
]


@app.on_event("startup")
def crear_tablas():
    Base.metadata.create_all(bind=engine)
    # Migración manual y minima (sin Alembic): agrega la columna `activo`
    # a usuario si la tabla ya existia de antes de que existiera este campo.
    # Necesaria para el panel de admin (desactivar cuentas en vez de borrarlas).
    with engine.begin() as conexion:
        conexion.execute(
            text("ALTER TABLE usuario ADD COLUMN IF NOT EXISTS activo BOOLEAN NOT NULL DEFAULT TRUE")
        )
        # Estado de aprobación del formulario de trabajo. Los formularios que
        # ya existían antes de este cambio quedan "aprobado" (mantienen el
        # comportamiento que ya tenían: visibles al público); los formularios
        # nuevos siempre entran como "pendiente" (ver crud_servicio.crear).
        conexion.execute(
            text(
                "ALTER TABLE servicio ADD COLUMN IF NOT EXISTS estado VARCHAR NOT NULL DEFAULT 'aprobado'"
            )
        )
        conexion.execute(
            text("ALTER TABLE servicio ADD COLUMN IF NOT EXISTS motivo_rechazo VARCHAR")
        )
        # Cuentas que ya existían antes de este campo se consideran ya
        # verificadas (no las vamos a bloquear ni a fastidiar con un aviso
        # de verificación por algo que no existía cuando se registraron).
        # Las cuentas nuevas parten en False (ver Usuario.correo_verificado
        # y crud_usuario.registrar_trabajador).
        conexion.execute(
            text("ALTER TABLE usuario ADD COLUMN IF NOT EXISTS correo_verificado BOOLEAN NOT NULL DEFAULT TRUE")
        )
        # Solicitudes que ya existian antes del sistema de pagos quedan
        # "no completadas" (no se les puede cobrar retroactivamente).
        conexion.execute(
            text("ALTER TABLE solicitud ADD COLUMN IF NOT EXISTS completada BOOLEAN NOT NULL DEFAULT FALSE")
        )
        # Numero de Nequi / llave Bancolombia del trabajador (sistema de
        # pagos con transferencia directa). Opcional, no todos lo llenan.
        conexion.execute(
            text("ALTER TABLE usuario ADD COLUMN IF NOT EXISTS datos_pago VARCHAR")
        )
        # La tabla "pago" se creo con un intento anterior (pasarela Wompi)
        # donde "referencia" era obligatoria; ahora ya no se usa (pagos por
        # transferencia directa), asi que se relaja esa restriccion para que
        # los nuevos registros no fallen al no traer ese dato.
        conexion.execute(text("ALTER TABLE pago ALTER COLUMN referencia DROP NOT NULL"))

    # Siembra las categorías base la primera vez que arranca el backend,
    # para que el frontend no dependa de datos de ejemplo (contenido.js).
    # No se repite si ya existen (evita duplicados en cada reinicio).
    db = SessionLocal()
    try:
        if db.query(Categoria).count() == 0:
            for datos in CATEGORIAS_INICIALES:
                db.add(Categoria(**datos))
            db.commit()
    finally:
        db.close()


app.include_router(api_router, prefix="/api/v1")


if FRONTEND_DISPONIBLE:
    @app.get("/{ruta_completa:path}", include_in_schema=False)
    def servir_frontend(ruta_completa: str):
        """
        Sirve el frontend ya compilado (SPA). Si la ruta pedida coincide con
        un archivo real dentro de frontend_dist (por ejemplo "robots.txt" o
        "favicon.png"), lo devuelve tal cual. Para cualquier otra ruta (por
        ejemplo "/registro", o rutas futuras del panel de admin) devuelve
        siempre "index.html": el enrutador de SvelteKit, ya cargado en el
        navegador, decide qué mostrar. Esta función se registra al final,
        después de "/api/v1/..." y "/static/...", para no interferir con
        esas rutas.
        """
        base = DIRECTORIO_FRONTEND.resolve()
        archivo_pedido = (base / ruta_completa).resolve()

        # Evita que alguien pida algo como "../../.env" y se salga de la
        # carpeta del frontend compilado.
        if base not in archivo_pedido.parents and archivo_pedido != base:
            archivo_pedido = base / "index.html"

        if archivo_pedido.is_file():
            return FileResponse(archivo_pedido)
        return FileResponse(base / "index.html")
else:
    @app.get("/")
    def root():
        return {"status": "ok", "mensaje": "API de la plataforma de servicios"}
