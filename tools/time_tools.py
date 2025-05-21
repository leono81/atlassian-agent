import datetime
from typing import Optional
from pydantic import BaseModel, Field
from config.settings import get_timezone

class CurrentDatetimeResponse(BaseModel):
    datetime_iso: str = Field(..., description="Fecha y hora actual en formato ISO 8601, con zona horaria.")
    timezone: str = Field(..., description="Zona horaria utilizada (IANA). Ejemplo: 'America/Buenos_Aires'.")

async def get_current_datetime() -> CurrentDatetimeResponse:
    """
    Devuelve la fecha y hora actual según la zona horaria configurada en TIMEZONE.
    Si TIMEZONE no está definida o es inválida, se usa UTC.
    """
    tz = get_timezone()
    now = datetime.datetime.now(tz)
    return CurrentDatetimeResponse(
        datetime_iso=now.isoformat(),
        timezone=str(tz)
    ) 