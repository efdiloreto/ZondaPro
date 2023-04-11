{% extends "base.md" %}
{% import "macros.md" as ma with context%}

{% block titulo_encabezado -%}
CÁLCULO DE PRESIONES DE VIENTO SOBRE CARTELES
{%- endblock %}

{% block datos_codigo -%}
Referencia: Capítulo 5.13
{%- endblock %}

{% block datos_geometria -%}
### CARTEL
Altura inferior: {{ '%.2f'|format(estructura.altura_inferior) }} m

Altura superior: {{ '%.2f'|format(estructura.altura_superior) }} m

Ancho: {{ '%.2f'|format(estructura.ancho) }} m

Profundidad: {{ '%.2f'|format(estructura.profundidad) }} m

Categoría: {{ estructura.categoria.value }}
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
Altura neta: {{ '%.2f'|format(estructura.geometria.altura_neta) }} m

Altura media: {{ '%.2f'|format(estructura.geometria.altura_media) }} m

Área: {{ '%.2f'|format(estructura.geometria.area) }} m^2^

Factor de direccionalidad, K~d~: {{ '%.2f'|format(estructura.presiones.factor_direccionalidad) }}

Disposición sobre el terreno: {% if estructura.cf.sobre_nivel_terreno() %} Sobre nivel de terreno % else %} A nivel de terreno {% endif %}
{%- endblock %}

{% block resultados_constantes_terreno %}
{{ super() }}
{{ ma.constantes_terreno(estructura.rafaga.constantes_exp_terreno) }}
{%- endblock %}

{% block resultados_rafaga -%}
{{ super() -}}
{% if not estructura.factor_g_simplificado -%}

{{ ma.tabla_rafaga(estructura.rafaga, estructura.flexibilidad) }}

{%- else -%}
Factor de ráfaga: {{ '%.2f'|format(0.85) }}
{%- endif %}
{%- endblock %}

{% block k3 -%}
{{ '%.2f'|format(estructura.topografia.parametros.k3[-1]) }}
{%- endblock %}

{% block resultados_topografia_pie -%}
Notas:

{% if estructura.topografia.topografia_considerada() -%}
- El valor de K~3~ que se muestra en la tabla es el correspondiente a la altura media. Los valores para las demás alturas se calculan automáticamente y no son mostrados.

- Los valores de K~zt~ se encuentan en las tablas de presiones.
{%- endif %}
{%- endblock %}

{% block presiones_sprfv -%}
### PRESIONES
{{ ma.presiones_cartel(
estructura.geometria.alturas,
estructura.presiones.coeficientes_exposicion,
estructura.presiones.factor_topografico,
estructura.presiones.presiones_velocidad,
estructura.cf(),
estructura.presiones(),
estructura.geometria.areas_parciales,
estructura.presiones.fuerzas_parciales,
estructura.presiones.fuerza_total,
) }}

Fuerza Total = {{ '%.2f'|format(estructura.presiones.fuerza_total|convertir_unidad(unidades.fuerza)) }} {{ unidades.fuerza.value }}

### Consideraciones

De acuerdo a la Tabla 11 - Nota 4, para considerar ambas direcciones del viento, normal y oblicua, se deben tener en cuenta dos casos:

 - La fuerza resultante actúa normalmente a la cara del cartel, sobre una línea vertical que
pasa a través del centro geométrico.
- La fuerza resultante actúa normalmente a la cara del cartel, a una distancia desde la línea
vertical.
{%- endblock %}
