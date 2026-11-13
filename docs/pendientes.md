# Decisiones pendientes

Lo que necesita una decisión humana antes de seguir. Cada punto dice qué hace el sitio mientras tanto.

| # | Tema | Decisión | Mientras tanto | Estado |
| --- | --- | --- | --- | --- |
| 1 | Capa de homicidios (ArcGIS) | ¿Hay licencia o autorización del propietario para publicar datos derivados? | — | **Resuelto (13 nov 2026):** CRISTIAN confirmó la autorización. Se publican solo conteos por mes, barrio, zona fusionada, sexo y modalidad. El archivo original no entra al repositorio. |
| 2 | Frecuencia de los informes | ¿Mensual, semanal o ambos? ¿Quién los revisa antes de publicarlos? | Informe mensual automático, marcado «incompleto» mientras falten datos. | Pendiente |
| 3 | Licencia de los datos abiertos | ¿CC BY 4.0? | Se muestra CC BY 4.0 con atribución. | Pendiente de confirmar |
| 4 | Población por municipio | ¿Qué cifras del DANE usar (año, proyección)? | No se muestran tasas por habitante (`data/poblacion.json` está vacío). | Pendiente |
| 5 | Datos crudos en el repositorio público | `data/notas.json` y `data/casos.json` tienen titulares que pueden nombrar víctimas. ¿Se mueven a un repositorio privado? | El sitio ya no los publica (usa `data/publico/`), pero siguen visibles en GitHub. | Pendiente |
| 6 | Mapa base de Esri | ¿Se aceptan los términos de uso de los mapas base de Esri, o se cambia a otro proveedor? | Se sigue usando el mapa base gris de Esri con su atribución. | Pendiente |
| 7 | Actualización de la capa de homicidios | ¿Cada cuánto llega una copia nueva, y quién la carga? | Se procesa a mano: `python -m publico --capa ruta/query.json`. | Pendiente |
| 8 | Revisión editorial de casos de prensa | ¿Se publican casos sin revisar? | Se publican con la etiqueta «Sin revisar». | Pendiente |
| 9 | Umbral de privacidad | ¿3 casos es el mínimo por zona y por barrio nombrado? | Se usa 3. | Pendiente de confirmar |
| 10 | Septiembre y octubre de 2026 | Los dos meses tienen cerca de la mitad de los homicidios de los anteriores, tanto en el registro como en SIEDCO. ¿Es un retraso en la carga o una baja real? | Se marcan «incompletos (posible retraso en la carga)» y no se presentan como una caída. | Pendiente de verificar con la fuente |
