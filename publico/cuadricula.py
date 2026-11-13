"""Cuadrícula de ~400 m y fusión de celdas con pocos casos.

Una celda con menos de 3 casos podría señalar un hecho puntual. Antes de
publicar, cada celda pequeña se une con la celda vecina que tenga menos casos
(así no se diluyen las zonas con más casos) hasta que el grupo llega a 3. Si
una celda no tiene vecinas con casos a menos de 1,2 km, no se publica en la
cuadrícula: sigue contando en las cifras del barrio y del municipio.

La misma regla está en web/datos.js para que el mapa la aplique con filtros.
"""

from __future__ import annotations

import math

TAMANO_M = 400
LAT0 = 10.97  # latitud de referencia del área metropolitana
M_POR_GRADO_LAT = 111_320
DLAT = TAMANO_M / M_POR_GRADO_LAT
DLON = TAMANO_M / (M_POR_GRADO_LAT * math.cos(math.radians(LAT0)))
MINIMO = 3
ALCANCE = 3  # celdas (1,2 km) para buscar vecinas de una celda aislada


def celda(lat: float, lon: float) -> tuple[int, int]:
    return (math.floor(lat / DLAT), math.floor(lon / DLON))


def limites(i: int, j: int) -> list[list[float]]:
    """[[sur, oeste], [norte, este]] de la celda."""
    return [[round(i * DLAT, 6), round(j * DLON, 6)], [round((i + 1) * DLAT, 6), round((j + 1) * DLON, 6)]]


def _dist(a: list[tuple[int, int]], b: list[tuple[int, int]]) -> int:
    return min(max(abs(x[0] - y[0]), abs(x[1] - y[1])) for x in a for y in b)


def fusionar(conteos: dict[tuple[int, int], int], minimo: int = MINIMO) -> tuple[list[dict], int]:
    """Agrupa celdas hasta que cada grupo tenga al menos `minimo` casos.

    Devuelve (grupos, casos_sin_publicar). Cada grupo: {"celdas": [(i, j), ...], "n": int}.
    """
    grupos = [{"celdas": [k], "n": n} for k, n in sorted(conteos.items()) if n > 0]
    ocultos = 0
    while True:
        chicos = [g for g in grupos if g["n"] < minimo]
        if not chicos:
            break
        g = min(chicos, key=lambda x: (x["n"], x["celdas"]))
        otros = [o for o in grupos if o is not g]
        vecinos = []
        for alcance in (1, ALCANCE):
            vecinos = [o for o in otros if _dist(g["celdas"], o["celdas"]) <= alcance]
            if vecinos:
                break
        grupos.remove(g)
        if not vecinos:
            ocultos += g["n"]
            continue
        v = min(vecinos, key=lambda o: (o["n"], _dist(g["celdas"], o["celdas"]), o["celdas"]))
        v["celdas"] = sorted(v["celdas"] + g["celdas"])
        v["n"] += g["n"]
    grupos.sort(key=lambda x: (-x["n"], x["celdas"]))
    return grupos, ocultos


def zonas(puntos: list[tuple[float, float]], minimo: int = MINIMO, prefijo: str = "z") -> tuple[list[dict], list[str | None]]:
    """Asigna cada punto a una zona publicable (grupo de celdas con al menos `minimo` puntos).

    Devuelve (zonas, zona_de_cada_punto). Cada zona: {"id", "n", "celdas", "centro": [lat, lon]}.
    El centro es el de las celdas, no el de los puntos, para no revelar ubicaciones.
    Un punto en una celda aislada queda con zona None.
    """
    conteo: dict[tuple[int, int], int] = {}
    celdas_pt = []
    for lat, lon in puntos:
        c = celda(lat, lon) if lat is not None and lon is not None else None
        celdas_pt.append(c)
        if c:
            conteo[c] = conteo.get(c, 0) + 1
    grupos, _ = fusionar(conteo, minimo)
    de_celda: dict[tuple[int, int], str] = {}
    salida = []
    for k, g in enumerate(grupos, 1):
        zid = f"{prefijo}{k:03d}"
        for c in g["celdas"]:
            de_celda[c] = zid
        lat = sum((i + 0.5) * DLAT for i, _ in g["celdas"]) / len(g["celdas"])
        lon = sum((j + 0.5) * DLON for _, j in g["celdas"]) / len(g["celdas"])
        salida.append({"id": zid, "n": g["n"], "celdas": [list(c) for c in g["celdas"]], "centro": [round(lat, 5), round(lon, 5)]})
    return salida, [de_celda.get(c) if c else None for c in celdas_pt]
