"""Uso: python -m oficiales.historico [--anios 2010-2019] [--salida data/oficiales_historico.json]

Antes de 2020 la Policía no publica un archivo único "a nivel de registro": publica
un Excel por delito y por año en https://www.policia.gov.co/estadistica-delictiva-old.
Este módulo los descarga, cuenta los casos del área metropolitana con las mismas
tablas que `python -m oficiales` y guarda el resultado en un archivo aparte, porque
esos años ya no cambian y descargar unos 150 archivos cada mes no tiene sentido.

La página tiene a veces dos versiones del mismo delito y año (por ejemplo
hurto_automotores_2018_1 y _2). Si cubren los mismos meses se usa la que tiene más
casos; si cubren meses distintos, se suman.
"""

from __future__ import annotations

import argparse
import io
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urljoin

import requests
from bs4 import BeautifulSoup

from .__main__ import AGENTE, anios_de
from .procesar import COLUMNAS, a_json, agregar, leer, normal

PAGINA = "https://www.policia.gov.co/estadistica-delictiva-old"

# (patrón sobre el nombre del archivo, clave del archivo, categoría del observatorio).
# El orden importa: "homicidios en accidente de tránsito" antes que "homicidio".
ARCHIVOS = [
    (r"HOMICIDIOS? (EN )?ACCIDENTE", "homicidio_transito", "transito"),
    (r"LESIONES EN ACCIDENTE", "lesiones_transito", "transito"),
    (r"HOMICIDIO", "homicidio", "homicidio"),
    (r"LESIONES PERSONALES", "lesiones", "lesiones"),
    (r"MOTO", "hurto_motos", "hurto_motos"),
    (r"AUTOMOTOR", "hurto_carros", "hurto_carros"),
    (r"COMERCIO", "hurto_comercio", "hurto_comercio"),
    (r"RESIDENCIA", "hurto_residencias", "hurto_residencias"),
    (r"ENTIDAD|FINANCIER", "hurto_entidades", "hurto_entidades"),
    (r"HURTO (A )?PERSONAS", "hurto_personas", "hurto_personas"),
    (r"EXTORSI", "extorsion", "extorsion"),
    (r"INTRAFAMILIAR", "violencia_intrafamiliar", "violencia_intrafamiliar"),
    (r"SEXUAL", "violencia_sexual", "violencia_sexual"),
    (r"AMEN?AZAS", "amenazas", "amenazas"),
    (r"SECUESTRO", "secuestro", "secuestro"),
]


def clasificar(nombre: str) -> tuple[str, str, int] | None:
    """Nombre de archivo -> (clave, categoría, año), o None si no nos sirve."""
    n = normal(unquote(nombre).rsplit("/", 1)[-1])
    m = re.search(r"(20[0-2]\d)", n)
    if not m:
        return None
    return next(((clave, cat, int(m[1])) for patron, clave, cat in ARCHIVOS if re.search(patron, n)), None)


def enlaces(sesion: requests.Session, anios: list[int]) -> dict[tuple[str, int], list[tuple[str, str]]]:
    """{(clave, año): [(url, categoría), ...]} recorriendo todas las páginas del listado."""
    out: dict[tuple[str, int], list[tuple[str, str]]] = defaultdict(list)
    vistos: set[str] = set()
    for p in range(0, 80):
        html = sesion.get(PAGINA + (f"?page={p}" if p else ""), timeout=60).text
        nuevos = 0
        for a in BeautifulSoup(html, "html.parser").find_all("a", href=True):
            url = urljoin(PAGINA, a["href"])
            if url in vistos or not re.search(r"\.xlsx?$", url, re.I):
                continue
            vistos.add(url)
            nuevos += 1
            c = clasificar(url)
            if c and c[2] in anios:
                out[(c[0], c[2])].append((url, c[1]))
        if not nuevos:
            break
    return out


def elegir(versiones: list[tuple[str, dict[str, Counter]]]) -> list[tuple[str, dict[str, Counter]]]:
    """Entre varias versiones del mismo delito y año, evita contar dos veces un mes."""
    def meses(t):
        return {(k[0], k[1]) for k in t["mensual"]}

    elegidas, cubiertos = [], set()
    for url, t in sorted(versiones, key=lambda v: -sum(v[1]["mensual"].values())):
        m = meses(t)
        if m and not (m & cubiertos):
            elegidas.append((url, t))
            cubiertos |= m
    return elegidas


def cobertura(resumen: Counter, anios: list[int]) -> list[list]:
    """[año, categoría] cuando están todos los archivos de esa categoría (tránsito son dos)."""
    claves: dict[str, set[str]] = defaultdict(set)
    for _, clave, cat in ARCHIVOS:
        claves[cat].add(clave)
    return [[a, cat] for a in anios for cat, cs in sorted(claves.items()) if all((a, c) in resumen for c in cs)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="oficiales.historico")
    ap.add_argument("--anios", default="2010-2019")
    ap.add_argument("--salida", default="data/oficiales_historico.json", type=Path)
    args = ap.parse_args(argv)
    anios = anios_de(args.anios)
    sesion = requests.Session()
    sesion.headers["User-Agent"] = AGENTE
    grupos = enlaces(sesion, anios)
    tablas: dict[str, Counter] = {k: Counter() for k in COLUMNAS}
    usados, resumen = [], Counter()
    for (clave, anio), lista in sorted(grupos.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        versiones = []
        for url, cat in lista:
            try:
                r = sesion.get(url, timeout=600)
                r.raise_for_status()
                df = leer(io.BytesIO(r.content))
                t = agregar(df, cat=cat)
            except Exception as e:  # un archivo dañado no debe frenar los demás
                print(f"{anio} · {clave}: no se pudo leer {unquote(url.rsplit('/', 1)[-1])} ({e})")
                continue
            # Solo cuenta lo que cae en el año del archivo.
            t = {k: Counter({x: n for x, n in c.items() if x[0] == anio}) for k, c in t.items()}
            print(f"{anio} · {clave} · {unquote(url.rsplit('/', 1)[-1])}: {sum(t['mensual'].values())} en el área · columnas {list(df.columns)}")
            versiones.append((url, t))
        for url, t in elegir(versiones):
            usados.append(url)
            for k, c in t.items():
                tablas[k].update(c)
            resumen[(anio, clave)] += sum(t["mensual"].values())
    faltan = [(clave, a) for a in anios for _, clave, _ in ARCHIVOS if (a, clave) not in resumen]
    print("Sin archivo con datos del área:", faltan or "ninguno")
    for (anio, clave), n in sorted(resumen.items()):
        print(f"RESUMEN {anio} {clave} {n}")
    datos = a_json(tablas, sorted(usados), datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    datos["fuente"] = "Policía Nacional: archivos por delito y año (estadística delictiva, histórico)"
    datos["url"] = PAGINA
    datos["cobertura"] = cobertura(resumen, anios)
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Escrito {args.salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
