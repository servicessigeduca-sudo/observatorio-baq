"""Clasificación por palabras clave del tipo de delito, municipio y barrio.

Es una primera pasada automática; el equipo revisa cada nota antes de
publicarla como caso.
"""

from __future__ import annotations

import re
import unicodedata


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


# Orden = prioridad: el primero que coincida es el tipo principal.
REGLAS: list[tuple[str, list[str]]] = [
    ("feminicidio", [r"feminicid"]),
    ("homicidio", [
        r"asesina", r"\bmatan\b", r"\bmataron\b", r"\bmato\b", r"homicid", r"sicariato",
        r"(muri[oó]|fallec|muerto|muerta|muertos|sin vida)", r"masacre", r"abatid",
    ]),
    ("lesiones", [r"herid[oa]s?\b", r"\bhier(e|en)\b", r"balead[oa]", r"apu[nñ]alad", r"atentado", r"ataque a bala", r"lesiones"]),
    ("violencia_sexual", [r"abuso sexual", r"violacion", r"acceso carnal", r"acto sexual"]),
    ("extorsion", [r"extorsi"]),
    ("secuestro", [r"secuestr"]),
    ("hurto", [r"hurto", r"\brobo\b", r"\broban\b", r"\brobaron\b", r"atraco", r"atracad", r"raponer", r"cosquiller"]),
    ("violencia_intrafamiliar", [r"violencia intrafamiliar", r"maltrato"]),
    ("desaparicion", [r"desaparecid"]),
    ("captura", [r"captura", r"capturad", r"aprehendid", r"incautan", r"incautacion"]),
]

_REGLAS_C = [(tipo, [re.compile(p) for p in patrones]) for tipo, patrones in REGLAS]


def tipos_delito(texto: str) -> list[str]:
    t = normalizar(texto)
    tipos = [tipo for tipo, pats in _REGLAS_C if any(p.search(t) for p in pats)]
    # Si hubo muerto, "lesiones" es secundario; si es feminicidio, también es homicidio.
    if "feminicidio" in tipos and "homicidio" not in tipos:
        tipos.insert(1, "homicidio")
    return tipos


MUNICIPIOS_AREA = {
    "barranquilla": "Barranquilla",
    "soledad": "Soledad",
    "malambo": "Malambo",
    "galapa": "Galapa",
    "puerto colombia": "Puerto Colombia",
}

MUNICIPIOS_FUERA = [
    "sabanalarga", "baranoa", "sabanagrande", "santo tomas", "palmar de varela", "ponedera",
    "juan de acosta", "tubara", "usiacuri", "luruaco", "repelon", "campo de la cruz",
    "santa lucia", "suan", "manati", "candelaria", "polonuevo", "sabanagrande", "piojo",
    "cartagena", "santa marta", "valledupar", "riohacha", "sincelejo", "monteria", "la guajira",
]


def municipio(texto: str) -> str | None:
    t = normalizar(texto)
    for clave, nombre in MUNICIPIOS_AREA.items():
        if re.search(rf"\b{clave}\b", t):
            if clave == "barranquilla":
                continue  # se decide al final: muchos medios dicen "Barranquilla" por contexto
            return nombre
    for m in MUNICIPIOS_FUERA:
        if re.search(rf"\b{m}\b", t):
            return "fuera_del_area"
    if "barranquilla" in t:
        return "Barranquilla"
    return None


# Barrios que los titulares suelen nombrar sin la palabra "barrio".
# Lista inicial, a completar con el listado oficial de la Alcaldía.
BARRIOS_CONOCIDOS = [
    "Rebolo", "La Chinita", "La Luz", "Barrio Abajo", "El Bosque", "Carrizal", "Las Flores",
    "La Esmeralda", "El Santuario", "Villate", "El Valle", "El Limón", "Las Malvinas",
    "Evaristo Sourdis", "Los Olivos", "Siete de Abril", "La Sierrita", "Las Nieves", "Simón Bolívar",
    "La Playa", "Me Quejo", "Ciudad Modesto", "Carlos Meisel", "Lipaya", "Los Andes", "La Victoria",
    "El Ferry", "San Roque", "Montes", "Las Estrellas", "Nueva Colombia", "Kennedy", "La Manga",
    "Villa María", "Ciudad Paraíso", "Terranova", "Los Cusules", "Los Fundadores", "Los Almendros",
    "Los Cedros", "Manuela Beltrán", "Mesolandia", "Torre del Pescado", "Mundo Feliz",
]
_BARRIOS_N = sorted(((normalizar(b), b) for b in BARRIOS_CONOCIDOS), key=lambda x: -len(x[0]))

_PATRON_BARRIO = re.compile(
    r"\b(?:barrio|sector|urbanizaci[oó]n)\s+"
    r"((?:[A-ZÁÉÍÓÚÑ0-9][\wáéíóúñ'’]*)(?:\s+(?:de|del|la|las|los|el|y|[A-ZÁÉÍÓÚÑ0-9IVX][\wáéíóúñ'’]*))*)"
)
_FINALES = {"de", "del", "la", "las", "los", "el", "y", "en"}
_INSTITUCION = re.compile(
    r"\b(clinica|hospital|ips|eps|caminos?|centro comercial|c\. ?c\.|colegio|institucion educativa|universidad|"
    r"estacion( de policia)?|cai|iglesia|parroquia|cementerio|centro de salud|puesto de salud|uci)\s+(de\s+)?$"
)


def barrio(texto: str) -> str | None:
    m = _PATRON_BARRIO.search(texto)
    if m:
        palabras = m[1].split()
        # "El Santuario de Barranquilla" -> "El Santuario"
        for i, w in enumerate(palabras[:-1]):
            siguiente = normalizar(" ".join(palabras[i + 1 :]))
            if w.lower() in ("de", "en") and any(siguiente.startswith(k) for k in MUNICIPIOS_AREA):
                palabras = palabras[:i]
                break
        while palabras and palabras[-1].lower() in _FINALES:
            palabras.pop()
        if palabras:
            return " ".join(palabras).rstrip(",.:;")
    t = normalizar(texto)
    for clave, nombre in _BARRIOS_N:
        for m in re.finditer(rf"\b{re.escape(clave)}\b", t):
            # «Clínica Los Almendros» o «colegio La Victoria» no dicen dónde ocurrió el hecho.
            if not _INSTITUCION.search(t[: m.start()]):
                return nombre
    return None


def clasificar(titular: str, resumen: str = "") -> dict:
    texto = f"{titular}. {resumen}"
    return {
        "tipos_delito": tipos_delito(texto),
        "municipio": municipio(texto),
        "barrio": barrio(titular) or barrio(resumen),
    }
