![Zonda](https://imgur.com/WJDyN6A.png)

Software libre de escritorio para el cálculo de cargas y presiones de viento en estructuras según el reglamento argentino **CIRSOC 102-2025**.

[![Licencia: GPL v3](https://img.shields.io/badge/Licencia-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python: >=3.13](https://img.shields.io/badge/Python->=3.13-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Plataformas](https://img.shields.io/badge/Plataforma-Windows%20|%20macOS%20|%20Linux-lightgrey.svg)]()

---

## Características

- **Cálculo reglamentario (CIRSOC 102-2025):**
  - Determinación de presiones dinámicas $q_z$ y $q_h$.
  - Factores de ráfaga ($G$), direccionalidad ($K_d$), altitud ($K_e$) y efecto topográfico ($K_{zt}$).
  - Coeficientes de presión externa ($C_p$) e interna ($GC_{pi}$).
  - Cargas en el Sistema Principal Resistente a la Fuerza del Viento (SPRFV) y en Componentes y Revestimientos (C&R).
- **Tipologías estructurales:**
  - **Edificios:** cerrados y parcialmente cerrados, cubiertas planas, a un agua y a dos aguas, con o sin parapetos.
  - **Carteles y muros:** sobre terreno o elevados, con soporte estructural.
  - **Cubiertas aisladas:** a un agua, dos aguas y abovedadas, abiertas o con obstrucciones.
- **Visualización 3D interactiva (Qt Quick 3D):**
  - Mapeo de presiones con escala de colores en tiempo real.
  - Vectores y etiquetas de presión direccionales con control de oclusión.
  - Vistas ortogonales fijas, perspectiva cónica/ortográfica y herramienta de medición de distancias entre vértices.
- **Memorias de cálculo técnicas:**
  - Generación de informes completos y detallados basados en plantillas Jinja2.
  - Exportación directa a PDF, Word (DOCX), LibreOffice (ODT) y Markdown.
- **Gestión de proyectos:**
  - Guardado y apertura del estado de trabajo en formato de archivo nativo `.zda`.
- **Servidor MCP (Model Context Protocol):**
  - Expone el cálculo como herramientas para un cliente LLM local (Claude Desktop, Claude Code, Gemini CLI y otros): el asistente calcula presiones, lee las coordenadas de cada zona y arma reportes o conecta software de cálculo estructural.

---

## Capturas de pantalla

| Selección de módulo | Módulo Edificios |
| :---: | :---: |
| ![Inicio](https://imgur.com/NQbA9GB.png) | ![Edificio](https://imgur.com/dlz7Sib.png) |

| Módulo Carteles | Módulo Cubiertas Aisladas |
| :---: | :---: |
| ![Cartel](https://imgur.com/IG4UE8j.png) | ![Cubierta Aislada](https://imgur.com/55xAq0k.png) |

| Visor y exportación de reportes |
| :---: |
| ![Reportes](https://imgur.com/DOw0StA.png) |

---

## Instalación

### Instaladores listos para usar (Recomendado)

Podés descargar el instalador ejecutable correspondiente a tu sistema operativo directamente desde la **[última release](https://github.com/efdiloreto/ZondaPro/releases/latest)**:

- **Windows:** Instalador `.msi`
- **macOS:** Imagen de disco `.dmg`
- **Linux:** Paquete `.flatpak` (se instala con `flatpak install --user Zonda-*.flatpak`)

> **Nota:** Los instaladores oficiales ya incluyen todas las herramientas necesarias: la exportación a PDF la hace Zonda por sí solo.

---

### Ejecución desde el código fuente

Requiere [uv](https://docs.astral.sh/uv/getting-started/installation/) y Python 3.13 o superior.

1. Cloná este repositorio:
   ```bash
   git clone https://github.com/efdiloreto/ZondaPro.git
   cd ZondaPro/python
   ```

2. Sincronizá el entorno y ejecutá Zonda:
   ```bash
   uv sync
   uv run zonda
   ```

> `uv sync` creará el entorno virtual e instalará Python 3.13 automáticamente si no está disponible en el sistema.
>
> No se necesita nada más: la exportación a PDF usa el motor de texto de Qt y viaja con las dependencias del proyecto.

---

## Servidor MCP

Zonda trae un servidor MCP local (por stdio, con [FastMCP](https://gofastmcp.com)) que expone el cálculo del CIRSOC 102-2025 a clientes LLM. Cada herramienta calcula una tipología y devuelve, en JSON:

- las **filas de resultados** (presiones, fuerzas, coeficientes y la referencia del Reglamento que las respalda),
- las **coordenadas de cada zona** de presión en los mismos ejes de la vista 3D, con las claves que las emparejan con las filas,
- la **metadata**: unidades, sistema de coordenadas y parámetros de entrada.

| Herramienta | Tipología |
| :--- | :--- |
| `calcular_edificio` | Edificio (SPRFV y componentes y revestimientos) |
| `calcular_cartel` | Cartel (Casos A, B y C) |
| `calcular_cubierta_aislada` | Cubierta aislada (presiones y componentes) |

### Instalar el servidor en un cliente

Desde Zonda, usá el acceso **Instalar servidor MCP...** del pie de la ventana de inicio (o del menú Archivo de los módulos). El diálogo agrega la entrada al cliente elegido —con respaldo del archivo de configuración— entre:

- **Claude Desktop** (macOS y Windows)
- **Claude Code** (`~/.claude.json`)
- **Antigravity** (`~/.gemini/config/mcp_config.json`)
- **OpenCode** (`~/.config/opencode/opencode.json`)

Después de instalar, reiniciá el cliente.

### Instalar con un agente

Para cualquier otro cliente (Cursor, VS Code, Goose, ...), el diálogo genera un **prompt de instalación** listo para pegarle a un agente (OpenCode, Claude Code, Antigravity, ...): el agente agrega la entrada a su propia configuración y la verifica por su cuenta, listando las herramientas y haciendo una llamada de prueba a `calcular_cartel`.

> **Nota:** si la configuración de un cliente tiene comentarios (JSONC), Zonda no la edita (marca el cliente como "ilegible") y conviene usar el prompt del agente.

**ChatGPT** no está soportado: solo acepta servidores MCP remotos por HTTP con URL pública, y este servidor corre local por stdio.

### Configuración manual

Si preferís configurar a mano, apuntá el cliente al servidor con `uv`:

```json
{
  "mcpServers": {
    "zonda": {
      "command": "uv",
      "args": ["run", "--project", "/ruta/a/ZondaPro/python", "zonda-mcp"]
    }
  }
}
```

> **Nota:** los clientes locales corren el servidor en un entorno aislado; en macOS conviene tener `uv` instalado globalmente (`brew install uv`) para que el cliente lo encuentre.

### Correr el servidor a mano

```bash
uv run zonda-mcp     # stdio, para un cliente MCP
```

---

## Desarrollo

Desde el directorio `python/`:

```bash
uv run pytest           # Ejecutar suite de tests
uv run ruff check .     # Análisis estático (linter)
uv run ruff format .    # Formateo de código
uv run mypy zonda       # Verificación de tipos
```

Para más detalles sobre la arquitectura interna, el motor de cálculo y la capa gráfica 3D, consultá [AGENTS.md](AGENTS.md).

---

## Licencia

Zonda es software libre: podés redistribuirlo y/o modificarlo bajo los términos de la [Licencia Pública General de GNU](LICENSE), versión 3 o posterior, publicada por la Free Software Foundation.

Se distribuye con la esperanza de que sea útil, pero **SIN NINGUNA GARANTÍA**; ni siquiera la garantía implícita de **COMERCIALIZACIÓN** o **APTITUD PARA UN PROPÓSITO PARTICULAR**. Consultá la Licencia Pública General de GNU para más detalles.

Copyright (c) 2018-2026 Eduardo Di Loreto <efdiloreto@gmail.com>, Natalia Alvarado <mnaa85@gmail.com>
