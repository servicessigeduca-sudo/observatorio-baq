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
