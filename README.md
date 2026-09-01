![Zonda](https://imgur.com/WJDyN6A.png)

Software libre de escritorio para el cálculo de cargas y presiones de viento en estructuras según el reglamento argentino **CIRSOC 102-2005**.

[![Licencia: GPL v3](https://img.shields.io/badge/Licencia-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python: >=3.13](https://img.shields.io/badge/Python->=3.13-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Plataformas](https://img.shields.io/badge/Plataforma-Windows%20|%20macOS%20|%20Linux-lightgrey.svg)]()

---

## Características

- **Cálculo reglamentario (CIRSOC 102-2005):**
  - Determinación de presiones dinámicas $q_z$ y $q_h$.
  - Factores de ráfaga ($G$), direccionalidad ($K_d$), importancia ($I$) y efecto topográfico ($K_{zt}$).
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

> **Nota:** Los instaladores oficiales ya incluyen todas las herramientas necesarias (incluido Pandoc para la exportación de reportes).

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
> Para exportar reportes a PDF, DOCX u ODT al correr desde el código, se requiere tener [pandoc](https://pandoc.org/installing.html) instalado y disponible en el `PATH` del sistema.

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

## Contribuir

Toda ayuda es bienvenida: reportar un error, discutir una figura del Reglamento, mejorar la interfaz o sumar código.

- **[Guía de contribución](.github/CONTRIBUTING.md):** entorno de desarrollo, convenciones, tests y flujo de ramas.
- **[Reportar un error o proponer una funcionalidad](https://github.com/efdiloreto/ZondaPro/issues/new/choose):** si un número no coincide con lo que da el Reglamento a mano, ese es el reporte más valioso que podés hacer.
- **[Código de Conducta](.github/CODE_OF_CONDUCT.md)**
- **[Política de seguridad](SECURITY.md):** las vulnerabilidades se reportan en privado, no como issue.

---

## Apoyá el proyecto

Zonda es libre y gratuito, y lo va a seguir siendo. Lo mantiene muy poca gente, en el tiempo que le queda libre, y le ahorra horas de cálculo y verificación a cada profesional que lo usa.

Los estudios que lo patrocinan aparecen en la columna lateral de la pantalla de inicio del programa. Hay tres niveles —oro, plata y bronce—, y quienes se sumen en los primeros meses conservan el distintivo de **Fundador**.

**[Cómo patrocinar el proyecto →](PATROCINIO.md)**

### Patrocinadores

Todavía no hay ninguno. **Tu estudio puede ser el primero.**

---

## Licencia

Zonda es software libre: podés redistribuirlo y/o modificarlo bajo los términos de la [Licencia Pública General de GNU](LICENSE), versión 3 o posterior, publicada por la Free Software Foundation.

Se distribuye con la esperanza de que sea útil, pero **SIN NINGUNA GARANTÍA**; ni siquiera la garantía implícita de **COMERCIALIZACIÓN** o **APTITUD PARA UN PROPÓSITO PARTICULAR**. Consultá la Licencia Pública General de GNU para más detalles.

Copyright (c) 2018-2026 Eduardo Di Loreto <efdiloreto@gmail.com>, Natalia Alvarado <mnaa85@gmail.com>
