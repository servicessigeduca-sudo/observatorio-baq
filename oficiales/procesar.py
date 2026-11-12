"""Convierte los archivos "a nivel de registro" de la Policía en conteos pequeños.

Cada archivo trae un delito por fila (con columna CANTIDAD) para todo el país.
Nos quedamos con los cinco municipios del área metropolitana y agregamos por
año, mes, municipio, categoría y arma o medio. La Policía no publica barrio
ni coordenadas: el nivel más fino es el municipio.
"""

from __future__ import annotations

import re
from collections import Counter

import pandas as pd

MUNICIPIOS = {
    "08001": "Barranquilla",
    "08758": "Soledad",
    "08433": "Malambo",
    "08296": "Galapa",
    "08573": "Puerto Colombia",
}

# Código ICCS entre paréntesis al inicio de DELITO -> categoría del observatorio.
CATEGORIAS = {
    "0101": "homicidio",
    "02011": "lesiones",
    "05022": "hurto_personas",
    "050212": "hurto_motos",
    "050211": "hurto_carros",
    "05023": "hurto_comercio",
    "05010": "hurto_residencias",
    "05030": "hurto_entidades",
    "02051": "extorsion",
    "02089": "violencia_intrafamiliar",
    "0301": "violencia_sexual",
    "02012": "amenazas",
    "020222": "secuestro",
    "10321": "transito",
    "02019": "transito",
}


def leer(contenido) -> pd.DataFrame:
    """Lee el Excel, buscando la fila de encabezados (no siempre es la misma)."""
    crudo = pd.read_excel(contenido, header=None, nrows=40, dtype=str)
    fila = next(i for i, r in crudo.iterrows() if "CODIGO DANE" in [str(v).strip().upper() for v in r.values])
    if hasattr(contenido, "seek"):
        contenido.seek(0)
    df = pd.read_excel(contenido, header=fila, dtype=str)
    df.columns = [str(c).strip().upper() for c in df.columns]
    return df


def categoria(delito: str) -> str:
    m = re.match(r"\((\d+)\)", str(delito).strip())
    return CATEGORIAS.get(m[1], "otros") if m else "otros"


def agregar(df: pd.DataFrame) -> tuple[Counter, Counter]:
    df = df.copy()
    df["CODIGO DANE"] = df["CODIGO DANE"].astype(str).str.strip().str.zfill(5)
    df = df[df["CODIGO DANE"].isin(MUNICIPIOS)].copy()
    df["CANTIDAD"] = pd.to_numeric(df["CANTIDAD"], errors="coerce").fillna(1).astype(int)
    # La columna de fecha cambia de nombre entre años (FECHA ISSO, FECHA HECHO...).
    col_fecha = next(c for c in df.columns if c.startswith("FECHA"))
    df["fecha"] = pd.to_datetime(df[col_fecha].astype(str).str[:10].str.replace("/", "-"), errors="coerce")
    df = df[df["fecha"].notna()]
    df["anio"], df["mes"] = df["fecha"].dt.year, df["fecha"].dt.month
    col_arma = next((c for c in df.columns if c.startswith("ARMA")), None)
    df["ARMAS MEDIOS"] = df[col_arma].fillna("NO REPORTADO") if col_arma else "NO REPORTADO"
    conteo: Counter = Counter()
    armas: Counter = Counter()
    for (anio, mes, dane, delito, arma), n in df.groupby(["anio", "mes", "CODIGO DANE", "DELITO", "ARMAS MEDIOS"])["CANTIDAD"].sum().items():
        cat = categoria(delito)
        conteo[(int(anio), int(mes), MUNICIPIOS[dane], cat)] += int(n)
        armas[(int(anio), cat, str(arma).strip().upper())] += int(n)
    return conteo, armas


def a_json(conteo: Counter, armas: Counter, fuentes: list[str], actualizado: str) -> dict:
    filas = [{"anio": a, "mes": m, "municipio": mu, "categoria": c, "cantidad": n}
             for (a, m, mu, c), n in sorted(conteo.items())]
    ultimo = max(((r["anio"], r["mes"]) for r in filas), default=None)
    return {
        "fuente": "Policía Nacional, SIEDCO: información de delitos a nivel de registro",
        "url": "https://www.policia.gov.co/estadistica-delictiva",
        "archivos": fuentes,
        "actualizado": actualizado,
        "ultimo_mes": {"anio": ultimo[0], "mes": ultimo[1]} if ultimo else None,
        "nota": "Cifras provisionales hasta marzo del año siguiente. Sin barrio ni coordenadas.",
        "conteos": filas,
        "armas": [{"anio": a, "categoria": c, "arma": ar, "cantidad": n} for (a, c, ar), n in sorted(armas.items())],
    }
