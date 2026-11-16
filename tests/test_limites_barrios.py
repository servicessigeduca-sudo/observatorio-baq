from publico.limites_barrios import clave, construir


def _way(i, nombre, x, y, d=0.004, **tags):
    pts = [(x, y), (x + d, y), (x + d, y + d), (x, y + d), (x, y)]
    return {"type": "way", "id": i, "tags": {"name": nombre, **tags}, "geometry": [{"lon": a, "lat": b} for a, b in pts]}


def test_clave():
    assert clave("Barrio El Bosque") == "el bosque"
    assert clave("Urbanización Villa Olímpica") == "villa olimpica"
    assert clave("7 de Abril") == "7 de abril"


def test_construir_asigna_municipio_y_prefiere_limite_administrativo():
    muni = _way(1, "Barranquilla", -74.9, 10.9, d=0.2)
    muni = {"type": "relation", "id": 1, "tags": {"name": "Barranquilla", "boundary": "administrative", "admin_level": "6"},
            "members": [{"type": "way", "role": "outer", "geometry": muni["geometry"]}]}
    datos = {"elements": [
        muni,
        _way(2, "El Bosque", -74.85, 10.95, boundary="administrative", admin_level="10"),
        _way(3, "Barrio El Bosque", -74.80, 10.95, landuse="residential"),
        _way(4, "Las Nieves", -74.82, 10.93, place="neighbourhood"),
        _way(5, "Fuera", -75.5, 10.5, place="neighbourhood"),
        _way(6, "Enorme", -74.89, 10.91, d=0.1, place="suburb"),
    ]}
    fc = construir(datos, {"Barranquilla|Nieves": "Las Nieves"})
    por = {f["properties"]["clave"]: f for f in fc["features"]}
    assert set(por) == {"el bosque", "las nieves"}
    assert por["el bosque"]["geometry"]["coordinates"][0][0][0] < -74.84  # el administrativo, no la urbanización
    assert por["las nieves"]["properties"]["otros"] == ["nieves"]
    assert fc["municipios"] == ["Barranquilla"]


def test_titulo():
    from publico.limites_barrios import titulo
    assert titulo("VILLA SAN PEDRO II") == "Villa San Pedro II"
    assert titulo("LAS NIEVES") == "Las Nieves"
    assert titulo("BARRIO DE LA PAZ") == "Barrio de la Paz"


def test_con_pot_reemplaza_barranquilla():
    from publico.limites_barrios import con_pot
    cuadro = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}
    fc = {"municipios": ["Barranquilla", "Soledad"], "features": [
        {"properties": {"barrio": "Osm", "municipio": "Barranquilla", "clave": "osm", "otros": []}, "geometry": cuadro},
        {"properties": {"barrio": "Ferrocarril", "municipio": "Soledad", "clave": "ferrocarril", "otros": []}, "geometry": cuadro}]}
    pot = {"features": [{"properties": {"nombre": "EL SANTUARIO"}, "geometry": cuadro}]}
    out = con_pot(fc, pot, {"Barranquilla|Santuario": "El Santuario"})
    claves = {(f["properties"]["municipio"], f["properties"]["clave"]) for f in out["features"]}
    assert claves == {("Barranquilla", "el santuario"), ("Soledad", "ferrocarril")}
    assert next(f for f in out["features"] if f["properties"]["clave"] == "el santuario")["properties"]["otros"] == ["santuario"]


def test_zonas_aproximadas_para_barrios_con_solo_un_punto():
    muni = {"type": "relation", "id": 1, "tags": {"name": "Soledad", "boundary": "administrative", "admin_level": "6"},
            "members": [{"type": "way", "role": "outer", "geometry": [{"lon": a, "lat": b} for a, b in
                         [(-74.80, 10.88), (-74.76, 10.88), (-74.76, 10.92), (-74.80, 10.92), (-74.80, 10.88)]]}]}
    datos = {"elements": [
        muni,
        _way(2, "Con Limite", -74.79, 10.90, d=0.004, place="neighbourhood"),
        {"type": "node", "id": 3, "lat": 10.905, "lon": -74.775, "tags": {"name": "Ferrocarril", "place": "neighbourhood"}},
        {"type": "node", "id": 4, "lat": 10.905, "lon": -74.770, "tags": {"name": "Pumarejo", "place": "neighbourhood"}},
        {"type": "node", "id": 5, "lat": 10.902, "lon": -74.788, "tags": {"name": "Con Limite", "place": "neighbourhood"}},
    ]}
    fc = construir(datos, {}, [{"municipio": "Soledad", "barrio": "Las Moras", "centro": [10.89, -74.775]},
                               {"municipio": "Soledad", "barrio": "Pumarejo", "centro": [10.885, -74.79]}])
    por = {f["properties"]["clave"]: f["properties"] for f in fc["features"]}
    assert set(por) == {"con limite", "ferrocarril", "pumarejo", "las moras"}
    assert not por["con limite"].get("aprox")
    assert por["ferrocarril"]["aprox"] and por["las moras"]["aprox"]
    from shapely.geometry import Point, shape
    geo = {f["properties"]["clave"]: shape(f["geometry"]) for f in fc["features"]}
    assert geo["pumarejo"].contains(Point(-74.770, 10.905))  # el punto de OSM gana al centro de los datos
    assert not geo["ferrocarril"].intersects(geo["pumarejo"].buffer(-1e-6))
    assert geo["ferrocarril"].bounds[2] - geo["ferrocarril"].bounds[0] < 0.009  # cortada a ~440 m
