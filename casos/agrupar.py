"""Agrupación de notas en casos.

Una nota es una URL de un medio; un caso es el hecho. Varias notas de
distintos medios sobre el mismo hecho se unen en un solo caso cuando:

1. el tipo de delito es compatible,
2. las fechas están a 2 días o menos,
3. el barrio coincide, o los textos se parecen mucho.

Los pares dudosos no se unen: el caso queda marcado como posible duplicado
para que el editor decida.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date

from scraper.clasificar import normalizar

# Tipos que no son un hecho delictivo por sí solos.
NO_SON_CASO = {"captura"}

# Grupos de tipos que pueden describir el mismo hecho (un herido que luego muere).
COMPATIBLES = [
    {"homicidio", "feminicidio", "lesiones"},
    {"hurto"},
    {"extorsion"},
    {"secuestro"},
    {"violencia_sexual"},
    {"violencia_intrafamiliar", "feminicidio", "lesiones", "homicidio"},
    {"desaparicion", "homicidio", "secuestro"},
]

DIAS_MAX = 2
UMBRAL_UNIR = 0.35  # similitud con la que se unen notas aunque no haya barrio
UMBRAL_DUDA = 0.20  # similitud desde la que se marca posible duplicado

VACIAS = set(
    """a al ante bajo con contra de del desde durante e el ella ellos en entre es esta este fue fueron ha
    han hasta la las le les lo los mas muy no o para pero por que se sin sobre su sus tras un una uno unos
    y ya hoy ayer anoche noche manana tarde madrugada barrio sector barranquilla soledad malambo galapa
    puerto colombia atlantico ano anos hombre mujer joven caso este esta tras habria seria luego cuando
    donde mientras dos tres""".split()
)


def tipo_principal(nota: dict) -> str | None:
    tipos = [t for t in nota.get("tipos_delito") or [] if t not in NO_SON_CASO]
    return tipos[0] if tipos else None


def es_candidata(nota: dict) -> bool:
    """Una nota entra a los casos si habla de un delito dentro del área."""
    if nota.get("estado") == "descartado":
        return False
    if nota.get("municipio") == "fuera_del_area":
        return False
    return tipo_principal(nota) is not None


def palabras(nota: dict) -> set[str]:
    texto = normalizar(f"{nota.get('titular', '')} {nota.get('resumen', '')}")
    return {w for w in re.findall(r"[a-z0-9]+", texto) if len(w) > 2 and w not in VACIAS}


def similitud(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _fecha(nota: dict) -> date | None:
    f = nota.get("fecha_publicacion")
    return date.fromisoformat(f[:10]) if f else None


def _compatibles(t1: str, t2: str) -> bool:
    return t1 == t2 or any(t1 in g and t2 in g for g in COMPATIBLES)


def _mismo_barrio(b1: str | None, b2: str | None) -> bool | None:
    """True si coinciden, False si ambos existen y difieren, None si falta alguno."""
    if not b1 or not b2:
        return None
    return normalizar(b1) == normalizar(b2)


def comparar(a: dict, b: dict, pa: set[str], pb: set[str]) -> str:
    """Devuelve 'unir', 'duda' o 'distinto'."""
    ta, tb = tipo_principal(a), tipo_principal(b)
    if not ta or not tb or not _compatibles(ta, tb):
        return "distinto"
    fa, fb = _fecha(a), _fecha(b)
    if not fa or not fb or abs((fa - fb).days) > DIAS_MAX:
        return "distinto"
    if (a.get("municipio") and b.get("municipio") and a["municipio"] != b["municipio"]):
        return "distinto"
    barrio = _mismo_barrio(a.get("barrio"), b.get("barrio"))
    sim = similitud(pa, pb)
    if barrio is False:
        return "distinto"
    if barrio is True:
        return "unir" if sim >= UMBRAL_DUDA else "duda"
    if sim >= UMBRAL_UNIR:
        return "unir"
    if sim >= UMBRAL_DUDA:
        return "duda"
    return "distinto"


class _Union:
    def __init__(self, n: int):
        self.padre = list(range(n))

    def raiz(self, i: int) -> int:
        while self.padre[i] != i:
            self.padre[i] = self.padre[self.padre[i]]
            i = self.padre[i]
        return i

    def unir(self, i: int, j: int) -> None:
        ri, rj = self.raiz(i), self.raiz(j)
        if ri != rj:
            self.padre[max(ri, rj)] = min(ri, rj)


def _caso_id(ids: list[str]) -> str:
    return hashlib.sha1(min(ids).encode()).hexdigest()[:12]


def agrupar(notas: list[dict], previos: list[dict] | None = None) -> list[dict]:
    """Agrupa las notas candidatas en casos.

    `previos` son los casos ya guardados: se conservan su estado y los campos
    que el editor haya corregido, y las notas que el editor ya unió siguen juntas.
    """
    cand = sorted((n for n in notas if es_candidata(n)), key=lambda n: (n.get("fecha_publicacion") or "", n["id"]))
    idx = {n["id"]: i for i, n in enumerate(cand)}
    pal = [palabras(n) for n in cand]
    u = _Union(len(cand))
    dudas: list[tuple[int, int]] = []

    # Lo que el editor ya unió se respeta.
    for c in previos or []:
        presentes = [idx[i] for i in c.get("notas", []) if i in idx]
        for k in presentes[1:]:
            u.unir(presentes[0], k)

    for i in range(len(cand)):
        fi = _fecha(cand[i])
        for j in range(i + 1, len(cand)):
            fj = _fecha(cand[j])
            if fi and fj and (fj - fi).days > DIAS_MAX:
                break
            r = comparar(cand[i], cand[j], pal[i], pal[j])
            if r == "unir":
                u.unir(i, j)
            elif r == "duda":
                dudas.append((i, j))

    grupos: dict[int, list[int]] = {}
    for i in range(len(cand)):
        grupos.setdefault(u.raiz(i), []).append(i)

    previo_por_nota = {nid: c for c in previos or [] for nid in c.get("notas", [])}
    casos: dict[int, dict] = {}
    for raiz, miembros in grupos.items():
        ns = [cand[i] for i in miembros]
        ids = [n["id"] for n in ns]
        tipos = []
        for n in ns:
            for t in n.get("tipos_delito") or []:
                if t not in tipos and t not in NO_SON_CASO:
                    tipos.append(t)
        # Si alguna nota dice que hubo muerto, el caso es homicidio.
        principal = next((t for t in ("feminicidio", "homicidio") if t in tipos), tipos[0])
        fechas = sorted(n["fecha_publicacion"][:10] for n in ns if n.get("fecha_publicacion"))
        barrios = [n["barrio"] for n in ns if n.get("barrio")]
        municipios = [n["municipio"] for n in ns if n.get("municipio")]
        caso = {
            "caso_id": _caso_id(ids),
            "tipo": principal,
            "tipos": tipos,
            "fecha": fechas[0] if fechas else None,
            "municipio": max(set(municipios), key=municipios.count) if municipios else None,
            "barrio": max(set(barrios), key=barrios.count) if barrios else None,
            "medios": sorted({n["medio"] for n in ns}),
            "notas": sorted(ids),
            "fuentes": [{"medio": n["medio"], "url": n["url"]} for n in ns],
            "estado": "pendiente",
            "posible_duplicado_de": [],
        }
        prev = next((previo_por_nota[i] for i in ids if i in previo_por_nota), None)
        if prev:
            for campo in ("caso_id", "estado", "tipo", "barrio", "municipio", "fecha", "revisado_por", "revisado_en"):
                if campo in prev and prev[campo] is not None:
                    caso[campo] = prev[campo]
        casos[raiz] = caso

    for i, j in dudas:
        ri, rj = u.raiz(i), u.raiz(j)
        if ri == rj:
            continue
        a, b = casos[ri], casos[rj]
        if b["caso_id"] not in a["posible_duplicado_de"]:
            a["posible_duplicado_de"].append(b["caso_id"])
        if a["caso_id"] not in b["posible_duplicado_de"]:
            b["posible_duplicado_de"].append(a["caso_id"])
    for c in casos.values():
        if c["posible_duplicado_de"] and c["estado"] == "pendiente":
            c["estado"] = "posible_duplicado"

    return sorted(casos.values(), key=lambda c: (c["fecha"] or "", c["caso_id"]), reverse=True)
