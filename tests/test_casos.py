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


def test_misma_persona_o_alias_une_aunque_cambie_el_barrio():
    notas = [
        nota("a", "zona-cero", "En la terraza de su casa asesinan a tía de alias ‘Kevin Masacre’ en el barrio Las Nieves", "2026-11-15", ["homicidio"], "Las Nieves", None),
        nota("b", "impacto", "Ataque sicarial contra núcleo familiar de alias Kevin Masacre: asesinaron a su tía", "2026-11-16", ["homicidio"]),
        nota("c", "la-libertad", "Investigan posible móvil pasional en el asesinato de Katy Mendoza, de 18 años", "2026-11-18", ["homicidio"], "El Bosque"),
        nota("d", "la-libertad", "Investigan si amenazas estarían detrás del crimen de Katy Mendoza", "2026-11-18", ["homicidio"], "La Paz"),
    ]
    casos = agrupar(notas)
    assert sorted(len(c["notas"]) for c in casos) == [2, 2]


def test_mismo_numero_de_victima_une():
    notas = [
        nota("a", "zona-cero", "Asesinan a bala a una mujer en Villa María: la número 80 en lo que va del 2026", "2026-11-18", ["homicidio"], "Villa María", "Soledad"),
        nota("b", "impacto", "Mujer fue asesinada en Soledad y pasó a ser la víctima 80 en 2026", "2026-11-18", ["homicidio"], None, "Soledad"),
    ]
    assert len(agrupar(notas)) == 1


def test_no_une_nombres_de_barrio_como_si_fueran_personas():
    notas = [
        nota("a", "zona-cero", "Asesinan a mototaxista en Alfonso López", "2026-11-10", ["homicidio"], None, None),
        nota("b", "ctv", "Hallan muerta a una mujer en Alfonso López", "2026-11-10", ["homicidio"], None, None),
    ]
    assert len(agrupar(notas)) == 2


def test_excluye_balances_seguimientos_accidentes_y_otros_paises():
    titulares = [
        "Atlántico registra 80 mujeres asesinadas en 2026 y piden acciones urgentes",
        "Indepaz reporta 26 masacres y 87 víctimas en los primeros 100 días",
        "Condenan a 10 años a adolescente que asesinó a puñaladas a su novio",
        "Aseguran a cuatro presuntos integrantes de ‘Los Cabros’ por homicidio de adolescente",
        "Joven murió en accidente en moto en la Circunvalar",
        "Ataque israelí contra hospital en Gaza dejó seis muertos",
        "Encuentran asesinado en Sitionuevo a barranquillero que había sido secuestrado",
    ]
    notas = [nota(str(i), "ctv", t, "2026-11-12", ["homicidio"]) for i, t in enumerate(titulares)]
    assert agrupar(notas) == []


def test_simon_bolivar_es_un_barrio_del_area():
    notas = [nota("a", "ctv", "Un muerto y un herido en ataque a bala frente a un billar en Simón Bolívar", "2026-11-15", ["homicidio"], municipio=None)]
    assert len(agrupar(notas)) == 1


def test_no_arrastra_uniones_automaticas_de_corridas_anteriores():
    notas = [
        nota("a", "zona-cero", "Asesinan a mujer en Villa María", "2026-11-18", ["homicidio"], None, "Soledad"),
        nota("b", "ctv", "Asesinan a motocarrista en Malambo", "2026-11-18", ["homicidio"], None, "Malambo"),
    ]
    previos = [{"caso_id": "x", "notas": ["a", "b"], "estado": "posible_duplicado"}]
    casos = agrupar(notas, previos)
    assert len(casos) == 2
    assert len({c["caso_id"] for c in casos}) == 2
    # Si el editor las unió, siguen juntas.
    previos[0]["estado"] = "publicado"
    assert len(agrupar(notas, previos)) == 1


def test_herido_que_muere_dias_despues_se_une_si_es_la_misma_persona():
    notas = [
        nota("a", "zona-cero", "Hieren a bala a Yeison Mercado en Rebolo", "2026-11-01", ["lesiones"], "Rebolo"),
        nota("b", "ctv", "Murió en el hospital Yeison Mercado, baleado la semana pasada", "2026-11-09", ["homicidio"]),
    ]
    casos = agrupar(notas)
    assert len(casos) == 1
    assert casos[0]["tipo"] == "homicidio"
    assert casos[0]["fecha"] == "2026-11-01"


def test_misma_persona_muy_lejos_en_el_tiempo_no_se_une():
    notas = [
        nota("a", "zona-cero", "Hieren a bala a Yeison Mercado en Rebolo", "2026-09-01", ["lesiones"], "Rebolo"),
        nota("b", "ctv", "Asesinan a Yeison Mercado en Rebolo", "2026-11-09", ["homicidio"], "Rebolo"),
    ]
    assert len(agrupar(notas)) == 2


def test_union_del_editor_conserva_su_caso_si_se_suma_otra_nota():
    a = nota("a", "zona-cero", "Asesinan a mototaxista en Rebolo", "2026-11-10", ["homicidio"], "Rebolo")
    b = nota("b", "ctv", "Hallan cuerpo de hombre en la vía", "2026-11-10", ["homicidio"])
    c = nota("c", "impacto", "Mototaxista asesinado en el barrio Rebolo", "2026-11-11", ["homicidio"], "Rebolo")
    previos = [
        {"caso_id": "otro", "notas": ["c"], "estado": "pendiente"},
        {"caso_id": "editor", "notas": ["a", "b"], "estado": "publicado", "revisado_por": "yo", "barrio": "Rebolo"},
    ]
    casos = agrupar([a, b, c], previos)
    assert len(casos) == 1
    assert casos[0]["caso_id"] == "editor"
    assert casos[0]["estado"] == "publicado"


def test_misma_edad_sola_queda_como_posible_duplicado():
    notas = [
        nota("a", "zona-cero", "Matan a un hombre de 42 años en Soledad", "2026-11-10", ["homicidio"], municipio="Soledad"),
        nota("b", "ctv", "Sicarios asesinan a hombre de 42 años frente a su casa en Soledad", "2026-11-10", ["homicidio"], municipio="Soledad"),
    ]
    casos = agrupar(notas)
    # Solo coincide la edad: no se unen solos, pero quedan para que el editor decida.
    assert len(casos) == 2
    assert all(c["estado"] == "posible_duplicado" for c in casos)


def test_edades_distintas_no_se_unen_aunque_el_texto_se_parezca():
    notas = [
        nota("a", "zona-cero", "Asesinan a mototaxista de 25 años en el sur de Barranquilla", "2026-11-10", ["homicidio"]),
        nota("b", "ctv", "Asesinan a mototaxista de 52 años en el sur de Barranquilla", "2026-11-10", ["homicidio"]),
    ]
    assert len(agrupar(notas)) == 2


def test_herido_que_muere_dias_despues_misma_edad_y_barrio():
    notas = [
        nota("a", "zona-cero", "Hieren a bala a joven de 19 años en Rebolo", "2026-11-01", ["lesiones"], "Rebolo"),
        nota("b", "ctv", "Murió el joven de 19 años baleado en Rebolo", "2026-11-07", ["homicidio"], "Rebolo"),
    ]
    assert len(agrupar(notas)) == 1
