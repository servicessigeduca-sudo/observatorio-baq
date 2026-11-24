"""Arma los datos que publica el sitio, a partir de los datos internos.

Entradas: data/casos.json, data/notas.json (prensa), data/oficiales.json
(Policía), data/publico/registro.json (capa de homicidios, ya agregada) y
data/poblacion.json.

Salidas en data/publico/: archivos JSON que lee el sitio y CSV de datos
abiertos, con diccionario de variables. Una copia fechada del resumen y de
los agregados queda en data/cortes/ para poder reproducir cada análisis.

Reglas de privacidad: no se publica nombre, dirección, hora ni descripción
de los hechos. Ubicación por barrio o zona de cuadrícula (celdas fusionadas
hasta tener 3 casos) y fecha por mes. De la prensa no se publica el titular
(puede nombrar a la víctima): se publica un resumen propio y el enlace.
"""

from __future__ import annotations

import csv
import io
import json
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .cuadricula import TAMANO_M, zonas
from .lista_barrios import DANE, a_csv
from .nombres_barrio import Referencia
from .limpieza import MUNICIPIOS, modalidad_de_texto, normalizar_modalidad, normalizar_municipio, normalizar_sexo, revisar_fecha

BOGOTA = timezone(timedelta(hours=-5))
LICENCIA = "CC BY 4.0: uso libre citando «Observatorio BAQ» y la fuente original de cada dato"
SITIO = "https://servicessigeduca-sudo.github.io/observatorio-baq/"
CITA = "Observatorio BAQ ({anio}). Datos abiertos sobre delitos en Barranquilla y su área metropolitana. Corte: {corte}. " + SITIO

TIPOS = {  # grupo: (nombre, tipos de prensa, categorías oficiales comparables)
    "hom": ("Homicidio", {"homicidio", "feminicidio"}, ["homicidio"]),
    "les": ("Lesiones", {"lesiones"}, ["lesiones"]),
    "hur": ("Hurto", {"hurto"}, ["hurto_personas", "hurto_comercio", "hurto_residencias", "hurto_carros", "hurto_motos", "hurto_entidades"]),
    "ext": ("Extorsión", {"extorsion"}, ["extorsion"]),
    "otr": ("Otros", set(), []),
}
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def grupo(tipo: str | None) -> str:
    for k, (_, de, _) in TIPOS.items():
        if tipo in de:
            return k
    return "otr"


def nombre_mes(mes: str) -> str:
    a, m = mes.split("-")
    return f"{MESES[int(m) - 1]} de {a}"


def _mes(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _meses(desde: str, hasta: str) -> list[str]:
    a, m = map(int, desde.split("-"))
    b, n = map(int, hasta.split("-"))
    out = []
    while (a, m) <= (b, n):
        out.append(f"{a:04d}-{m:02d}")
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)
    return out


def _fin_de_mes(mes: str) -> date:
    a, m = map(int, mes.split("-"))
    return (date(a + (m == 12), m % 12 + 1, 1)) - timedelta(days=1)


def _pct(a: float, b: float) -> int | None:
    return round(100 * (a - b) / b) if b else None


# ---------------------------------------------------------------- prensa

FUENTE_REGISTRO = "Base de homicidios 2026 (capa ArcGIS del Atlántico), usada con autorización de su propietario"


def oficializar_registro(registro: dict | None, ref: Referencia) -> dict | None:
    """Une las grafías de un mismo barrio del registro («Santo Domingo» y «Santo Domingo de Guzman»)
    bajo el nombre más usado, para que un barrio no se cuente partido en dos."""
    if not registro:
        return registro
    usos = defaultdict(Counter)  # (municipio, nombre oficial) -> grafías y cuántos casos
    for f in registro["filas"]:
        oficial = ref.oficial(f[3], f[1]) if f[3] != "Sin barrio" else None
        if oficial:
            usos[(f[1], oficial)][f[3]] += f[-1]
    nombre = {}
    for (m, oficial), grafias in usos.items():
        elegido = max(grafias, key=lambda g: (grafias[g], g == oficial))
        for g in grafias:
            nombre[(m, g)] = elegido
    filas = Counter()
    for *k, n in registro["filas"]:
        k[3] = nombre.get((k[1], k[3]), k[3])
        filas[tuple(k)] += n
    barrios = {}
    for b in registro.get("barrios", []):
        b = {**b, "barrio": nombre.get((b["municipio"], b["barrio"]), b["barrio"])}
        previo = barrios.get((b["municipio"], b["barrio"]))
        if previo is None or (previo.get("centro") is None and b.get("centro")):
            barrios[(b["municipio"], b["barrio"])] = b
    return {**registro, "filas": [list(k) + [n] for k, n in filas.items()],
            "barrios": sorted(barrios.values(), key=lambda b: (b["municipio"], b["barrio"]))}


def fuera_de_lista(internos: list[dict], registro: dict | None, ref: Referencia) -> dict:
    """Nombres de barrio que no están en la lista única, con cuántos casos tienen, para agregarlos como alias."""
    faltan = {"prensa": Counter(), "registro": Counter()}
    for c in internos:
        if c["barrio"] and c["municipio"] and not ref.oficial(c["barrio"], c["municipio"]):
            faltan["prensa"][f'{c["barrio"]} ({c["municipio"]})'] += 1
    for f in (registro or {}).get("filas", []):
        if f[3] != "Sin barrio" and not ref.oficial(f[3], f[1]):
            faltan["registro"][f"{f[3]} ({f[1]})"] += f[-1]
    return {k: dict(v.most_common()) for k, v in faltan.items()}


def prensa_publica(casos: list[dict], notas: list[dict], hoy: date) -> tuple[dict, list[dict], dict]:
    """Casos de prensa sin datos sensibles. Devuelve (publicable, internos con fecha, calidad)."""
    por_nota = {n["id"]: n for n in notas}
    internos, calidad = [], Counter()
    for c in casos:
        if c.get("estado") == "descartado":
            continue
        notas_c = [por_nota[i] for i in c.get("notas", []) if i in por_nota]
        publicada = min((n.get("fecha_publicacion") or "" for n in notas_c), default=None) or None
        alerta = revisar_fecha(c.get("fecha"), publicada, hoy)
        if alerta in ("sin_fecha", "invalida", "futura", "anio_invalido"):
            calidad[f"fecha_{alerta}"] += 1
            continue
        if alerta:
            calidad[f"fecha_{alerta}"] += 1
        muni_txt = c.get("municipio")
        muni = normalizar_municipio(muni_txt)
        if muni_txt and muni and muni != muni_txt:
            calidad["municipio_corregido"] += 1
        texto = " ".join((n.get("titular") or "") + " " + (n.get("resumen") or "") for n in notas_c)
        barrio = c.get("barrio") if c.get("lat") is not None or c.get("barrio") else None
        internos.append({
            "id": c["caso_id"], "fecha": date.fromisoformat(c["fecha"]), "tipo": c.get("tipo"), "grupo": grupo(c.get("tipo")),
            "municipio": muni, "barrio": barrio,
            "lat": c.get("lat"), "lon": c.get("lon"), "modalidad": modalidad_de_texto(texto),
            "medios": [{"medio": f.get("medio"), "url": f.get("url")} for f in c.get("fuentes") or []],
            "revisado": c.get("estado") == "publicado", "alerta_fecha": alerta,
        })
    internos.sort(key=lambda x: (x["fecha"], x["id"]), reverse=True)
    lista_zonas, de = zonas([(c["lat"], c["lon"]) for c in internos], prefijo="p")
    publicos = []
    for c, z in zip(internos, de):
        c["zona"] = z
        lugar = ", ".join(x for x in (c["barrio"], c["municipio"]) if x) or "el área metropolitana (sin barrio identificado)"
        n = len(c["medios"])
        publicos.append({
            "id": c["id"], "mes": _mes(c["fecha"]), "grupo": c["grupo"], "tipo": c["tipo"], "municipio": c["municipio"],
            "barrio": c["barrio"], "zona": z, "modalidad": c["modalidad"], "revisado": c["revisado"],
            "resumen": f"{TIPOS[c['grupo']][0] if c['grupo'] != 'otr' else (c['tipo'] or 'Hecho').capitalize().replace('_', ' ')} reportado en {lugar}, "
                       f"{nombre_mes(_mes(c['fecha']))}. Lo {'cubrieron' if n > 1 else 'cubrió'} {n} {'medios' if n > 1 else 'medio'}.",
            "medios": c["medios"],
        })
    barrios = defaultdict(list)
    for c in internos:
        if c["barrio"] and c["lat"] is not None:
            barrios[(c["municipio"], c["barrio"])].append((c["lat"], c["lon"]))
    return ({"casos": publicos, "zonas": lista_zonas,
             "barrios": [{"municipio": m, "barrio": b, "centro": [round(p[0][0], 3), round(p[0][1], 3)]} for (m, b), p in sorted(barrios.items(), key=lambda x: (str(x[0][0]), x[0][1]))]},
            internos, dict(calidad))


# ---------------------------------------------------------------- oficiales

def oficial_mensual(oficiales: dict) -> dict[tuple[str, str, str], int]:
    """(mes, municipio, grupo) -> casos, solo para los grupos comparables con la prensa."""
    cat_a_grupo = {cat: g for g, (_, _, cats) in TIPOS.items() for cat in cats}
    out: dict[tuple[str, str, str], int] = defaultdict(int)
    for anio, mes, muni, cat, n in (oficiales.get("tablas", {}).get("mensual", {}).get("filas") or []):
        g = cat_a_grupo.get(cat)
        if g:
            out[(f"{anio:04d}-{mes:02d}", muni, g)] += n
    return out


def homicidios_oficiales(oficial: dict, oficiales: dict, lista_inf: list[dict]) -> dict | None:
    """Cifra principal de la portada: homicidios de la Policía en el área, en lo que va del año.

    Cuenta hasta el último mes con datos completos (según los informes mensuales), para
    no mostrar como baja un mes que todavía está cargándose, y compara con el mismo
    periodo del año anterior. Incluye la serie de los últimos 24 meses para el gráfico.
    """
    ult = oficiales.get("ultimo_mes") or {}
    if not ult:
        return None
    ultimo = f"{ult['anio']:04d}-{ult['mes']:02d}"
    total = lambda m: sum(n for (mes, _, g), n in oficial.items() if mes == m and g == "hom")
    incompletos = {i["periodo"] for i in lista_inf if i.get("estado") == "incompleto"}
    completos = [m for m in _meses(f"{ult['anio']:04d}-01", ultimo) if m not in incompletos]
    hasta = completos[-1] if completos else ultimo
    anio, mes_fin = map(int, hasta.split("-"))
    actual = sum(total(f"{anio:04d}-{m:02d}") for m in range(1, mes_fin + 1))
    previo = sum(total(f"{anio - 1:04d}-{m:02d}") for m in range(1, mes_fin + 1))
    a0, m0 = map(int, ultimo.split("-"))
    desde = f"{a0 - 2 + (m0 == 12):04d}-{m0 % 12 + 1:02d}"
    return {"fuente": "Policía Nacional (SIEDCO)", "anio": anio, "desde": f"{anio:04d}-01", "hasta": hasta,
            "ultimo_publicado": ultimo, "casos": actual, "anio_anterior": previo, "variacion_pct": _pct(actual, previo),
            "dias": (_fin_de_mes(hasta) - date(anio, 1, 1)).days + 1,
            "por_mes": [{"mes": m, "casos": total(m), "incompleto": m > hasta} for m in _meses(desde, ultimo)]}


def oficial_perfil(oficiales: dict) -> list[list]:
    """Género, edad y arma de los datos oficiales con valores normalizados."""
    t = oficiales.get("tablas", {})
    filas: dict[tuple, int] = defaultdict(int)
    for anio, muni, cat, v, n in (t.get("genero", {}).get("filas") or []):
        filas[(anio, muni, cat, "sexo", normalizar_sexo(v))] += n
    for anio, muni, cat, v, n in (t.get("armas", {}).get("filas") or []):
        filas[(anio, muni, cat, "modalidad", normalizar_modalidad(v))] += n
    for anio, muni, cat, v, n in (t.get("edad", {}).get("filas") or []):
        filas[(anio, muni, cat, "edad", str(v).capitalize() if v and not str(v).startswith("NO ") else "Sin dato")] += n
    return [list(k) + [n] for k, n in sorted(filas.items(), key=lambda x: tuple(str(v) for v in x[0]))]


# ---------------------------------------------------------------- registro

def registro_mensual(registro: dict | None) -> dict[tuple[str, str], int]:
    out: dict[tuple[str, str], int] = defaultdict(int)
    if registro:
        for fila in registro["filas"]:
            out[(fila[0], fila[1])] += fila[-1]
    return out


# ---------------------------------------------------------------- resumen y comparación

def resumen(internos: list[dict], hoy: date, inicio_prensa: date | None) -> dict:
    hasta = hoy - timedelta(days=1)  # el último día completo
    def ventana(fin: date):
        ini = fin - timedelta(days=6)
        sel = [c for c in internos if ini <= c["fecha"] <= fin]
        return ini, fin, sel
    i1, f1, act = ventana(hasta)
    i0, f0, ant = ventana(hasta - timedelta(days=7))
    zonas_sem = Counter((c["municipio"], c["barrio"]) for c in act if c["barrio"])
    munis_sem = Counter(c["municipio"] for c in act if c["municipio"])
    zona = None
    if zonas_sem:
        (m, b), n = sorted(zonas_sem.items(), key=lambda x: (-x[1], str(x[0])))[0]
        zona = {"nivel": "barrio", "nombre": b, "municipio": m, "casos": n}
    if munis_sem and (not zona or zona["casos"] < 2):
        m, n = sorted(munis_sem.items(), key=lambda x: (-x[1], x[0]))[0]
        zona = {"nivel": "municipio", "nombre": m, "municipio": m, "casos": n}
    ant_parcial = bool(inicio_prensa and i0 < inicio_prensa)
    semanas = []
    for k in range(25, -1, -1):
        fin = hasta - timedelta(days=7 * k)
        ini = fin - timedelta(days=6)
        semanas.append({"desde": ini.isoformat(), "hasta": fin.isoformat(),
                        "casos": sum(1 for c in internos if ini <= c["fecha"] <= fin),
                        "parcial": bool(inicio_prensa and ini < inicio_prensa)})
    return {
        "semana": {"desde": i1.isoformat(), "hasta": f1.isoformat(), "casos": len(act),
                   "por_tipo": dict(Counter(c["grupo"] for c in act)),
                   "anterior": {"desde": i0.isoformat(), "hasta": f0.isoformat(), "casos": len(ant), "parcial": ant_parcial},
                   "variacion_pct": None if ant_parcial else _pct(len(act), len(ant)),
                   "zona": zona},
        "semanal": semanas,
    }


def comparacion(internos, oficial, reg_mes, oficiales, registro, inicio_prensa, hoy) -> list[dict]:
    ult = oficiales.get("ultimo_mes") or {}
    ultimo_oficial = f"{ult.get('anio', 0):04d}-{ult.get('mes', 0):02d}" if ult else None
    prensa = Counter((_mes(c["fecha"]), c["municipio"], c["grupo"]) for c in internos if c["municipio"])
    desde = "2026-01"
    hasta = _mes(hoy)
    filas = []
    for mes in _meses(desde, hasta):
        for muni in MUNICIPIOS:
            for g in ("hom", "les", "hur", "ext"):
                of = oficial.get((mes, muni, g)) if ultimo_oficial and mes <= ultimo_oficial else None
                pr = prensa.get((mes, muni, g), 0)
                rg = reg_mes.get((mes, muni)) if g == "hom" and registro and mes <= registro["corte"][:7] else None
                if g == "hom" and rg is None and registro and mes <= registro["corte"][:7]:
                    rg = 0
                notas = []
                prensa_completa = bool(inicio_prensa and date.fromisoformat(mes + "-01") >= inicio_prensa and _fin_de_mes(mes) < hoy)
                if not prensa_completa:
                    notas.append("prensa_parcial")
                if of is not None and mes >= _mes(_fin_de_mes(ultimo_oficial) - timedelta(days=60)):
                    notas.append("oficial_provisional")
                if rg is not None and mes == registro["corte"][:7] and registro["corte"] < _fin_de_mes(mes).isoformat():
                    notas.append("registro_incompleto")
                filas.append({"mes": mes, "municipio": muni, "delito": g, "prensa": pr,
                              "oficial": of if of is not None else (0 if ultimo_oficial and mes <= ultimo_oficial else None),
                              "registro": rg,
                              "proporcion_prensa": round(pr / of, 3) if of and prensa_completa else None,
                              "notas": notas})
    return filas


# ---------------------------------------------------------------- informes

def posible_retraso(valor: int | None, previos: list[int | None], umbral: float = 0.6) -> bool:
    """True si un mes reciente tiene mucho menos casos que la mediana de los anteriores (carga atrasada)."""
    vals = sorted(v for v in previos if v)
    if valor is None or len(vals) < 3:
        return False
    mediana = vals[len(vals) // 2] if len(vals) % 2 else (vals[len(vals) // 2 - 1] + vals[len(vals) // 2]) / 2
    return valor < umbral * mediana


def informes(internos, comp, registro, oficiales, hoy, inicio_prensa) -> tuple[list[dict], dict]:
    """Un informe mensual por cada mes con datos de alguna fuente, con la plantilla fija."""
    ult = oficiales.get("ultimo_mes") or {}
    ultimo_oficial = f"{ult.get('anio', 0):04d}-{ult.get('mes', 0):02d}"
    por_mes = defaultdict(lambda: defaultdict(lambda: {"prensa": 0, "oficial": None, "registro": None}))
    for f in comp:
        if f["delito"] != "hom":
            continue
        d = por_mes[f["mes"]][f["municipio"]]
        d["prensa"] += f["prensa"]
        d["oficial"] = f["oficial"]
        d["registro"] = f["registro"]
    reg_barrios = defaultdict(Counter)
    reg_mod = defaultdict(Counter)
    reg_sexo = defaultdict(Counter)
    if registro:
        for mes, muni, loc, barrio, zona, sexo, mod, n in registro["filas"]:
            if barrio != "Sin barrio":
                reg_barrios[mes][(barrio, muni)] += n
            reg_mod[mes][mod] += n
            reg_sexo[mes][sexo] += n
    meses = sorted(m for m in por_mes if any((v["registro"] or 0) + (v["oficial"] or 0) + v["prensa"] for v in por_mes[m].values()))
    lista, docs = [], {}
    def total(m, campo):
        vals = [v[campo] for v in por_mes.get(m, {}).values() if v[campo] is not None]
        return sum(vals) if vals else None
    for i, mes in enumerate(meses):
        anterior = meses[i - 1] if i else None
        reg, reg_ant = total(mes, "registro"), total(anterior, "registro") if anterior else None
        of, pr = total(mes, "oficial"), total(mes, "prensa")
        if not inicio_prensa or mes < _mes(inicio_prensa):
            pr = None  # antes de la recolección diaria, la prensa no se puede comparar
        fuente_principal = "registro" if reg is not None else ("oficial" if of is not None else "prensa")
        if reg is None and of is None and pr is None:
            continue
        principal = {"registro": reg, "oficial": of, "prensa": pr}[fuente_principal]
        incompleto, motivos = False, []
        if mes >= _mes(hoy):
            incompleto, motivos = True, ["El mes no ha terminado."]
        if registro and mes == registro["corte"][:7] and registro["corte"] < _fin_de_mes(mes).isoformat():
            incompleto = True
            motivos.append(f"La base de homicidios llega hasta el {int(registro['corte'][8:])} de {nombre_mes(mes)}.")
        if of is not None and mes == ultimo_oficial:
            motivos.append("Las cifras de la Policía de este mes son provisionales y suelen subir en los meses siguientes.")
        if registro and reg is not None and mes >= _mes(date.fromisoformat(registro["corte"]) - timedelta(days=62)) and posible_retraso(reg, [total(m, "registro") for m in meses[max(0, i - 6):i]]):
            incompleto = True
            motivos.append("Posible retraso en la carga: el mes tiene muchos menos casos que los seis anteriores, así que puede no ser una caída real.")
        top = reg_barrios[mes].most_common(5)
        nombre_fuente = {"registro": "la base de homicidios", "oficial": "la Policía Nacional", "prensa": "la prensa local"}[fuente_principal]
        frases = []
        if principal is not None:
            frases.append(f"En {nombre_mes(mes)} {nombre_fuente} contó {principal} homicidios en el área metropolitana"
                          + (" (cifra parcial)." if incompleto else "."))
        if reg is not None and reg_ant and not incompleto:
            v = _pct(reg, reg_ant)
            frases.append(f"Son {abs(reg - reg_ant)} {'más' if reg > reg_ant else 'menos'} que en {MESES[int(anterior[5:]) - 1]} ({'+' if v > 0 else ''}{v} %)." if v else f"La misma cifra que en {MESES[int(anterior[5:]) - 1]}.")
        if top and top[0][1] >= 3:
            frases.append(f"El barrio con más casos fue {top[0][0][0]} ({top[0][0][1]}), con {top[0][1]}.")
        if of is not None and reg is not None:
            frases.append(f"La Policía Nacional registró {of} en el mismo mes; la comparación entre fuentes está al final del informe.")
        munis = sorted(((m, v[fuente_principal]) for m, v in por_mes[mes].items() if v[fuente_principal]), key=lambda x: -x[1])
        tendencia = [{"mes": m, "registro": total(m, "registro"), "oficial": total(m, "oficial"),
                      "prensa": total(m, "prensa") if inicio_prensa and date.fromisoformat(m + "-01") >= inicio_prensa.replace(day=1) else None}
                     for m in meses[max(0, i - 11): i + 1]]
        mods = reg_mod[mes]
        doc = {
            "periodo": mes, "titulo": f"Informe de {nombre_mes(mes)}", "tipo": "mensual",
            "estado": "incompleto" if incompleto else "completo", "motivos": motivos,
            "generado": hoy.isoformat(), "fuente_principal": fuente_principal,
            "resumen": frases,
            "cifras": [x for x in [
                {"etiqueta": "Homicidios en la base 2026", "valor": reg, "comparacion": _pct(reg, reg_ant) if reg is not None and reg_ant and not incompleto else None, "frente_a": nombre_mes(anterior) if anterior else None} if reg is not None else None,
                {"etiqueta": "Homicidios según la Policía", "valor": of, "comparacion": None, "frente_a": None} if of is not None else None,
                {"etiqueta": "Homicidios en la prensa", "valor": pr, "comparacion": None, "frente_a": None} if pr is not None else None,
                {"etiqueta": "Por sicariato", "valor": mods.get("Sicariato"), "comparacion": round(100 * mods["Sicariato"] / sum(mods.values())) if mods.get("Sicariato") else None, "frente_a": "% del total"} if mods else None,
            ] if x],
            "zonas": {"municipios": [{"nombre": m, "casos": n} for m, n in munis],
                      "barrios": [{"nombre": b, "municipio": m, "casos": n} for (b, m), n in top if n >= 3]},
            "perfil": {"modalidad": dict(reg_mod[mes]), "sexo": dict(reg_sexo[mes])} if reg is not None else None,
            "tendencia": tendencia,
            "limitaciones": [
                "La prensa no cubre todos los casos: sus cifras muestran lo que llega a los medios, no el total.",
                "La base de homicidios y las cifras de la Policía pueden diferir por fecha de corte, criterio de registro y municipio asignado.",
                "Los barrios con menos de 3 casos en el mes no se nombran.",
                "Los datos no permiten atribuir causas: muestran cuántos casos hubo, dónde y cuándo.",
            ] + ([f"La cobertura automática de prensa empezó el {inicio_prensa.day} de {MESES[inicio_prensa.month - 1]} de {inicio_prensa.year}" + "; antes de esa fecha solo hay notas sueltas."] if inicio_prensa and date.fromisoformat(mes + "-01") < inicio_prensa else []),
        }
        docs[mes] = doc
        lista.append({"periodo": mes, "titulo": doc["titulo"], "estado": doc["estado"], "homicidios": principal, "fuente": fuente_principal})
    return list(reversed(lista)), docs


# ---------------------------------------------------------------- escritura

def _csv(columnas: list[str], filas: list[list]) -> str:
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(columnas)
    w.writerows(filas)
    return out.getvalue()


def diccionario(corte: dict) -> dict:
    return {
        "licencia": LICENCIA, "cita": CITA.format(anio=date.today().year, corte=corte.get("prensa")), "corte": corte,
        "archivos": {
            "prensa_mensual.csv": {"fuente": "Notas de Zona Cero, Diario La Libertad, Emisora Atlántico, Impacto News y CTV Barranquilla",
                "descripcion": "Casos reportados por la prensa local, contados por mes, municipio, barrio, delito y modalidad.",
                "variables": {"mes": "Año y mes del hecho (AAAA-MM)", "municipio": "Municipio del área metropolitana; vacío si la nota no lo dice",
                              "barrio": "Barrio mencionado en la nota; vacío si no lo dice", "delito": "hom, les, hur, ext u otr (ver «delitos»)",
                              "modalidad": "Arma de fuego, Arma blanca o Sin dato, deducida del titular", "casos": "Número de casos (un hecho cubierto por varios medios cuenta una vez)", "cod_municipio": "Código DANE del municipio (Barranquilla 08001, Soledad 08758, Malambo 08433, Galapa 08296, Puerto Colombia 08573)", "cod_barrio": "Código del barrio en barrios.csv; vacío si el nombre no está en la lista"}},
            "registro_homicidios.csv": {"fuente": FUENTE_REGISTRO,
                "descripcion": "Homicidios de la base 2026 en los cinco municipios, contados por mes, ubicación agregada, sexo y modalidad. Sin nombres, direcciones, horas ni descripciones.",
                "variables": {"mes": "Año y mes del hecho (AAAA-MM), según la fecha y hora del registro", "municipio": "Municipio",
                              "localidad": "Localidad de Barranquilla, o el municipio", "barrio": "Barrio del registro, con mayúsculas normalizadas",
                              "zona": f"Zona de cuadrícula de {TAMANO_M} m: celdas con menos de 3 casos fusionadas con sus vecinas (ver zonas en registro.json); vacía si la celda quedó aislada",
                              "sexo": "Hombre, Mujer o Sin dato", "modalidad": "Sicariato, Riña, Hurto, Por establecer o Sin dato (errores de digitación corregidos)", "casos": "Número de homicidios", "cod_municipio": "Código DANE del municipio (Barranquilla 08001, Soledad 08758, Malambo 08433, Galapa 08296, Puerto Colombia 08573)", "cod_barrio": "Código del barrio en barrios.csv; vacío si el nombre no está en la lista"}},
            "barrios.csv": {"fuente": "Barranquilla: Barrios según POT (Alcaldía de Barranquilla, datos.gov.co). Otros municipios: © colaboradores de OpenStreetMap (ODbL)",
                "descripcion": "Lista única de barrios del área metropolitana que usa el observatorio para unir nombres entre fuentes.",
                "variables": {"codigo": "Código del observatorio: código DANE del municipio + nombre sin tildes", "barrio": "Nombre del barrio",
                              "municipio": "Municipio", "cod_municipio": "Código DANE del municipio",
                              "alias": "Otras formas de escribirlo que el sitio reconoce, separadas por «;»",
                              "limite": "POT, OpenStreetMap, aproximado o sin límite"}},
            "prensa_vs_oficial.csv": {"fuente": "Prensa, Policía Nacional (SIEDCO) y base de homicidios 2026",
                "descripcion": "Comparación por mes, municipio y delito.",
                "variables": {"mes": "AAAA-MM", "municipio": "Municipio", "delito": "hom, les, hur o ext", "prensa": "Casos en la prensa",
                              "oficial": "Casos registrados por la Policía; vacío si aún no se publican", "registro": "Homicidios del registro (solo hom)",
                              "proporcion_prensa": "prensa ÷ oficial, solo en meses con cobertura de prensa completa", "notas": "prensa_parcial, oficial_provisional, registro_incompleto"}},
            "oficiales_mensual.csv": {"fuente": "Policía Nacional, SIEDCO", "descripcion": "Delitos registrados por la Policía por año, mes, municipio y categoría, desde 2003.",
                "variables": {"anio": "Año", "mes": "Mes (1-12)", "municipio": "Municipio", "categoria": "Categoría de delito", "cantidad": "Casos"}},
            "oficiales_perfil.csv": {"fuente": "Policía Nacional, SIEDCO", "descripcion": "Sexo, edad y arma o medio por año, con valores normalizados.",
                "variables": {"anio": "Año", "municipio": "Municipio", "categoria": "Categoría de delito", "variable": "sexo, edad o modalidad",
                              "valor": "Valor normalizado (por ejemplo, «NO REPORTA» y «NO REGISTRA» pasan a «Sin dato»)", "cantidad": "Casos"}},
        },
        "delitos": {k: v[0] for k, v in TIPOS.items()},
    }


def construir(raiz: Path, hoy: date | None = None, ahora: datetime | None = None) -> dict:
    ahora = ahora or datetime.now(BOGOTA)
    hoy = hoy or ahora.date()
    d = raiz / "data"
    leer = lambda p, defecto: json.loads(p.read_text(encoding="utf-8")) if p.exists() else defecto
    casos, notas = leer(d / "casos.json", []), leer(d / "notas.json", [])
    oficiales = leer(d / "oficiales.json", {})
    pub = d / "publico"
    ref = Referencia.desde(raiz)
    registro = oficializar_registro(leer(pub / "registro.json", None), ref)
    if registro:
        registro["fuente"] = FUENTE_REGISTRO
    poblacion = leer(d / "poblacion.json", {})

    capturas = [n.get("fecha_captura") for n in notas if n.get("fecha_captura")]
    inicio_prensa = datetime.fromisoformat(min(capturas)).date() if capturas else None
    prensa, internos, calidad = prensa_publica(casos, notas, hoy)
    oficial = oficial_mensual(oficiales)
    comp = comparacion(internos, oficial, registro_mensual(registro), oficiales, registro, inicio_prensa, hoy)
    lista_inf, docs_inf = informes(internos, comp, registro, oficiales, hoy, inicio_prensa)
    ult = oficiales.get("ultimo_mes") or {}
    corte = {"prensa": (hoy - timedelta(days=1)).isoformat(), "inicio_prensa": inicio_prensa.isoformat() if inicio_prensa else None,
             "oficial": f"{ult['anio']:04d}-{ult['mes']:02d}" if ult else None, "oficial_actualizado": oficiales.get("actualizado"),
             "registro": registro["corte"] if registro else None}
    meta = {"generado": ahora.isoformat(timespec="minutes"), "corte": corte, "licencia": LICENCIA,
            "cita": CITA.format(anio=hoy.year, corte=corte["prensa"])}
    res = {**meta, **resumen(internos, hoy, inicio_prensa),
           "totales": {"prensa": len(internos), "prensa_con_barrio": sum(1 for c in internos if c["barrio"]),
                       "prensa_revisados": sum(1 for c in internos if c["revisado"]),
                       "registro": sum(f[-1] for f in registro["filas"]) if registro else None},
           "homicidios": homicidios_oficiales(oficial, oficiales, lista_inf),
           "poblacion": poblacion, "calidad": {"prensa": calidad, "registro": registro.get("calidad") if registro else None,
                                               "barrios_fuera_de_la_lista": fuera_de_lista(internos, registro, ref)}}

    pub.mkdir(parents=True, exist_ok=True)
    (pub / "informes").mkdir(exist_ok=True)
    escribir = lambda p, obj: p.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    escribir(pub / "prensa.json", {**meta, "fuente": "Prensa local de Barranquilla", **prensa})
    escribir(pub / "resumen.json", res)
    escribir(pub / "prensa_vs_oficial.json", {**meta, "filas": comp})
    escribir(pub / "informes" / "index.json", {**meta, "informes": lista_inf})
    for mes, doc in docs_inf.items():
        escribir(pub / "informes" / f"{mes}.json", doc)
    escribir(pub / "diccionario.json", diccionario(corte))

    pm = Counter((c["mes"], c["municipio"] or "", c["barrio"] or "", c["grupo"], c["modalidad"]) for c in prensa["casos"])
    # Códigos DANE de municipio y de la lista única de barrios, para cruzar con otras bases.
    cods = lambda muni, barrio: [DANE.get(muni, ""), ref.codigo(barrio, muni) if barrio and barrio != "Sin barrio" else ""]
    (pub / "prensa_mensual.csv").write_text(_csv(["mes", "municipio", "barrio", "delito", "modalidad", "casos", "cod_municipio", "cod_barrio"],
                                                 [list(k) + [n] + cods(k[1], k[2]) for k, n in sorted(pm.items())]), encoding="utf-8")
    (pub / "barrios.csv").write_text(a_csv(ref.lista()), encoding="utf-8")
    # Registro público de cambios en los datos (se edita a mano en data/cambios.json).
    escribir(pub / "cambios.json", sorted(leer(d / "cambios.json", []), key=lambda c: c["fecha"], reverse=True))
    (pub / "prensa_vs_oficial.csv").write_text(_csv(["mes", "municipio", "delito", "prensa", "oficial", "registro", "proporcion_prensa", "notas"],
        [[f["mes"], f["municipio"], f["delito"], f["prensa"], f["oficial"], f["registro"], f["proporcion_prensa"], " ".join(f["notas"])] for f in comp]), encoding="utf-8")
    (pub / "oficiales_perfil.csv").write_text(_csv(["anio", "municipio", "categoria", "variable", "valor", "cantidad"], oficial_perfil(oficiales)), encoding="utf-8")
    if registro:
        escribir(pub / "registro.json", registro)
        (pub / "registro_homicidios.csv").write_text(_csv(registro["columnas"] + ["cod_municipio", "cod_barrio"],
                                                          [f + cods(f[1], f[3]) for f in registro["filas"]]), encoding="utf-8")

    # Copia fechada para reproducir los análisis de cada día.
    cortes = d / "cortes"
    cortes.mkdir(exist_ok=True)
    escribir(cortes / f"{hoy.isoformat()}.json", {"resumen": res, "prensa_mensual": [list(k) + [n] for k, n in sorted(pm.items())],
                                                   "registro_corte": corte["registro"], "oficial_corte": corte["oficial"]})
    return res
