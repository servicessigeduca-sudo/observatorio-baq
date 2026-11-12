"""Convierte los archivos "a nivel de registro" de la Policía en conteos pequeños.

Cada archivo trae un delito por fila (con columna CANTIDAD) para todo el país.
Nos quedamos con los cinco municipios del área metropolitana y agregamos por
mes, día de la semana, arma o medio, género y grupo de edad. La Policía no
publica barrio ni coordenadas: el nivel más fino es el municipio.

Los nombres de columna cambian entre años (FECHA ISSO / FECHA HECHO,
DELITO / DELITOS, EDAD ETARIA / *AGRUPA EDAD PERSONA*), así que se buscan
por prefijo.
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

# Respaldo para archivos viejos que traen el nombre del delito sin código ICCS.
POR_NOMBRE = [
    (r"HOMICIDIO.*TR[AÁ]NSITO|TR[AÁ]NSITO", "transito"),
    (r"HOMICIDIO", "homicidio"),
    (r"LESIONES", "lesiones"),
    (r"HURTO.*MOTO", "hurto_motos"),
    (r"HURTO.*(AUTOMOTOR|CARRO|VEH)", "hurto_carros"),
    (r"HURTO.*COMERCIO", "hurto_comercio"),
    (r"HURTO.*RESIDENCIA", "hurto_residencias"),
    (r"HURTO.*(ENTIDAD|FINANCIER)", "hurto_entidades"),
    (r"HURTO", "hurto_personas"),
    (r"EXTORSI", "extorsion"),
    (r"VIOLENCIA INTRAFAMILIAR", "violencia_intrafamiliar"),
    (r"SEXUAL|VIOLACI|ACCESO CARNAL", "violencia_sexual"),
    (r"AMENAZA", "amenazas"),
    (r"SECUESTRO|RETENCI", "secuestro"),
]

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def leer(contenido) -> pd.DataFrame:
    """Lee el Excel, buscando la fila de encabezados (no siempre es la misma)."""
    crudo = pd.read_excel(contenido, header=None, nrows=40, dtype=str)
    fila = next(i for i, r in crudo.iterrows() if "CODIGO DANE" in [str(v).strip().upper() for v in r.values])
    if hasattr(contenido, "seek"):
        contenido.seek(0)
    df = pd.read_excel(contenido, header=fila, dtype=str)
    df.columns = [str(c).strip().strip("*").strip().upper() for c in df.columns]
    return df


def categoria(delito: str) -> str:
    texto = str(delito).strip()
    m = re.match(r"\((\d+)\)", texto)
    if m:
        return CATEGORIAS.get(m[1], "otros")
    t = texto.upper()
    return next((cat for patron, cat in POR_NOMBRE if re.search(patron, t)), "otros")


def _col(df: pd.DataFrame, *prefijos: str) -> str | None:
    return next((c for c in df.columns for p in prefijos if c.startswith(p) or p in c), None)


def _limpio(serie: pd.Series, defecto: str) -> pd.Series:
    s = serie.fillna(defecto).astype(str).str.strip().str.upper()
    return s.replace({"": defecto, "NAN": defecto, "-": defecto})


def agregar(df: pd.DataFrame) -> dict[str, Counter]:
    """Devuelve contadores por tabla: mensual, armas, dias, genero, edad."""
    df = df.copy()
    df["DANE"] = df[_col(df, "CODIGO DANE")].astype(str).str.strip().str.split(".").str[0].str.zfill(5)
    df = df[df["DANE"].isin(MUNICIPIOS)].copy()
    df["N"] = pd.to_numeric(df[_col(df, "CANTIDAD")], errors="coerce").fillna(1).astype(int)
    df["fecha"] = pd.to_datetime(df[_col(df, "FECHA")].astype(str).str[:10].str.replace("/", "-"), errors="coerce")
    df = df[df["fecha"].notna()].copy()
    df["anio"], df["mes"], df["dia"] = df["fecha"].dt.year, df["fecha"].dt.month, df["fecha"].dt.dayofweek
    df["muni"] = df["DANE"].map(MUNICIPIOS)
    df["cat"] = df[_col(df, "DELITO")].map(categoria)
    col_arma, col_gen, col_edad = _col(df, "ARMA"), _col(df, "GENERO"), _col(df, "EDAD")
    df["arma"] = _limpio(df[col_arma], "NO REPORTADO") if col_arma else "NO REPORTADO"
    df["genero"] = _limpio(df[col_gen], "NO REPORTADO").replace({"MA": "MASCULINO", "FE": "FEMENINO"}) if col_gen else "NO REPORTADO"
    df["edad"] = _limpio(df[col_edad], "NO REPORTADO") if col_edad else "NO REPORTADO"

    def contar(claves: list[str]) -> Counter:
        return Counter({tuple(_nativo(v) for v in k): int(n) for k, n in df.groupby(claves)["N"].sum().items()})

    return {
        "mensual": contar(["anio", "mes", "muni", "cat"]),
        "armas": contar(["anio", "muni", "cat", "arma"]),
        "dias": contar(["anio", "mes", "muni", "cat", "dia"]),
        "genero": contar(["anio", "muni", "cat", "genero"]),
        "edad": contar(["anio", "muni", "cat", "edad"]),
    }


COLUMNAS = {
    "mensual": ["anio", "mes", "municipio", "categoria", "cantidad"],
    "armas": ["anio", "municipio", "categoria", "arma", "cantidad"],
    "dias": ["anio", "mes", "municipio", "categoria", "dia_semana", "cantidad"],
    "genero": ["anio", "municipio", "categoria", "genero", "cantidad"],
    "edad": ["anio", "municipio", "categoria", "edad", "cantidad"],
}


def _nativo(v):
    return v.item() if hasattr(v, "item") else v


def a_json(tablas: dict[str, Counter], fuentes: list[str], actualizado: str) -> dict:
    """Formato compacto: cada tabla es {columnas, filas} con filas como listas."""
    mensual = tablas.get("mensual", Counter())
    ultimo = max(((int(_nativo(k[0])), int(_nativo(k[1]))) for k in mensual), default=None)
    out = {
        "fuente": "Policía Nacional, SIEDCO: información de delitos a nivel de registro",
        "url": "https://www.policia.gov.co/estadistica-delictiva",
        "archivos": fuentes,
        "actualizado": actualizado,
        "ultimo_mes": {"anio": ultimo[0], "mes": ultimo[1]} if ultimo else None,
        "nota": "Cifras provisionales hasta marzo del año siguiente. Sin barrio ni coordenadas. dia_semana: 0 = lunes.",
        "tablas": {},
    }
    for nombre, cols in COLUMNAS.items():
        filas = [[_nativo(v) for v in k] + [n] for k, n in sorted(tablas.get(nombre, Counter()).items(), key=lambda x: tuple(str(v) for v in x[0]))]
        out["tablas"][nombre] = {"columnas": cols, "filas": filas}
    return out
