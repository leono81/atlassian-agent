import dateparser
from datetime import datetime

def parse_relative_date(text, base_date=None, timezone=None):
    """
    Interpreta una fecha relativa (ej: 'el lunes que viene') respecto a base_date.
    Devuelve un datetime.date o None si no puede interpretarla.
    """
    settings = {'PREFER_DATES_FROM': 'future'}
    if timezone:
        settings['TIMEZONE'] = timezone
        settings['RETURN_AS_TIMEZONE_AWARE'] = True
    if base_date is None:
        base_date = datetime.now()
    dt = dateparser.parse(text, settings=settings, languages=['es', 'en'], relative_base=base_date)
    return dt.date() if dt else None

def get_weekday_name(date_obj):
    """
    Devuelve el nombre del día de la semana para una fecha dada.
    """
    dias = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
    return dias[date_obj.weekday()] 