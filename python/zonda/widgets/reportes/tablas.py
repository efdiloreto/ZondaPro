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

"""Tablas de resultados y sus generadores.

Cada función generadora porta un bloque de reporte: mismas columnas,
mismo formato de ``%.2f`` y la referencia al Reglamento que la acompaña.
Se alimenta de la `Tabla` plana de ``zonda.cirsoc.resultados`` filtrada y
agrupada, nunca de las estructuras anidadas del núcleo, y devuelve el
modelo de :mod:`zonda.widgets.reportes.documento`: la vista lo muestra en
una ``TablaResultados`` y el PDF lo convierte en tabla de
``QTextDocument``.

Los extremos de presión de cada tabla se resaltan con negrita y color —
rojo para el empuje máximo, azul para la succión máxima, la misma
semántica azul→rojo de la escala de la vista 3D— y además llevan un
tooltip que lo dice en texto, para que el color no sea el único aviso.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6 import QtCore, QtGui, QtWidgets

from zonda.enums import (
    Flexibilidad,
    SistemaResistente,
    TipoPresionComponentesParedesCubierta,
    Unidad,
)
from zonda.unidades import convertir_unidad
from zonda.widgets.reportes.documento import Celda, Tabla

if TYPE_CHECKING:
    from collections.abc import Sequence

    from zonda.cirsoc.factores import Rafaga, Topografia
    from zonda.cirsoc.resultados import (
        FilaCartel,
        FilaComponentesCubiertaAislada,
        FilaCubiertaAislada,
        FilaEdificio,
    )
    from zonda.cirsoc.resultados import (
        Tabla as TablaNucleo,
    )

# El empuje máximo va en rojo y la succión máxima en azul: es la misma
# semántica de la escala de colores de la vista 3D, de azul (succión) a
# rojo (presión).
_COLOR_MAXIMO = QtGui.QColor("#a5373d")
_COLOR_MINIMO = QtGui.QColor("#1858a8")

_TOOLTIPS_EXTREMOS = {
    "maximo": "Máxima presión de diseño de esta tabla",
    "minimo": "Máxima succión de diseño de esta tabla",
}


def numero(valor: float) -> str:
    """Formatea un valor con los dos decimales que usa todo el programa."""
    return f"{valor:.2f}"


def _convertir(valor: float, unidad: Unidad) -> float:
    return convertir_unidad(valor, unidad)


def _clases_extremos(valores: Sequence[float]) -> list[str | None]:
    """La clase de resaltado de cada valor de una columna de presiones.

    Args:
        valores: Los valores de la columna, en el orden de las filas.

    Returns:
        La clase de cada celda: ``maximo`` para el mayor si es positivo,
        ``minimo`` para el menor si es negativo, ``None`` para el resto.
    """
    if not valores:
        return []
    maximo = max(valores)
    minimo = min(valores)
    return [
        "maximo"
        if (valor == maximo and maximo > 0)
        else ("minimo" if (valor == minimo and minimo < 0) else None)
        for valor in valores
    ]


class TablaResultados(QtWidgets.QTableWidget):
    """La tabla de resultados, con números que no se pueden editar.

    Las columnas se dimensionan por su contenido, las filas alternan
    color para que el ojo siga la línea, y el resaltado de extremos se
    aplica desde las celdas que traen clase.
    """

    def __init__(
        self,
        columnas: Sequence[str],
        filas: Sequence[Sequence[Celda | str]],
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        """
        Args:
            columnas: Los títulos de las columnas, con sus unidades.
            filas: Las filas de la tabla; cada una trae una celda por
                columna, como texto plano o como `Celda` resaltada.
            parent: El widget parent.
        """
        super().__init__(len(filas), len(columnas), parent)
        self.setProperty("class", "tabla-resultados")
        self._anchos_base: list[int] = []

        # El contenido del reporte va un punto más grande que el resto de
        # la interfaz; las alturas de fila se derivan de esta métrica, así
        # que sube solo.
        fuente = self.font()
        fuente.setPointSize(fuente.pointSize() + 1)
        self.setFont(fuente)

        self.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.setAlternatingRowColors(True)
        self.setWordWrap(False)
        self.setCornerButtonEnabled(False)
        self.setVerticalScrollMode(
            QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        self.setHorizontalScrollMode(
            QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel
        )

        # El alto de fila es uniforme y deriva de la métrica de la fuente:
        # las tablas del reporte son numéricas y unas filas con aire se
        # leen mejor que las filas pegadas al texto. QSS no soporta padding
        # en los items de una vista de tabla, así que el aire va acá.
        vertical = self.verticalHeader()
        assert vertical is not None
        vertical.setVisible(False)
        vertical.setDefaultSectionSize(max(28, self.fontMetrics().height() + 10))

        encabezado = self.horizontalHeader()
        assert encabezado is not None
        encabezado.setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        encabezado.setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        encabezado.setStretchLastSection(False)

        for columna, titulo in enumerate(columnas):
            self.setHorizontalHeaderItem(columna, QtWidgets.QTableWidgetItem(titulo))

        for fila, valores in enumerate(filas):
            for columna, valor in enumerate(valores):
                self.setItem(fila, columna, self._item(valor))

        self.resizeColumnsToContents()
        self._congelar_anchos()
        self._ajustar_altura()

    def _congelar_anchos(self) -> None:
        """Fija los anchos de contenido como base para llenar el ancho.

        Al pasar el encabezado a modo interactivo, las columnas quedan con
        el ancho que pide su contenido —respetándolo como mínimo— y el
        usuario puede arrastrarlas; el sobrante del viewport lo reparte
        `resizeEvent`.
        """
        self._anchos_base = [
            self.columnWidth(columna) for columna in range(self.columnCount())
        ]
        encabezado = self.horizontalHeader()
        assert encabezado is not None
        encabezado.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Interactive)

    def resizeEvent(self, event: QtGui.QResizeEvent | None) -> None:
        super().resizeEvent(event)
        self._llenar_ancho()

    def _llenar_ancho(self) -> None:
        """Reparte el sobrante del viewport entre todas las columnas.

        Con las columnas al ancho de su contenido queda espacio en blanco
        a la derecha: se lo reparte en partes iguales, de modo que la
        tabla ocupe todo el ancho disponible. Si el viewport no alcanza
        para el contenido, las columnas vuelven a sus anchos base y la
        página que contiene la tabla se desplaza horizontal.
        """
        if not self._anchos_base:
            return
        viewport = self.viewport()
        assert viewport is not None
        columnas = self.columnCount()
        ancho_base = sum(self._anchos_base)
        disponible = viewport.width()
        if disponible < ancho_base:
            for columna in range(columnas):
                self.setColumnWidth(columna, self._anchos_base[columna])
            return
        sobra = disponible - ancho_base
        extra = sobra // columnas
        for columna in range(columnas - 1):
            self.setColumnWidth(columna, self._anchos_base[columna] + extra)
        self.setColumnWidth(
            columnas - 1,
            self._anchos_base[columnas - 1] + sobra - extra * (columnas - 1),
        )

    def _ajustar_altura(self) -> None:
        """Hace que la tabla mida exactamente lo que ocupan sus filas.

        El alto por defecto de una vista de desplazamiento no depende del
        contenido: una tabla de una sola fila pediría el mismo lugar que
        una de diez y sobraría media tarjeta. Se fija el alto al de su
        contenido. El margen cubre el padding del encabezado que la hoja
        de estilo agrega y que el sizeHint no refleja: sin él, el viewport
        queda un par de píxeles corto y aparecen las barras de scroll.
        """
        encabezado = self.horizontalHeader()
        assert encabezado is not None
        alto = (
            encabezado.sizeHint().height()
            + sum(self.rowHeight(fila) for fila in range(self.rowCount()))
            + 2 * self.frameWidth()
            + 16
        )
        self.setFixedHeight(alto)

    @staticmethod
    def _item(valor: Celda | str) -> QtWidgets.QTableWidgetItem:
        """Convierte el valor de la celda en un item de la tabla.

        Args:
            valor: El texto o la celda resaltada.

        Returns:
            El item armado, con su alineación, tipografía y tooltip.
        """
        if isinstance(valor, str):
            valor = Celda(valor)
        item = QtWidgets.QTableWidgetItem(valor.texto)
        item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        item.setFlags(
            QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable
        )
        if valor.clase:
            tipografia = item.font()
            tipografia.setBold(True)
            item.setFont(tipografia)
            item.setForeground(
                _COLOR_MAXIMO if valor.clase == "maximo" else _COLOR_MINIMO
            )
            item.setToolTip(_TOOLTIPS_EXTREMOS[valor.clase])
        return item


def tabla_presiones(
    filas: TablaNucleo[FilaEdificio], unidades: dict[str, Unidad]
) -> Tabla:
    """La tabla de presiones de una superficie del edificio.

    Es el port del macro ``presiones`` de ``macros.md``: las columnas se
    adaptan a lo que traen las filas —si varía la altura, si la superficie
    está dividida en rangos o zonas, si lleva presión interna— sin que el
    que arma la página tenga que decidir nada.

    Args:
        filas: Las filas de una superficie, ya agrupadas.
        unidades: Las unidades de fuerza y presión a mostrar.

    Returns:
        La tabla armada.
    """
    primera = filas[0]
    por_altura = len({fila.q.altura for fila in filas}) > 1
    es_componente = primera.sistema == SistemaResistente.COMPONENTES
    simbolo_cp = "GCp" if es_componente else "Cp"
    unidad = f"{unidades['presion'].value}/m²"
    sub_z = "z" if por_altura else "h"
    sub_kzt = "zt" if por_altura else "zth"

    if por_altura:
        encabezado = "Alturas (m)"
    elif primera.rango:
        encabezado = "Distancias (m)"
    elif primera.zona_componente:
        encabezado = "Zona"
    else:
        encabezado = "Superficie"

    columnas = [
        encabezado,
        f"K{sub_z}",
        f"K{sub_kzt}",
        simbolo_cp,
        f"q{sub_z} ({unidad})",
    ]
    if primera.con_presion_interna:
        columnas += [
            f"pn [+GCpi] ({unidad})",
            f"pn [-GCpi] ({unidad})",
        ]
    else:
        columnas += [f"pn ({unidad})"]

    presiones_q = [_convertir(fila.q.valor, unidades["presion"]) for fila in filas]
    presiones_pos = [_convertir(fila.pos, unidades["presion"]) for fila in filas]
    presiones_neg = [_convertir(fila.neg, unidades["presion"]) for fila in filas]
    clases_pos = _clases_extremos(presiones_pos)
    clases_neg = _clases_extremos(presiones_neg)

    filas_tabla: list[list[Celda | str]] = []
    for indice, fila in enumerate(filas):
        if por_altura:
            etiqueta = numero(fila.q.altura)
        elif fila.rango:
            etiqueta = f"{numero(fila.rango[0])} a {numero(fila.rango[1])}"
        elif fila.zona_componente:
            etiqueta = fila.zona_componente.value.capitalize()
            # El positivo suele ser único y viajar en la zona "todas".
            # Cuando el Reglamento lo distingue por zona (Fig. 5.3-2A, Nota
            # 5, con parapeto), la zona aparece con dos filas y hay que
            # decir cuál es cuál.
            if (
                fila.tipo_presion == TipoPresionComponentesParedesCubierta.POSITIVA
                and fila.zona_componente.name != "TODAS"
            ):
                etiqueta += " (positiva)"
        else:
            etiqueta = "Total"

        celdas: list[Celda | str] = [
            etiqueta,
            numero(fila.q.kz),
            numero(fila.q.kzt),
            numero(fila.cp),
            numero(presiones_q[indice]),
        ]
        if primera.con_presion_interna:
            celdas += [
                Celda(numero(presiones_pos[indice]), clases_pos[indice]),
                Celda(numero(presiones_neg[indice]), clases_neg[indice]),
            ]
        else:
            # Sin presión interna ambas coinciden por construcción; la
            # única presión de la fila ocupa la columna de signo único.
            celdas.append(Celda(numero(presiones_pos[indice]), clases_pos[indice]))
        filas_tabla.append(celdas)

    return Tabla(columnas, filas_tabla)


def tabla_parapeto_sprfv(
    filas: TablaNucleo[FilaEdificio], unidades: dict[str, Unidad]
) -> Tabla:
    """La tabla del parapeto para SPRFV (Art. 2.4.5).

    El coeficiente GCpn es una presión neta combinada que ya incluye el
    factor de ráfaga y no lleva presión interna; la presión dinámica se
    evalúa en la coronación.

    Args:
        filas: Las filas del parapeto, una por posición respecto al viento.
        unidades: Las unidades de fuerza y presión a mostrar.

    Returns:
        La tabla armada.
    """
    unidad = f"{unidades['presion'].value}/m²"
    presiones = [_convertir(fila.pos, unidades["presion"]) for fila in filas]
    clases = _clases_extremos(presiones)
    filas_tabla: list[list[Celda | str]] = [
        [
            fila.pared.value.capitalize() if fila.pared else "",
            numero(fila.q.kz),
            numero(fila.q.kzt),
            numero(fila.cp),
            numero(_convertir(fila.q.valor, unidades["presion"])),
            Celda(numero(presiones[indice]), clases[indice]),
        ]
        for indice, fila in enumerate(filas)
    ]
    return Tabla(
        ["Caso", "Kz", "Kzt", "GCpn", f"qp ({unidad})", f"pp ({unidad})"],
        filas_tabla,
    )


def tabla_parapeto_componentes(
    filas: TablaNucleo[FilaEdificio], unidades: dict[str, Unidad]
) -> Tabla:
    """La tabla del parapeto para componentes y revestimientos (Art. 5.6).

    Muestra el desglose del coeficiente combinado en las presiones externas
    de las dos caras del parapeto, como el macro
    ``presiones_parapeto_componentes``.

    Args:
        filas: Las filas del parapeto, una por caso de carga y segmento.
        unidades: Las unidades de fuerza y presión a mostrar.

    Returns:
        La tabla armada.
    """
    unidad = f"{unidades['presion'].value}/m²"
    presiones_pos = [_convertir(fila.pos, unidades["presion"]) for fila in filas]
    presiones_neg = [_convertir(fila.neg, unidades["presion"]) for fila in filas]
    clases_pos = _clases_extremos(presiones_pos)
    clases_neg = _clases_extremos(presiones_neg)

    def celdas_parapeto(indice: int, fila: FilaEdificio) -> list[Celda | str]:
        # Las filas del parapeto traen siempre el desglose del Art. 5.6.
        assert fila.cp_frontal is not None
        assert fila.cp_posterior is not None
        return [
            fila.pared.value.capitalize() if fila.pared else "",
            fila.zona_parapeto.value.capitalize() if fila.zona_parapeto else "",
            numero(fila.q.kz),
            numero(fila.q.kzt),
            numero(fila.cp_frontal),
            numero(fila.cp_posterior),
            numero(fila.cp),
            numero(_convertir(fila.q.valor, unidades["presion"])),
            Celda(numero(presiones_pos[indice]), clases_pos[indice]),
            Celda(numero(presiones_neg[indice]), clases_neg[indice]),
        ]

    filas_tabla = [celdas_parapeto(indice, fila) for indice, fila in enumerate(filas)]
    return Tabla(
        [
            "Caso",
            "Zona",
            "Kz",
            "Kzt",
            "GCp frontal",
            "GCp posterior",
            "GCp",
            f"qp ({unidad})",
            f"pn [+GCpi] ({unidad})",
            f"pn [-GCpi] ({unidad})",
        ],
        filas_tabla,
    )


def tabla_cubierta_aislada(
    filas: TablaNucleo[FilaCubiertaAislada], unidades: dict[str, Unidad]
) -> Tabla:
    """La tabla de presiones normales de la cubierta aislada.

    Args:
        filas: Las filas de una dirección de viento.
        unidades: Las unidades de fuerza y presión a mostrar.

    Returns:
        La tabla armada, con una fila por caso de carga y zona.
    """
    unidad = f"{unidades['presion'].value}/m²"
    presiones = [_convertir(fila.presion, unidades["presion"]) for fila in filas]
    clases = _clases_extremos(presiones)
    friccion = _convertir(filas[0].presion_friccion, unidades["presion"])
    filas_tabla = [
        [
            fila.caso.value,
            fila.zona.value if fila.zona else "",
            numero(fila.q.kz),
            numero(fila.q.kzt),
            numero(fila.cpn),
            numero(_convertir(fila.q.valor, unidades["presion"])),
            Celda(numero(presiones[indice]), clases[indice]),
            numero(friccion),
        ]
        for indice, fila in enumerate(filas)
    ]
    return Tabla(
        [
            "Caso",
            "Zona",
            "Kh",
            "Kzth",
            "Cpn",
            f"qh ({unidad})",
            f"p ({unidad})",
            f"p fricción ({unidad})",
        ],
        filas_tabla,
    )


def tabla_componentes_cubierta_aislada(
    filas: TablaNucleo[FilaComponentesCubiertaAislada], unidades: dict[str, Unidad]
) -> Tabla:
    """La tabla de componentes y revestimientos de la cubierta aislada.

    Cada zona trae una fila con el coeficiente positivo y una con el
    negativo; los C_N son presiones netas y no llevan presión interna.

    Args:
        filas: Las filas de un componente.
        unidades: Las unidades de fuerza y presión a mostrar.

    Returns:
        La tabla armada.
    """
    unidad = f"{unidades['presion'].value}/m²"
    presiones = [_convertir(fila.presion, unidades["presion"]) for fila in filas]
    filas_tabla: list[list[Celda | str]] = []
    for tipo in (
        TipoPresionComponentesParedesCubierta.POSITIVA,
        TipoPresionComponentesParedesCubierta.NEGATIVA,
    ):
        # El extremo se busca por signo: el máximo de los positivos y el
        # mínimo de los negativos, que son dos familias de coeficientes.
        indices = [
            indice for indice, fila in enumerate(filas) if fila.tipo_presion == tipo
        ]
        clases = _clases_extremos([presiones[indice] for indice in indices])
        resaltados = dict(zip(indices, clases, strict=True))
        for indice, fila in enumerate(filas):
            if fila.tipo_presion != tipo:
                continue
            etiqueta = f"{fila.zona_componente.value} ({fila.tipo_presion.value})"
            filas_tabla.append(
                [
                    etiqueta,
                    numero(fila.q.kz),
                    numero(fila.q.kzt),
                    numero(fila.cpn),
                    numero(_convertir(fila.q.valor, unidades["presion"])),
                    Celda(numero(presiones[indice]), resaltados[indice]),
                ]
            )
    return Tabla(
        ["Zona", "Kh", "Kzth", "CN", f"qh ({unidad})", f"p ({unidad})"],
        filas_tabla,
    )


def tabla_cartel(
    filas: TablaNucleo[FilaCartel],
    limites_regiones: dict,
    unidades: dict[str, Unidad],
) -> Tabla:
    """La tabla de presiones del cartel para un caso de la Figura 4.4-1.

    Los Casos A y B traen una fila con la superficie completa; el Caso C
    una fila por región, con los límites medidos desde el borde de
    barlovento.

    Args:
        filas: Las filas del caso.
        limites_regiones: Los límites de cada región, tal como los publica
            la selección de coeficientes del cartel.
        unidades: Las unidades de fuerza y presión a mostrar.

    Returns:
        La tabla armada.
    """
    unidad = f"{unidades['presion'].value}/m²"
    unidad_fuerza = unidades["fuerza"].value
    presiones = [_convertir(fila.presion, unidades["presion"]) for fila in filas]
    clases = _clases_extremos(presiones)
    filas_tabla: list[list[Celda | str]] = []
    for indice, fila in enumerate(filas):
        celdas: list[Celda | str] = []
        if fila.region:
            limites = limites_regiones[fila.region]
            celdas.append(f"{numero(limites[0])} a {numero(limites[1])} m")
        celdas += [
            numero(fila.cf),
            numero(_convertir(fila.q.valor, unidades["presion"])),
            Celda(numero(presiones[indice]), clases[indice]),
            numero(fila.area),
            numero(_convertir(fila.fuerza, unidades["fuerza"])),
        ]
        filas_tabla.append(celdas)
    if filas[0].region:
        columnas = ["Región (m)", "Cf", f"qh ({unidad})", f"p ({unidad})"]
    else:
        columnas = ["Cf", f"qh ({unidad})", f"p ({unidad})"]
    columnas += ["Área (m²)", f"F ({unidad_fuerza})"]
    return Tabla(columnas, filas_tabla)


def tabla_constantes_terreno(
    constantes: Sequence[float],
) -> Tabla:
    """Las constantes de exposición del terreno de la Tabla 1.6-1.

    Args:
        constantes: Los diez parámetros de la categoría de exposición, en
            el orden que publica ``zonda.cirsoc.factores``.

    Returns:
        La tabla armada, de una fila.
    """
    return Tabla(
        [
            "α",
            "Zg (m)",
            "â",
            "b̂",
            "ᾱ",
            "b̄",
            "c",
            "ι (m)",
            "ε̄",
            "Zmin (m)",
        ],
        [[numero(constante) for constante in constantes]],
    )


def tabla_rafaga(rafaga: Rafaga, flexibilidad: Flexibilidad) -> Tabla:
    """Los parámetros del factor de ráfaga de una dirección de viento.

    Args:
        rafaga: La ráfaga de la dirección.
        flexibilidad: La flexibilidad de la estructura, que decide si la
            tabla lleva los parámetros de resonancia.

    Returns:
        La tabla armada, de una fila.
    """
    parametros = rafaga.parametros
    columnas = ["z̄ (m)", "Iz̄", "Lz̄ (m)"]
    valores: list[str] = [
        numero(parametros.z),
        numero(parametros.iz),
        numero(parametros.lz),
    ]
    if flexibilidad == Flexibilidad.FLEXIBLE:
        columnas += ["gR", "R"]
        valores += [numero(parametros.gr), numero(parametros.r)]
    columnas += ["Q", "G"]
    valores += [numero(rafaga.factor_q), numero(rafaga.factor)]
    return Tabla(columnas, [valores])


def tabla_topografia(topografia: Topografia, k3: float) -> Tabla:
    """Los parámetros del factor topográfico de la Figura 1.8-1.

    Args:
        topografia: La topografía de la estructura.
        k3: El factor K3 a la altura de referencia (la media de cubierta,
            o h para el cartel).

    Returns:
        La tabla armada, de una fila.
    """
    parametros = topografia.parametros
    valores = [numero(parametro) for parametro in parametros[:-1]] + [numero(k3)]
    return Tabla(
        ["K1/(H/Lh)", "γ", "μ", "Lh (m)", "K1", "K2", "K3"],
        [valores],
    )
