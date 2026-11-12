"""Uso: python -m oficiales [--anios 2025,2026] [--salida data/oficiales.json]

Descarga de policia.gov.co los archivos de delitos a nivel de registro y
escribe conteos del área metropolitana en data/oficiales.json.
"""

from __future__ import annotations

import argparse
import io
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urljoin

import requests
from bs4 import BeautifulSoup

from .procesar import a_json, agregar, leer

PAGINA = "https://www.policia.gov.co/estadistica-delictiva"
AGENTE = "ObservatorioBAQ/0.1 (+https://github.com/servicessigeduca-sudo/observatorio-baq)"


def enlaces(sesion: requests.Session, anios: list[int]) -> dict[int, str]:
    html = sesion.get(PAGINA, timeout=60).text
    out = {}
    for a in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        nombre = unquote(a["href"]).upper()
        if "NIVEL_DE_REGISTRO" in nombre and nombre.endswith(".XLSX"):
            m = re.search(r"(20\d\d)", nombre)
            if m and int(m[1]) in anios:
                out[int(m[1])] = urljoin(PAGINA, a["href"])
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="oficiales")
    ap.add_argument("--anios", default="2025,2026")
    ap.add_argument("--salida", default="data/oficiales.json", type=Path)
    args = ap.parse_args(argv)
    anios = [int(a) for a in args.anios.split(",")]
    sesion = requests.Session()
    sesion.headers["User-Agent"] = AGENTE
    urls = enlaces(sesion, anios)
    faltan = [a for a in anios if a not in urls]
    if faltan:
        print(f"Sin archivo a nivel de registro (xlsx) para: {faltan}")
    conteo: Counter = Counter()
    armas: Counter = Counter()
    for anio, url in sorted(urls.items()):
        r = sesion.get(url, timeout=600)
        r.raise_for_status()
        c, ar = agregar(leer(io.BytesIO(r.content)))
        conteo.update(c)
        armas.update(ar)
        print(f"{anio}: {sum(c.values())} delitos en el área ({url})")
    datos = a_json(conteo, armas, sorted(urls.values()), datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(json.dumps(datos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Escrito {args.salida}: {len(datos['conteos'])} filas, último mes {datos['ultimo_mes']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
