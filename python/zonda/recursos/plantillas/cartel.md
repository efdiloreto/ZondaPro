{% extends "base.md" %}
{% import "macros.md" as ma with context%}

{% block titulo_encabezado -%}
CÁLCULO DE PRESIONES DE VIENTO SOBRE CARTELES
{%- endblock %}

{% block datos_codigo -%}
Referencia: Artículo 4.4.1 - Figura 4.4-1
{%- endblock %}

{% block datos_geometria -%}
### CARTEL
Altura inferior: {{ '%.2f'|format(estructura.altura_inferior) }} m

Altura superior: {{ '%.2f'|format(estructura.altura_superior) }} m

Ancho: {{ '%.2f'|format(estructura.ancho) }} m

Profundidad: {{ '%.2f'|format(estructura.profundidad) }} m

{%- endblock %}

{% block datos_rafaga -%}
{% if not estructura.factor_g_simplificado -%}
Flexibilidad: {{ estructura.flexibilidad.value|capitalize }}

Frecuencia natural: {{ '%.2f'|format(estructura.frecuencia) }} Hz

Relación de amortiguamiento: {{ '%.2f'|format(estructura.beta) }}
{% else -%}
Se adopta el factor de ráfaga igual a 0.85 de acuerdo al artículo 1.9.
{% endif %}
{%- endblock %}

{% block resultados_geometria -%}
### PARÁMETROS DE CÁLCULO
Altura neta, s: {{ '%.2f'|format(estructura.geometria.altura_neta) }} m

Altura media: {{ '%.2f'|format(estructura.geometria.altura_media) }} m

Altura de evaluación de la presión dinámica, h: {{ '%.2f'|format(estructura.altura_superior) }} m

Área: {{ '%.2f'|format(estructura.geometria.area) }} m^2^

Factor de direccionalidad, K~d~: {{ '%.2f'|format(estructura.presiones.factor_direccionalidad) }}

Relación de espacio libre, s/h: {{ '%.2f'|format(estructura.cf.relacion_espacio_libre) }}

Relación de aspecto, B/s: {{ '%.2f'|format(estructura.cf.relacion_aspecto) }}

{% if estructura.epsilon < 1 -%}
Relación de área sólida, ε: {{ '%.2f'|format(estructura.epsilon) }}

Factor de reducción por aberturas: {{ '%.3f'|format(estructura.cf.factor_aberturas) }}

{% endif -%}
{% if estructura.doble_cara -%}
Cartel de doble cara con todos los lados cerrados.

R~min~ = t / min(B, s) = {{ '%.3f'|format(estructura.cf.r_min) }}{% if estructura.cf.r_min <= 0.75 %}. Factor de reducción de C~f~ para los Casos A y B: {{ '%.3f'|format(1 - 0.133 * estructura.cf.r_min) }}{% endif %}

R~max~ = t / max(B, s) = {{ '%.3f'|format(estructura.cf.r_max) }}{% if estructura.cf.r_max <= 0.4 %}. Excentricidad reducida del Caso B: e = (0.2 - 0.25·R~max~)·B = {{ '%.2f'|format(estructura.cf.excentricidad) }} m{% endif %}

{% endif -%}
{% if estructura.esquina_retorno > 0 -%}
Esquina de retorno, L~r~: {{ '%.2f'|format(estructura.esquina_retorno) }} m (L~r~/s = {{ '%.2f'|format(estructura.esquina_retorno / estructura.geometria.altura_neta) }})

Factor de reducción por esquina de retorno: {{ '%.2f'|format(estructura.cf.factor_esquina_retorno) }}
{% endif -%}
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
- El valor de K~3~ que se muestra en la tabla es el correspondiente a la altura h. Los valores para las demás alturas se calculan automáticamente y no son mostrados.

- Los valores de K~zt~ se encuentan en las tablas de presiones.
{%- endif %}
{%- endblock %}

{% block presiones_sprfv -%}
### PRESIONES
{{ ma.presiones_cartel(estructura) }}

### Consideraciones

De acuerdo a la Nota 2 de la Figura 4.4-1, para considerar ambas direcciones del viento, normal y oblicua, se deben tener en cuenta los siguientes casos:

 - Caso A: la fuerza resultante actúa perpendicular a la cara del cartel en el centro geométrico.
 - Caso B: la fuerza resultante actúa perpendicular a la cara del cartel, a una distancia desde el centro geométrico hacia el borde de barlovento igual a e = {{ '%.2f'|format(estructura.cf.excentricidad) }} m.
{% if estructura.cf.aplica_caso_c %}
 - Caso C (B/s ≥ 2): las fuerzas resultantes actúan perpendiculares a la cara del cartel en los centros geométricos de cada región. Para viento desde el borde de sotavento, la disposición de las regiones se espeja.
{% else %}
 - Como B/s < 2, no corresponde considerar el Caso C.
{% endif %}
{% if estructura.cf.relacion_espacio_libre >= 0.999 %}
Como s/h = 1 (cartel o pared apoyado en forma continua en el terreno), la fuerza resultante actúa a una distancia igual a 0.05h por encima del centro geométrico.
{% endif %}
{% if estructura.cf.relacion_espacio_libre > 0.8 and estructura.cf.aplica_caso_c %}
Por la Nota 3, los coeficientes de fuerza del Caso C se multiplican por el factor de reducción (1.8 - s/h) = {{ '%.2f'|format(1.8 - estructura.cf.relacion_espacio_libre) }}.
{% endif %}
{%- set fuerzas = estructura.presiones.fuerzas_totales -%}
{%- if fuerzas.get(enums.CasoCartel.CASO_C, 0) > fuerzas[enums.CasoCartel.CASO_A] -%}
La fuerza de diseño es la del Caso C.
{%- else -%}
La fuerza de diseño es la de los Casos A y B.
{%- endif %}
{%- endblock %}
