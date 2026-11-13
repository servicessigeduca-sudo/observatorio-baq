import json
from datetime import date, datetime, timedelta, timezone

from publico.construir import construir, posible_retraso
from publico.cuadricula import celda, fusionar, zonas
from publico.limpieza import (anio_valido, modalidad_de_texto, normalizar_modalidad, normalizar_municipio,
                              normalizar_sexo, revisar_fecha)
from publico.registro import normalizar_localidad, normalizar_modalidad_registro, normalizar_sexo_registro, procesar

HOY = date(2026, 11, 13)


def test_municipios_mal_escritos():
    assert normalizar_municipio("PUERTO COLOMBIA") == "Puerto Colombia"
    assert normalizar_municipio("Pto. Colombia") == "Puerto Colombia"
    assert normalizar_municipio("Barranquila") == "Barranquilla"
    assert normalizar_municipio("SOLEAD") == "Soledad"
    assert normalizar_municipio("Municipio de Galapa") == "Galapa"
    assert normalizar_municipio("Sabanalarga") is None
    assert normalizar_municipio(None) is None


def test_sexo_y_modalidad():
    assert normalizar_sexo("NO REPORTA") == "Sin dato"
    assert normalizar_sexo("FEMENINO") == "Mujer"
    assert normalizar_sexo_registro("MACULINO") == "Hombre"
    assert normalizar_sexo_registro("FEMANINO") == "Mujer"
    assert normalizar_sexo_registro("Según lo manifestado por el hermano de la víctima...") == "Sin dato"
    assert normalizar_modalidad("ARMA BLANCA / CORTOPUNZANTE") == "Arma blanca"
    assert normalizar_modalidad("NO REPORTADO") == "Sin dato"
    assert normalizar_modalidad_registro("SICARITO") == "Sicariato"
    assert normalizar_modalidad_registro("SICIARIATO") == "Sicariato"
    assert normalizar_modalidad_registro("RIÑAS") == "Riña"
    assert normalizar_modalidad_registro("RILA") == "Riña"
    assert normalizar_modalidad_registro("Manifiesta el cuadrante, que reciben información de los vecinos") == "Sin dato"
    assert modalidad_de_texto("Lo asesinaron a bala en Rebolo") == "Arma de fuego"
    assert modalidad_de_texto("Hombre herido con cuchillo") == "Arma blanca"


def test_localidades():
    assert normalizar_localidad("METRPOLITANA", "Barranquilla") == "Metropolitana"
    assert normalizar_localidad("NORTE CENTRI HISTORICO", "Barranquilla") == "Norte-Centro Histórico"
    assert normalizar_localidad("SURPORIENTE", "Barranquilla") == "Suroriente"
    assert normalizar_localidad("SOLEAD", "Soledad") == "Soledad"


def test_fechas_y_anios():
    assert anio_valido(2026, hoy=HOY) and not anio_valido(20226, hoy=HOY) and not anio_valido(None)
    assert revisar_fecha("2026-12-01", hoy=HOY) == "futura"
    assert revisar_fecha("2026-11-10", "2026-11-09T08:00:00-05:00", hoy=HOY) == "posterior_a_la_nota"
    assert revisar_fecha("2026-11-08", "2026-11-09T08:00:00-05:00", hoy=HOY) is None
    assert revisar_fecha("no", hoy=HOY) == "invalida"


def test_fusion_de_celdas_llega_a_tres():
    grupos, ocultos = fusionar({(0, 0): 1, (0, 1): 1, (0, 2): 5, (10, 10): 2, (10, 12): 1, (30, 30): 1})
    assert all(g["n"] >= 3 for g in grupos)
    assert ocultos == 1  # la celda aislada no se publica
    assert sum(g["n"] for g in grupos) + ocultos == 11
    # La celda pequeña se une con la vecina más pequeña, no con la más grande.
    grupos, _ = fusionar({(0, 0): 1, (0, 1): 2, (1, 0): 9})
    assert {"celdas": [(0, 0), (0, 1)], "n": 3} in grupos


def test_zonas_no_revelan_puntos():
    pts = [(10.95, -74.78), (10.9501, -74.7801), (10.951, -74.781), (11.10, -74.90)]
    zs, de = zonas(pts)
    assert len(zs) == 1 and zs[0]["n"] == 3 and de[3] is None
    assert celda(*pts[0]) in [tuple(c) for c in zs[0]["celdas"]]


def test_posible_retraso():
    assert posible_retraso(50, [90, 100, 110, 95])
    assert not posible_retraso(90, [90, 100, 110, 95])
    assert not posible_retraso(10, [None, 5])


def _ms(y, m, d, h=12):
    return int(datetime(y, m, d, h, tzinfo=timezone(timedelta(hours=-5))).timestamp() * 1000)


def _capa():
    feats = []
    for k in range(4):
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [-74.78 + k * 1e-4, 10.95]},
                      "properties": {"municipio": "BARRANQUILLA", "barrio": "REBOLO", "localidad": "SURORIENTE", "año": 2026,
                                     "mesennumero": 3, "hora": _ms(2026, 3, 5 + k), "NOMBRE_DEL_OCCISO": "Nombre Secreto",
                                     "direccion": "Calle 1 # 2-3", "SEXO": "MASCULINO", "MODALIDAD": "SICARIATO",
                                     "DESCRIPCION": "Texto de los hechos"}})
    feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [-74.9, 10.6]},
                  "properties": {"municipio": "SABANALARGA", "año": 2026, "mesennumero": 3, "hora": _ms(2026, 3, 9)}})
    feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [-74.78, 10.95]},
                  "properties": {"municipio": "BARRANQUILLA", "barrio": "REBOLO", "año": 20226, "mesennumero": 4,
                                 "hora": _ms(2026, 4, 2), "SEXO": "FEMANINO", "MODALIDAD": "RILA"}})
    return {"type": "FeatureCollection", "features": feats}


def test_registro_no_publica_datos_personales():
    reg = procesar(_capa(), hoy=HOY)
    texto = json.dumps(reg, ensure_ascii=False)
    for prohibido in ("Nombre Secreto", "Calle 1", "Texto de los hechos", "hora", "direccion", "-74.7801", "-74.7803"):
        assert prohibido not in texto
    assert reg["calidad"]["fuera_del_area"] == 1
    assert reg["calidad"]["alertas_fecha"] == {"anio_o_mes_inconsistente": 1}
    total = {(f[0], f[5], f[6]): f[-1] for f in reg["filas"]}
    assert total[("2026-03", "Hombre", "Sicariato")] == 4
    assert total[("2026-04", "Mujer", "Riña")] == 1  # el mes sale de la fecha del hecho, no del año mal digitado


def test_construir_sin_titulares_ni_coordenadas(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    notas = [{"id": "n1", "medio": "Zona Cero", "url": "https://zc.co/1", "titular": "Asesinan a Pedro Pérez a bala en Rebolo",
              "resumen": "", "fecha_publicacion": "2026-11-10T08:00:00-05:00", "fecha_captura": "2026-11-01T08:00:00-05:00"}]
    casos = [{"caso_id": "c1", "tipo": "homicidio", "fecha": "2026-11-10", "municipio": "Barranquila", "barrio": "Rebolo",
              "notas": ["n1"], "fuentes": [{"medio": "Zona Cero", "url": "https://zc.co/1", "titular": notas[0]["titular"]}],
              "estado": "pendiente", "lat": 10.9512345, "lon": -74.7712345},
             {"caso_id": "c2", "tipo": "hurto", "fecha": "2026-12-30", "municipio": "Soledad", "notas": [], "fuentes": [], "estado": "pendiente"}]
    (data / "notas.json").write_text(json.dumps(notas))
    (data / "casos.json").write_text(json.dumps(casos))
    (data / "oficiales.json").write_text(json.dumps({"ultimo_mes": {"anio": 2026, "mes": 9},
        "tablas": {"mensual": {"filas": [[2026, 9, "Barranquilla", "homicidio", 30]]}}}))
    res = construir(tmp_path, hoy=HOY, ahora=datetime(2026, 11, 13, 6, tzinfo=timezone(timedelta(hours=-5))))
    pub = data / "publico"
    prensa = json.loads((pub / "prensa.json").read_text())
    texto = (pub / "prensa.json").read_text()
    assert "Pedro" not in texto and "10.9512345" not in texto and "2026-11-10" not in texto
    assert [c["id"] for c in prensa["casos"]] == ["c1"]  # el caso con fecha futura no se publica
    assert prensa["casos"][0]["municipio"] == "Barranquilla" and prensa["casos"][0]["mes"] == "2026-11"
    assert prensa["casos"][0]["zona"] is None  # un solo caso: su celda no se publica
    assert res["semana"]["casos"] == 1 and res["calidad"]["prensa"]["fecha_futura"] == 1
    assert (pub / "prensa_vs_oficial.csv").read_text().startswith("mes,municipio,delito,prensa,oficial")
    assert (data / "cortes" / "2026-11-13.json").exists()
    assert json.loads((pub / "informes" / "index.json").read_text())["informes"]


def test_barrios_con_errores_de_digitacion():
    from publico.registro import nombre_barrio
    assert nombre_barrio("SANTODOMINGO") == "Santo Domingo"
    assert nombre_barrio("EL MANALTIAL") == "El Manantial"
    assert nombre_barrio("LOS OLIVOS II") == "Los Olivos 2"
    assert nombre_barrio("VILLA DEL REY") == "Villa del Rey"
