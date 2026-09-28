from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    access_token_expire_minutes: int = 60
    algorithm: str = "HS256"

    # URLs del frontend que pueden llamar a esta API (CORS). En local es
    # Vite (5173); en producción, agrega aquí la URL real que te dé Render
    # separando varias con comas si algún día hay más de un frontend, por
    # ejemplo: FRONTEND_URL=https://manosya.onrender.com
    frontend_url: str = "http://localhost:5173"

    # Envío de correos (recuperar contraseña, notificaciones) vía Resend.
    # Vacío hasta que se cree la cuenta en resend.com y se agregue la key
    # real; mientras tanto, ver app/core/email.py (falla explícito, no
    # silencioso, y queda registrado en la pestaña "Errores" del admin).
    resend_api_key: str = ""
    correo_remitente: str = "Voz Profesional <onboarding@resend.dev>"


    class Config:
        env_file = ".env"

    @property
    def origenes_permitidos(self) -> list[str]:
        return [url.strip() for url in self.frontend_url.split(",") if url.strip()]

    @property
    def frontend_url_principal(self) -> str:
        """La primera URL de frontend_url, para construir enlaces (por
        ejemplo el de restablecer contraseña) cuando hay varias separadas
        por comas."""
        return self.origenes_permitidos[0] if self.origenes_permitidos else "http://localhost:5173"


settings = Settings()
