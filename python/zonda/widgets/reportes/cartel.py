# Copyright (c) 2018-2026, Eduardo Di Loreto <efdiloreto@gmail.com>

# This file is part of Zonda.

# Zonda is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Zonda is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Zonda.  If not, see <https://www.gnu.org/licenses/>.

"""El documento de reporte del cartel.

Arma las páginas del modelo: el resumen con las fuerzas por caso y la de
diseño resaltada, los datos de entrada, los parámetros de la Figura
4.4-1 y las presiones por caso de carga con sus consideraciones. La vista
y el PDF lo consumen sin conocerse entre sí.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from zonda.enums import CasoCartel, Unidad
from zonda.unidades import convertir_unidad
from zonda.widgets.reportes import tablas
from zonda.widgets.reportes.comunes import (
    grupo_constantes_terreno,
    grupo_factor_rafaga,
    grupo_factor_topografico,
    grupo_rafaga,
    grupo_topografia,
    grupo_viento,
)
from zonda.widgets.reportes.documento import (
    Bloque,
    Datos,
    Documento,
    Grupo,
    Nota,
    Pagina,
    Tarjeta,
    Tarjetas,
    Texto,
)
from zonda.widgets.reportes.navegacion import VistaReporte
from zonda.widgets.reportes.secciones import unidades_desde_settings

if TYPE_CHECKING:
    from zonda.cirsoc import Cartel

TEXTO_RAFAGA_SIMPLIFICADA = (
    "Se adopta el factor de ráfaga igual a 0.85 de acuerdo al artículo 1.9."
)
NOTA_MINIMAS = (
    "La fuerza de viento de diseño no debe ser menor que 0,80 kN/m² "
    "multiplicada por el área proyectada del cartel Af. Los valores de las "
    "tablas ya la tienen aplicada."
)


def vista(cartel: Cartel) -> VistaReporte:
    """Arma la vista de reporte del cartel.

    Args:
        cartel: El cartel calculado.

    Returns:
        La vista con sus páginas.
    """
    return VistaReporte(documento(cartel))


def documento(cartel: Cartel) -> Documento:
    """Arma el documento de reporte del cartel.

    Args:
        cartel: El cartel calculado.

    Returns:
        El documento con sus páginas.
    """
    unidades = unidades_desde_settings()
    return Documento(
        "PRESIONES DE VIENTO — CARTEL",
        [
            Pagina("Resumen", _bloques_resumen(cartel, unidades), exportable=False),
            Pagina("Datos de entrada", _bloques_datos(cartel)),
            Pagina("Parámetros de cálculo", _bloques_parametros(cartel)),
            Pagina("Presiones", _bloques_presiones(cartel, unidades)),
        ],
    )


def _unidad_fuerza(unidades: dict[str, Unidad]) -> str:
    return unidades["fuerza"].value


def _fuerza_total(cartel: Cartel, caso: CasoCartel, unidades: dict[str, Unidad]) -> str:
    """La fuerza total de un caso, formateada con su unidad.

    Args:
        cartel: El cartel calculado.
        caso: El caso de carga.
        unidades: Las unidades a mostrar.

    Returns:
        El texto de la fuerza.
    """
    fuerza = convertir_unidad(
        cartel.presiones.fuerzas_totales[caso], unidades["fuerza"]
    )
    return f"{fuerza:.2f} {_unidad_fuerza(unidades)}"


def _caso_de_diseño(cartel: Cartel) -> str:
    """El texto del caso que gobierna el diseño.

    Args:
        cartel: El cartel calculado.

    Returns:
        La conclusión del informe.
    """
    fuerzas = cartel.presiones.fuerzas_totales
    if fuerzas.get(CasoCartel.CASO_C, 0) > fuerzas[CasoCartel.CASO_A]:
        return "La fuerza de diseño es la del Caso C."
    return "La fuerza de diseño es la de los Casos A y B."


def _bloques_resumen(cartel: Cartel, unidades: dict[str, Unidad]) -> list[Bloque]:
    """Los bloques con las fuerzas de diseño por caso.

    Args:
        cartel: El cartel calculado.
        unidades: Las unidades a mostrar.

    Returns:
        Los bloques de la página de resumen.
    """
    fuerzas = cartel.presiones.fuerzas_totales
    # El Caso C gobierna cuando su fuerza supera a la del Caso A; si no,
    # el diseño queda en los Casos A y B.
    caso_c_gobierna = fuerzas.get(CasoCartel.CASO_C, 0) > fuerzas[CasoCartel.CASO_A]
    detalles = {
        CasoCartel.CASO_A: f"{cartel.geometria.area:.2f} m² de área proyectada",
        CasoCartel.CASO_B: (
            f"excentricidad e = {cartel.cf.excentricidad:.2f} m"
            if cartel.cf.excentricidad
            else None
        ),
        CasoCartel.CASO_C: "repartida en regiones",
    }
    tarjetas_fuerza = []
    for caso in (CasoCartel.CASO_A, CasoCartel.CASO_B, CasoCartel.CASO_C):
        if caso not in fuerzas:
            continue
        destacada = (
            caso == CasoCartel.CASO_C
            if caso_c_gobierna
            else caso in (CasoCartel.CASO_A, CasoCartel.CASO_B)
        )
        tarjetas_fuerza.append(
            Tarjeta(
                f"Fuerza {caso.value}",
                _fuerza_total(cartel, caso, unidades),
                detalle=detalles[caso],
                destacada=destacada,
            )
        )

    return [
        Tarjetas(
            [
                Tarjeta("Velocidad básica", f"{cartel.velocidad:.2f} m/s"),
                Tarjeta(
                    "Presión dinámica, qh",
                    f"{convertir_unidad(cartel.resultados[0].q.valor, unidades['presion']):.2f} "
                    f"{unidades['presion'].value}/m²",
                ),
                Tarjeta("Área proyectada", f"{cartel.geometria.area:.2f} m²"),
            ]
        ),
        Tarjetas(tarjetas_fuerza),
        Nota(_caso_de_diseño(cartel), "Fuerza de diseño"),
    ]


def _bloques_datos(cartel: Cartel) -> list[Bloque]:
    """Los bloques con el reglamento y los datos de entrada.

    Args:
        cartel: El cartel calculado.

    Returns:
        Los bloques de la página de datos.
    """
    return [
        Grupo(
            "Cartel",
            [
                Datos(
                    (
                        ("Altura inferior", f"{cartel.altura_inferior:.2f} m"),
                        ("Altura superior", f"{cartel.altura_superior:.2f} m"),
                        ("Ancho", f"{cartel.ancho:.2f} m"),
                        ("Profundidad", f"{cartel.profundidad:.2f} m"),
                    )
                )
            ],
        ),
        grupo_viento(cartel),
        grupo_rafaga(cartel, TEXTO_RAFAGA_SIMPLIFICADA),
        grupo_topografia(cartel),
    ]


def _bloques_parametros(cartel: Cartel) -> list[Bloque]:
    """Los bloques con los parámetros de la Figura 4.4-1.

    Args:
        cartel: El cartel calculado.

    Returns:
        Los bloques de la página de parámetros.
    """
    filas: list[tuple[str, str]] = [
        ("Altura neta, s", f"{cartel.geometria.altura_neta:.2f} m"),
        ("Altura media", f"{cartel.geometria.altura_media:.2f} m"),
        (
            "Altura de evaluación de la presión dinámica, h",
            f"{cartel.altura_superior:.2f} m",
        ),
        ("Área", f"{cartel.geometria.area:.2f} m²"),
        (
            "Factor de direccionalidad, Kd",
            f"{cartel.presiones.factor_direccionalidad:.2f}",
        ),
        (
            "Relación de espacio libre, s/h",
            f"{cartel.cf.relacion_espacio_libre:.2f}",
        ),
        ("Relación de aspecto, B/s", f"{cartel.cf.relacion_aspecto:.2f}"),
    ]
    if cartel.epsilon < 1:
        filas += [
            ("Relación de área sólida, ε", f"{cartel.epsilon:.2f}"),
            (
                "Factor de reducción por aberturas",
                f"{cartel.cf.factor_aberturas:.3f}",
            ),
        ]
    if cartel.doble_cara:
        filas.append(("Rmin = t / min(B, s)", f"{cartel.cf.r_min:.3f}"))
        filas.append(("Rmax = t / max(B, s)", f"{cartel.cf.r_max:.3f}"))
        if cartel.cf.r_max <= 0.4:
            filas.append(
                (
                    "Excentricidad reducida del Caso B, e",
                    f"{cartel.cf.excentricidad:.2f} m",
                )
            )
    if cartel.esquina_retorno > 0:
        filas += [
            (
                "Esquina de retorno, Lr",
                f"{cartel.esquina_retorno:.2f} m "
                f"(Lr/s = {cartel.esquina_retorno / cartel.geometria.altura_neta:.2f})",
            ),
            (
                "Factor de reducción por esquina de retorno",
                f"{cartel.cf.factor_esquina_retorno:.2f}",
            ),
        ]

    return [
        Grupo("Cartel", [Datos(filas)]),
        grupo_constantes_terreno(cartel.rafaga),
        grupo_factor_rafaga(
            cartel.rafaga, cartel.flexibilidad, TEXTO_RAFAGA_SIMPLIFICADA
        ),
        grupo_factor_topografico(
            cartel,
            cartel.topografia.parametros.k3[-1],
            [
                "El valor de K3 que se muestra en la tabla es el "
                "correspondiente a la altura h. Los valores para las demás "
                "alturas se calculan automáticamente y no son mostrados."
            ],
        ),
    ]


def _consideraciones(cartel: Cartel) -> str:
    """El texto de las consideraciones de la Figura 4.4-1.

    Args:
        cartel: El cartel calculado.

    Returns:
        El texto con la lista de casos y las notas que aplican, en el
        subset de HTML que entiende Qt.
    """
    parrafos = [
        "De acuerdo a la Nota 2 de la Figura 4.4-1, para considerar ambas "
        "direcciones del viento, normal y oblicua, se deben tener en cuenta "
        "los siguientes casos:",
        "<ul>"
        "<li><b>Caso A:</b> la fuerza resultante actúa perpendicular a la "
        "cara del cartel en el centro geométrico.</li>"
        f"<li><b>Caso B:</b> la fuerza resultante actúa perpendicular a la "
        f"cara del cartel, a una distancia desde el centro geométrico hacia "
        f"el borde de barlovento igual a e = {cartel.cf.excentricidad:.2f} m.</li>",
    ]
    if cartel.cf.aplica_caso_c:
        parrafos.append(
            "<li><b>Caso C (B/s ≥ 2):</b> las fuerzas resultantes actúan "
            "perpendiculares a la cara del cartel en los centros geométricos "
            "de cada región. Para viento desde el borde de sotavento, la "
            "disposición de las regiones se espeja.</li></ul>"
        )
    else:
        parrafos.append(
            "<li>Como B/s &lt; 2, no corresponde considerar el Caso C.</li></ul>"
        )
    if cartel.cf.relacion_espacio_libre >= 0.999:
        parrafos.append(
            "Como s/h = 1 (cartel o pared apoyado en forma continua en el "
            "terreno), la fuerza resultante actúa a una distancia igual a "
            "0.05h por encima del centro geométrico."
        )
    if cartel.cf.relacion_espacio_libre > 0.8 and cartel.cf.aplica_caso_c:
        parrafos.append(
            f"Por la Nota 3, los coeficientes de fuerza del Caso C se "
            f"multiplican por el factor de reducción (1.8 - s/h) = "
            f"{1.8 - cartel.cf.relacion_espacio_libre:.2f}."
        )
    parrafos.append(f"<b>{_caso_de_diseño(cartel)}</b>")
    return "".join(parrafos)


def _bloques_presiones(cartel: Cartel, unidades: dict[str, Unidad]) -> list[Bloque]:
    """Los bloques con las presiones y fuerzas por caso de carga.

    Args:
        cartel: El cartel calculado.
        unidades: Las unidades a mostrar.

    Returns:
        Los bloques de la página de presiones.
    """
    bloques: list[Bloque] = []
    referencia = cartel.resultados[0].referencia
    for caso in (CasoCartel.CASO_A, CasoCartel.CASO_B, CasoCartel.CASO_C):
        filas_caso = cartel.resultados.filtrar(caso=caso)
        if not filas_caso:
            continue
        bloques.append(
            Grupo(
                caso.value,
                [
                    tablas.tabla_cartel(
                        filas_caso, cartel.cf.limites_regiones, unidades
                    ),
                    Datos(
                        (
                            (
                                f"Fuerza total del {caso.value}",
                                _fuerza_total(cartel, caso, unidades),
                            ),
                        )
                    ),
                ],
                referencia=referencia,
            )
        )

    bloques.append(Grupo("Consideraciones", [Texto(_consideraciones(cartel))]))
    bloques.append(Nota(NOTA_MINIMAS, "Cargas de viento de diseño mínimas (Art. 4.8)"))
    return bloques
