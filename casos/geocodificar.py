"""Ubica cada caso en el mapa a partir de su barrio, con Nominatim (OpenStreetMap).

Reglas de uso de Nominatim: máximo una consulta por segundo, user-agent propio
y caché local. Cada barrio se consulta una sola vez; el resultado (o la falta
de resultado) queda en data/geocodigos.json, que el equipo puede corregir a mano.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import requests

from scraper.clasificar import normalizar

log = logging.getLogger(__name__)

URL = "https://nominatim.openstreetmap.org/search"
AGENTE = "ObservatorioBAQ/0.1 (+https://github.com/servicessigeduca-sudo/observatorio-baq)"
# Caja del área metropolitana: oeste, norte, este, sur.
CAJA = "-74.98,11.13,-74.70,10.82"
CENTROS_MUNICIPIO = {
    "Barranquilla": (10.9685, -74.7813),
    "Soledad": (10.9184, -74.7646),
    "Malambo": (10.8597, -74.7739),
    "Galapa": (10.8984, -74.8862),
    "Puerto Colombia": (10.9877, -74.9547),
}


def clave(barrio: str, municipio: str | None) -> str:
    return f"{normalizar(barrio)}|{municipio or 'Barranquilla'}"


def consultar(barrio: str, municipio: str | None, sesion: requests.Session) -> dict | None:
    q = f"{barrio}, {municipio or 'Barranquilla'}, Atlántico, Colombia"
    r = sesion.get(URL, params={"q": q, "format": "jsonv2", "limit": 1, "countrycodes": "co",
                                "viewbox": CAJA, "bounded": 1}, timeout=30)
    r.raise_for_status()
    res = r.json()
    if not res:
        return None
    return {"lat": round(float(res[0]["lat"]), 5), "lon": round(float(res[0]["lon"]), 5),
            "nombre_osm": res[0].get("display_name", "")[:120]}


def geocodificar(casos: list[dict], cache_ruta: Path, consultar_red: bool = True, pausa: float = 1.1) -> int:
    """Agrega lat, lon y confianza_ubicacion a cada caso. Devuelve cuántas consultas hizo."""
    cache = json.loads(cache_ruta.read_text(encoding="utf-8")) if cache_ruta.exists() else {}
    sesion = requests.Session()
    sesion.headers["User-Agent"] = AGENTE
    consultas = 0
    for c in casos:
        c["lat"] = c["lon"] = None
        c["confianza_ubicacion"] = "baja"
        if c.get("barrio"):
            k = clave(c["barrio"], c.get("municipio"))
            if k not in cache and consultar_red:
                try:
                    cache[k] = consultar(c["barrio"], c.get("municipio"), sesion)
                except requests.RequestException as e:
                    log.warning("Nominatim falló para %s: %s", k, e)
                    continue
                consultas += 1
                time.sleep(pausa)
            pos = cache.get(k)
            if pos:
                c["lat"], c["lon"] = pos["lat"], pos["lon"]
                c["confianza_ubicacion"] = "alta"
                continue
        centro = CENTROS_MUNICIPIO.get(c.get("municipio") or "")
        if centro:
            c["confianza_ubicacion"] = "municipio"
    cache_ruta.parent.mkdir(parents=True, exist_ok=True)
    cache_ruta.write_text(json.dumps(dict(sorted(cache.items())), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return consultas
