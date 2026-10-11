"""Envío de correos vía la API HTTP de Resend (https://resend.com).

Se usa `urllib` de la librería estándar en vez de agregar una dependencia
nueva (httpx/requests): es una sola llamada HTTP simple y así no hay que
tocar requirements.txt ni preocuparse por versiones.

Si RESEND_API_KEY no está configurada (todavía no se creó la cuenta de
Resend), esto no revienta el flujo que lo llama: registra el problema como
un error del sistema (visible en la pestaña "Errores" del panel de admin)
y devuelve False, para que quien llama decida qué hacer (normalmente:
nada, porque por seguridad "olvidé mi contraseña" siempre responde igual
sin importar si el correo se pudo enviar o no)."""

import json
import urllib.error
import urllib.request

from app.core.config import settings


def enviar_correo(destinatario: str, asunto: str, html: str) -> bool:
    if not settings.resend_api_key:
        raise RuntimeError(
            "RESEND_API_KEY no está configurada: no se pudo enviar el correo "
            f"'{asunto}' a {destinatario}. Crea una cuenta gratis en resend.com, "
            "genera una API key, y agrégala como RESEND_API_KEY en el .env."
        )

    cuerpo = json.dumps(
        {
            "from": settings.correo_remitente,
            "to": [destinatario],
            "subject": asunto,
            "html": html,
        }
    ).encode("utf-8")

    solicitud = urllib.request.Request(
        "https://api.resend.com/emails",
        data=cuerpo,
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
            # Sin User-Agent propio, Cloudflare (delante de Resend) rechaza con 403 / código 1010
            # el "Python-urllib" por defecto.
            "User-Agent": "voz-profesional/1.0",
        },
    )
    try:
        with urllib.request.urlopen(solicitud, timeout=10) as respuesta:
            return 200 <= respuesta.status < 300
    except urllib.error.HTTPError as exc:
        detalle = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Resend respondió {exc.code} al enviar a {destinatario}: {detalle}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"No se pudo conectar con Resend para enviar a {destinatario}: {exc}") from exc
