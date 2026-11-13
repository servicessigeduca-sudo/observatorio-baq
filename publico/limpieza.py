"""Limpieza automática de los datos antes de publicarlos.

- Municipios mal escritos ("Barranquila", "Pto. Colombia") pasan a su nombre oficial.
- Sexo y modalidad (arma o medio) se agrupan en pocas categorías estables.
- Los años se validan y las fechas imposibles (futuras, anteriores a la nota
  que las reporta) se marcan para que el editor las revise. No se borran.
"""

from __future__ import annotations

import difflib
import re
from datetime import date, datetime

from scraper.clasificar import normalizar

MUNICIPIOS = ["Barranquilla", "Soledad", "Malambo", "Galapa", "Puerto Colombia"]

_ALIAS = {
    "b/quilla": "Barranquilla", "bquilla": "Barranquilla", "baq": "Barranquilla", "barranquila": "Barranquilla",
    "barraquilla": "Barranquilla", "quilla": "Barranquilla", "distrito de barranquilla": "Barranquilla",
    "pto colombia": "Puerto Colombia", "pto. colombia": "Puerto Colombia", "puertocolombia": "Puerto Colombia",
    "pto colombi": "Puerto Colombia",
}
_RUIDO = re.compile(r"\b(municipio de|distrito de|atlantico|atl\.?)\b|,? colombia$")


def normalizar_municipio(texto: str | None) -> str | None:
    """Devuelve el nombre oficial del municipio del área, o None si no es del área."""
    if not texto or not str(texto).strip():
        return None
    t = normalizar(str(texto)).strip()
    claves = {normalizar(m): m for m in MUNICIPIOS}
    if t in _ALIAS:
        return _ALIAS[t]
    if t in claves:
        return claves[t]
    t = _RUIDO.sub(" ", t.replace(",", " ")).strip(" .-")
    t = re.sub(r"\s+", " ", t)
    if t in _ALIAS:
        return _ALIAS[t]
    if t in claves:
        return claves[t]
    for k, m in claves.items():  # "soledad 2000" sigue siendo Soledad
        if t.startswith(k + " "):
            return m
    cerca = difflib.get_close_matches(t, list(claves), n=1, cutoff=0.8)
    return claves[cerca[0]] if cerca else None


def normalizar_sexo(texto: str | None) -> str:
    t = normalizar(str(texto or "")).strip()
    if t in {"femenino", "mujer", "f", "fem"}:
        return "Mujer"
    if t in {"masculino", "hombre", "m", "masc"}:
        return "Hombre"
    return "Sin dato"


def normalizar_modalidad(texto: str | None) -> str:
    """Agrupa el arma o medio en categorías comparables entre años."""
    t = normalizar(str(texto or "")).strip()
    if not t or t.startswith("no report") or t in {"no registra", "no reporta", "sin dato", "-"}:
        return "Sin dato"
    if "traumatica" in t:
        return "Otra"
    if "fuego" in t:
        return "Arma de fuego"
    if any(k in t for k in ("blanca", "cortopunz", "cortante", "punzante")):
        return "Arma blanca"
    if "contundent" in t:
        return "Contundente"
    if "sin empleo" in t:
        return "Sin arma"
    return "Otra"


# Palabras clave para deducir la modalidad de un caso de prensa a partir del titular.
_FUEGO = re.compile(r"\b(bala|balead|baleo|balacera|tiros?|disparo|dispar|sicari|arma de fuego|pistol|revolver|escopeta)")
_BLANCA = re.compile(r"\b(cuchill|apunal|punal|machete|arma blanca|herida con arma blanca|navaja|chuzo)")


def modalidad_de_texto(texto: str | None) -> str:
    t = normalizar(texto or "")
    if _FUEGO.search(t):
        return "Arma de fuego"
    if _BLANCA.search(t):
        return "Arma blanca"
    return "Sin dato"


def anio_valido(anio, minimo: int = 2003, hoy: date | None = None) -> bool:
    hoy = hoy or date.today()
    try:
        a = int(anio)
    except (TypeError, ValueError):
        return False
    return minimo <= a <= hoy.year


def revisar_fecha(fecha: str | None, publicada: str | None = None, hoy: date | None = None) -> str | None:
    """None si la fecha es razonable; si no, el motivo para que el editor la revise."""
    hoy = hoy or date.today()
    if not fecha:
        return "sin_fecha"
    try:
        f = date.fromisoformat(str(fecha)[:10])
    except ValueError:
        return "invalida"
    if f > hoy:
        return "futura"
    if f.year < 2000:
        return "anio_invalido"
    if publicada:
        try:
            p = datetime.fromisoformat(str(publicada)).date()
        except ValueError:
            p = None
        if p and f > p:
            return "posterior_a_la_nota"
    return None
