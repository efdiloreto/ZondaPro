---
layout: ../../layouts/Articulo.astro
titulo: 'CIRSOC 102-2025 vs ASCE 7: en qué se basa y en qué se diferencia'
descripcion: >-
  El CIRSOC 102-2025 está basado en los capítulos de viento de ASCE/SEI 7:
  equivalencias de capítulos y conceptos (SPRFV/MWFRS, C&R/C&C) y las
  diferencias entre las dos normas.
fecha: '10 de septiembre de 2026'
fechaIso: '2026-09-10'
entradilla: >-
  El CIRSOC 102-2025 adopta como base los capítulos de viento de ASCE/SEI
  7-10, incorpora las actualizaciones de ASCE 7-16 y 7-22 y las adapta a las
  condiciones de Argentina. Acá están las equivalencias de capítulos y
  conceptos y el detalle de dónde se separan las dos normas.
---

<!--
  Este archivo es parte de Zonda, un programa para calcular cargas de
  viento según CIRSOC 102-2025.
  Copyright (C) 2018-2026 Eduardo Di Loreto <efdiloreto@gmail.com>

  Zonda es software libre: puede redistribuirse y/o modificarse bajo los
  términos de la Licencia Pública General de GNU publicada por la Free
  Software Foundation, versión 3 o posterior.

  Zonda se distribuye con la esperanza de que sea útil, pero SIN NINGUNA
  GARANTÍA; ni siquiera la garantía implícita de COMERCIALIZACIÓN o
  APTITUD PARA UN PROPÓSITO PARTICULAR. Véase la GNU General Public
  License para más detalles.
-->

## En qué se basa

- **Edición 2025:** adopta como base los **Capítulos 26 a 31 de ASCE/SEI 7-10**, con consulta de las revisiones ASCE 7-16 y 7-22 (reconocimiento inicial, pág. 7).
- **Edición 2005:** se basó en ASCE 7-98.
- **Otras fuentes** (comentario del art. 1.1): el AS/NZS 1170.2 australiano para silos y tanques, y la investigación argentina para cubiertas abovedadas y el mapa de velocidades.

## Equivalencia de capítulos

La reorganización de 2025 siguió de cerca la estructura de ASCE 7-22, con un detalle: el procedimiento envolvente se corrió al **Apéndice C** para conservar la numeración general.

| CIRSOC 102-2025 | ASCE 7-22 |
| --- | --- |
| Cap. 1 — Requisitos generales (parámetros básicos) | Cap. 26 — Wind loads: general requirements |
| Cap. 2 — SPRFV: procedimiento direccional (Parte 1) y simplificado (Parte 2) | Cap. 27 — Wind loads on buildings: MWFRS (directional procedure) |
| Apéndice C — SPRFV: procedimiento envolvente | Cap. 28 — MWFRS (envelope procedure) |
| Cap. 4 — Otras estructuras, carteles, silos y tanques | Cap. 29 — Wind loads on other structures and building appurtenances |
| Cap. 5 — Componentes y revestimientos | Cap. 30 — Wind loads: components and cladding |
| Cap. 6 — Procedimiento de túnel de viento | Cap. 31 — Wind tunnel procedure (con ASCE 49 como guía de ensayos) |

## Equivalencia de conceptos

| CIRSOC 102-2025 | ASCE 7-22 |
| --- | --- |
| SPRFV — sistema principal resistente a la fuerza del viento | MWFRS — main wind force resisting system |
| Componentes y revestimientos (C&R) | Components & cladding (C&C) |
| Velocidad básica de viento (ráfaga de 3 s, 10 m, exposición C) | Basic wind speed (3-s gust, 10 m, exposure C) |
| Presión dinámica qz | Velocity pressure |
| Coeficiente de exposición Kz | Velocity pressure exposure coefficient Kz |
| Factor topográfico (loma, escarpa y colina) | Topographic factor Kzt |
| Factor de direccionalidad Kd | Wind directionality factor Kd |
| Factor de ráfaga G, Gf | Gust-effect factor G, Gf |
| Presión interna (GCpi) | Internal pressure coefficient (GCpi) |
| Exposiciones B, C y D (la A fue eliminada en ambas normas) | Exposures B, C and D |

## Dónde se separan

- **Mapas de viento:** el CIRSOC usa el mapa argentino de 51 estaciones meteorológicas (Viollaz, 1997; isolíneas de Altinger, 1997); el ASCE, los mapas estadounidenses. Mismos criterios (períodos de retorno, promedios, alturas de referencia), datos locales.
- **Tornados:** ASCE 7-22 incorporó un capítulo de tornados; el CIRSOC no lo incluye porque todavía no existen los mapas para aplicarlo en Argentina, y remite a los estudios de Schwarzkopf y Rosso (1993).
- **Procedimiento simplificado:** el CIRSOC mantiene el método tabulado para edificios de baja altura (**arts. 2.5 y 5.13**) que ASCE 7-22 no ofrece, con 16 velocidades de ciudades argentinas y presión interna incluida.
- **Cubiertas abovedadas:** ASCE 7 usaba el modelo de Albert Smith de 1914 (hasta la revisión de 2022); la **Figura 5.3-8** del CIRSOC adopta el tratamiento actualizado de Natalini y Natalini (2017), con coeficientes de túnel de viento.
- **Silos y tanques:** las paredes verticales llevan Cp(α) en el CIRSOC y (GCp) en el ASCE 7-22; el CIRSOC sigue a la norma australiana AS/NZS 1170.2:2011 para no sobreestimar la carga.
- **Vidriado sin protección:** ASCE 7 eliminó la opción en la revisión de 2005; el CIRSOC la mantiene por el estado de la industria local de cerramientos.
