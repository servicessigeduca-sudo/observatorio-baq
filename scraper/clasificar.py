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


# Categorías: las mismas de la base oficial de la Policía (oficiales/procesar.py),
# más feminicidio y desaparición, que la prensa distingue. Tránsito no se usa:
# los accidentes no entran como casos.
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
    ("hurto", [r"hurto", r"\brobo\b", r"\broban\b", r"\brobaron\b", r"\brobar(le|les)?\b", r"atraco", r"atracad",
               r"\batracan\b", r"raponer", r"cosquiller", r"fleteo", r"fletead", r"asalt"]),
    ("violencia_intrafamiliar", [r"violencia intrafamiliar", r"maltrato", r"violencia de genero"]),
    ("amenazas", [r"amenaza", r"panfleto", r"intimidad"]),
    ("desaparicion", [r"desaparecid"]),
    ("captura", [r"captura", r"capturad", r"aprehendid", r"incautan", r"incautacion"]),
]

_REGLAS_C = [(tipo, [re.compile(p) for p in patrones]) for tipo, patrones in REGLAS]

# Modalidades de hurto de la base oficial; si no se reconoce ninguna, es hurto a personas.
_HURTOS = [
    ("hurto_entidades", re.compile(r"\b(banco|bancaria|entidad financiera|cajero|corresponsal|punto de recaudo|giros|casa de cambio|chance)\b")),
    ("hurto_motos", re.compile(r"\b(moto|motos|motocicleta\w*|motociclista|motoneta)\b")),
    ("hurto_carros", re.compile(r"\b(carro|carros|vehiculo|camioneta|automovil|automotor\w*|camion)\b")),
    ("hurto_residencias", re.compile(r"\b(vivienda|residencia|casa|apartamento|hogar|conjunto residencial)\b")),
    ("hurto_comercio", re.compile(r"\b(tienda|local|comercio|establecimiento|almacen|supermercado|supertienda|drogueria|"
                                  r"ferreteria|panaderia|restaurante|estacion de servicio|bomba|olimpica|ara|d1|joyeria|negocio)\b")),
]
TIPOS_HURTO = [t for t, _ in _HURTOS] + ["hurto_personas"]


def tipo_hurto(texto: str) -> str:
    """Modalidad de hurto como la clasifica la base oficial."""
    t = normalizar(texto)
    return next((tipo for tipo, p in _HURTOS if p.search(t)), "hurto_personas")


# Titulares sobre capturas o procesos judiciales: cuentan que detuvieron, imputaron
# o condenaron a alguien por un delito, no un delito nuevo («Capturan a alias
# 'El Mello', señalado de homicidios»).
_CAPTURA_O_JUDICIAL = re.compile(
    r"\b(captur(an|aron|o|ada|ado|adas|ados|a a|as)|recaptur\w*|aprehend\w*|aprehension|"
    r"cay(o|eron)\b(?! (muert\w*|herid\w*|abatid\w*|sin vida|desde|de un|de una|al)\b)|"
    r"judicializ\w*|imput(an|aron|ado|ada|ados|adas|acion|aran)\b|cargos (contra|a|por)|"
    r"condena(n|ron|do|da|dos|das)? (a|de|por)\b|fue(ron)? condenad|condenad[oa]s?\b|sentencia(n|do|da)? a|"
    r"(enviad|mandad)[oa]s? a la carcel|a la carcel|tras las rejas|medida de aseguramiento|"
    r"(legaliz|orden)\w* (de )?captura|se entrego|se entregaron|extradi\w*|llaman? a juicio|"
    r"van a juicio|preacuerdo|aceptaron cargos|acepto cargos|responsable[s]? (de|del) (homicidio|asesinato|crimen|feminicidio))"
)
# Marcas de que la captura ocurrió en el mismo hecho que se está contando
# («capturan a sicario tras asesinar a un hombre en Rebolo»).
_HECHO_EN_CURSO = re.compile(r"\b(en flagrancia|tras (asesinar|matar|herir|disparar|atracar|robar)|luego de (asesinar|matar|herir|disparar|atracar|robar)|minutos despues|momentos despues|cuando (huia|intentaba|escapaba))\b")


def es_captura_o_judicial(titular: str) -> bool:
    """El titular cuenta una captura, imputación o condena, no un delito nuevo."""
    t = normalizar(titular)
    return bool(_CAPTURA_O_JUDICIAL.search(t)) and not _HECHO_EN_CURSO.search(t)


def tipos_delito(texto: str, titular: str | None = None) -> list[str]:
    """Tipos de delito que menciona el texto, el principal primero.

    Si el titular cuenta una captura o un proceso judicial, el tipo principal es
    «captura»: los demás tipos quedan como el delito por el que se capturó."""
    t = normalizar(texto)
    tipos = [tipo for tipo, pats in _REGLAS_C if any(p.search(t) for p in pats)]
    # Si hubo muerto, "lesiones" es secundario; si es feminicidio, también es homicidio.
    if "feminicidio" in tipos and "homicidio" not in tipos:
        tipos.insert(1, "homicidio")
    if "hurto" in tipos:
        tipos[tipos.index("hurto")] = tipo_hurto(texto)
    if es_captura_o_judicial(texto if titular is None else titular):
        tipos = ["captura"] + [x for x in tipos if x != "captura"]
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
        "tipos_delito": tipos_delito(texto, titular),
        "municipio": municipio(texto),
        "barrio": barrio(titular) or barrio(resumen),
    }
