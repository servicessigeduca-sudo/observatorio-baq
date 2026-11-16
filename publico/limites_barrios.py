"""Límites de barrios del área metropolitana: POT de Barranquilla + OpenStreetMap.

Uso:
    python -m publico.limites_barrios           # descarga OSM y escribe data/publico/barrios.geojson
    python -m publico.limites_barrios --sin-red # solo rehace Barranquilla con el POT y los alias

Barranquilla usa la capa oficial «Barrios de Barranquilla según POT» (Alcaldía,
datos.gov.co), guardada simplificada en data/barrios_pot.geojson. Los otros cuatro
municipios usan OpenStreetMap.

Toma, en este orden de preferencia, los límites administrativos de barrio
(admin_level 9 o 10), las áreas marcadas como barrio o sector (place=neighbourhood,
suburb o quarter) y las urbanizaciones con nombre (landuse=residential). Cada
polígono se asigna al municipio que contiene su punto interior; los que caen fuera
de los cinco municipios se descartan. La geometría se simplifica (~4 m) para que
el archivo pese poco.

Los nombres de OSM no siempre coinciden con los del registro o la prensa. En
data/barrios_alias.json se puede escribir {"Municipio|Nombre en los datos":
"Nombre en OSM"} para unirlos a mano. Datos © colaboradores de OpenStreetMap, ODbL.
"""

from __future__ import annotations

import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import requests
from shapely.geometry import LineString, Polygon, mapping, shape
from shapely.ops import linemerge, polygonize, unary_union

from scraper.clasificar import normalizar

URLS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
AGENTE = "ObservatorioBAQ/0.1 (+https://github.com/servicessigeduca-sudo/observatorio-baq)"
CAJA = "10.80,-74.99,11.13,-74.68"  # sur, oeste, norte, este
MUNICIPIOS = ["Barranquilla", "Soledad", "Malambo", "Galapa", "Puerto Colombia"]
CONSULTA = f"""[out:json][timeout:240];
(
  relation["boundary"="administrative"]["admin_level"~"^(6|7)$"]({CAJA});
  relation["boundary"="administrative"]["admin_level"~"^(9|10)$"]({CAJA});
  way["boundary"="administrative"]["admin_level"~"^(9|10)$"]({CAJA});
  way["place"~"^(neighbourhood|suburb|quarter)$"]({CAJA});
  relation["place"~"^(neighbourhood|suburb|quarter)$"]({CAJA});
  way["landuse"="residential"]["name"]({CAJA});
  relation["landuse"="residential"]["name"]({CAJA});
);
out geom;"""
AREA_MIN_KM2, AREA_MAX_KM2 = 0.004, 6.0
KM2_POR_GRADO2 = 111.32 * 109.3  # a 11° N
PREFIJOS = re.compile(r"^(barrio|urbanizacion|urb|conjunto residencial|conjunto|ciudadela|sector|asentamiento)\s+")


def clave(nombre: str) -> str:
    """Igual que claveBarrio() en web/mapa.html: sin tildes, sin signos y sin «barrio», «urbanización»…"""
    t = re.sub(r"[^a-z0-9ñ]+", " ", normalizar(nombre)).strip()
    t = PREFIJOS.sub("", t)
    return re.sub(r"\s+", " ", t)


def geometria(el: dict):
    if el["type"] == "way":
        pts = [(p["lon"], p["lat"]) for p in el.get("geometry", [])]
        return Polygon(pts) if len(pts) >= 4 and pts[0] == pts[-1] else None
    externos, internos = [], []
    for m in el.get("members", []):
        if m.get("type") != "way" or not m.get("geometry"):
            continue
        (internos if m.get("role") == "inner" else externos).append(LineString([(p["lon"], p["lat"]) for p in m["geometry"]]))
    if not externos:
        return None
    g = unary_union(list(polygonize(linemerge(externos))))
    if internos:
        g = g.difference(unary_union(list(polygonize(linemerge(internos)))))
    return None if g.is_empty else g


def descargar() -> dict:
    for intento, url in enumerate(URLS * 2):
        try:
            r = requests.post(url, data={"data": CONSULTA}, headers={"User-Agent": AGENTE}, timeout=300)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            print(f"Overpass falló ({url}): {e}", file=sys.stderr)
            time.sleep(20 * (intento + 1))
    raise SystemExit("No se pudo descargar de Overpass")


def construir(datos: dict, alias: dict[str, str] | None = None) -> dict:
    munis = {}
    candidatos = []
    for el in datos.get("elements", []):
        t = el.get("tags", {})
        nombre = (t.get("name") or "").strip()
        if not nombre:
            continue
        nivel = t.get("admin_level")
        if t.get("boundary") == "administrative" and nivel in ("6", "7"):
            m = next((x for x in MUNICIPIOS if normalizar(x) == normalizar(nombre)), None)
            g = geometria(el) if m else None
            if g is not None and (m not in munis or g.area > munis[m].area):
                munis[m] = g
            continue
        prioridad = 0 if t.get("boundary") == "administrative" else 1 if t.get("place") else 2
        g = geometria(el)
        if g is None or not g.is_valid and (g := g.buffer(0)).is_empty:
            continue
        km2 = g.area * KM2_POR_GRADO2
        if AREA_MIN_KM2 <= km2 <= AREA_MAX_KM2:
            candidatos.append((prioridad, nombre, g))
    grupos = defaultdict(list)
    for prioridad, nombre, g in candidatos:
        p = g.representative_point()
        m = next((x for x, mg in munis.items() if mg.contains(p)), None)
        if m:
            grupos[(m, clave(nombre))].append((prioridad, nombre, g))
    otros = defaultdict(list)
    for k, v in (alias or {}).items():
        m, nombre = k.split("|", 1)
        otros[(m, clave(v))].append(clave(nombre))
    feats = []
    for (m, k), lista in sorted(grupos.items()):
        mejor = min(p for p, _, _ in lista)
        g = unary_union([g for p, _, g in lista if p == mejor]).simplify(0.00004, preserve_topology=True)
        nombre = next(n for p, n, _ in lista if p == mejor)
        geo = json.loads(json.dumps(mapping(g)), parse_float=lambda x: round(float(x), 5))
        feats.append({"type": "Feature", "properties": {"barrio": nombre, "municipio": m, "clave": k, "otros": otros.get((m, k), [])},
                      "geometry": geo})
    return {"type": "FeatureCollection", "fuente": "© colaboradores de OpenStreetMap (ODbL), vía Overpass",
            "generado": time.strftime("%Y-%m-%d"), "municipios": sorted(munis), "features": feats}


MINUSCULAS = {"de", "del", "la", "las", "los", "el", "y", "e"}


def titulo(nombre: str) -> str:
    """«VILLA SAN PEDRO II» → «Villa San Pedro II»."""
    pal = nombre.strip().split()
    out = []
    for i, w in enumerate(pal):
        lw = w.lower()
        if re.fullmatch(r"[ivx]+", lw):
            out.append(w.upper())
        elif i and lw in MINUSCULAS:
            out.append(lw)
        else:
            out.append(lw[:1].upper() + lw[1:])
    return " ".join(out)


def con_pot(fc: dict, pot: dict, alias: dict[str, str] | None = None) -> dict:
    """Reemplaza los barrios de Barranquilla por los del POT (la capa oficial)."""
    otros = defaultdict(list)
    for k, v in (alias or {}).items():
        m, nombre = k.split("|", 1)
        if m == "Barranquilla":
            otros[clave(v)].append(clave(nombre))
    feats = [f for f in fc["features"] if f["properties"]["municipio"] != "Barranquilla"]
    vistos = set()
    for f in pot["features"]:
        nombre = titulo(f["properties"]["nombre"])
        k = clave(nombre)
        if k in vistos:
            continue
        vistos.add(k)
        feats.append({"type": "Feature", "properties": {"barrio": nombre, "municipio": "Barranquilla", "clave": k, "otros": otros.get(k, [])},
                      "geometry": f["geometry"]})
    feats.sort(key=lambda f: (f["properties"]["municipio"], f["properties"]["clave"]))
    return {**fc, "fuente": "Barranquilla: Barrios según POT (Alcaldía de Barranquilla, datos.gov.co). "
                            "Soledad, Malambo, Galapa y Puerto Colombia: © colaboradores de OpenStreetMap (ODbL).",
            "municipios": sorted(set(fc.get("municipios", [])) | {"Barranquilla"}), "features": feats}


def cobertura(fc: dict, raiz: Path) -> tuple[int, int, list[str]]:
    """Cuántos barrios del registro (con casos) tienen polígono."""
    claves = {(f["properties"]["municipio"], c) for f in fc["features"] for c in [f["properties"]["clave"], *f["properties"]["otros"]]}
    ruta = raiz / "data" / "publico" / "registro.json"
    if not ruta.exists():
        return 0, 0, []
    por = defaultdict(int)
    for f in json.loads(ruta.read_text(encoding="utf-8"))["filas"]:
        if f[3] != "Sin barrio":
            por[(f[1], f[3])] += f[7]
    con = [k for k in por if (k[0], clave(k[1])) in claves]
    faltan = sorted(por, key=lambda k: -por[k])
    faltan = [f"{b} ({m}): {por[(m, b)]}" for m, b in faltan if (m, b) not in con]
    return sum(por[k] for k in con), sum(por.values()), faltan


def main() -> int:
    raiz = Path(".")
    ruta_alias = raiz / "data" / "barrios_alias.json"
    alias = json.loads(ruta_alias.read_text(encoding="utf-8")) if ruta_alias.exists() else {}
    destino = raiz / "data" / "publico" / "barrios.geojson"
    if "--sin-red" in sys.argv[1:]:
        fc = json.loads(destino.read_text(encoding="utf-8"))
    else:
        fc = construir(descargar(), alias)
    ruta_pot = raiz / "data" / "barrios_pot.geojson"
    if ruta_pot.exists():
        fc = con_pot(fc, json.loads(ruta_pot.read_text(encoding="utf-8")), alias)
    destino.write_text(json.dumps(fc, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    con, total, faltan = cobertura(fc, raiz)
    print(f"{len(fc['features'])} barrios con límite en {', '.join(fc['municipios'])} ({destino.stat().st_size // 1024} KB).")
    if total:
        print(f"\nHomicidios del registro en barrios con límite: {con} de {total} ({100 * con / total:.0f} %).")
        print("\nBarrios del registro sin límite (agregar en data/barrios_alias.json si OSM lo tiene con otro nombre):\n")
        print("\n".join(f"- {x}" for x in faltan[:80]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
