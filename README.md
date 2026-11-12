# Observatorio BAQ

**[Ver el mapa → servicessigeduca-sudo.github.io/observatorio-baq](https://servicessigeduca-sudo.github.io/observatorio-baq/)**

Mapa y tablero abiertos de los delitos reportados por la prensa en Barranquilla y su área metropolitana. Es un proyecto periodístico.

En la página puedes:

- Ver en el mapa dónde ocurren los casos, por barrio o caso por caso.
- Filtrar por tipo de delito (homicidio, lesiones, hurto, extorsión, otros) y por periodo.
- Comparar los barrios con más casos y la tendencia semana a semana.
- Leer los últimos casos con el enlace a cada noticia original.
- Cambiar entre modo claro y oscuro.

Los datos salen de notas publicadas por Zona Cero, Diario La Libertad, Emisora Atlántico, Impacto News y CTV Barranquilla. Cuando varios medios cubren el mismo hecho, se cuenta una sola vez. La página se actualiza sola cada día a las 6:00 a. m. (hora de Barranquilla).

**Datos preliminares:** la clasificación es automática y un editor revisa cada caso. Mientras tanto, la página marca los casos como "Sin revisar".

## Datos abiertos

| Archivo | Qué contiene |
| --- | --- |
| [`data/casos.json`](data/casos.json) | Un registro por hecho: tipo, fecha, barrio, municipio, ubicación aproximada, medios y enlaces |
| [`data/notas.json`](data/notas.json) | Una entrada por noticia: medio, titular, fecha, enlace y resumen corto |
| [`data/geocodigos.json`](data/geocodigos.json) | Coordenadas de cada barrio según OpenStreetMap, corregibles a mano |

## Cómo revisar casos

En `data/casos.json`, cambia el `estado` de un caso a `publicado` (revisado) o `descartado`, o corrige su `tipo` o `barrio`. La corrida diaria conserva esos cambios. Si un barrio sale en un lugar equivocado del mapa, corrige sus coordenadas en `data/geocodigos.json`.

---

# Detalles técnicos

## Página web

`web/index.html` es la página pública: mapa (Leaflet con el mapa base gris de Esri), barrios con más casos, tendencia semanal y últimos casos, con modo claro y oscuro. Lee `data/casos.json`.

El flujo **Página** ubica los barrios con Nominatim (máximo una consulta por segundo, con caché en `data/geocodigos.json`) y publica en GitHub Pages cada vez que cambian los datos en `main` y después de cada corrida del scraper. Para activarlo una sola vez: **Settings → Pages → Source: GitHub Actions**.

Para verla en local:

```bash
python -m casos && mkdir -p _site/data && cp web/index.html _site/ && cp data/casos.json _site/data/
python -m http.server -d _site 8000
```

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

## Agrupación en casos

```bash
python -m casos --reporte reporte-casos.md
```

Lee `data/notas.json` y escribe `data/casos.json`: un caso por hecho, con las notas de todos los medios que lo cubrieron. Dos notas se unen cuando el tipo de delito es compatible (un herido que luego muere sigue siendo el mismo hecho), las fechas están a 2 días o menos y el barrio coincide o los textos se parecen mucho. Los pares dudosos no se unen: quedan con estado `posible_duplicado` para que el editor decida. Las capturas sin otro delito y las notas de fuera del área metropolitana no generan casos.

Cada caso empieza como `pendiente`. Si el editor cambia el `estado` (`publicado`, `descartado`), el tipo o el barrio en `data/casos.json`, la siguiente corrida conserva esos cambios.

El flujo **Scraper** corre solo todos los días a las 6:00 a. m. (hora de Barranquilla), guarda las notas nuevas y los casos, y deja el resumen de casos en la pestaña Actions.

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest
```
