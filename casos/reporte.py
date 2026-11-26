"""Resumen en Markdown de los casos, para la pestaña Actions y el pull request."""

from __future__ import annotations

from collections import Counter

from .agrupar import motivo_exclusion, tipo_principal

NOMBRES = {
    "homicidio": "Homicidio", "feminicidio": "Feminicidio", "lesiones": "Lesiones",
    "hurto": "Hurto", "extorsion": "Extorsión", "secuestro": "Secuestro",
    "violencia_sexual": "Violencia sexual", "violencia_intrafamiliar": "Violencia intrafamiliar",
    "desaparicion": "Desaparición", "amenazas": "Amenazas",
    "hurto_personas": "Hurto a personas", "hurto_motos": "Hurto de motos", "hurto_carros": "Hurto de carros",
    "hurto_comercio": "Hurto a comercio", "hurto_residencias": "Hurto a residencias",
    "hurto_entidades": "Hurto a entidades financieras",
}


def _tabla(titulo: str, conteo: Counter, total: int, n: int | None = None) -> list[str]:
    filas = [f"| {titulo} | Casos | % |", "| --- | ---: | ---: |"]
    for k, v in conteo.most_common(n):
        filas.append(f"| {k} | {v} | {100 * v / total:.0f} % |")
    return filas + [""]


def generar(notas: list[dict], casos: list[dict]) -> str:
    total = len(casos)
    if not total:
        return "Sin casos todavía: `data/notas.json` está vacío o ninguna nota describe un delito en el área.\n"
    fechas = sorted(c["fecha"] for c in casos if c["fecha"])
    multi = [c for c in casos if len(c["notas"]) > 1]
    dudas = sum(1 for c in casos if c["estado"] == "posible_duplicado")
    sin_barrio = sum(1 for c in casos if not c["barrio"])
    en_casos = sum(len(c["notas"]) for c in casos)
    fuera = Counter(m for n in notas if tipo_principal(n) and n.get("estado") != "publicado" and (m := motivo_exclusion(n)))
    out = [
        "## Casos",
        "",
        f"**{total} casos** a partir de {len(notas)} notas ({en_casos} describen un delito en el área), "
        f"del {fechas[0]} al {fechas[-1]}." if fechas else f"**{total} casos** a partir de {len(notas)} notas.",
        "",
        f"- {len(multi)} casos reúnen notas de más de un medio o más de una nota.",
        f"- {dudas} quedan como posible duplicado para que el editor decida.",
        f"- {sin_barrio} no tienen barrio identificado.",
        f"- {sum(1 for c in casos if c.get('varios_hechos'))} vienen de notas que cuentan varios hechos: el editor debe separarlos.",
        f"- {sum(fuera.values())} notas con delito no cuentan como caso: {fuera['fuera_del_area']} de fuera del área, "
        f"{fuera['balance']} balances o cifras acumuladas, {fuera['seguimiento_judicial']} seguimientos judiciales "
        f"y {fuera['accidente']} accidentes.",
        "",
    ]
    out += _tabla("Tipo", Counter(NOMBRES.get(c["tipo"], c["tipo"]) for c in casos), total)
    out += _tabla("Municipio", Counter(c["municipio"] or "Sin identificar" for c in casos), total)
    out += _tabla("Barrio (10 con más casos)", Counter(c["barrio"] for c in casos if c["barrio"]), total, 10)
    if multi:
        out += ["### Notas unidas en un mismo caso", ""]
        for c in multi[:10]:
            out.append(f"- {c['fecha']} · {NOMBRES.get(c['tipo'], c['tipo'])} · {c['barrio'] or c['municipio'] or 'sin lugar'}: "
                       + ", ".join(f"[{f['medio']}]({f['url']})" for f in c["fuentes"]))
        out.append("")
    return "\n".join(out)
