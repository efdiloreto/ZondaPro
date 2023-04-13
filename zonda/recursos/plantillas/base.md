---
linestretch: 1
lang: es
table-numbers: false
title: {% block titulo_encabezado -%}{%- endblock %}
subtitle: CIRSOC 102-2005
header-includes:
    - \usepackage[labelformat=empty]{caption}
    - \pagenumbering{gobble}
---

## DATOS GENERALES
### REGLAMENTO
{% block datos_codigo -%}
{%- endblock %}

## DATOS DE ENTRADA
{% block datos_geometria -%}
{%- endblock %}

### VIENTO
Velocidad básica: {{ '%.2f'|format(estructura.velocidad) }} m/s

Categoría de exposición: {{ estructura.categoria_exp.value }}

### FACTOR DE RÁFAGA
{% block datos_rafaga -%}
{%- endblock %}

### TOPOGRAFÍA
{% if estructura.considerar_topografia -%}
Tipo de terreno: {{ estructura.tipo_terreno.value|capitalize }}

Altura de terreno: {{ '%.2f'|format(estructura.altura_terreno) }} m

Distancia a la cresta: {{ '%.2f'|format(estructura.distancia_cresta) }} m

Distancia a {{ estructura.direccion.value|capitalize }}: {{ '%.2f'|format(estructura.distancia_barlovento_sotavento) }} m
{% else -%}
Topografía no considerada.
{% endif %}
## RESULTADOS
{% block resultados_geometria %}
{% endblock -%}
{% block resultados_constantes_terreno %}
### CONSTANTES DE EXPOSICIÓN DEL TERRENO
{% endblock %}
{% block resultados_rafaga %}
### FACTOR DE RÁFAGA
{% endblock %}

### FACTOR TOPOGRÁFICO
{% if estructura.topografia.topografia_considerada() -%}
|K~1~/(H/L~h~)| $\gamma$ | $\mu$ |L~h~|K~1~|K~2~|K~3~|
|:-----------:|:-:|:-:|:--:|:--:|:--:|:--:|
|
{%- for parametro in estructura.topografia.parametros[:-1] -%}
{{ '%.2f'|format(parametro) }} |
{%- endfor %}
{%- block k3 %} |
{% endblock %}
{% block resultados_topografia_pie %}
{% endblock %}
{% else -%}
Factor topográfico, K~zt~: {{'%.2f'|format(1)}}
{% if estructura.considerar_topografia %}
No se considera la topografía debido a que no se cumplen todas las condiciones del artículo 5.7.1.
{% endif -%}
{% endif %}

{% block presiones_sprfv %}
{% endblock %}
{% block presiones_componentes %}
{% endblock %}
