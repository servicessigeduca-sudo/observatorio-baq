"""Agrupación de notas en casos.

Una nota es una URL de un medio; un caso es el hecho. Varias notas de
distintos medios sobre el mismo hecho se unen en un solo caso cuando:

1. el tipo de delito es compatible,
2. las fechas están a 2 días o menos,
3. el barrio coincide, o los textos se parecen mucho.

También se unen, aunque cambie el barrio o el texto, cuando las dos notas
nombran a la misma persona, el mismo alias o el mismo número de víctima
("la mujer 80 asesinada en 2026").

Los pares dudosos no se unen: el caso queda marcado como posible duplicado
para que el editor decida.

No entran como caso las notas que no cuentan un hecho nuevo en el área:
balances y cifras acumuladas, seguimientos judiciales de hechos viejos,
accidentes y noticias de otras regiones o países.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date

from scraper.clasificar import BARRIOS_CONOCIDOS, normalizar

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
# Un herido puede morir días después en el hospital: si las notas nombran a la
# misma persona o alias, se unen aunque estén más separadas.
DIAS_MAX_MISMA_PERSONA = 30
UMBRAL_UNIR = 0.35  # similitud con la que se unen notas aunque no haya barrio
UMBRAL_DUDA = 0.20  # similitud desde la que se marca posible duplicado

VACIAS = set(
    """a al ante bajo con contra de del desde durante e el ella ellos en entre es esta este fue fueron ha
    han hasta la las le les lo los mas muy no o para pero por que se sin sobre su sus tras un una uno unos
    y ya hoy ayer anoche noche manana tarde madrugada barrio sector barranquilla soledad malambo galapa
    puerto colombia atlantico ano anos hombre mujer joven caso este esta tras habria seria luego cuando
    donde mientras dos tres diario libertad zona cero emisora impacto news ctv""".split()
)


def tipo_principal(nota: dict) -> str | None:
    tipos = [t for t in nota.get("tipos_delito") or [] if t not in NO_SON_CASO]
    return tipos[0] if tipos else None


# Departamentos y ciudades que delatan una nota de fuera del área metropolitana
# cuando el scraper no identificó el municipio.
FUERA_DEL_AREA = re.compile(
    r"\b(casanare|antioquia|medellin|bogota|cundinamarca|cauca|popayan|cali|valle del cauca|narino|choco|"
    r"santander|bucaramanga|cucuta|norte de santander|arauca|meta|villavicencio|huila|tolima|caldas|risaralda|"
    r"quindio|boyaca|bolivar|cartagena|magdalena|santa marta|cesar|valledupar|la guajira|riohacha|sucre|"
    r"sincelejo|cordoba|monteria|putumayo|caqueta|amazonas|guaviare|vichada|venezuela|ecuador|"
    r"guajira|aracataca|sitionuevo|cienaga|fundacion|el banco|cerete|lorica|panamericana|"
    r"gaza|israel|palestina|ucrania|rusia|mexico|guadalajara|sinaloa|estados unidos|eeuu|madrid|espana|peru|chile|argentina|brasil)\b"
)
# Nombres de lugares del área que contienen el de otra región ("Simón Bolívar").
_LUGARES_DEL_AREA = re.compile(r"\b(simon bolivar|calle sucre|avenida cordoba|carrera cordoba|rio magdalena|barrio cesar|valle de|el valle)\b")
# En el titular solo se usan los nombres que no se confunden con palabras comunes.
_AMBIGUOS = {"meta", "cesar", "sucre", "cordoba", "bolivar", "magdalena", "valle del cauca", "cauca", "chile", "peru"}
_DEL_AREA = re.compile(r"\b(barranquilla|soledad|malambo|galapa|puerto colombia)\b")

# Notas que no cuentan un hecho nuevo: se miran solo en el titular.
_BALANCE = re.compile(
    r"\b\d{2,}\s+(mujeres|personas|hombres|homicidios|masacres|asesinatos|muertes|victimas|feminicidios)\b"
    r"|\b(registra|registran|reporta|reportan|suma|suman)\s+\d+"
    r"|riesgo de feminicidio|enciende las alarmas|premios?\b"
)
_JUDICIAL = re.compile(
    r"^(condenan|condenado|condenada|aseguran|imputan|cargos|llaman a juicio|a juicio|a indagacion|absuelven|juez|fiscalia)\b"
    r"|\b(indagacion previa|medida de aseguramiento|fue condenad[oa]|condenan a|aseguran a|seguira investigando)\b"
)
_ACCIDENTE = re.compile(r"\b(accidente|choque|chocar|choco|atropell\w*|volco|volcamiento|ahogad[oa]|ahogo|naufragio|hundio|electrocutad[oa]|ola golpeo)\b")
_VIOLENTO = re.compile(r"asesin|sicari|a bala|a tiros|disparo|balead|homicid|feminicid|apunal|machete|arma")


def motivo_exclusion(nota: dict) -> str | None:
    """Por qué una nota con tipo de delito no es un hecho nuevo en el área, o None."""
    titular = normalizar(nota.get("titular", ""))
    texto = normalizar(f"{nota.get('titular', '')} {nota.get('resumen', '')}")
    if nota.get("municipio") == "fuera_del_area":
        return "fuera_del_area"
    titular, texto = _LUGARES_DEL_AREA.sub(" ", titular), _LUGARES_DEL_AREA.sub(" ", texto)
    if any(m not in _AMBIGUOS for m in FUERA_DEL_AREA.findall(titular)) and not _DEL_AREA.search(titular):
        return "fuera_del_area"
    if not nota.get("municipio") and FUERA_DEL_AREA.search(texto):
        return "fuera_del_area"
    if _BALANCE.search(titular):
        return "balance"
    if _JUDICIAL.search(titular):
        return "seguimiento_judicial"
    if _ACCIDENTE.search(titular) and not _VIOLENTO.search(titular):
        return "accidente"
    return None


def es_candidata(nota: dict) -> bool:
    """Una nota entra a los casos si habla de un delito dentro del área."""
    if nota.get("estado") == "descartado":
        return False
    if nota.get("estado") != "publicado" and motivo_exclusion(nota):
        return False
    return tipo_principal(nota) is not None


_ALIAS = re.compile(r"\balias\s+(?:[‘'\"“]([^’'\"”,.:;]{2,30}?)[’'\"”]|([a-z]+(?:\s+(?!de\b|del\b|la\b|en\b|y\b|que\b|fue\b)[a-z]+)?))")
_NUMERO_VICTIMA = re.compile(r"\b(?:la numero|el numero|la victima|la mujer|eleva a)\s+(\d{2,3})\b")
_NOMBRE = re.compile(r"(?<![\w])([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,})\s+((?:[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}\s*){1,2})")
# Palabras con mayúscula que no son nombres de personas.
_NO_NOMBRE = set(
    """villa san santa santo ciudad barrio sector diario libertad zona cero emisora atlantico impacto news policia
    fiscalia gobernacion alcaldia olimpica nueva nuevo los las la el del alta via calle carrera circunvalar cordialidad
    murillo barranquilla soledad malambo galapa puerto colombia rebolo bosque nieves prosperidad caribe verde
    tras sicarios asesinan identifican encuentran hallan joven mujer hombre redaccion judicial ejercito nacional
    fuerza publica corredor universitario mas alla clan golfo""".split()
) | {normalizar(w) for b in BARRIOS_CONOCIDOS for w in b.split() if len(w) > 3}
_ANTES_DE_LUGAR = re.compile(r"(?:\ben|barrio|sector|urbanizacion|hacia|frente a)\s*$")


def _identidad(nota: dict) -> set[str]:
    """Alias, nombres propios y número de víctima que identifican el hecho."""
    crudo = f"{nota.get('titular', '')}. {nota.get('resumen', '')}"
    t = normalizar(crudo)
    alias = {" ".join((a or b).split()) for a, b in _ALIAS.findall(t)}
    marcas = {"alias:" + a for a in alias if len(a) > 2 and a not in VACIAS}
    marcas |= {"victima:" + n for n in _NUMERO_VICTIMA.findall(t)}
    for m in _NOMBRE.finditer(crudo):
        if _ANTES_DE_LUGAR.search(normalizar(crudo[max(0, m.start() - 12):m.start()])):
            continue
        partes = [m[1], *m[2].split()]
        if any(normalizar(p) in _NO_NOMBRE for p in partes):
            continue
        marcas.add("nombre:" + normalizar(" ".join(partes[:2])))
    return marcas


_EDAD = re.compile(
    r"(?:\bde|,)\s+(\d{1,2})\s+anos\b(?!\s+de\s+(?:prision|carcel|condena|creacion|fundacion|historia|servicio|trayectoria))"
)


def _edades(nota: dict) -> set[str]:
    """Edades de las víctimas que menciona la nota ("un hombre de 42 años")."""
    return set(_EDAD.findall(normalizar(f"{nota.get('titular', '')}. {nota.get('resumen', '')}")))


def _persona(nota: dict) -> set[str]:
    """Solo nombre y alias: sirven para unir notas separadas por varios días."""
    return {m for m in _identidad(nota) if m.startswith(("nombre:", "alias:"))}


def _palabras(texto: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", normalizar(texto)) if len(w) > 2 and w not in VACIAS}


def palabras(nota: dict) -> tuple[set[str], set[str]]:
    """Palabras del titular solo, y del titular más el resumen."""
    titular = _palabras(nota.get("titular", ""))
    return titular, titular | _palabras(nota.get("resumen", ""))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def similitud(a: tuple[set[str], set[str]], b: tuple[set[str], set[str]]) -> float:
    """La mayor entre la similitud de titulares y la de titular más resumen:
    dos medios suelen copiar el titular aunque el resumen sea distinto."""
    return max(_jaccard(a[0], b[0]), _jaccard(a[1], b[1]))


def _fecha(nota: dict) -> date | None:
    f = nota.get("fecha_publicacion")
    return date.fromisoformat(f[:10]) if f else None


def _compatibles(t1: str, t2: str) -> bool:
    return t1 == t2 or any(t1 in g and t2 in g for g in COMPATIBLES)


def _mismo_barrio(a: dict, b: dict) -> bool | None:
    """True si coinciden, False si ambos existen y difieren, None si no se sabe.

    Si una nota no tiene barrio pero su texto nombra el barrio de la otra
    (\"en San Isidro\" sin la palabra \"barrio\"), cuenta como el mismo barrio."""
    b1, b2 = a.get("barrio"), b.get("barrio")
    if b1 and b2:
        return normalizar(b1) == normalizar(b2)
    conocido, otra = (b1, b) if b1 else (b2, a)
    if conocido:
        texto = normalizar(f"{otra.get('titular', '')} {otra.get('resumen', '')}")
        if re.search(rf"\b{re.escape(normalizar(conocido))}\b", texto):
            return True
    return None


def comparar(a: dict, b: dict, pa: tuple[set[str], set[str]], pb: tuple[set[str], set[str]]) -> str:
    """Devuelve 'unir', 'duda' o 'distinto'."""
    ta, tb = tipo_principal(a), tipo_principal(b)
    if not ta or not tb or not _compatibles(ta, tb):
        return "distinto"
    fa, fb = _fecha(a), _fecha(b)
    if not fa or not fb:
        return "distinto"
    dias = abs((fa - fb).days)
    if dias > DIAS_MAX:
        if dias > DIAS_MAX_MISMA_PERSONA or (a.get("municipio") and b.get("municipio") and a["municipio"] != b["municipio"]):
            return "distinto"
        if _persona(a) & _persona(b):
            return "unir"
        # Misma edad y mismo barrio también identifican a la víctima.
        return "unir" if _edades(a) & _edades(b) and _mismo_barrio(a, b) else "distinto"
    if (a.get("municipio") and b.get("municipio") and a["municipio"] != b["municipio"]):
        return "distinto"
    barrio = _mismo_barrio(a, b)
    sim = similitud(pa, pb)
    if _identidad(a) & _identidad(b):
        # Misma persona, alias o número de víctima: es el mismo hecho aunque
        # un medio ubique el barrio distinto (Villa Sol / Villa María).
        return "unir"
    if barrio is False:
        return "distinto"
    ea, eb = _edades(a), _edades(b)
    if ea and eb and not ea & eb:
        # Edades distintas: son víctimas distintas aunque el texto se parezca.
        return "distinto"
    if barrio is True:
        # Mismo barrio, tipo compatible y a 2 días o menos: casi siempre es el
        # mismo hecho contado por otro medio o en una nota de seguimiento.
        return "unir"
    if sim >= UMBRAL_UNIR:
        return "unir"
    if ea & eb and sim >= UMBRAL_DUDA:
        # Texto parecido y la misma edad de la víctima.
        return "unir"
    if sim >= UMBRAL_DUDA:
        return "duda"
    if ea & eb:
        # Solo coincide la edad: puede ser otra víctima, que lo decida el editor.
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


def _revisado(caso: dict) -> bool:
    return caso.get("estado") in ("publicado", "descartado") or bool(caso.get("revisado_por"))


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

    # Lo que el editor ya revisó se respeta. Las uniones automáticas de
    # corridas anteriores no: se recalculan con las reglas vigentes.
    for c in previos or []:
        if not _revisado(c):
            continue
        presentes = [idx[i] for i in c.get("notas", []) if i in idx]
        for k in presentes[1:]:
            u.unir(presentes[0], k)

    for i in range(len(cand)):
        fi = _fecha(cand[i])
        for j in range(i + 1, len(cand)):
            fj = _fecha(cand[j])
            if fi and fj and (fj - fi).days > DIAS_MAX_MISMA_PERSONA:
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
    usados: set[str] = set()
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
            "fuentes": [{"medio": n["medio"], "url": n["url"], "titular": n.get("titular", "")} for n in ns],
            "estado": "pendiente",
            "posible_duplicado_de": [],
        }
        # Si el grupo toca varios casos previos, manda el que revisó el editor.
        previos_grupo = [previo_por_nota[i] for i in ids if i in previo_por_nota and previo_por_nota[i].get("caso_id") not in usados]
        prev = next((c for c in previos_grupo if _revisado(c)), previos_grupo[0] if previos_grupo else None)
        if prev:
            campos = ("caso_id", "estado", "tipo", "barrio", "municipio", "fecha", "revisado_por", "revisado_en") if _revisado(prev) else ("caso_id",)
            for campo in campos:
                if campo in prev and prev[campo] is not None:
                    caso[campo] = prev[campo]
        usados.add(caso["caso_id"])
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
