"""Uso: python -m oficiales [--anios 2020-2026] [--salida data/oficiales.json]

Descarga de policia.gov.co los archivos de delitos a nivel de registro (XLSX o
ZIP con XLSX), y escribe conteos del área metropolitana en data/oficiales.json
y la serie mensual en data/oficiales_mensual.csv.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urljoin

import requests
from bs4 import BeautifulSoup

from .procesar import COLUMNAS, a_json, agregar, leer

PAGINA = "https://www.policia.gov.co/estadistica-delictiva"
AGENTE = "ObservatorioBAQ/0.1 (+https://github.com/servicessigeduca-sudo/observatorio-baq)"


def anios_de(texto: str) -> list[int]:
    if "-" in texto:
        a, b = (int(x) for x in texto.split("-"))
        return list(range(a, b + 1))
    return [int(x) for x in texto.split(",")]


def enlaces(sesion: requests.Session, anios: list[int]) -> dict[int, str]:
    html = sesion.get(PAGINA, timeout=60).text
    out = {}
    for a in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        nombre = unquote(a["href"]).upper()
        if "NIVEL_DE_REGISTRO" in nombre and re.search(r"\.(XLSX|ZIP)$", nombre):
            m = re.search(r"(20\d\d)", nombre)
            if m and int(m[1]) in anios:
                out[int(m[1])] = urljoin(PAGINA, a["href"])
    return out


def libros(contenido: bytes, url: str):
    """Devuelve los Excel de una descarga: el archivo mismo o los que traiga el ZIP."""
    if url.lower().endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(contenido)) as z:
            for n in z.namelist():
                if n.lower().endswith(".xlsx") and not n.startswith("__MACOSX"):
                    yield n, io.BytesIO(z.read(n))
    else:
        yield url.rsplit("/", 1)[-1], io.BytesIO(contenido)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="oficiales")
    ap.add_argument("--anios", default="2020-2026")
    ap.add_argument("--salida", default="data/oficiales.json", type=Path)
    args = ap.parse_args(argv)
    anios = anios_de(args.anios)
    sesion = requests.Session()
    sesion.headers["User-Agent"] = AGENTE
    urls = enlaces(sesion, anios)
    faltan = [a for a in anios if a not in urls]
    if faltan:
        print(f"Sin archivo a nivel de registro para: {faltan}")
    tablas: dict[str, Counter] = {k: Counter() for k in COLUMNAS}
    for anio, url in sorted(urls.items()):
        r = sesion.get(url, timeout=900)
        r.raise_for_status()
        for nombre, libro in libros(r.content, url):
            df = leer(libro)
            parcial = agregar(df)
            for k, c in parcial.items():
                tablas[k].update(c)
            print(f"{anio} · {nombre}: {sum(parcial['mensual'].values())} delitos en el área · columnas {list(df.columns)}")
    datos = a_json(tablas, sorted(urls.values()), datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    t = datos["tablas"]["mensual"]
    with open(args.salida.with_name("oficiales_mensual.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(t["columnas"])
        w.writerows(t["filas"])
    print(f"Escrito {args.salida}: {len(t['filas'])} filas mensuales, último mes {datos['ultimo_mes']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
