# Guía para agentes — Zonda

Aplicación de escritorio para calcular cargas de viento según **CIRSOC 102-2005** (reglamento argentino).
Interfaz en **PyQt6**, visualización 3D en **Qt Quick 3D** y reportes técnicos en Markdown vía **Jinja2 + pandoc**.

**Convención de idioma:** Todo el código, nombres de funciones/variables, comentarios y docstrings están en **español**. Mantené esta convención en cualquier cambio o agregado.

---

## Estructura y Comandos

El proyecto de Python vive en la carpeta `python/` y usa [uv](https://docs.astral.sh/uv/):

```bash
cd python
uv sync                 # Sincronizar entorno virtual (Python >= 3.13)
uv run zonda            # Iniciar la aplicación
uv run pytest           # Correr suite de tests
uv run ruff check .     # Linting con Ruff
uv run ruff format .    # Formateo de código
uv run mypy zonda       # Chequeo estático de tipos

uv run python -m tests.referencia   # Regenerar los resultados de referencia
```

---

## Arquitectura

El flujo de dependencias es estrictamente unidireccional:
`cirsoc` (cálculo puro) ← `graficos` (visualización 3D) ← `widgets` (interfaz de usuario)

1. **`zonda/cirsoc/` (Motor de cálculo):**
   - **Sin dependencias de Qt.** Código Python/NumPy puro testeable de forma aislada.
   - `estructuras.py`: Fachada (`Edificio`, `Cartel`, `CubiertaAislada`). Instanciar dispara el cálculo.
   - `geometria/`, `factores.py`: Geometría, factor de ráfaga y factor topográfico.
   - `cp/`: Selección de figuras y tablas del Reglamento. Devuelve `EntradaCp`
     (`EntradaCpn` en cubiertas aisladas): el coeficiente con las claves que lo
     identifican.
   - `presiones/`: Le agrega a cada entrada la presión de velocidad, el factor de
     ráfaga y la presión interna, y devuelve filas.
   - `resultados.py`: **El modelo de la salida.** Define `PresionVelocidad`, las
     entradas, las filas y `Tabla`; no calcula nada. Ver *Tabla de resultados*.
2. **`zonda/graficos/` (Visualización 3D):**
   - `escena.py` (`Escena3D`), `actores.py` (modelos `QObject` reactivos), `mallas.py` (geometrías Qt Quick 3D), `camara.py`, `colores.py`.
   - `Visor.qml`, `contorno.vert`, `contorno.frag`: Componentes QML y shaders de contorno.
   - `directores/` y `escenas/`: Orquestación y armado de actores para cada tipología.
3. **`zonda/widgets/` (Interfaz PyQt6):**
   - `zonda.py` (ventana de inicio). Es una ventana común del sistema, con
     barra de título y geometría recordada en `QSettings`. Además de elegir el
     módulo, ofrece los proyectos recientes, abrir uno del disco, los accesos
     generales (ayuda, configuración, acerca de) y la franja que avisa de una
     versión nueva. `abrir_proyecto()` vive acá y no en `main.py` porque es la
     bienvenida la que abre los módulos.
   - `modulos.py` (`QMainWindow` por tipología), `entrada.py` (formularios), `resultados.py` (tablas y gráficos), `reportes.py` (visor de reportes con `QtWebEngine`).
   - `apoyo.py` (columna lateral de patrocinadores de la pantalla de inicio, el
     perfil de un patrocinador de oro y la ventana de Agradecimientos). Cada
     nivel se comporta distinto y eso es lo que compra: oro abre su perfil
     dentro del programa, plata abre el enlace que eligió, bronce sólo figura
     en Agradecimientos. Las instrucciones para patrocinar viven en
     `PATROCINIO.md`, no en el programa: así los montos cambian sin publicar
     una versión.
4. **Módulos transversales (`zonda/`):**
   - `enums.py` (enumerados del dominio), `tipos.py` (sólo alias geométricos y
     numéricos; los resultados se describen en `cirsoc/resultados.py`),
     `unidades.py`, `excepciones.py`.
   - `proyecto.py`: Serialización y deserialización de proyectos `.zda`.
   - `reportes.py`: Motor de plantillas Jinja2 y compilación con pandoc.
   - `recursos/`: Carga de assets (`recursos.ruta()`, `recursos.pixmap()`, `recursos.icono()`) mediante `importlib.resources`.
   - `recientes.py`: Los últimos proyectos abiertos o guardados, en `QSettings`.
     Los que ya no están en disco se saltean al listar pero no se borran: pueden
     estar en un disco desconectado.
   - `patrocinadores.py`: Lee `recursos/patrocinadores/patrocinadores.json` y
     `colaboradores.json`. **Los enlaces se validan al leer**: sólo `http`,
     `https` y `mailto`, porque terminan en `QDesktopServices.openUrl()` y un
     `file://` ahí abriría archivos de la máquina del usuario. Los dos archivos
     viajan empaquetados con cada versión, y ninguna entrada mal formada puede
     impedir que el programa arranque: se ignora y sigue. Cómo sumar a alguien
     está en el `LEEME.md` de ese directorio.

---

## Invariantes y Reglas Clave

- **Licencia GPLv3:** Todo archivo de código (`.py`, `.qml`, `.vert`, `.frag`) debe comenzar con el encabezado de licencia GPLv3. El docstring del módulo va inmediatamente después.
- **Recursos:** Los assets se leen con `zonda.recursos`. Si agregás un asset nuevo, debe registrarse obligatoriamente en `recursos/recursos.qrc`.
- **Reactividad 3D:** Los actores (`actores.py`) son `QObject` con `pyqtProperty`. La vista 3D se actualiza automáticamente al mutar las propiedades del actor (no invocar renders manuales).
- **Proyectos (`.zda`):** Guardan el estado crudo de los widgets de entrada (`estado()` / `cargar_estado()`), no los `parametros()` de cálculo. Los `Enum` se serializan por su `name`. Si cambia el esquema, incrementar `VERSION_FORMATO`.
- **QtWebEngine:** Requiere `AA_ShareOpenGLContexts` configurado antes de instanciar `QApplication` (definido en `main.py`). No agregar banderas de ventana nativa (`WA_NativeWindow`) a `QWebEngineView`.
- **Separación de excepciones:**
  - `ErrorLineamientos`: Se lanza en `cirsoc` cuando la geometría excede el alcance del reglamento.
  - `ErrorEstructura`, `ErrorViento`, `ErrorComponentes`: Se lanzan en la capa de `widgets` al validar formularios.
- **Presión mínima (Art. 1.4) pendiente de verificar:** Se aplica a todos los
  componentes y revestimientos salvo a las paredes bajo la Figura 8, donde el
  cálculo original no la aplicaba. Se mantiene el comportamiento para no cambiar
  resultados (ver `ParedesComponentes.considerar_presion_minima`), pero hay que
  contrastarlo con el Reglamento.
- **Tabla de resultados:** Los consumidores (reporte, vista 3D, tablas de la
  interfaz) leen `estructura.resultados` -y en el edificio `resultados_sprfv` /
  `resultados_componentes`- y **filtran o agrupan**; no navegan las estructuras
  anidadas de `cp/` y `presiones/`, que son detalle interno. Si una fila necesita
  un dato nuevo, va como campo de la fila, no como una consulta al cálculo desde
  la vista: cuando la plantilla o la escena le preguntan algo al núcleo (por
  ejemplo si el ángulo llega a 10°) terminan repitiendo la lógica del Reglamento.
  El edificio separa SPRFV de componentes porque el Reglamento puede no proveer
  lineamientos para los segundos, y en ese caso `resultados_componentes` lanza
  `ErrorLineamientos` mientras el SPRFV sigue siendo válido.
- **Resultados de referencia:** `tests/referencia/*.tsv` guardan todos los números
  que produce hoy la matriz de casos de `tests/referencia.py`. No afirman que los
  valores sean correctos según el Reglamento, sino que no cambiaron: si un cambio
  al núcleo mueve alguno, `test_referencia.py` falla y señala la línea. Cuando el
  cambio es deliberado se regeneran con `uv run python -m tests.referencia` y
  **hay que revisar el diff antes de commitear**: es la única revisión que tienen.
  Si se agrega una rama de cálculo, sumar un caso a la matriz que la recorra.
- **Tests de cálculo:** Los valores numéricos en `tests/test_calculos.py` son referencias reglamentarias fijas. No alterar tolerancias ni valores esperados sin justificación técnica de cálculo.
