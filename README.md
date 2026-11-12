# Observatorio BAQ

Mapa y tablero abiertos de los delitos reportados por la prensa en Barranquilla y su área metropolitana. Es un proyecto periodístico.

Los datos salen de notas publicadas por medios locales. De cada nota se guarda solo el titular, la fecha, el enlace y un resumen corto. Cada punto del mapa enlaza a la nota original.

## Scraper

```bash
pip install -r requirements.txt
python -m scraper                          # todas las fuentes
python -m scraper --fuentes zona-cero -v   # una fuente, con detalle
```

Desde GitHub: pestaña **Actions** → **Scraper** → **Run workflow**. Al terminar, el resumen muestra cuántas notas trajo cada medio y el archivo queda como artefacto `notas`. Si se marca "Guardar", las notas nuevas se suben a `data/notas.json`.

Escribe `data/notas.json`: una entrada por nota con `id`, `medio`, `url`, `titular`, `resumen` (máx. 300 caracteres), `fecha_publicacion`, `fecha_captura`, `tipos_delito`, `municipio`, `barrio` y `estado` (`pendiente` al llegar). Las notas ya guardadas no se vuelven a abrir ni se sobrescriben, así que las correcciones del equipo se conservan.

### Fuentes

| Prioridad | Medio | Método |
| --- | --- | --- |
| 1 | Zona Cero | Sección `/judiciales` y metadatos de cada nota |
| 1 | Diario La Libertad | Sección Crónica Judicial, 10 s entre peticiones (su `Crawl-delay`) |
| 2 | Emisora Atlántico | RSS, categoría Judiciales |
| 3 | Impacto News | RSS, categoría Judiciales |
| 3 | CTV Barranquilla | Sección `/category/judiciales` y metadatos de cada nota |

Quedan fuera El Heraldo y El Tiempo, porque prohíben el scraping sin permiso escrito, y ADN Barranquilla, La Cháchara y Q'hubo Barranquilla, porque bloquean el acceso.

### Reglas

- User-agent propio (`ObservatorioBAQ/0.1`) con enlace a este repositorio.
- Lee el `robots.txt` de cada medio y no visita rutas prohibidas. Si el `robots.txt` no se puede leer o responde 401/403, no visita ese medio.
- Al menos 5 s entre peticiones al mismo dominio, o el `Crawl-delay` del medio si es mayor.
- No guarda el cuerpo de los artículos, las fotos ni los comentarios. Tampoco se usa el contenido para entrenar modelos de IA (La Libertad y CTV lo prohíben con `ai-train=no`).
- La clasificación de tipo de delito, municipio y barrio se hace por palabras clave y es provisional: el equipo la revisa antes de publicar un caso.

## Casos

```bash
python -m casos --reporte reporte-casos.md
```

Lee `data/notas.json` y escribe `data/casos.json`: un caso por hecho, con las notas de todos los medios que lo cubrieron. Dos notas se unen cuando el tipo de delito es compatible (un herido que luego muere sigue siendo el mismo hecho), las fechas están a 2 días o menos y el barrio coincide o los textos se parecen mucho. Los pares dudosos no se unen: quedan con estado `posible_duplicado` para que el editor decida. Las capturas sin otro delito y las notas de fuera del área metropolitana no generan casos.

Cada caso empieza como `pendiente`. Si el editor cambia el `estado` (`publicado`, `descartado`), el tipo o el barrio en `data/casos.json`, la siguiente corrida conserva esos cambios.

El flujo **Scraper** corre solo todos los días a las 6:00 a. m. (hora de Barranquilla), guarda las notas nuevas y los casos, y deja el resumen de casos en la pestaña Actions.

## Página

`web/index.html` es la página pública: mapa (Leaflet con mapas de OpenStreetMap y CARTO), barrios con más casos, tendencia semanal y últimos casos, con modo claro y oscuro. Lee `data/casos.json`.

El flujo **Página** ubica los barrios con Nominatim (máximo una consulta por segundo, con caché en `data/geocodigos.json`) y publica en GitHub Pages cada vez que cambian los datos en `main` y después de cada corrida del scraper. Para activarlo una sola vez: **Settings → Pages → Source: GitHub Actions**.

Para verla en local:

```bash
python -m casos && mkdir -p _site/data && cp web/index.html _site/ && cp data/casos.json _site/data/
python -m http.server -d _site 8000
```

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest
```
