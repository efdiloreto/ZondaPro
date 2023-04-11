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

Categoría: {{ estructura.categoria.value }}

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
{{ '%.2f'|format(estructura.topografia.parametros.k3[estructura.geometria.alturas == estructura.geometria.cubierta.altura_media][0]) }}
{%- endblock %}

{% block resultados_topografia_pie -%}
Notas:

{% if estructura.topografia.topografia_considerada() -%}
- El valor de K~3~ que se muestra en la tabla es el correspondiente a la altura media. Los valores para las demás alturas se calculan automáticamente y no son mostrados.

- Los valores de K~zt~ se encuentan en las tablas de presiones.
{%- endif %}
{%- endblock %}
{%- set param_comunes_pared_cubierta = {
'kh': estructura.presiones.cubierta.sprfv.coeficiente_exposicion_media,
'kzth': estructura.presiones.cubierta.sprfv.factor_topografico_media,
'qh': estructura.presiones.cubierta.sprfv.presion_velocidad_media,
} -%}
{%- set zonas_cubierta_sprfv = estructura.cp.cubierta.sprfv.zonas -%}
{%- set cp_paredes_sprfv = estructura.cp.paredes.sprfv() -%}
{%- set cp_cubierta_sprfv = estructura.cp.cubierta.sprfv() -%}
{%- set presiones_paredes_sprfv = estructura.presiones.paredes.sprfv() -%}
{%- set presiones_cubierta_sprfv = estructura.presiones.cubierta.sprfv() -%}

{% block presiones_sprfv -%}
### PRESIONES - SPRFV
#### VIENTO PARALELO A LA CUMBRERA
{{ ma.presiones_paredes_barlovento(
estructura.presiones.paredes.sprfv.alturas,
estructura.presiones.paredes.sprfv.coeficientes_exposicion,
estructura.presiones.paredes.sprfv.factor_topografico,
estructura.presiones.paredes.sprfv.presiones_velocidad,
presiones_paredes_sprfv[enums.DireccionVientoMetodoDireccionalSprfv.PARALELO][enums.ParedEdificioSprfv.BARLOVENTO],
) -}}
{%- for pared, valor in cp_paredes_sprfv[enums.DireccionVientoMetodoDireccionalSprfv.PARALELO].items() -%}
{%- if pared != enums.ParedEdificioSprfv.BARLOVENTO -%}
{{- ma.presiones_otras_paredes_cubierta(
cp=valor,
presiones=presiones_paredes_sprfv[enums.DireccionVientoMetodoDireccionalSprfv.PARALELO][pared],
titulo="PARED %s"|format(pared.value|upper),
encabezado_alturas='Alturas',
**param_comunes_pared_cubierta
) -}}
{%- endif %}
{%- endfor %}
{{- ma.presiones_cubierta_paralelo(
zonas=zonas_cubierta_sprfv[enums.DireccionVientoMetodoDireccionalSprfv.PARALELO],
cp=cp_cubierta_sprfv[enums.DireccionVientoMetodoDireccionalSprfv.PARALELO],
presiones=presiones_cubierta_sprfv[enums.DireccionVientoMetodoDireccionalSprfv.PARALELO],
**param_comunes_pared_cubierta
) -}}
{%- if estructura.alero -%}
{%- set cp_alero_sprfv = estructura.cp.alero.sprfv() -%}
{%- set presiones_alero_sprfv = estructura.presiones.alero.sprfv() -%}
{{- ma.presiones_cubierta_paralelo_aleros(
zonas=zonas_cubierta_sprfv[enums.DireccionVientoMetodoDireccionalSprfv.PARALELO],
cp=cp_alero_sprfv[enums.DireccionVientoMetodoDireccionalSprfv.PARALELO],
presiones=presiones_alero_sprfv[enums.DireccionVientoMetodoDireccionalSprfv.PARALELO],
**param_comunes_pared_cubierta
) }}
{%- endif -%}
#### VIENTO NORMAL A LA CUMBRERA
{{- ma.presiones_paredes_barlovento(
estructura.presiones.paredes.sprfv.alturas,
estructura.presiones.paredes.sprfv.coeficientes_exposicion_alero,
estructura.presiones.paredes.sprfv.factor_topografico_alero,
estructura.presiones.paredes.sprfv.presion_velocidad_alero,
presiones_paredes_sprfv[enums.DireccionVientoMetodoDireccionalSprfv.NORMAL][enums.ParedEdificioSprfv.BARLOVENTO],
) -}}
{% for pared, valor in cp_paredes_sprfv[enums.DireccionVientoMetodoDireccionalSprfv.NORMAL].items() -%}
{% if pared != enums.ParedEdificioSprfv.BARLOVENTO -%}
{{- ma.presiones_otras_paredes_cubierta(
cp=valor,
presiones=presiones_paredes_sprfv[enums.DireccionVientoMetodoDireccionalSprfv.NORMAL][pared],
titulo="PARED %s"|format(pared.value|upper),
encabezado_alturas='Alturas',
**param_comunes_pared_cubierta
) }}
{%- endif %}
{%- endfor -%}
{%- if estructura.cp.cubierta.sprfv.normal_como_paralelo -%}
{{- ma.presiones_cubierta_paralelo(
zonas=zonas_cubierta_sprfv[enums.DireccionVientoMetodoDireccionalSprfv.NORMAL],
cp=cp_cubierta_sprfv[enums.DireccionVientoMetodoDireccionalSprfv.NORMAL],
presiones=presiones_cubierta_sprfv[enums.DireccionVientoMetodoDireccionalSprfv.NORMAL],
**param_comunes_pared_cubierta
) }}
{%- else -%}
{%- for cubierta, valor in cp_cubierta_sprfv[enums.DireccionVientoMetodoDireccionalSprfv.NORMAL].items() -%}
{% if cubierta == enums.PosicionCubiertaAleroSprfv.BARLOVENTO -%}
{% for caso, cp in valor.items() -%}
{{ ma.presiones_otras_paredes_cubierta(
cp=cp, presiones=presiones_cubierta_sprfv[enums.DireccionVientoMetodoDireccionalSprfv.NORMAL][cubierta][caso],
titulo="CUBIERTA %s - %s"|format(cubierta.value|upper, caso.value|upper),
encabezado_alturas='Distancias',
**param_comunes_pared_cubierta
) }}
{%- endfor %}
{%- else -%}
{{ ma.presiones_otras_paredes_cubierta(
cp=valor,
presiones=presiones_cubierta_sprfv[enums.DireccionVientoMetodoDireccionalSprfv.NORMAL][cubierta],
titulo="CUBIERTA %s"|format(cubierta.value|upper),
encabezado_alturas='Distancias',
**param_comunes_pared_cubierta
) }}
{%- endif %}
{%- endfor %}
{%- endif %}
{%- if estructura.alero -%}
{% if estructura.cp.cubierta.sprfv.normal_como_paralelo -%}
{{- ma.presiones_cubierta_paralelo_aleros(
zonas=zonas_cubierta_sprfv[enums.DireccionVientoMetodoDireccionalSprfv.NORMAL],
cp=cp_alero_sprfv[enums.DireccionVientoMetodoDireccionalSprfv.NORMAL],
presiones=presiones_alero_sprfv[enums.DireccionVientoMetodoDireccionalSprfv.NORMAL],
**param_comunes_pared_cubierta
) -}}
{%- else -%}
{%- for cubierta, valor in cp_alero_sprfv[enums.DireccionVientoMetodoDireccionalSprfv.NORMAL].items() -%}
{%- if cubierta == enums.PosicionCubiertaAleroSprfv.BARLOVENTO -%}
{% for caso, cp in valor.items() -%}
{{- ma.presiones_normal_aleros(
cp=cp, presiones=presiones_alero_sprfv[enums.DireccionVientoMetodoDireccionalSprfv.NORMAL][cubierta][caso],
titulo="ALERO %s - %s"|format(cubierta.value|upper, caso.value|upper),
**param_comunes_pared_cubierta
) }}
{%- endfor %}
{%- else -%}
{{ ma.presiones_normal_aleros(
cp=valor,
presiones=presiones_alero_sprfv[enums.DireccionVientoMetodoDireccionalSprfv.NORMAL][cubierta],
titulo="ALERO %s"|format(cubierta.value|upper),
**param_comunes_pared_cubierta
) }}
{%- endif %}
{%- endfor %}
{%- endif %}
{% endif %}
{%- endblock -%}
{%- block presiones_componentes -%}
{%- if estructura.componentes_paredes or estructura.componentes_cubierta -%}
{%- set param_comunes_pared_cubierta_comp = {
'kh': estructura.presiones.cubierta.componentes.coeficiente_exposicion_media,
'kzth': estructura.presiones.cubierta.componentes.factor_topografico_media,
'qh': estructura.presiones.cubierta.componentes.presion_velocidad_media,
} -%}
### PRESIONES - COMPONENTES Y REVESTIMIENTOS
{% endif -%}
{% if estructura.componentes_paredes -%}
#### PAREDES
{% set referencia_componentes_paredes = estructura.cp.paredes.componentes.referencia -%}
{% set distancia_a_paredes = estructura.cp.paredes.componentes.distancia_a -%}
{% set cp_paredes_componentes = estructura.cp.paredes.componentes() -%}
{% set presiones_paredes_componentes = estructura.presiones.paredes.componentes() -%}
{% if referencia_componentes_paredes != "Figura 8" -%}
{% for nombre, area in estructura.componentes_paredes.items() -%}
{{ ma.presiones_componentes(
componente=cp_paredes_componentes[nombre],
presiones=presiones_paredes_componentes[nombre],
titulo="%s (%s m^2^)"|format(nombre, area),
referencia=referencia_componentes_paredes,
distancia_a=distancia_a_paredes,
**param_comunes_pared_cubierta_comp
) }}
{%- endfor %}
{%- else -%}
{% for pared, componentes in presiones_paredes_componentes.items() %}
{% if pared == enums.ParedEdificioSprfv.BARLOVENTO -%}
{{ ma.presiones_componentes_pared_barlovento(
estructura.presiones.paredes.sprfv.alturas,
estructura.presiones.paredes.sprfv.coeficientes_exposicion,
estructura.presiones.paredes.sprfv.factor_topografico,
cp_paredes_componentes,
estructura.presiones.paredes.sprfv.presiones_velocidad,
componentes,
estructura.componentes_paredes,
referencia_componentes_paredes,
distancia_a_paredes,
) }}

{% else %}

{% for componente, presiones in componentes.items() %}
{{ ma.presiones_componentes_pared(
componente=cp_paredes_componentes[componente],
presiones=presiones,
titulo="%s (%s m^2^)"|format(componente, estructura.componentes_paredes[componente]),
referencia=referencia_componentes_paredes,
distancia_a=distancia_a_paredes,
pared=pared.value,
**param_comunes_pared_cubierta_comp
) }}
{%- endfor %}
{%- endif %}
{%- endfor %}
{%- endif %}
{%- endif %}
{% if estructura.componentes_cubierta -%}
#### CUBIERTA
{%- set referencia_componentes_cubierta =  estructura.cp.cubierta.componentes.referencia -%}
{% set distancia_a_cubierta = estructura.cp.cubierta.componentes.distancia_a -%}
{% set cp_cubierta_componentes = estructura.cp.cubierta.componentes() -%}
{% set presiones_cubierta_componentes = estructura.presiones.cubierta.componentes() -%}
{% for nombre, area in estructura.componentes_cubierta.items() -%}
{{ ma.presiones_componentes(
componente=cp_cubierta_componentes[nombre],
presiones=presiones_cubierta_componentes[nombre],
titulo="%s (%s m^2^)"|format(nombre, area),
referencia=referencia_componentes_cubierta,
distancia_a=distancia_a_cubierta,
**param_comunes_pared_cubierta_comp
) }}
{%- endfor %}
{%- if estructura.alero -%}
#### ALERO
{%- set referencia_componentes_alero =  estructura.cp.alero.componentes.referencia -%}
{%- set cp_alero_componentes = estructura.cp.alero.componentes() -%}
{%- set presiones_alero_componentes= estructura.presiones.alero.componentes() -%}
{% for nombre, area in estructura.componentes_cubierta.items() -%}
{{ ma.presiones_componentes_alero(
componente=cp_alero_componentes[nombre],
presiones=presiones_alero_componentes[nombre],
titulo="%s (%s m^2^)"|format(nombre, area),
referencia=referencia_componentes_alero,
distancia_a=distancia_a_cubierta,
**param_comunes_pared_cubierta_comp
) }}
{%- endfor %}
{%- endif %}
{%- endif %}
{%- endblock %}
