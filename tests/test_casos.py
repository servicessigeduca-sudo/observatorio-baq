from casos.agrupar import agrupar


def nota(id, medio, titular, fecha, tipos, barrio=None, municipio="Barranquilla", resumen=""):
    return {
        "id": id, "medio": medio, "url": f"https://{medio}.co/{id}", "titular": titular, "resumen": resumen,
        "fecha_publicacion": f"{fecha}T08:00:00-05:00", "tipos_delito": tipos, "barrio": barrio,
        "municipio": municipio, "estado": "pendiente",
    }


def test_une_mismo_hecho_en_dos_medios_por_barrio():
    notas = [
        nota("a", "zona-cero", "Asesinan a bala a mototaxista en el barrio Rebolo", "2026-11-10", ["homicidio"], "Rebolo"),
        nota("b", "ctv", "Mototaxista fue asesinado a tiros en Rebolo", "2026-11-11", ["homicidio"], "Rebolo"),
    ]
    casos = agrupar(notas)
    assert len(casos) == 1
    assert casos[0]["medios"] == ["ctv", "zona-cero"]
    assert casos[0]["fecha"] == "2026-11-10"


def test_no_une_barrios_distintos():
    notas = [
        nota("a", "zona-cero", "Asesinan a bala a mototaxista en el barrio Rebolo", "2026-11-10", ["homicidio"], "Rebolo"),
        nota("b", "ctv", "Asesinan a bala a mototaxista en el barrio La Luz", "2026-11-10", ["homicidio"], "La Luz"),
    ]
    assert len(agrupar(notas)) == 2


def test_no_une_fechas_lejanas_ni_tipos_distintos():
    notas = [
        nota("a", "zona-cero", "Asesinan a comerciante en Rebolo", "2026-11-01", ["homicidio"], "Rebolo"),
        nota("b", "ctv", "Asesinan a comerciante en Rebolo", "2026-11-09", ["homicidio"], "Rebolo"),
        nota("c", "ctv", "Roban a comerciante en Rebolo", "2026-11-01", ["hurto"], "Rebolo"),
    ]
    assert len(agrupar(notas)) == 3


def test_herido_que_luego_muere_es_un_homicidio():
    notas = [
        nota("a", "zona-cero", "Joven herido a bala en el barrio Carrizal tras riña", "2026-11-10", ["lesiones"], "Carrizal"),
        nota("b", "ctv", "Murió el joven herido a bala en Carrizal tras riña", "2026-11-11", ["homicidio", "lesiones"], "Carrizal"),
    ]
    casos = agrupar(notas)
    assert len(casos) == 1 and casos[0]["tipo"] == "homicidio"


def test_sin_barrio_une_solo_si_el_texto_se_parece():
    notas = [
        nota("a", "zona-cero", "Asesinan a vendedor de tinto frente al estadio Metropolitano", "2026-11-10", ["homicidio"]),
        nota("b", "ctv", "Vendedor de tinto asesinado frente al estadio Metropolitano", "2026-11-10", ["homicidio"]),
        nota("c", "impacto", "Asesinan a conductor de bus en la Circunvalar", "2026-11-10", ["homicidio"]),
    ]
    casos = agrupar(notas)
    assert len(casos) == 2


def test_excluye_capturas_y_fuera_del_area():
    notas = [
        nota("a", "zona-cero", "Capturan a alias el Flaco", "2026-11-10", ["captura"]),
        nota("b", "ctv", "Asesinan a hombre en Sabanalarga", "2026-11-10", ["homicidio"], municipio="fuera_del_area"),
    ]
    assert agrupar(notas) == []


def test_conserva_lo_que_reviso_el_editor():
    notas = [nota("a", "zona-cero", "Asesinan a hombre en Rebolo", "2026-11-10", ["homicidio"], "Rebolo")]
    primero = agrupar(notas)
    primero[0]["estado"] = "publicado"
    primero[0]["barrio"] = "San Roque"
    notas.append(nota("b", "ctv", "Hombre asesinado en Rebolo", "2026-11-10", ["homicidio"]))
    segundo = agrupar(notas, primero)
    caso = next(c for c in segundo if "a" in c["notas"])
    assert caso["estado"] == "publicado" and caso["barrio"] == "San Roque"
    assert caso["caso_id"] == primero[0]["caso_id"]


def test_geocodificar_usa_la_cache_sin_red(tmp_path):
    import json
    from casos.geocodificar import clave, geocodificar
    cache = tmp_path / "geo.json"
    cache.write_text(json.dumps({clave("Rebolo", "Barranquilla"): {"lat": 10.96, "lon": -74.78}}))
    casos = [
        {"barrio": "Rebolo", "municipio": "Barranquilla"},
        {"barrio": "Inexistente", "municipio": "Soledad"},
        {"barrio": None, "municipio": None},
    ]
    assert geocodificar(casos, cache, consultar_red=False) == 0
    assert (casos[0]["lat"], casos[0]["confianza_ubicacion"]) == (10.96, "alta")
    assert casos[1]["lat"] is None and casos[1]["confianza_ubicacion"] == "municipio"
    assert casos[2]["confianza_ubicacion"] == "baja"


def test_barrio_nombrado_sin_la_palabra_barrio():
    notas = [
        nota("a", "zona-cero", "Asesinan de seis disparos a conductor cuando reparaban su vehículo en San Isidro", "2026-11-12", ["homicidio"]),
        nota("b", "emisora", "Asesinan a tiros a hombre en el barrio San Isidro", "2026-11-12", ["homicidio"], "San Isidro"),
    ]
    assert len(agrupar(notas)) == 1


def test_excluye_notas_de_otros_departamentos():
    notas = [nota("a", "ctv", "Ataque contra la Policía en Casanare: un uniformado muerto", "2026-11-12", ["homicidio"], municipio=None)]
    assert agrupar(notas) == []
