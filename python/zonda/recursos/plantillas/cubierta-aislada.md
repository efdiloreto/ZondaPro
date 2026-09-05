{% extends "base.md" %}
{% import "macros.md" as ma with context%}

{% block titulo_encabezado -%}
CÁLCULO DE PRESIONES DE VIENTO SOBRE CUBIERTAS AISLADAS
{%- endblock %}

{% block datos_codigo -%}
Referencia: Cap. 2, Art. 2.4.3
{%- endblock %}

{% block datos_geometria -%}
### CUBIERTA AISLADA
Ancho: {{ '%.2f'|format(estructura.ancho) }} m

Longitud: {{ '%.2f'|format(estructura.longitud) }} m

Altura de alero: {{ '%.2f'|format(estructura.altura_alero) }} m

Altura de cumbrera: {{ '%.2f'|format(estructura.altura_cumbrera) }} m

Tipo de cubierta: {{ estructura.geometria.tipo_cubierta.value|capitalize }}

{%- endblock %}

{% block datos_rafaga -%}
{% if estructura.factor_g_simplificado -%}
Se adopta el factor de efecto de ráfaga simplificado G = 0.85, según el artículo 1.9.4.
{% else -%}
Se calcula el factor de efecto de ráfaga G~f~ de estructura flexible, según el artículo 1.9.5.
{% endif -%}
{%- endblock %}

{% block resultados_geometria -%}
### PARÁMETROS DE CÁLCULO
Ángulo de cubierta: {{ '%.2f'|format(estructura.geometria.angulo) }}°

Altura media de cubierta: {{ '%.2f'|format(estructura.geometria.altura_media) }} m

Bloqueo: {{ '%.0f'|format(estructura.geometria.bloqueo) }} %
({{ "flujo de viento obstruido" if estructura.geometria.con_bloqueo else "flujo de viento libre" }})

Factor de direccionalidad, K~d~: {{ '%.2f'|format(estructura.presiones.factor_direccionalidad) }}
{%- endblock %}

{% block resultados_constantes_terreno %}
{{ super() }}
{{ ma.constantes_terreno(estructura.rafaga.constantes_exp_terreno) }}
{%- endblock %}

{% block resultados_rafaga -%}
{{ super() }}
Factor de ráfaga: {{ '%.2f'|format(estructura.rafaga.factor) }}
{%- endblock %}

{% block k3 -%}
{{ '%.2f'|format(estructura.topografia.parametros.k3[0]) }}
{%- endblock %}

{% block resultados_topografia_pie -%}
Notas:

{% if estructura.topografia.topografia_considerada() -%}
- El valor de K~3~ es el correspondiente a la altura media.

- Los valores de K~zt~ se encuentan en las tablas de presiones.
{%- endif %}
{%- endblock %}

{% block presiones_sprfv -%}
### PRESIONES NORMALES
Se deben investigar todos los casos de carga para cada ángulo de cubierta. Las fuerzas de fricción, incluidas en las
tablas, se calculan sobre la superficie superior e inferior con flujo de viento libre, o sólo sobre la superior con
flujo obstruido, y se combinan con las fuerzas debidas a la presión normal (art. 2.4.3.1).

{% for direccion in enums.DireccionVientoCubiertaAislada -%}
{{ ma.presiones_cubierta_aislada(
    estructura.resultados.filtrar(direccion=direccion),
    "PRESIONES — VIENTO " ~ direccion.value,
) }}

{% endfor %}
### PRESIONES LATERALES
#### Presiones sobre Cenefas, Parapetos y Tímpanos
{% set presion_velocidad = estructura.resultados[0].q.valor -%}
Según el artículo 2.4.5 se debe agregar la carga horizontal resultante de considerar las cenefas, parapetos o
tímpanos con q~p~ = q~h~ (art. 2.4.3.1), en caso de existir: {{ '%.2f'|format(1.5 * presion_velocidad|convertir_unidad(unidades.presion)) }} {{ unidades.presion.value + "/m^2^" }}
a barlovento (GC~pn~ = +1.5, actuando hacia el lado frontal del parapeto) y {{ '%.2f'|format(1.0 * presion_velocidad|convertir_unidad(unidades.presion)) }} {{ unidades.presion.value + "/m^2^" }}
a sotavento (GC~pn~ = -1.0). Los coeficientes GC~pn~ ya incluyen el factor de ráfaga.

#### Fuerzas de fricción
Según el artículo 2.4.3.1, para viento paralelo a la cumbrera se debe agregar la mayor entre la carga de las cenefas,
parapetos o tímpanos y la fuerza de fricción, calculada con los coeficientes de empuje por fricción de la Tabla 2.4-1
que correspondan al tipo de superficie según su orientación respecto de la dirección del viento.

{%- endblock %}

{%- block presiones_componentes -%}
{%- if estructura.resultados_componentes %}
### COMPONENTES Y REVESTIMIENTOS
Los coeficientes de presión neta C~N~ salen de la figura indicada en cada tabla, para edificios abiertos, según el área
efectiva de viento de cada componente y la situación de bloqueo del flujo bajo la cubierta. La presión de cada zona es
p = q~h~ · G · C~N~ (expresión 5.5-1), con q~h~ calculada a la altura media de la cubierta. Los coeficientes son
presiones netas (contribuciones de las superficies superior e inferior) y no llevan presión interna. Los signos positivo
y negativo indican presiones que actúan acercándose o alejándose de la superficie superior de la cubierta,
respectivamente (nota 4), y para ángulos distintos de los tabulados se permite la interpolación lineal (nota 3). Las
figuras cubren 0,25 ≤ h/L ≤ 1,0, con L medido a lo largo de la dirección del viento, normal a la cumbrera o a lo largo
de la vertiente.

{% for componente, area in estructura.componentes.items() %}
{{ ma.presiones_componentes_cubierta_aislada(
    estructura.resultados_componentes.filtrar(componente=componente),
    "COMPONENTES Y REVESTIMIENTOS — %s (%s m^2^)"|format(componente, area),
) }}

{% endfor %}
{%- endif -%}
{%- endblock %}
