{% extends "base.md" %}
{% import "macros.md" as ma with context%}

{% block titulo_encabezado -%}
CÁLCULO DE PRESIONES DE VIENTO SOBRE CUBIERTAS AISLADAS
{%- endblock %}

{% block datos_codigo -%}
Referencia: Anexo 1
{%- endblock %}

{% block datos_geometria -%}
### CUBIERTA AISLADA
Ancho: {{ '%.2f'|format(estructura.ancho) }} m

Longitud: {{ '%.2f'|format(estructura.longitud) }} m

Altura de alero: {{ '%.2f'|format(estructura.altura_alero) }} m

Altura de cumbrera: {{ '%.2f'|format(estructura.altura_cumbrera) }} m

Tipo de cubierta: {{ estructura.geometria.tipo_cubierta.value|capitalize }}

Categoría: {{ estructura.categoria.value }}
{%- endblock %}

{% block datos_rafaga -%}
Se adopta el factor de ráfaga igual a 0.85 de acuerdo al Anexo 1 - I.1.
{%- endblock %}

{% block resultados_geometria -%}
### PARÁMETROS DE CÁLCULO
Ángulo de cubierta: {{ '%.2f'|format(estructura.geometria.angulo) }}°

Altura media de cubierta: {{ '%.2f'|format(estructura.geometria.altura_media) }} m

Relación de bloqueo: {{ '%.2f'|format(estructura.geometria.relacion_bloqueo) }}

Factor de direccionalidad, K~d~: {{ '%.2f'|format(estructura.presiones.factor_direccionalidad) }}
{%- endblock %}

{% block resultados_constantes_terreno %}
{{ super() }}
{{ ma.constantes_terreno(estructura.rafaga.constantes_exp_terreno) }}
{%- endblock %}

{% block resultados_rafaga -%}
{{ super() }}
Factor de ráfaga: {{ '%.2f'|format(0.85) }}
{%- endblock %}

{% block k3 -%}
{{ '%.2f'|format(estructura.topografia.parametros.k3) }}
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
Considerar que para las presiones globales, las cubiertas a dos aguas deben ser capaces de resistir las fuerzas 
considerando un faldón con las presiones máximas o mínimas y el otro descargado.

{{ ma.presiones_cubierta_aislada_globales(
estructura.presiones.coeficientes_exposicion,
estructura.presiones.factor_topografico,
estructura.presiones.presiones_velocidad,
estructura.cpn()[enums.TipoPresionCubiertaAislada.GLOBAL],
estructura.presiones()[enums.TipoPresionCubiertaAislada.GLOBAL],
estructura.cpn.referencia,
) }}
{{ ma.presiones_cubierta_aislada_locales(
estructura.presiones.coeficientes_exposicion,
estructura.presiones.factor_topografico,
estructura.presiones.presiones_velocidad,
estructura.cpn()[enums.TipoPresionCubiertaAislada.LOCAL],
estructura.presiones()[enums.TipoPresionCubiertaAislada.LOCAL],
estructura.cpn.referencia,
) }}

### PRESIONES LATERALES
#### Presiones sobre Cenefas y Tímpanos
Según el articulo I.5 se deben considerar presiones sobre los tímpanos o cenefas a barlovento y sotavento, en caso de existir,
 de {{ '%.2f'|format(1.3 * estructura.presiones.presiones_velocidad|convertir_unidad(unidades.presion)) }} {{ unidades.presion.value + "/m^2^" }} (C~pn~=1.3) y
 {{ '%.2f'|format(0.6 * estructura.presiones.presiones_velocidad|convertir_unidad(unidades.presion)) }} {{ unidades.presion.value + "/m^2^" }} (C~pn~=0.6) respectivamente. 

#### Fuerzas de fricción
Según el articulo I.6 de deben considerar fuerzas de friccón que actuarán conjuntamente con las fuerzas normales, en caso
 de existir cenefas o tímpanos se debe adoptar la mayor entre las fuerzas de fricción o las fuerzas sobre estas últimas.

{%- endblock %}
