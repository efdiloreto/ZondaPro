# Guía para agentes — Zonda

Aplicación de escritorio para calcular cargas de viento según **CIRSOC 102-2025** (reglamento argentino).
Interfaz en **PyQt6**, visualización 3D en **Qt Quick 3D** y reportes técnicos en Markdown vía **Jinja2 + pandoc**.

**Convención de idioma:** Todo el código, nombres de funciones/variables, comentarios y docstrings están en **español**. Mantené esta convención en cualquier cambio o agregado.

**Comunicaciones técnicas:** Los mensajes de issues, pull requests, commits, releases y demás comunicaciones del repositorio se escriben en español, **claros y concisos**: un tema por mensaje, explicando el efecto (sobre todo en los cambios numéricos) y sin rodeos.

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
   - `directores/`: **Geometría.** Una clase por tipología y sistema resistente (`Geometria`, `PresionesSprfvMetodoDireccional`, `PresionesComponentes`). Los métodos devuelven sólo coordenadas; el decorador `actores_poligonos` (en `actores.py`) recorre lo devuelto -un polígono, una tupla o un diccionario anidado- con `aplicar_func_recursivamente`, crea un `ActorPresion` por polígono respetando esa estructura y, con `crear_atributo=True`, lo guarda como `actores_<nombre del método>`. Los helpers de `utils_geometria.py` proyectan distancias horizontales sobre el plano de cubierta.
   - `escenas/`: **Presentación.** Leen `estructura.resultados`, indexan las filas, arman la `TablaColores` con `resultados.min_max()`, instancian el director y en cada `actualizar_*` buscan la fila y llaman `actor.asignar_presion()`. Son las que consumen los widgets, que del director sólo usan la cámara (`setear_posicion_camara`) y `volumen()`: nunca le piden geometría ni presiones.
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
- **Ejes de la vista 3D:** X es el ancho (0 → `ancho`), Y la altura (más `elevacion`) y Z la longitud, **negativa** (0 → `-longitud`), para que la estructura crezca hacia atrás. Los rangos de zonas se escriben en esas coordenadas. En `directores/utils_geometria.py`: `coords_pared_rectangular` para paredes, `coords_zona_cubierta_desde_proyeccion` para llevar un rango de X al plano del faldón que definen dos puntos 2D, y `invertir_sentido` para dar vuelta la normal del polígono.
- **Vista 3D por dirección de viento (SPRFV):** El director crea de una sola vez **todos** los actores de **todas** las direcciones, ocultos (`mostrar=False`), en diccionarios indexados por `DireccionVientoMetodoDireccionalSprfv` y, donde corresponde, por `PosicionCubiertaAleroSprfv` o `TipoPresionCubiertaBarloventoSprfv`. Cambiar de dirección **no** rearma geometría: la escena oculta el conjunto actual y le pide el nuevo al director con `obtener_paredes()` / `obtener_cubierta()` / `obtener_alero()`, que eligen el subdiccionario según el estado del director (`direccion`, `posicion_cubierta_un_agua`). El intercambio de barlovento y sotavento de la cubierta a un agua vive en `obtener_paredes()`, no en la escena.
- **Vista 3D de componentes:** Los actores van por zona (`ZonaComponenteParedEdificio` / `ZonaComponenteCubiertaEdificio`) y están todos visibles; lo que cambia con la interfaz es sólo el valor de presión, según componente, zona y tipo de presión.
- **El signo del coeficiente de componentes:** Las filas de componentes traen `tipo_presion` (`POSITIVA` / `NEGATIVA`). Las tablas dan un único valor positivo para todas las zonas, y esa fila viaja con `zona_componente` en `TODAS`; pero el Reglamento puede darle a una zona su propio positivo (Fig. 5.3-2A, Nota 5, con parapeto de 1 m o más), y entonces la zona tiene dos filas. Por eso la vista busca primero `(…, zona, tipo_presion)` y sólo cae en `(…, TODAS, tipo_presion)` como respaldo (`_filas_zona` en `escenas/edificio.py`), y el reporte le agrega "(positiva)" a la etiqueta de la zona cuando el positivo es propio. Nunca asumir que el positivo es único.
- **Contrato actor ↔ fila:** Las claves con las que el director agrupa los actores tienen que ser **los mismos enums** con los que `presiones/` etiqueta las filas. Si aparece una zona en `cp/` que el director no dibuja -o al revés-, la zona queda sin presión o el actor sin valor, sin que nada falle. Los tests de `test_graficos.py` cubren justamente eso: que las áreas de las zonas cubran la superficie sin huecos ni solapes y que ningún actor quede sin presión.
- **Migrar una figura o tabla de C&R:** El camino es siempre el mismo. 1) En `cp/`, el nuevo string de `referencia` con sus valores, y las dimensiones que definen las zonas expuestas como propiedad (por ejemplo `distancias_zonas`), nunca recalculadas en la vista. 2) En `enums.py`, la zona nueva si hace falta. 3) En el director, agregar la `referencia` al dispatch (`_seleccionar_cubierta`) **y** el método que arma las zonas: si no está en el dispatch la cubierta se queda sin zonas y no hay error. El alero reusa la geometría de la cubierta recortada con `recortar_poligono` contra el plano de la pared. 4) Los tests de valores, de áreas por zona y de escena.
- **Proyectos (`.zda`):** Guardan el estado crudo de los widgets de entrada (`estado()` / `cargar_estado()`), no los `parametros()` de cálculo. Los `Enum` se serializan por su `name`. Si cambia el esquema, incrementar `VERSION_FORMATO`.
- **QtWebEngine:** Requiere `AA_ShareOpenGLContexts` configurado antes de instanciar `QApplication` (definido en `main.py`). No agregar banderas de ventana nativa (`WA_NativeWindow`) a `QWebEngineView`.
- **Separación de excepciones:**
  - `ErrorLineamientos`: Se lanza en `cirsoc` cuando la geometría excede el alcance del reglamento.
  - `ErrorEstructura`, `ErrorViento`, `ErrorComponentes`: Se lanzan en la capa de `widgets` al validar formularios.
- **Presión mínima:** Hay dos, con distinto alcance:
  - **Componentes y revestimientos:** ±800 N/m² (Art. 5.2.2, `PRESION_MINIMA_COMPONENTES` en `presiones/edificio.py`), aplicado al módulo de cada signo del valor neto, incluyendo las paredes bajo la Figura 5.4-1 y el alero. Ojo al escribir tests: en edificios chicos el recorte tapa las diferencias entre zonas, así que un test que compare zonas necesita una velocidad alta.
  - **SPRFV:** Cargas de viento de diseño mínimas (Art. 2.1.5): 0,75 kN/m² por el área de pared más 0,4 kN/m² por el área de cubierta, proyectadas. Son fuerzas sobre áreas proyectadas, no presiones por superficie, así que hoy van sólo como nota en la plantilla del reporte y no se aplican a los valores calculados (issue #10, junto con el cartel y la cubierta aislada, que no aplican ningún mínimo).
- **Estado de la migración a 102-2025:** Migrados la presión dinámica (Art. 1.13), mapas (Fig. 1.5-1), $K_z$ (Tabla 1.13-1), factor topográfico (Art. 1.8), ráfaga (Art. 1.9), altitud (Art. 1.12), el SPRFV por método direccional (Fig. 2.4-1), las paredes de C&R de edificios bajos (Tabla C 5.3-1), la cubierta de C&R a dos aguas con θ ≤ 7° y h ≤ 20 m (Tabla C 5.3-2 / Fig. 5.3-2A completa, con las Zonas 1', 1, 2 y 3 medidas con h y las Notas 5, 6 y 7), las Tablas C 5.3-3, 5.3-4 y 5.3-5 (Figs. 5.3-2B, C y D), la cubierta a un agua de C&R para θ ≤ 30° y h ≤ 20 m (Figs. 5.3-5A y 5.3-5B, con θ ≤ 3° a la 5.3-2 sobre el faldón único) y la rama de gran altura de C&R para h > 20 m y θ ≤ 7° (Figura 5.4-1, la reemplazante de la Figura 8 del 2005, con el positivo de paredes evaluado con $q_z$ altura por altura y los negativos con $q_h$, Nota 4, y la Nota 7 del parapeto). **Pendiente** (marcado con `TODO` en el código): el resto de las figuras de componentes de cubierta de gran altura para θ > 7° (Figs. 5.3-2 E a G) y el alero de gran altura (Art. 5.7). Además falta la zona 4⁺ de la superficie inferior de edificios separados del suelo (Nota 8 / Fig. 5.4-1A), que está en el issue #9.
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
