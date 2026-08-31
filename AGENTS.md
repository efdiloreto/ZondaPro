# Guía para agentes — Zonda

Aplicación de escritorio para calcular cargas de viento según **CIRSOC 102-2025** (reglamento argentino).
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
   - `zonda.py` (pantalla de bienvenida / selector de módulo).
   - `modulos.py` (`QMainWindow` por tipología), `entrada.py` (formularios), `resultados.py` (tablas y gráficos), `reportes.py` (visor de reportes con `QtWebEngine`).
4. **Módulos transversales (`zonda/`):**
   - `enums.py` (enumerados del dominio), `tipos.py` (sólo alias geométricos y
     numéricos; los resultados se describen en `cirsoc/resultados.py`),
     `unidades.py`, `excepciones.py`.
   - `proyecto.py`: Serialización y deserialización de proyectos `.zda`.
   - `reportes.py`: Motor de plantillas Jinja2 y compilación con pandoc.
   - `recursos/`: Carga de assets (`recursos.ruta()`, `recursos.pixmap()`, `recursos.icono()`) mediante `importlib.resources`.

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
- **Presión mínima:** Hay dos, con distinto alcance:
  - **Componentes y revestimientos:** ±500 N/m² (Art. 1.4.2, `presiones/edificio.py:presion_minima`), incluyendo las paredes bajo la Figura 8. *Todavía sigue la numeración de CIRSOC 102-2005: pendiente de migrar a 2025.*
  - **SPRFV:** Cargas de viento de diseño mínimas (Art. 2.1.5), nota agregada en la plantilla del reporte.
- **Estado de la migración a 102-2025:** Migrados la presión dinámica (Art. 1.13), mapas (Fig. 1.5-1), $K_z$ (Tabla 1.13-1), factor topográfico (Art. 1.8), ráfaga (Art. 1.9), altitud (Art. 1.12), el SPRFV por método direccional (Fig. 2.4-1), las paredes de C&R de edificios bajos (Tabla C 5.3-1) y la cubierta de C&R a dos aguas con θ ≤ 7° y h ≤ 20 m (Tabla C 5.3-2 / Fig. 5.3-2A, con las Zonas 1', 1, 2 y 3 medidas con h). **Pendiente** (marcado con `TODO` en el código): el resto de las figuras de componentes de cubierta (5B/7A/8), la rama de paredes de gran altura de C&R (Figura 8), los valores positivos por zona que pide la Nota 5 de la Fig. 5.3-2A cuando hay parapeto y la presión mínima de componentes (Art. 1.4.2), que siguen CIRSOC 102-2005.
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
- **Tests de cálculo:** Los valores numéricos en `tests/test_calculos.py` son referencias reglamentarias fijas. No alterar tolerancias ni valores esperados sin justificación técnica de cálculo.
