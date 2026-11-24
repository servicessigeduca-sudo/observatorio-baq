"""Lista única de barrios del área metropolitana, con códigos.

Se arma a partir de los límites publicados (data/publico/barrios.geojson), los
alias (data/barrios_alias.json) y los municipios fijados a mano
(data/barrios_municipio.json), y se publica en data/publico/barrios.csv para
que cualquier entidad pueda cruzar las cifras con sus propias bases.

Columnas:
- codigo: código del observatorio, estable mientras el nombre no cambie
  (código DANE del municipio + nombre sin tildes, p. ej. «08001-7-de-abril»).
- barrio, municipio, cod_municipio (DANE).
- alias: otras formas de escribir el barrio que el sitio reconoce, separadas por «;».
- limite: «POT» (capa oficial de Barranquilla), «OpenStreetMap», «aproximado» o «sin límite».
"""

from __future__ import annotations

import csv
import io
from collections import defaultdict

from .nombres_barrio import clave

DANE = {"Barranquilla": "08001", "Galapa": "08296", "Malambo": "08433", "Puerto Colombia": "08573", "Soledad": "08758"}
COLUMNAS = ["codigo", "barrio", "municipio", "cod_municipio", "alias", "limite"]


def codigo(barrio: str, municipio: str) -> str:
    return f"{DANE.get(municipio, '00000')}-{clave(barrio).replace(' ', '-')}"


def filas(geojson: dict, alias: dict[str, str] | None = None, fijos: dict[str, str] | None = None) -> list[dict]:
    otros = defaultdict(set)
    for k, v in (alias or {}).items():
        m, dato = k.split("|", 1)
        otros[(m, clave(v))].add(dato)
    salida, vistos = [], set()
    for f in geojson.get("features", []):
        p = f.get("properties", {})
        m, b = p.get("municipio"), p.get("barrio")
        if not m or not b or (m, clave(b)) in vistos:
            continue
        vistos.add((m, clave(b)))
        salida.append({
            "codigo": codigo(b, m), "barrio": b, "municipio": m, "cod_municipio": DANE.get(m, ""),
            "alias": ";".join(sorted(otros.get((m, clave(b)), set()))),
            "limite": "aproximado" if p.get("aprox") else ("POT" if m == "Barranquilla" else "OpenStreetMap"),
        })
    # Barrios que el equipo ubicó en un municipio pero que aún no tienen límite (p. ej. El Ferry).
    for b, m in (fijos or {}).items():
        if (m, clave(b)) not in vistos:
            vistos.add((m, clave(b)))
            salida.append({"codigo": codigo(b, m), "barrio": b, "municipio": m, "cod_municipio": DANE.get(m, ""),
                           "alias": ";".join(sorted(otros.get((m, clave(b)), set()))), "limite": "sin límite"})
    return sorted(salida, key=lambda r: (r["municipio"], clave(r["barrio"])))


def a_csv(lista: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNAS, lineterminator="\n")
    w.writeheader()
    w.writerows(lista)
    return buf.getvalue()
