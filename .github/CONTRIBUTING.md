# Cómo contribuir a Zonda

¡Gracias por pasar por acá! Zonda es software libre y toda ayuda es bienvenida:
reportar un error, discutir una figura del Reglamento, mejorar la interfaz o
sumar código.

Antes que nada, tené en cuenta una particularidad del proyecto: **Zonda calcula
cargas que después se usan para dimensionar estructuras reales.** Un número mal
no es un pixel corrido: es una decisión de diseño equivocada en la oficina de
alguien. Por eso las contribuciones que tocan el motor de cálculo se revisan con
la lupa puesta en el Reglamento, y los cambios de comportamiento numérico tienen
que venir justificados con el artículo, la tabla o la figura del **CIRSOC
102-2005** que los respalda.

Este proyecto se rige por el [Código de Conducta](CODE_OF_CONDUCT.md).
Participando, aceptás sostenerlo.

---

## Reportar errores 🐞

1. **Buscá primero** en los [issues existentes](https://github.com/efdiloreto/ZondaPro/issues?q=is%3Aissue).
   Si ya está reportado, sumá un 👍 o un comentario con datos nuevos en vez de
   abrir otro.
2. Abrí el issue con la plantilla que corresponda:
   - **Resultado de cálculo dudoso**, si un número no coincide con lo que da el
     Reglamento a mano. Es el reporte más valioso que podés hacer, y el que más
     datos necesita: la tipología, la geometría, los parámetros de viento, el
     valor que devuelve Zonda, el valor que esperabas y **la referencia
     reglamentaria** (artículo, tabla o figura).
   - **Error de la aplicación**, si algo se cierra, se traba, no dibuja o el
     reporte sale mal.
3. **Contá cómo reproducirlo.** Un reporte sin pasos para reproducir, o sin el
   archivo `.zda` que lo dispara, es casi imposible de atender.
4. Si podés, adjuntá el `.zda` del proyecto y el traceback completo.

## Proponer funcionalidades 🎉

Discutilo primero. Abrí un issue con la plantilla de solicitud de funcionalidad
y contá **el problema de ingeniería que querés resolver**, no solamente la
solución que imaginaste: muchas veces el Reglamento o la arquitectura del
proyecto ya empujan hacia otra forma de resolverlo.

Cosas que conviene acordar antes de escribir código:

- Si implica **una tipología estructural nueva**, hay que definir de entrada de
  dónde salen los coeficientes y cómo se van a testear.
- Si implica **cambiar la interfaz**, mejor charlar el flujo antes: la ventana
  está pensada alrededor de una secuencia (geometría → viento → resultados).
- Si es **soporte para otro reglamento** (por ejemplo el CIRSOC 102-2025), es un
  cambio grande que necesita un plan; no lo arranques sin discutirlo.

## Cambios cosméticos ✨

Los cambios que no agregan nada a la estabilidad ni a la funcionalidad
—reformatear a mano, renombrar variables por gusto, reordenar imports que ruff
ya deja como quiere— **en general no se van a mergear**. Consumen revisión y,
sobre todo, ensucian el historial de un código donde después hay que poder
rastrear por qué un número cambió.

---

## Preparar el entorno

El proyecto de Python vive en `python/` y usa [uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/efdiloreto/ZondaPro.git
cd ZondaPro/python
uv sync                 # Entorno virtual (Python >= 3.13)
uv run zonda            # Iniciar la aplicación
```

Enganchá los hooks una sola vez: corren ruff y un par de chequeos de higiene
sobre lo que estás por commitear, así no te enterás en el runner.

```bash
uv run pre-commit install
```

Verificaciones antes de abrir un pull request (las mismas que corren en CI):

```bash
uv run ruff check .          # Linter
uv run ruff format .         # Formato
uv run pytest                # Tests
uv run mypy zonda            # Tipos (hoy no bloquea, pero no lo empeoremos)

uv run pre-commit run --all-files   # Los hooks sobre todo el repositorio
```

Los hooks no reemplazan a CI: si no los instalás, el workflow de `dev` frena
igual lo que esté mal. mypy y pytest quedan fuera de los hooks a propósito
(mypy arrastra errores preexistentes y pytest tarda demasiado para un commit).

Para exportar reportes a PDF, DOCX u ODT corriendo desde el código fuente hace
falta [pandoc](https://pandoc.org/installing.html) en el `PATH`.

## Convenciones del código

- **Todo en español:** nombres de funciones y variables, comentarios y
  docstrings. Es la convención del proyecto y no se negocia por archivo.
- **Los comentarios explican el *por qué*,** no el *qué*. Si un comentario
  repite lo que la línea ya dice, sobra; si explica una decisión del Reglamento
  o una rareza de Qt, vale oro.
- **El flujo de dependencias es unidireccional:**
  `cirsoc` (cálculo puro) ← `graficos` (3D) ← `widgets` (interfaz).
  `zonda/cirsoc/` no importa Qt. Nunca.
- **La vista no recalcula.** Si la plantilla del reporte o la escena 3D
  necesitan un dato, ese dato viaja como campo de la fila de resultados, no como
  una consulta al núcleo: preguntarle al cálculo desde la vista termina
  duplicando la lógica del Reglamento.
- La arquitectura está documentada en [AGENTS.md](../AGENTS.md). Leelo antes de
  tocar el núcleo o la vista 3D.

## Tests

- Los valores numéricos de `tests/test_calculos.py` son **referencias
  reglamentarias fijas**. No se toca ni una tolerancia ni un valor esperado sin
  justificación técnica de cálculo en el pull request.
- `tests/referencia/*.tsv` guarda todos los números que produce hoy la matriz de
  casos. No afirman que sean correctos: afirman que no cambiaron. Si tu cambio
  mueve alguno, `test_referencia.py` va a fallar y señalar la línea.
- Cuando el cambio es **deliberado**, se regeneran y **hay que revisar el diff
  antes de commitear**: es la única revisión que esos números tienen.

  ```bash
  uv run python -m tests.referencia
  ```

- Si agregás una rama de cálculo, sumá un caso a la matriz que la recorra.
- Funcionalidad nueva sin tests es difícil de mergear. Si no sabés cómo testear
  algo, decilo en el pull request y lo vemos.

---

## Flujo de ramas y pull requests

```
feat/lo-que-sea  →  dev  →  master
```

- **`dev` es la rama de integración.** Todo pull request de una funcionalidad o
  un arreglo va contra `dev`.
- **`master` sólo se integra desde `dev`.** Es la rama de release: cada merge a
  `master` publica los tres instaladores. El ruleset del repositorio rechaza los
  pull requests que vengan de cualquier otra rama, y los pushes directos.
- Ramas: `feat/...` para funcionalidad, `fix/...` para arreglos,
  `refactor/...`, `migracion/...`.
- **Mensajes de commit en español, en imperativo y explicando el efecto:**
  `Aplicar la parte positiva de la Nota 5 de la Figura 5.3-2A`, no
  `cambios varios en cp.py`.
- Un pull request, un tema. Si el diff mezcla un arreglo con un refactor y un
  cambio de estilo, la revisión se vuelve imposible.
- Completá la [plantilla de pull request](pull_request_template.md): en
  particular, **el efecto sobre los resultados numéricos**. Si los cambia, hay
  que decirlo explícitamente.

### Releases

La versión es única y sale de `python/zonda/__acercade__.py` (`__version__`); de
ahí la leen el empaquetado y la pantalla "Acerca de". El pull request de `dev` a
`master` verifica que esa versión **no esté publicada todavía**: si lo está, hay
que subirla antes de mergear, o el merge pisaría la release anterior.

## Licencia de los aportes

Zonda se distribuye bajo la **GPL-3.0-or-later**. Al enviar un pull request
aceptás que tu contribución se licencie en esos términos.

---

¿Dudas? Abrí una [discusión](https://github.com/efdiloreto/ZondaPro/discussions)
o preguntá en el issue. Equivocarse es parte del proceso: nadie nació sabiendo
las notas de la Figura 5.3-2A. 🌬️
