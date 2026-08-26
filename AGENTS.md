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
```

---

## Arquitectura

El flujo de dependencias es estrictamente unidireccional:
`cirsoc` (cálculo puro) ← `graficos` (visualización 3D) ← `widgets` (interfaz de usuario)

1. **`zonda/cirsoc/` (Motor de cálculo):**
   - **Sin dependencias de Qt.** Código Python/NumPy puro testeable de forma aislada.
   - `estructuras.py`: Fachada (`Edificio`, `Cartel`, `CubiertaAislada`). Instanciar dispara el cálculo.
   - `geometria/`, `cp/`, `presiones/`, `factores.py`: Lógica del reglamento.
2. **`zonda/graficos/` (Visualización 3D):**
   - `escena.py` (`Escena3D`), `actores.py` (modelos `QObject` reactivos), `mallas.py` (geometrías Qt Quick 3D), `camara.py`, `colores.py`.
   - `Visor.qml`, `contorno.vert`, `contorno.frag`: Componentes QML y shaders de contorno.
   - `directores/` y `escenas/`: Orquestación y armado de actores para cada tipología.
3. **`zonda/widgets/` (Interfaz PyQt6):**
   - `zonda.py` (pantalla de bienvenida / selector de módulo).
   - `modulos.py` (`QMainWindow` por tipología), `entrada.py` (formularios), `resultados.py` (tablas y gráficos), `reportes.py` (visor de reportes con `QtWebEngine`).
4. **Módulos transversales (`zonda/`):**
   - `enums.py` (enumerados del dominio), `tipos.py`, `unidades.py`, `excepciones.py`.
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
- **Tests de cálculo:** Los valores numéricos en `tests/test_calculos.py` son referencias reglamentarias fijas. No alterar tolerancias ni valores esperados sin justificación técnica de cálculo.
