"""Uso: python -m oficiales.manual [--salida data/oficiales.json]

Completa los datos oficiales con consultas descargadas a mano del portal de
SIEDCO (Policía Nacional) y guardadas en data/siedco/*.xlsx. Esas consultas
traen conteos por año, mes, municipio, arma, edad, género y día de la semana,
sin fecha exacta.

Solo llenan los años y delitos que no traen los archivos públicos (por ejemplo,
homicidios de 2003 a 2009, 2014 y 2018). Donde los dos existen se usa el
archivo público; en los años que coinciden, las cifras son iguales.

`python -m oficiales` llama a `completar` en cada corrida mensual. Este comando
sirve para aplicar un archivo nuevo sin volver a descargar todo.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import pandas as pd

from .procesar import MUNICIPIOS, _col, _dane, _limpio, _nativo, categoria, normal

CARPETA = Path("data/siedco")
MESES = {m: i for i, m in enumerate(["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO",
                                      "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"], 1)}
DIAS = {"LUN": 0, "MAR": 1, "MIE": 2, "JUE": 3, "VIE": 4, "SAB": 5, "DOM": 6}


def leer(ruta) -> pd.DataFrame:
    df = pd.read_excel(ruta, dtype=str)
    df.columns = [normal(c) for c in df.columns]
    return df


def agregar(df: pd.DataFrame) -> dict[str, Counter]:
    """Mismas tablas que procesar.agregar, a partir de una consulta de SIEDCO."""
    df = df.copy()
    df["DANE"] = _dane(df[_col(df, "CODIGO DANE")])
    df = df[df["DANE"].isin(MUNICIPIOS)].copy()
    df["N"] = pd.to_numeric(df[_col(df, "CANTIDAD")], errors="coerce").fillna(0).astype(int)
    df["anio"] = pd.to_numeric(df[_col(df, "ANO")], errors="coerce")
    df["mes"] = df[_col(df, "MES")].map(lambda m: MESES.get(normal(m)))
    df = df[df["anio"].notna() & df["mes"].notna()].copy()
    df["anio"], df["mes"] = df["anio"].astype(int), df["mes"].astype(int)
    df["muni"] = df["DANE"].map(MUNICIPIOS)
    df["cat"] = df[_col(df, "TEMATICA", "DELITO")].map(categoria)
    df["dia"] = df[_col(df, "DIA")].map(lambda d: DIAS.get(normal(d)[:3], -1))
    col_arma, col_gen, col_edad = _col(df, "ARMA"), _col(df, "GENERO"), _col(df, "EDAD")
    df["arma"] = _limpio(df[col_arma], "NO REPORTADO") if col_arma else "NO REPORTADO"
    df["genero"] = _limpio(df[col_gen], "NO REPORTADO") if col_gen else "NO REPORTADO"
    df["edad"] = _limpio(df[col_edad], "NO REPORTADO") if col_edad else "NO REPORTADO"

    def contar(d, claves):
        return Counter({tuple(_nativo(v) for v in k): int(n) for k, n in d.groupby(claves)["N"].sum().items()})

    return {
        "mensual": contar(df, ["anio", "mes", "muni", "cat"]),
        "armas": contar(df, ["anio", "muni", "cat", "arma"]),
        "dias": contar(df[df["dia"] >= 0], ["anio", "mes", "muni", "cat", "dia"]),
        "genero": contar(df, ["anio", "muni", "cat", "genero"]),
        "edad": contar(df, ["anio", "muni", "cat", "edad"]),
    }


def _anio_cat(nombre: str, clave: tuple) -> tuple[int, str]:
    # mensual y dias: (anio, mes, muni, cat, ...); las demás: (anio, muni, cat, ...)
    return clave[0], clave[3] if nombre in ("mensual", "dias") else clave[2]


def completar(tablas: dict[str, Counter], cobertura: set, carpeta: Path = CARPETA) -> list[str]:
    """Suma a `tablas` los años y delitos que faltan. Devuelve los archivos usados.

    Primero junta todos los archivos, porque una categoría puede venir en varios
    (tránsito: muertes y lesiones). Si dos archivos traen el mismo delito, se usa
    solo el primero para no contarlo dos veces.
    """
    juntas: dict[str, Counter] = {}
    usados, vistos = [], {}
    for ruta in sorted(carpeta.glob("*.xlsx")):
        df = leer(ruta)
        delitos = frozenset(df[_col(df, "TEMATICA", "DELITO")].dropna().map(normal))
        if delitos in vistos:
            print(f"SIEDCO manual · {ruta.name}: trae los mismos delitos que {vistos[delitos]}; se omite")
            continue
        vistos[delitos] = ruta.name
        for k, c in agregar(df).items():
            juntas.setdefault(k, Counter()).update(c)
        usados.append(ruta.as_posix())
    if not juntas:
        return []
    meses = Counter((k[0], k[3]) for k in juntas["mensual"])
    ultimo = max(a for a, _ in meses)
    # Solo años completos: un año en curso a medias no reemplaza nada.
    nuevos = {ac for ac, n in meses.items() if (n == 12 or ac[0] < ultimo) and ac not in cobertura}
    for nombre, c in juntas.items():
        for k, n in c.items():
            if _anio_cat(nombre, k) in nuevos:
                tablas[nombre][k] += n
    cobertura |= nuevos
    for cat in sorted({c for _, c in nuevos}):
        print(f"SIEDCO manual · {cat}: agrega {sorted(a for a, c in nuevos if c == cat)}")
    return usados if nuevos else []


def main(argv: list[str] | None = None) -> int:
    from .__main__ import escribir

    ap = argparse.ArgumentParser(prog="oficiales.manual")
    ap.add_argument("--salida", default="data/oficiales.json", type=Path)
    args = ap.parse_args(argv)
    datos = json.loads(args.salida.read_text(encoding="utf-8"))
    tablas = {n: Counter({tuple(f[:-1]): f[-1] for f in t["filas"]}) for n, t in datos["tablas"].items()}
    cobertura = {(a, c) for c, anios in datos.get("cobertura", {}).items() for a in anios}
    usados = completar(tablas, cobertura)
    if not usados:
        print("Nada que agregar")
        return 0
    escribir(tablas, sorted(set(datos["archivos"]) | set(usados)), datos["actualizado"], cobertura,
             datos.get("inicio_registro"), args.salida)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
