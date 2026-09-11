---
layout: ../../layouts/Articulo.astro
titulo: 'Zonda como servidor MCP: el cálculo de viento para tu asistente de IA'
descripcion: >-
  Zonda expone el cálculo del CIRSOC 102-2025 como servidor MCP: tres
  herramientas que devuelven presiones por zona, con sus coordenadas y las
  referencias del Reglamento, para armar reportes propios o usar los
  resultados con software de cálculo estructural.
fecha: '11 de septiembre de 2026'
fechaIso: '2026-09-11'
entradilla: >-
  Zonda trae un servidor MCP que expone el cálculo del Reglamento a
  asistentes de IA como Claude, Antigravity u OpenCode. El asistente calcula
  las presiones, lee cada zona con sus coordenadas y puede armar el reporte
  que necesites o llevar los resultados a otro software.
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

## Qué es

MCP (Model Context Protocol) es el estándar con el que los asistentes de IA se
conectan a herramientas externas. El asistente consulta un servidor, ve qué
herramientas ofrece y las llama cuando las necesita. Los clientes locales de IA
lo soportan de forma generalizada: Claude Desktop, Claude Code, Antigravity,
OpenCode, Cursor y otros.

Zonda trae su propio servidor MCP. Corre local, por stdio, y expone el cálculo
del CIRSOC 102-2025. Tu asistente puede calcular las presiones de un edificio,
un cartel o una cubierta aislada y usar esos números como parte de su trabajo.
El servidor no requiere que Zonda esté abierto: el cliente lo lanza cuando lo
necesita.

## Qué expone

Tres herramientas, una por tipología:

- `calcular_edificio`: el sistema principal resistente a la fuerza del viento
  (SPRFV) y, cuando el Reglamento da lineamientos, los componentes y
  revestimientos. Cada fila trae la zona, la pared, la dirección del viento, el
  coeficiente, la presión positiva y negativa, y la referencia del artículo o
  la figura del Reglamento que la respalda.
- `calcular_cartel`: los casos de fuerza de la Figura 4.4-1, con la fuerza
  resultante de cada caso y, para el Caso C, de cada región.
- `calcular_cubierta_aislada`: las presiones de las Figuras 2.4-4 a 2.4-7 por
  dirección del viento y caso de carga, con la fricción, y los componentes si
  se cargan.

Además de las filas de resultados, cada respuesta trae las coordenadas de cada
zona en los mismos ejes de la vista 3D de Zonda, con las claves que las
emparejan con las filas. El asistente sabe qué presión actúa sobre qué
superficie y de qué tamaño es esa superficie. Las unidades y la descripción del
sistema de coordenadas viajan en la respuesta, y los parámetros que no aplica
el Reglamento llegan señalados en un campo propio.

## Para qué sirve

Armá el informe que necesites. El reporte de Zonda es un PDF con formato fijo;
por MCP los resultados llegan como datos. Podés pedirle al asistente una
memoria de cálculo con tu formato, una tabla para tu planilla o un resumen de
las zonas más críticas, con cada valor referenciado al artículo o la figura del
Reglamento.

Llevá los resultados a tu software de cálculo. Si tu programa de análisis o
diseño expone su propio servidor MCP, el asistente puede trabajar de puente:
toma de Zonda las presiones y las coordenadas de cada zona y las aplica en el
modelo del otro software, sin copiar números a mano. Varios programas
estructurales ya publican su servidor MCP, sea el fabricante o la comunidad.

## Cómo instalarlo

Desde la bienvenida de Zonda, el acceso «Instalar servidor MCP» agrega la
entrada al cliente que elijas, con una copia de respaldo del archivo de
configuración. Hoy soporta Claude Desktop, Claude Code, Antigravity y OpenCode.
Después de instalar, reiniciá el cliente.

Para otro cliente (Cursor, VS Code, Goose), el diálogo genera un prompt listo
para pegarle a un agente: el agente agrega la entrada a su propia configuración
y verifica la instalación por su cuenta, listando las herramientas y haciendo
una llamada de prueba con un cartel de ejemplo.

## Sobre ChatGPT

ChatGPT solo acepta servidores MCP remotos por HTTP con URL pública, y este
servidor corre local. No se puede conectar por ahora.
