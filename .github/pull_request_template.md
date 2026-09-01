<!--
Un título corto y en imperativo, igual que un mensaje de commit. Ejemplos:

  * Corregir el Cp de barlovento en cubiertas a dos aguas
  * Sumar el factor de direccionalidad a la memoria de cálculo
  * Actualizar PyQt6 a 6.11
-->

## Qué cambia y por qué

<!--
Describí el cambio y la motivación. Si resuelve un issue, linkealo así:
Cierra #12
-->

## Efecto sobre los resultados numéricos

<!--
OBLIGATORIO. Marcá una:

- [ ] No cambia ningún número: los .tsv de referencia quedan intactos.
- [ ] Cambia números, deliberadamente. Detallá abajo qué casos se mueven y por
      qué, con la referencia reglamentaria (artículo / tabla / figura del
      CIRSOC 102-2005) que respalda el valor nuevo, y confirmá que revisaste el
      diff de tests/referencia/*.tsv línea por línea.
-->

## Referencia reglamentaria

<!--
Si el cambio toca el motor de cálculo (zonda/cirsoc/), citá de dónde sale:
artículo, tabla, figura y nota. Si no lo toca, borrá esta sección.
-->

## Cómo se probó

<!--
Qué tests agregaste o modificaste, y por qué demuestran que esto funciona y que
un cambio futuro no lo va a romper en silencio.

Si el cambio es de interfaz o de la vista 3D, sumá capturas: antes y después.
-->

## Capturas

<!-- Opcional. Borrá la sección si no aplica. -->

## Checklist

<!--
Es un recordatorio de cosas que se olvidan fácil, no un trámite. Marcá con [x]
lo que corresponda y borrá lo que no aplique a este pull request.
-->

- [ ] Leí las [guías de contribución](CONTRIBUTING.md).
- [ ] El pull request va contra `dev` (a `master` sólo se mergea desde `dev`).
- [ ] Pasan `uv run ruff check .`, `uv run ruff format --check .` y `uv run pytest`.
- [ ] `uv run mypy zonda` no suma errores nuevos.
- [ ] El código y los comentarios están en español, como el resto del proyecto.
- [ ] Los comentarios explican el *por qué*, no el *qué*.
- [ ] Agregué o actualicé los tests que corresponden.
- [ ] Si se agregó una rama de cálculo, sumé un caso a la matriz de
      `tests/referencia.py` que la recorra.
- [ ] Actualicé la documentación (`README.md`, `AGENTS.md`) si hacía falta.
- [ ] Un solo tema por pull request: el diff no mezcla arreglos con refactors.

## Para hacer antes de mergear

<!--
Opcional. Por ejemplo:

- [ ] Subir __version__ en python/zonda/__acercade__.py
- [ ] Esperar que se mergee el #34
- [ ] Probar el .msi que dejó la corrida como artefacto
-->
