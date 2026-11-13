"""Capa de homicidios (ArcGIS, GeoJSON) → conteos publicables.

El archivo original trae nombre de la víctima, dirección, hora y descripción
de los hechos. Nada de eso sale de aquí: solo se publican conteos por mes,
municipio, localidad, barrio, zona de cuadrícula fusionada, sexo y modalidad.
El archivo original nunca se guarda en el repositorio.
"""

from __future__ import annotations

import difflib
import json
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from scraper.clasificar import normalizar

from .cuadricula import DLAT, DLON, celda, zonas
from .limpieza import MUNICIPIOS, normalizar_municipio, normalizar_sexo

BOGOTA = timezone(timedelta(hours=-5))

MODALIDADES = {"sicariato": "Sicariato", "rina": "Riña", "por hurtarle": "Hurto", "hurto": "Hurto",
               "por establecer": "Por establecer"}
LOCALIDADES_BAQ = ["Riomar", "Norte-Centro Histórico", "Suroccidente", "Suroriente", "Metropolitana"]
_LOC_CLAVES = {normalizar(x).replace("-", " "): x for x in LOCALIDADES_BAQ}


def normalizar_modalidad_registro(texto: str | None) -> str:
    """Corrige errores de digitación ("SICARITO", "RILA", "RIÑAS"); un texto largo pegado en la columna queda "Sin dato"."""
    t = normalizar(str(texto or "")).strip()
    if not t or len(t) > 30:
        return "Sin dato"
    t = t.rstrip("s") if t.endswith("as") else t
    if t in MODALIDADES:
        return MODALIDADES[t]
    cerca = difflib.get_close_matches(t, list(MODALIDADES), n=1, cutoff=0.75)
    return MODALIDADES[cerca[0]] if cerca else "Sin dato"


def normalizar_sexo_registro(texto: str | None) -> str:
    t = normalizar(str(texto or "")).strip()
    if len(t) > 15:
        return "Sin dato"
    for nombre, valor in (("masculino", "Hombre"), ("femenino", "Mujer")):
        if t == nombre or difflib.SequenceMatcher(None, t, nombre).ratio() >= 0.8:
            return valor
    return normalizar_sexo(t)


def normalizar_localidad(texto: str | None, municipio: str) -> str:
    if municipio != "Barranquilla":
        return municipio
    t = normalizar(str(texto or "")).replace("-", " ").strip()
    t = t.replace("centri", "centro").replace("norte centro historico", "norte centro historico")
    if t in _LOC_CLAVES:
        return _LOC_CLAVES[t]
    if t.startswith("metr"):
        return "Metropolitana"
    cerca = difflib.get_close_matches(t, list(_LOC_CLAVES), n=1, cutoff=0.75)
    return _LOC_CLAVES[cerca[0]] if cerca else "Sin dato"


def nombre_barrio(texto: str | None) -> str | None:
    if not texto or not str(texto).strip():
        return None
    t = " ".join(str(texto).split()).title()
    for chico in (" De ", " Del ", " La ", " Las ", " Los ", " El ", " Y "):
        t = t.replace(chico, chico.lower())
    return t


def fecha_del_hecho(p: dict) -> tuple[date | None, str | None]:
    """Fecha del hecho (hora de Bogotá) y, si año o mes no coinciden con ella, el motivo."""
    ms = p.get("hora")
    f = datetime.fromtimestamp(ms / 1000, BOGOTA).date() if isinstance(ms, (int, float)) else None
    anio, mes = p.get("año"), p.get("mesennumero")
    if f is None:
        try:
            f = date(int(anio), int(mes), 1)
        except (TypeError, ValueError):
            return None, "sin_fecha"
        return f, "solo_mes"
    if anio != f.year or mes != f.month:
        return f, "anio_o_mes_inconsistente"
    return f, None


def procesar(geojson: dict, hoy: date | None = None) -> dict:
    hoy = hoy or datetime.now(BOGOTA).date()
    filas, alertas, fuera = [], Counter(), Counter()
    for feat in geojson.get("features", []):
        p = feat.get("properties") or {}
        muni = normalizar_municipio(p.get("municipio"))
        if muni not in MUNICIPIOS:
            fuera[p.get("municipio") or "sin municipio"] += 1
            continue
        f, alerta = fecha_del_hecho(p)
        if f is None or f > hoy:
            alertas["futura" if f else "sin_fecha"] += 1
            continue
        if alerta:
            alertas[alerta] += 1
        coords = (feat.get("geometry") or {}).get("coordinates") or [None, None]
        filas.append({
            "mes": f"{f.year:04d}-{f.month:02d}", "municipio": muni,
            "localidad": normalizar_localidad(p.get("localidad"), muni), "barrio": nombre_barrio(p.get("barrio")),
            "sexo": normalizar_sexo_registro(p.get("SEXO")), "modalidad": normalizar_modalidad_registro(p.get("MODALIDAD")),
            "lat": coords[1], "lon": coords[0], "fecha": f,
        })
    lista_zonas, de = zonas([(f["lat"], f["lon"]) for f in filas], prefijo="h")
    # Centro de barrio: promedio de los centros de celda de sus casos, solo si tiene 3 casos o más.
    por_barrio = defaultdict(list)
    for f in filas:
        if f["barrio"] and f["lat"] is not None:
            i, j = celda(f["lat"], f["lon"])
            por_barrio[(f["municipio"], f["barrio"])].append(((i + 0.5) * DLAT, (j + 0.5) * DLON))
    barrios = []
    for (m, b), pts in sorted(por_barrio.items()):
        centro = [round(sum(x for x, _ in pts) / len(pts), 3), round(sum(y for _, y in pts) / len(pts), 3)] if len(pts) >= 3 else None
        barrios.append({"municipio": m, "barrio": b, "centro": centro})
    conteo = Counter()
    for f, z in zip(filas, de):
        conteo[(f["mes"], f["municipio"], f["localidad"], f["barrio"] or "Sin barrio", z, f["sexo"], f["modalidad"])] += 1
    fechas = [f["fecha"] for f in filas]
    return {
        "fuente": "Capa de homicidios 2026 (ArcGIS), con autorización de uso del propietario",
        "corte": max(fechas).isoformat() if fechas else None,
        "desde": min(fechas).isoformat() if fechas else None,
        "columnas": ["mes", "municipio", "localidad", "barrio", "zona", "sexo", "modalidad", "casos"],
        "filas": [list(k) + [n] for k, n in sorted(conteo.items(), key=lambda x: tuple(str(v) for v in x[0]))],
        "zonas": lista_zonas,
        "barrios": barrios,
        "calidad": {"registros": len(geojson.get("features", [])), "en_el_area": len(filas),
                    "fuera_del_area": sum(fuera.values()), "alertas_fecha": dict(alertas)},
    }


def leer(ruta: Path) -> dict:
    return json.loads(Path(ruta).read_text(encoding="utf-8"))
