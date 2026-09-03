{% extends "base.md" %}
{% import "macros.md" as ma with context%}

{% block titulo_encabezado -%}
CÁLCULO DE PRESIONES DE VIENTO SOBRE EDIFICIO
{%- endblock %}

{% block datos_codigo -%}
Método de cálculo: Método 2 (Analítico) - Procedimiento {{ estructura.metodo_sprfv.value|capitalize }}
{%- endblock %}

{% block datos_geometria -%}
### EDIFICIO
Elevación sobre terreno: {{ '%.2f'|format(estructura.elevacion) }} m

Ancho: {{ '%.2f'|format(estructura.ancho) }} m

Longitud: {{ '%.2f'|format(estructura.longitud) }} m

Altura de alero: {{ '%.2f'|format(estructura.altura_alero) }} m

{% if estructura.tipo_cubierta != enums.TipoCubierta.PLANA -%}
Altura de cumbrera: {{ '%.2f'|format(estructura.altura_cumbrera) }} m
{%- endif %}
{% if estructura.alero %}
Alero: {{ '%.2f'|format(estructura.alero) }} m
{% endif %}
{%- if estructura.parapeto %}
Parapeto: {{ '%.2f'|format(estructura.parapeto) }} m
{% endif %}
Tipo de cubierta: {{ estructura.geometria.tipo_cubierta.value|capitalize }}

Clasificación de cerramiento: {{ estructura.cerramiento.value|capitalize }}
{%- endblock %}

{% block datos_rafaga -%}
{% if not estructura.factor_g_simplificado -%}
Flexibilidad: {{ estructura.flexibilidad.value|capitalize }}

Frecuencia natural: {{ '%.2f'|format(estructura.frecuencia) }} Hz

Relación de amortiguamiento: {{ '%.2f'|format(estructura.beta) }}
{% else -%}
Se adopta el factor de ráfaga igual a 0.85 de acuerdo al artículo 5.8.1.
{% endif %}
{%- endblock %}

{% block resultados_geometria -%}
### PARÁMETROS DE CÁLCULO
Ángulo de cubierta: {{ '%.2f'|format(estructura.geometria.cubierta.angulo) }}°

Altura media de cubierta: {{ '%.2f'|format(estructura.geometria.cubierta.altura_media) }} m
{% if estructura.reducir_gcpi %}
Factor de reducción de coeficiente de presión interna: {{ '%.2f'|format(estructura.presiones.cubierta.sprfv.factor_reduccion_gcpi) }}
{% endif %}
Coeficiente de presión interna, GC~pi~: ±{{ '%.2f'|format(estructura.presiones.cubierta.sprfv.gcpi) }}

Factor de direccionalidad, K~d~: {{ '%.2f'|format(estructura.presiones.cubierta.sprfv.factor_direccionalidad) }}
{%- endblock %}
{% block resultados_constantes_terreno %}
{{ super() }}
{{- ma.constantes_terreno(estructura.rafaga[enums.DireccionVientoMetodoDireccionalSprfv.PARALELO].constantes_exp_terreno) }}
{%- endblock %}

{% block resultados_rafaga -%}
{{ super() -}}
{% if not estructura.factor_g_simplificado -%}
PARALELO A LA CUMBRERA

{{ ma.tabla_rafaga(estructura.rafaga[enums.DireccionVientoMetodoDireccionalSprfv.PARALELO], estructura.flexibilidad) }}

NORMAL A LA CUMBRERA

{{ ma.tabla_rafaga(
estructura.rafaga[enums.DireccionVientoMetodoDireccionalSprfv.NORMAL],
estructura.flexibilidad,
) }}
{%- else -%}
Factor de ráfaga: {{ '%.2f'|format(0.85) }}
{%- endif %}
{%- endblock %}

{% block k3 -%}
{{ '%.2f'|format(estructura.topografia.k3_en(estructura.geometria.cubierta.altura_media)) }}
{%- endblock %}

{% block resultados_topografia_pie -%}
Notas:

{% if estructura.topografia.topografia_considerada() -%}
- El valor de K~3~ que se muestra en la tabla es el correspondiente a la altura media. Los valores para las demás alturas se calculan automáticamente y no son mostrados.

- Los valores de K~zt~ se encuentan en las tablas de presiones.
{%- endif %}
{%- endblock %}
{%- set sprfv = estructura.resultados_sprfv -%}

{% block presiones_sprfv -%}
### PRESIONES - SPRFV
{% for direccion in enums.DireccionVientoMetodoDireccionalSprfv -%}
{%- set filas_direccion = sprfv.filtrar(direccion=direccion) -%}
#### VIENTO {{ direccion.value|upper }} A LA CUMBRERA
{% for pared, filas in filas_direccion.filtrar(zona=enums.ZonaEdificio.PAREDES).agrupar('pared') -%}
{{ ma.presiones(filas, "PARED %s"|format(pared.value|upper)) }}
{%- endfor -%}
{%- for clave, filas in filas_direccion.filtrar(zona=enums.ZonaEdificio.CUBIERTA).agrupar('posicion', 'caso') -%}
{{ ma.presiones(filas, ma.titulo_superficie("CUBIERTA", clave)) }}
{%- endfor -%}
{%- for clave, filas in filas_direccion.filtrar(zona=enums.ZonaEdificio.ALERO).agrupar('posicion', 'caso') -%}
{{ ma.presiones(filas, ma.titulo_superficie("ALERO", clave, "ALEROS")) }}
{%- endfor -%}
{% endfor %}

Notas:

- **Cargas de viento de diseño mínimas (Art. 2.1.5):** La carga de viento que se debe usar en el diseño del SPRFV para un edificio cerrado o parcialmente cerrado, no debe ser menor que 0,75 kN/m^2^ multiplicado por el área de la pared del edificio y 0,4 kN/m^2^ multiplicado por el área de cubierta del edificio, proyectadas sobre un plano vertical normal a la dirección supuesta del viento. Las cargas de paredes y cubiertas se deben aplicar simultáneamente. La fuerza del viento de diseño para edificios abiertos no debe ser menor que 0,75 kN/m^2^ multiplicado por el área A~f~.
{%- endblock -%}

{%- block presiones_componentes -%}
{%- set componentes = estructura.resultados_componentes -%}
{%- if componentes %}
### PRESIONES - COMPONENTES Y REVESTIMIENTOS
{% for zona, filas_zona in componentes.agrupar('zona') -%}
#### {{ zona.value|upper }}
{% set areas = estructura.componentes_paredes if zona == enums.ZonaEdificio.PAREDES else estructura.componentes_cubierta -%}
{% for clave, filas in filas_zona.agrupar('pared', 'componente') -%}
{%- set titulo_pared = "PARED %s - "|format(clave[0].value|upper) if clave[0] else "" -%}
{%- set nombre = clave[1] -%}
{%- if filas|map(attribute='q.altura')|unique|list|length > 1 -%}
{%- for zona_componente, filas_zona_componente in filas.agrupar('zona_componente') -%}
{{ ma.presiones(filas_zona_componente, "%sComponente: %s (%s m^2^) (Zona: %s)"|format(titulo_pared, nombre, areas[nombre], zona_componente.value|capitalize)) }}
{%- endfor -%}
{%- else -%}
{{ ma.presiones(filas, "%sComponente: %s (%s m^2^)"|format(titulo_pared, nombre, areas[nombre])) }}
{%- endif -%}
{%- endfor -%}
{% endfor %}
Notas:

- **Presiones de viento de diseño mínimas (Art. 5.2.2):** La presión de viento de diseño para componentes y revestimientos de edificios y otras estructuras no debe ser menor que una presión neta de 0,80 kN/m^2^ actuando en cualquier dirección normal a la superficie. Los valores de las tablas ya la tienen aplicada.
{%- endif -%}
{%- endblock %}
