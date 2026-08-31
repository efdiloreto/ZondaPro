
{% set unidad_presion = unidades.presion.value + "/m^2^" %}

{% macro constantes_terreno(constantes) -%}
| $\alpha$ | Z~g~ (m) | $\hat{a}$ | $\hat{b}$ | $\bar{\alpha}$ | $\bar{b}$ | c | $\iota$ (m) | $\bar{\epsilon}$ | Z~min~ (m) |
|:--------:|:--------:|:---------:|:---------:|:--------------:|:---------:|:-:|:-----------:|:----------------:|:----------:|
|{% for parametro in constantes -%}{{ '%.2f'|format(parametro) }}|{% endfor %}
{%- endmacro %}

{% macro tabla_rafaga(rafaga, flexibilidad) -%}
{%- if flexibilidad == enums.Flexibilidad.FLEXIBLE -%}
| $\bar{z}$ | $I_{\bar{z}}$ | $I_{\bar{z}}$ | g~R~ | R | Q | G |
|:---------:|:-------------:|:-------------:|:----:|:-:|:-:|:-:|
{% else -%}
| z¯ | I~z¯~ | L~z¯~ | Q | G |
|:--:|:-----:|:-----:|:-:|:-:|
{% endif -%}
|
{%- for parametro in rafaga.parametros -%}
{%- if parametro is not none -%}
{{ '%.2f'|format(parametro) }}|
{%- endif -%}
{%- endfor -%}
{{ '%.2f'|format(rafaga.factor_q) }}|{{ '%.2f'|format(rafaga.factor) }}|
{%- endmacro %}

{#
  Tabla de presiones de edificio.

  Todo lo que antes decidía la plantilla -si la superficie está zonificada, si
  varía con la altura, si lleva presión interna, qué símbolos usan las columnas-
  sale ahora de las propias filas.
#}
{% macro presiones(filas, titulo) -%}
{%- set primera = filas|first -%}
{%- set por_altura = filas|map(attribute='q.altura')|unique|list|length > 1 -%}
{%- set sub = 'z' if por_altura else 'h' -%}
{%- set sub_kzt = 'zt' if por_altura else 'zth' -%}
{%- set es_componente = primera.sistema == enums.SistemaResistente.COMPONENTES -%}
{%- set simbolo_cp = 'GC~p~' if es_componente else 'C~p~' -%}
{%- if por_altura -%}
{%- set encabezado = 'Alturas (m)' -%}
{%- elif primera.rango -%}
{%- set encabezado = 'Distancias (m)' -%}
{%- elif primera.zona_componente -%}
{%- set encabezado = 'Zona (m)' -%}
{%- elif primera.zona != enums.ZonaEdificio.PAREDES -%}
{%- set encabezado = 'Distancias (m)' -%}
{%- else -%}
{%- set encabezado = 'Alturas (m)' -%}
{%- endif %}
: {{ titulo }} _(Ref: {{ primera.referencia }})_{% if primera.distancia_a is not none %} _(a: {{ primera.distancia_a }})_{% endif %}

{% if primera.con_presion_interna -%}
| {{ encabezado }} | K~{{ sub }}~ | K~{{ sub_kzt }}~ | {{ simbolo_cp }} | q~{{ sub }}~ ({{ unidad_presion }}) | p~n~ [+GC~pi~] ({{ unidad_presion }}) | p~n~ [-GC~pi~] ({{ unidad_presion }}) |
|:-----------:|:----:|:-----:|:----:|:---------------------------:|:-------------------------------------:|:-------------------------------------:|
{% else -%}
| {{ encabezado }} | K~{{ sub }}~ | K~{{ sub_kzt }}~ | {{ simbolo_cp }} | q~{{ sub }}~ ({{ unidad_presion }}) | p~n~ ({{ unidad_presion }}) |
|:-----------:|:----:|:-----:|:----:|:---------------------------:|:---------------------------:|
{% endif -%}
{% for fila in filas -%}
{%- if por_altura -%}
{%- set etiqueta = '%.2f'|format(fila.q.altura) -%}
{%- elif fila.rango -%}
{%- set etiqueta = '%.2f a %.2f'|format(fila.rango[0], fila.rango[1]) -%}
{%- elif fila.zona_componente -%}
{%- set etiqueta = fila.zona_componente.value|capitalize -%}
{#- El positivo suele ser único y viajar en la zona "todas". Cuando el
    Reglamento lo distingue por zona (Fig. 5.3-2A, Nota 5, con parapeto), la
    zona aparece con dos filas y hay que decir cuál es cuál. -#}
{%- if fila.tipo_presion == enums.TipoPresionComponentesParedesCubierta.POSITIVA and fila.zona_componente.name != 'TODAS' -%}
{%- set etiqueta = '%s (positiva)'|format(etiqueta) -%}
{%- endif -%}
{%- else -%}
{%- set etiqueta = 'Total' -%}
{%- endif -%}
|
{{- etiqueta }} |
{{- '%.2f'|format(fila.q.kz) }} |
{{- '%.2f'|format(fila.q.kzt) }} |
{{- '%.2f'|format(fila.cp) }} |
{{- '%.2f'|format(fila.q.valor|convertir_unidad(unidades.presion)) }} |
{{- '%.2f'|format(fila.pos|convertir_unidad(unidades.presion)) }} |
{%- if fila.con_presion_interna -%}
{{ '%.2f'|format(fila.neg|convertir_unidad(unidades.presion)) }} |
{%- endif %}
{% endfor -%}
{% endmacro %}

{% macro presiones_cubierta_aislada(filas, titulo) -%}
{%- set primera = filas|first %}
: {{ titulo }} _(Ref: {{ primera.referencia }})_

| {{ 'Zona - Tipo' if primera.zona else 'Tipo' }} | K~h~ | K~zth~ | C~pn~ | q~h~ ({{ unidad_presion }}) | p ({{ unidad_presion }}) | p~fricción~ ({{ unidad_presion }}) |
|:-----------:|:----:|:------:|:-----:|:---------------------------:|:------------------------:|:----------------------------------:|
{% for fila in filas -%}
|
{%- if fila.zona -%}
{{ "%s - %s"|format(fila.zona.value|upper, fila.extremo.value|capitalize) }} |
{%- else -%}
{{ fila.extremo.value|capitalize }} |
{%- endif -%}
{{- '%.2f'|format(fila.q.kz) }} |
{{- '%.2f'|format(fila.q.kzt) }} |
{{- '%.2f'|format(fila.cpn) }} |
{{- '%.2f'|format(fila.q.valor|convertir_unidad(unidades.presion)) }} |
{{- '%.2f'|format(fila.presion|convertir_unidad(unidades.presion)) }} |
{{- '%.2f'|format(fila.presion_friccion|convertir_unidad(unidades.presion)) }} |
{% endfor %}
{% endmacro %}

{% macro presiones_cartel(filas) -%}
{%- set primera = filas|first %}
: PRESIONES LOCALES _(Ref: {{ primera.referencia }})_

| Alturas (m) | K~z~ | K~zt~ | C~f~ | q~z~ ({{ unidad_presion }}) | p~n~ ({{ unidad_presion }}) | Área Parcial (m^2^) | F~z~ ({{ unidades.fuerza.value }}) |
|:-----------:|:----:|:-----:|:----:|:---------------------------:|:---------------------------:|:-------------------:|:----------------------------------:|
{% for fila in filas -%}
|
{{- '%.2f'|format(fila.q.altura) }} |
{{- '%.2f'|format(fila.q.kz) }} |
{{- '%.2f'|format(fila.q.kzt) }} |
{{- '%.2f'|format(fila.cf) }} |
{{- '%.2f'|format(fila.q.valor|convertir_unidad(unidades.presion)) }} |
{{- '%.2f'|format(fila.presion|convertir_unidad(unidades.presion)) }} |
{%- if fila.area_parcial is none -%}- | - |
{% else -%}
{{- '%.2f'|format(fila.area_parcial) }} |
{{- '%.2f'|format(fila.fuerza|convertir_unidad(unidades.fuerza)) }} |
{% endif -%}
{% endfor %}
{% endmacro %}

{#
  Arma el título de una superficie de cubierta o alero. Cuando la superficie
  está dividida en zonas sin posición se muestra igualmente el caso de presión
  si la fila lo tiene (el caso positivo del nuevo Reglamento con ángulo < 10°).
#}
{% macro titulo_superficie(base, clave, sin_posicion=none) -%}
{%- if clave[0] is none -%}
{{- sin_posicion or base }}{% if clave[1] %} - {{ clave[1].value|upper }}{% endif %}
{%- else -%}
{{- base }} {{ clave[0].value|upper }}{% if clave[1] %} - {{ clave[1].value|upper }}{% endif %}
{%- endif -%}
{%- endmacro %}
