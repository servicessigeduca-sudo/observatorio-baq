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
import time
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urljoin

import requests
from bs4 import BeautifulSoup

from .manual import completar
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


def escribir(tablas: dict[str, Counter], fuentes: list[str], actualizado: str, cobertura: set,
             inicio_registro: int | None, salida: Path) -> None:
    """Escribe data/oficiales.json y la serie mensual en CSV."""
    datos = a_json(tablas, fuentes, actualizado)
    por_cat: dict[str, list[int]] = {}
    for a, c in sorted(cobertura):
        por_cat.setdefault(c, []).append(a)
    datos["cobertura"] = por_cat
    datos["inicio_registro"] = inicio_registro
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    t = datos["tablas"]["mensual"]
    with open(salida.with_name("oficiales_mensual.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(t["columnas"])
        w.writerows(t["filas"])
    print(f"Escrito {salida}: {len(t['filas'])} filas mensuales, último mes {datos['ultimo_mes']}")


def descargar(sesion: requests.Session, url: str, intentos: int = 4) -> bytes:
    """Descarga un archivo grande; la Policía a veces corta la conexión a mitad."""
    for i in range(1, intentos + 1):
        try:
            r = sesion.get(url, timeout=900)
            r.raise_for_status()
            return r.content
        except (requests.ConnectionError, requests.exceptions.ChunkedEncodingError, requests.Timeout) as e:
            if i == intentos:
                raise
            print(f"Descarga cortada ({e.__class__.__name__}), reintento {i}/{intentos - 1}: {url}")
            time.sleep(30 * i)
    raise AssertionError("inalcanzable")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="oficiales")
    ap.add_argument("--anios", default="2020-2026")
    ap.add_argument("--salida", default="data/oficiales.json", type=Path)
    ap.add_argument("--historico", default="data/oficiales_historico.json", type=Path,
                    help="años anteriores ya procesados por python -m oficiales.historico")
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
        for nombre, libro in libros(descargar(sesion, url), url):
            df = leer(libro)
            parcial = agregar(df)
            for k, c in parcial.items():
                tablas[k].update(c)
            print(f"{anio} · {nombre}: {sum(parcial['mensual'].values())} delitos en el área · columnas {list(df.columns)}")
    cobertura = {(a, c) for a in urls for c in {k[3] for k in tablas["mensual"]}}
    fuentes = sorted(urls.values())
    if args.historico.exists() and urls:
        primero = min(urls)
        h = json.loads(args.historico.read_text(encoding="utf-8"))
        for nombre, t in h["tablas"].items():
            for fila in t["filas"]:
                if fila[0] < primero:
                    tablas[nombre][tuple(fila[:-1])] += fila[-1]
        cobertura |= {(a, c) for a, c in h.get("cobertura", []) if a < primero}
        fuentes += h.get("archivos", [])
        print(f"Histórico agregado: {sorted({a for a, _ in cobertura if a < primero})}")
    fuentes += completar(tablas, cobertura)
    escribir(tablas, fuentes, datetime.now(timezone.utc).strftime("%Y-%m-%d"), cobertura,
             min(urls) if urls else None, args.salida)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
