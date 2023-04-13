
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

{% macro presiones_paredes_barlovento(alturas, kz, kzt, qz, presiones) %}
:PARED BARLOVENTO _(Ref: Figura 3 cont.)_

| Alturas (m) | K~z~ | K~zt~ | C~p~ | q~z~ ({{ unidad_presion }}) | p~n~ [+GC~pi~] ({{ unidad_presion }}) | p~n~ [-GC~pi~] ({{ unidad_presion }}) |
|:-----------:|:----:|:-----:|:----:|:---------------------------:|:-------------------------------------:|:-------------------------------------:|
{% for k in kz -%}
|
{{- '%.2f'|format(alturas[loop.index0]) }} |
{{- '%.2f'|format(k) }} |
{{- '%.2f'|format(kzt[loop.index0]) }} |
{{- '%.2f'|format(0.8) }} |
{{- '%.2f'|format(qz[loop.index0]|convertir_unidad(unidades.presion)) }} |
{{- '%.2f'|format(presiones.pos[loop.index0]|convertir_unidad(unidades.presion)) }} |
{{- '%.2f'|format(presiones.neg[loop.index0]|convertir_unidad(unidades.presion)) }} |
{% endfor -%}
{% endmacro %}

{% macro presiones_otras_paredes_cubierta(kh, kzth, cp, qh, presiones, titulo, encabezado_alturas) %}
: {{ titulo }} _(Ref: Figura 3 cont.)_

| {{ encabezado_alturas }} (m) | K~h~ | K~zth~ | C~p~ | q~h~ ({{ unidad_presion }}) | p~n~ [+GC~pi~] ({{ unidad_presion }}) | p~n~ [-GC~pi~] ({{ unidad_presion }}) |
|:----------------------------:|:----:|:------:|:----:|:---------------------------:|:-------------------------------------:|:-------------------------------------:|
| Total |
{{- '%.2f'|format(kh) }} |
{{- '%.2f'|format(kzth) }} |
{{- '%.2f'|format(cp) }} |
{{- '%.2f'|format(qh|convertir_unidad(unidades.presion)) }} |
{{- '%.2f'|format(presiones.pos|convertir_unidad(unidades.presion)) }} |
{{- '%.2f'|format(presiones.neg|convertir_unidad(unidades.presion)) }} |
{% endmacro %}

{% macro presiones_normal_aleros(kh, kzth, cp, qh, presiones, titulo) %}
: {{ titulo }} _(Ref: Figura 3 cont.)_

| Distancias (m) | K~h~ | K~zth~ | C~p~ | q~h~ ({{ unidad_presion }}) | p~n~ ({{ unidad_presion }}) |
|:--------------:|:----:|:------:|:----:|:---------------------------:|:---------------------------:|
| Total |
{{- '%.2f'|format(kh) }} |
{{- '%.2f'|format(kzth) }} |
{{- '%.2f'|format(cp) }} |
{{- '%.2f'|format(qh|convertir_unidad(unidades.presion)) }} |
{{- '%.2f'|format(presiones|convertir_unidad(unidades.presion)) }} |
{% endmacro %}

{% macro presiones_cubierta_paralelo(zonas, kh, kzth, cp, qh, presiones) %}
: CUBIERTA _(Ref: Figura 3 cont.)_

| Distancias (m) | K~h~ | K~zth~ | C~p~ | q~h~ ({{ unidad_presion }}) | p~n~ [+GC~pi~] ({{ unidad_presion }}) | p~n~ [-GC~pi~] ({{ unidad_presion }}) |
|:--------------:|:----:|:------:|:----:|:---------------------------:|:-------------------------------------:|:-------------------------------------:|
{% for distancia, cp, presion_pos, presion_neg in zip(zonas, cp, presiones.pos, presiones.neg) -%}
|
{{- '%.2f'|format(distancia[0]) }} a {{ '%.2f'|format(distancia[1]) }} |
{{- '%.2f'|format(kh) }} |
{{- '%.2f'|format(kzth) }} |
{{- '%.2f'|format(cp) }} |
{{- '%.2f'|format(qh|convertir_unidad(unidades.presion)) }} |
{{- '%.2f'|format(presion_pos|convertir_unidad(unidades.presion)) }} |
{{- '%.2f'|format(presion_neg|convertir_unidad(unidades.presion)) }} |
{% endfor -%}
{% endmacro %}

{% macro presiones_cubierta_paralelo_aleros(zonas, kh, kzth, cp, qh, presiones) %}
: ALEROS _(Ref: Figura 3 cont.)_

| Distancias (m) | K~h~ | K~zth~ | C~p~ | q~h~ ({{ unidad_presion }}) | p~n~ ({{ unidad_presion }}) |
|:--------------:|:----:|:------:|:----:|:---------------------------:|:---------------------------:|
{% for distancia, cp, presion in zip(zonas, cp, presiones) -%}
|
{{- '%.2f'|format(distancia[0]) }} a {{ '%.2f'|format(distancia[1]) }} |
{{- '%.2f'|format(kh) }} |
{{- '%.2f'|format(kzth) }} |
{{- '%.2f'|format(cp) }} |
{{- '%.2f'|format(qh|convertir_unidad(unidades.presion)) }} |
{{- '%.2f'|format(presion|convertir_unidad(unidades.presion)) }} |
{% endfor %}
{% endmacro %}

{% macro presiones_componentes(componente, kh, kzth, qh, presiones, titulo, referencia, distancia_a) %}
: Componente: {{ titulo }} _(Ref: {{ referencia }})_ _(a: {{ distancia_a }})_

| Zona (m) | K~h~ | K~zth~ | GC~p~ | q~h~ ({{ unidad_presion }}) | p~n~ [+GC~pi~] ({{ unidad_presion }}) | p~n~ [-GC~pi~] ({{ unidad_presion }}) |
|:--------:|:----:|:------:|:-----:|:---------------------------:|:-------------------------------------:|:-------------------------------------:|
{% for zona, cp in componente.items() -%}
|
{{- zona.value|capitalize }} |
{{- '%.2f'|format(kh) }} |
{{- '%.2f'|format(kzth) }} |
{{- '%.2f'|format(cp) }} |
{{- '%.2f'|format(qh|convertir_unidad(unidades.presion)) }} |
{{- '%.2f'|format(presiones[zona].pos|convertir_unidad(unidades.presion)) }} |
{{- '%.2f'|format(presiones[zona].neg|convertir_unidad(unidades.presion)) }} |
{% endfor -%}
{% endmacro %}

{% macro presiones_componentes_alero(componente, kh, kzth, qh, presiones, titulo, referencia, distancia_a) %}
: Componente: {{ titulo }} _(Ref: {{ referencia }})_ _(a: {{ distancia_a }})_

| Zona (m) | K~h~ | K~zth~ | GC~p~ | q~h~ ({{ unidad_presion }}) | p~n~ ({{ unidad_presion }}) |
|:--------:|:----:|:------:|:-----:|:---------------------------:|:---------------------------:|
{% for zona, cp in componente.items() -%}
|
{{- zona.value|capitalize }} |
{{- '%.2f'|format(kh) }} |
{{- '%.2f'|format(kzth) }} |
{{- '%.2f'|format(cp) }} |
{{- '%.2f'|format(qh|convertir_unidad(unidades.presion)) }} |
{{- '%.2f'|format(presiones[zona]|convertir_unidad(unidades.presion)) }} |
{% endfor -%}
{% endmacro %}

{% macro presiones_componentes_pared(componente, kh, kzth, qh, presiones, titulo, referencia, distancia_a, pared) %}
: PARED {{ pared|upper }} - Componente: {{ titulo }} _(Ref: {{ referencia }})_ _(a: {{ distancia_a }})_

| Zona (m) | K~h~ | K~zth~ | GC~p~ | q~h~ ({{ unidad_presion }}) | p~n~ [+GC~pi~] ({{ unidad_presion }}) | p~n~ [-GC~pi~] ({{ unidad_presion }}) |
|:--------:|:----:|:------:|:-----:|:---------------------------:|:-------------------------------------:|:-------------------------------------:|
{% for zona, cp in componente.items() -%}
|
{{- zona.value|capitalize }} |
{{- '%.2f'|format(kh) }} |
{{- '%.2f'|format(kzth) }} |
{{- '%.2f'|format(cp) }} |
{{- '%.2f'|format(qh|convertir_unidad(unidades.presion)) }} |
{{- '%.2f'|format(presiones[zona].pos|convertir_unidad(unidades.presion)) }} |
{{- '%.2f'|format(presiones[zona].neg|convertir_unidad(unidades.presion)) }} |
{% endfor -%}
{% endmacro %}

{% macro presiones_componentes_pared_barlovento(alturas, kz, kzt, gcp, qz, presiones_componentes, areas_componentes, referencia, distancia_a) %}
{% for componente, zonas in presiones_componentes.items() %}
{% for zona, presion in zonas.items() -%}
: PARED BARLOVENTO - Componente: _({{ componente }}: {{ areas_componentes[componente] }} m~2~)_  _(Zona: {{ zona.value|capitalize }})_ _(Ref: {{ referencia }})_ _(a: {{ distancia_a }})_

| Alturas (m) | K~z~ | K~zt~ | GC~p~ | q~z~ ({{ unidad_presion }}) | p~n~ [+GC~pi~] ({{ unidad_presion }}) | p~n~ [-GC~pi~] ({{ unidad_presion }}) |
|:-----------:|:----:|:-----:|:-----:|:---------------------------:|:-------------------------------------:|:-------------------------------------:|
{% for k in kz -%}
|
{{- '%.2f'|format(alturas[loop.index0]) }} |
{{- '%.2f'|format(k) }} |
{{- '%.2f'|format(kzt[loop.index0]) }} |
{{- '%.2f'|format(gcp[componente][zona]) }} |
{{- '%.2f'|format(qz[loop.index0]|convertir_unidad(unidades.presion)) }} |
{{- '%.2f'|format(presion.pos[loop.index0]|convertir_unidad(unidades.presion)) }} |
{{- '%.2f'|format(presion.neg[loop.index0]|convertir_unidad(unidades.presion)) }} |
{% endfor -%}
{% endfor -%}
{% endfor -%}
{% endmacro %}

{% macro presiones_cubierta_aislada_globales(kh, kzth, qh, cpn, presiones, referencia) %}
: PRESIONES GLOBALES _(Ref: {{ referencia }})_

| Tipo | K~h~ | K~zth~ | C~pn~ | q~h~ ({{ unidad_presion }}) | p ({{ unidad_presion }}) | p~fricción~ ({{ unidad_presion }}) |
|:-----------:|:----:|:------:|:-----:|:--------------------:|:------------------------:|:----------------------------------:|
{% for tipo, valor_cpn in cpn.items() -%}
|
{{- tipo.value|capitalize }} |
{{- '%.2f'|format(kh) }} |
{{- '%.2f'|format(kzth) }} |
{{- '%.2f'|format(valor_cpn) }} |
{{- '%.2f'|format(qh|convertir_unidad(unidades.presion)) }} |
{{- '%.2f'|format(presiones[tipo]|convertir_unidad(unidades.presion)) }} |
{{- '%.2f'|format(presiones[tipo] * estructura.coeficiente_friccion|convertir_unidad(unidades.presion)) }} |
{% endfor %}
{% endmacro %}

{% macro presiones_cubierta_aislada_locales(kh, kzth, qh, cpn, presiones, referencia) %}
: PRESIONES LOCALES _(Ref: {{ referencia }})_

| Zona - Tipo | K~h~ | K~zth~ | C~pn~ | q~h~ ({{ unidad_presion }}) | p ({{ unidad_presion }}) | p~fricción~ ({{ unidad_presion }}) |
|:-----------:|:----:|:------:|:-----:|:---------------------------:|:------------------------:|:----------------------------------:|
{% for zona, tipos in cpn.items() -%}
{% for tipo, valor_cpn in tipos.items() -%}
{% if zona not in (enums.ZonaPresionCubiertaAislada.BC, enums.ZonaPresionCubiertaAislada.BD) -%}
|
{{- "%s - %s"|format(zona.value|upper, tipo.value|capitalize) }} |
{{- '%.2f'|format(kh) }} |
{{- '%.2f'|format(kzth) }} |
{{- '%.2f'|format(valor_cpn) }} |
{{- '%.2f'|format(qh|convertir_unidad(unidades.presion)) }} |
{{- '%.2f'|format(presiones[zona][tipo]|convertir_unidad(unidades.presion)) }} |
{{- '%.2f'|format(presiones[zona][tipo] * estructura.coeficiente_friccion|convertir_unidad(unidades.presion)) }} |
{% endif -%}
{% endfor -%}
{% endfor %}
{% endmacro %}

{% macro presiones_cartel(alturas, kz, kzt, qz, cf, presiones, areas, fuerzas, fuerza_total) %}
: PRESIONES LOCALES _(Ref: Tabla 11)_

| Alturas (m) | K~z~ | K~zt~ | C~f~ | q~z~ ({{ unidad_presion }}) | p~n~ ({{ unidad_presion }}) | Área Parcial (m^2^) | F~z~ ({{ unidades.fuerza.value }}) |
|:-----------:|:----:|:-----:|:----:|:---------------------------:|:---------------------------:|:-------------------:|:----------------------------------:|
{% for k in kz -%}
|
{{- '%.2f'|format(alturas[loop.index0]) }} |
{{- '%.2f'|format(k) }} |
{{- '%.2f'|format(kzt[loop.index0]) }} |
{{- '%.2f'|format(cf) }} |
{{- '%.2f'|format(qz[loop.index0]|convertir_unidad(unidades.presion)) }} |
{{- '%.2f'|format(presiones[loop.index0]|convertir_unidad(unidades.presion)) }} |
{%- if loop.index0 == 0 -%}- | - |
{% else -%}
{{- '%.2f'|format(areas[loop.index0 - 1]) }} |
{{- '%.2f'|format(fuerzas[loop.index0 - 1]|convertir_unidad(unidades.fuerza)) }} |
{% endif -%}
{% endfor %}
{% endmacro %}