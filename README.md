# Observatorio BAQ

**[Ver la página → servicessigeduca-sudo.github.io/observatorio-baq](https://servicessigeduca-sudo.github.io/observatorio-baq/)**

Observatorio abierto de la seguridad en Barranquilla y su área metropolitana: un solo sitio, con el mismo análisis para todos y tres niveles de profundidad (resumen, informe completo y datos descargables). Tiene seis secciones:

- **[Inicio](https://servicessigeduca-sudo.github.io/observatorio-baq/):** titular de la semana que se actualiza solo, buscador por barrio o municipio, vista previa del mapa, fuentes y límites, y enlace al último informe.
- **[Mapa](https://servicessigeduca-sudo.github.io/observatorio-baq/mapa.html):** un punto aproximado por caso (al azar dentro de su zona), homicidios por barrio con los límites de OpenStreetMap y mapa de calor en metros reales, con filtros de periodo, delito, municipio y modalidad guardados en la URL, y casos recientes de prensa.
- **[Informes](https://servicessigeduca-sudo.github.io/observatorio-baq/informes.html):** un informe por mes con plantilla fija y archivo por fecha.
- **[Prensa vs. oficial](https://servicessigeduca-sudo.github.io/observatorio-baq/prensa-oficial.html):** qué parte de los casos llega a los medios, por municipio y mes.
- **[Estadísticas oficiales](https://servicessigeduca-sudo.github.io/observatorio-baq/estadisticas.html):** los delitos que registra la Policía desde 2003 en los cinco municipios del área. Tiene media móvil de 12 meses, mapas de calor por mes y por día de la semana, variación anual por tipo de delito, promedios por periodo de Presidencia, Alcaldía y Gobernación, el peso de Barranquilla frente al resto del área, y arma, género y edad. Cada vista se descarga en CSV.
- **[Metodología y datos](https://servicessigeduca-sudo.github.io/observatorio-baq/metodologia.html):** cómo se obtienen y procesan los datos, y descargas.

Todas las páginas tienen modo claro y oscuro.

Los datos salen de notas publicadas por Zona Cero, Diario La Libertad, Emisora Atlántico, Impacto News y CTV Barranquilla. Cuando varios medios cubren el mismo hecho, se cuenta una sola vez. La página se actualiza sola cada día a las 6:00 a. m. (hora de Barranquilla).

**Datos preliminares:** la clasificación es automática y un editor revisa cada caso. Mientras tanto, la página marca los casos como "Sin revisar".

## Datos abiertos

| Archivo | Qué contiene |
| --- | --- |
| [`data/publico/`](data/publico) | Lo que publica el sitio: casos de prensa sin titulares, conteos del registro de homicidios 2026, comparación prensa vs. oficial, informes mensuales y diccionario de variables (CSV y JSON) |
| [`data/casos.json`](data/casos.json) | Uso interno: un registro por hecho, con titulares y ubicación aproximada. El sitio no lo publica |
| [`data/notas.json`](data/notas.json) | Una entrada por noticia: medio, titular, fecha, enlace y resumen corto |
| [`data/oficiales.json`](data/oficiales.json) | Delitos registrados por la Policía (SIEDCO) en los cinco municipios del área desde 2003: por mes, día de la semana, arma, género y edad, y qué años cubre cada delito. Sin barrio: la Policía no lo publica |
| [`data/oficiales_mensual.csv`](data/oficiales_mensual.csv) | La serie mensual anterior en CSV: año, mes, municipio, tipo y cantidad |
| [`data/publico/barrios.geojson`](data/publico/barrios.geojson) | Límites de barrio para el mapa por barrio: Barranquilla con la capa oficial del POT ([`data/barrios_pot.geojson`](data/barrios_pot.geojson), Alcaldía de Barranquilla en datos.gov.co) y los otros municipios con OpenStreetMap (ODbL). Lo arma el flujo **Límites de barrios** cada mes; los nombres que no coinciden se unen a mano en [`data/barrios_alias.json`](data/barrios_alias.json) |
| [`data/geocodigos.json`](data/geocodigos.json) | Coordenadas de cada barrio según OpenStreetMap, corregibles a mano |

## Cómo revisar casos

Entra al **[panel de revisión](https://servicessigeduca-sudo.github.io/observatorio-baq/revisar.html)** (no aparece en el menú ni en buscadores). La primera vez pide una clave de GitHub: créala en [Fine-grained tokens](https://github.com/settings/personal-access-tokens/new) solo para este repositorio, con **Contents: Read and write**, y pégala; el navegador la recuerda.

El panel muestra los casos sin revisar con sus notas. Por cada uno puedes **Publicar**, **Descartar**, corregir tipo, municipio, barrio o fecha, y en los posibles duplicados **unirlo** con el otro caso. Al pulsar **Guardar** se sube un solo commit a `data/casos.json` y la página pública se actualiza en unos 2 minutos. La corrida diaria conserva esas decisiones.

También se puede editar `data/casos.json` a mano: cambia el `estado` a `publicado` o `descartado`, o corrige `tipo` o `barrio`. Si un barrio sale en un lugar equivocado del mapa, corrige sus coordenadas en `data/geocodigos.json`.

---

# Detalles técnicos

## Página web

`web/` tiene una página por sección (`index.html`, `mapa.html`, `informes.html`, `estadisticas.html`, `prensa-oficial.html`, `metodologia.html`), los estilos comunes (`estilos.css`), el cambio de tema (`comun.js`), las utilidades de datos, mapa y gráficos (`datos.js`) y los gráficos de estadísticas (`estadisticas.js`). La única librería es Leaflet 1.9.4, servida desde el propio sitio (`web/leaflet.js` y `web/leaflet.css`) para que el sitio cargue aunque una red bloquee los CDN, con el mapa base gris de Esri. Los nombres de barrio se comparan con el mismo criterio en Python (`publico/nombres_barrio.py`) y en la página (`O.claveBarrio` en `web/datos.js`): sin tildes ni «barrio» o «etapa», y con los números en cifras («Siete de Abril» = «7 de Abril», «II» = 2). Las páginas leen `data/publico/` (nunca `data/casos.json`, que tiene titulares) y `data/oficiales.json`.

El flujo **Página** ubica los barrios con Nominatim (máximo una consulta por segundo, con caché en `data/geocodigos.json`) y publica en GitHub Pages cada vez que cambian los datos en `main` y después de cada corrida del scraper. Para activarlo una sola vez: **Settings → Pages → Source: GitHub Actions**.

Para verla en local:

```bash
python -m casos && python -m publico && mkdir -p _site/data && cp web/* _site/ && cp -r data/publico _site/data/ && cp data/oficiales.json data/oficiales_mensual.csv _site/data/
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

Lee `data/notas.json` y escribe `data/casos.json`: un caso por hecho, con las notas de todos los medios que lo cubrieron. Dos notas se unen cuando el tipo de delito es compatible (un herido que luego muere sigue siendo el mismo hecho), las fechas están a 2 días o menos y coinciden el barrio, el nombre o alias de la víctima, o el texto y la edad. Si nombran a la misma persona (o coinciden edad y barrio), se unen aunque estén hasta 30 días separadas, porque un herido puede morir días después. Dos notas con edades distintas no se unen por parecido del texto. También se unen cuando las dos notas nombran a la misma persona, el mismo alias o el mismo número de víctima ("la mujer 80 asesinada en 2026"). Los pares dudosos no se unen: quedan con estado `posible_duplicado` para que el editor decida. Las capturas sin otro delito, las notas de fuera del área metropolitana o de otros países, los balances con cifras acumuladas, los seguimientos judiciales (condenas, imputaciones) y los accidentes no generan casos.

Cada corrida vuelve a agrupar todas las notas con las reglas vigentes, así que una nota que se vuelve a leer otro día no crea un caso nuevo (cada nota se guarda una sola vez por su URL). Solo se mantienen fijas las uniones de los casos que el editor ya revisó (`publicado` o `descartado`).

Cada caso empieza como `pendiente`. Si el editor cambia el `estado` (`publicado`, `descartado`), el tipo o el barrio en `data/casos.json`, la siguiente corrida conserva esos cambios.

El flujo **Scraper** corre solo todos los días a las 6:00 a. m. (hora de Barranquilla), guarda las notas nuevas y los casos, y deja el resumen de casos en la pestaña Actions.

## Datos oficiales

```bash
python -m oficiales.historico   # 2010-2019, una sola vez
python -m oficiales             # 2020 a hoy, y une el histórico
```

`python -m oficiales` descarga de [policia.gov.co/estadistica-delictiva](https://www.policia.gov.co/estadistica-delictiva) los archivos de delitos a nivel de registro (un delito por fila, todo el país, desde 2020), se queda con Barranquilla, Soledad, Malambo, Galapa y Puerto Colombia, y guarda conteos en `data/oficiales.json` y `data/oficiales_mensual.csv`. El flujo **Datos oficiales** lo corre el día 5 de cada mes. Las cifras son provisionales hasta marzo del año siguiente y llegan con unos dos meses de retraso.

Antes de 2020 la Policía publica un Excel por delito y por año en [su histórico](https://www.policia.gov.co/estadistica-delictiva-old). `python -m oficiales.historico` (flujo **Histórico oficial**) los procesa una vez y guarda `data/oficiales_historico.json`; si hay dos versiones del mismo archivo, no cuenta dos veces un mes. `data/oficiales.json` indica en `cobertura` qué años tiene cada delito, para que un archivo que falta no se lea como cero. Si una corrida no encuentra un archivo que antes sí estaba, conserva lo que ya se tenía.

Las consultas descargadas a mano del portal de SIEDCO se guardan en `data/siedco/` (todos los delitos de alto impacto desde 2003). Solo llenan los años y delitos que no traen los archivos públicos; para aplicarlas sin volver a descargar todo: `python -m oficiales.manual`.

## Datos publicables

```bash
python -m publico                              # arma data/publico/ (lo corre el flujo Página)
python -m publico --capa privado/query.json    # agrega la capa de homicidios 2026
```

Convierte los datos internos en lo que publica el sitio, con las reglas de privacidad: sin nombre de la víctima, dirección, hora ni descripción de los hechos; ubicación por barrio o por zona de cuadrícula de 400 m (las celdas con menos de 3 casos se fusionan con la vecina que tenga menos casos) y fecha por mes. De la prensa no se publica el titular, que puede nombrar a la víctima: se publica un resumen propio y el enlace a la nota.

También limpia los datos: corrige municipios y localidades mal escritos, agrupa sexo y modalidad, valida años y marca fechas futuras o posteriores a la nota. Los casos con fecha futura no se publican. Escribe los CSV de datos abiertos con su diccionario (`data/publico/diccionario.json`), un informe por mes (`data/publico/informes/`) y una copia fechada en `data/cortes/` para reproducir cada análisis.

La capa de homicidios (GeoJSON exportado de ArcGIS) tiene datos personales: se guarda fuera del repositorio (la carpeta `privado/` está en `.gitignore`), y solo se suben sus conteos (`data/publico/registro.json`). Su publicación fue autorizada por el propietario.

Las decisiones que siguen abiertas están en [`docs/pendientes.md`](docs/pendientes.md). La estructura del sitio y los wireframes están en [`docs/estructura.md`](docs/estructura.md), y la plantilla de informe en [`docs/plantilla-informe.md`](docs/plantilla-informe.md).

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest
```
