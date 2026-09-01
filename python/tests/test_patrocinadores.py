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

"""Tests de la lista de patrocinadores.

Lo que más importa acá no es que lea bien una lista correcta, sino que **nada
de lo que venga en el JSON pueda voltear al programa**: es información de
cortesía y el usuario abrió Zonda para calcular cargas de viento.
"""

import json
from pathlib import Path

from PyQt6 import QtWidgets

from zonda import patrocinadores
from zonda.enums import NivelPatrocinio


def _escribir(directorio: Path, entradas: list[dict]) -> Path:
    (directorio / patrocinadores.NOMBRE_ARCHIVO).write_text(
        json.dumps({"patrocinadores": entradas}), encoding="utf-8"
    )
    return directorio


def test_lee_una_lista_valida(tmp_path):
    _escribir(
        tmp_path,
        [{"nombre": "Estudio Uno", "nivel": "plata", "web": "https://uno.com.ar"}],
    )

    lista = patrocinadores.cargar(tmp_path)

    assert len(lista) == 1
    assert lista[0].nombre == "Estudio Uno"
    assert lista[0].nivel is NivelPatrocinio.PLATA
    assert lista[0].web == "https://uno.com.ar"
    assert lista[0].logo is None
    assert not lista[0].fundador


def test_ordena_por_nivel_sin_importar_el_orden_del_archivo(tmp_path):
    _escribir(
        tmp_path,
        [
            {"nombre": "Bronce", "nivel": "bronce"},
            {"nombre": "Oro", "nivel": "oro"},
            {"nombre": "Plata", "nivel": "plata"},
        ],
    )

    assert [p.nombre for p in patrocinadores.cargar(tmp_path)] == [
        "Oro",
        "Plata",
        "Bronce",
    ]


def test_resuelve_el_logo_que_existe(tmp_path):
    (tmp_path / "logo.png").write_bytes(b"no importa el contenido")
    _escribir(tmp_path, [{"nombre": "Uno", "nivel": "oro", "logo": "logo.png"}])

    assert patrocinadores.cargar(tmp_path)[0].logo == tmp_path / "logo.png"


def test_un_logo_que_falta_no_descarta_al_patrocinador(tmp_path):
    """Se lo muestra por nombre: es mejor que el hueco de una imagen rota."""
    _escribir(tmp_path, [{"nombre": "Uno", "nivel": "oro", "logo": "no-esta.png"}])

    lista = patrocinadores.cargar(tmp_path)

    assert len(lista) == 1
    assert lista[0].logo is None


def test_el_logo_se_busca_dentro_del_directorio(tmp_path):
    """Una ruta relativa en el JSON no puede apuntar a otro lado del disco."""
    afuera = tmp_path.parent / "afuera.png"
    afuera.write_bytes(b"")
    _escribir(tmp_path, [{"nombre": "Uno", "nivel": "oro", "logo": "../afuera.png"}])

    assert patrocinadores.cargar(tmp_path)[0].logo is None


def test_descarta_las_entradas_que_no_sirven(tmp_path):
    _escribir(
        tmp_path,
        [
            {"nombre": "", "nivel": "oro"},
            {"nombre": "Sin nivel"},
            {"nombre": "Nivel inventado", "nivel": "platino"},
            "esto no es un objeto",
            {"nombre": "Válido", "nivel": "bronce"},
        ],
    )

    lista = patrocinadores.cargar(tmp_path)

    assert [p.nombre for p in lista] == ["Válido"]


def test_un_json_roto_no_hace_fallar_nada(tmp_path):
    (tmp_path / patrocinadores.NOMBRE_ARCHIVO).write_text("{esto no es json")

    assert patrocinadores.cargar(tmp_path) == ()


def test_sin_archivo_la_lista_es_vacia(tmp_path):
    assert patrocinadores.cargar(tmp_path) == ()


def test_agrupa_por_nivel_y_saltea_los_vacios(tmp_path):
    _escribir(
        tmp_path,
        [
            {"nombre": "Oro Uno", "nivel": "oro"},
            {"nombre": "Oro Dos", "nivel": "oro"},
            {"nombre": "Bronce", "nivel": "bronce"},
        ],
    )

    agrupados = patrocinadores.por_nivel(patrocinadores.cargar(tmp_path))

    assert list(agrupados) == [NivelPatrocinio.ORO, NivelPatrocinio.BRONCE]
    assert len(agrupados[NivelPatrocinio.ORO]) == 2


def test_mezclar_conserva_a_todos_y_no_cruza_niveles(tmp_path):
    _escribir(
        tmp_path,
        [{"nombre": f"Oro {i}", "nivel": "oro"} for i in range(5)]
        + [{"nombre": "Bronce", "nivel": "bronce"}],
    )
    lista = patrocinadores.cargar(tmp_path)

    mezclados = patrocinadores.mezclados_por_nivel(lista)

    assert {p.nombre for p in mezclados[NivelPatrocinio.ORO]} == {
        f"Oro {i}" for i in range(5)
    }
    assert [p.nombre for p in mezclados[NivelPatrocinio.BRONCE]] == ["Bronce"]


def test_la_lista_empaquetada_se_lee(qapp):
    """La que viaja en el paquete tiene que ser legible, aunque esté vacía."""
    assert isinstance(patrocinadores.cargar(), tuple)


def test_la_seccion_invita_si_no_hay_nadie(qapp):
    """Con lista vacía la columna invita en lugar de dejar el hueco."""
    from zonda.widgets.apoyo import WidgetSeccionPatrocinadores

    seccion = WidgetSeccionPatrocinadores(())

    textos = " ".join(label.text() for label in seccion.findChildren(QtWidgets.QLabel))
    assert "patrocinan" in textos
    # El rótulo "Patrocinado por" sobre una columna vacía se leería como error.
    assert "Patrocinado por" not in textos
    assert [b.text() for b in seccion.findChildren(QtWidgets.QPushButton)] == [
        "Apoyá el proyecto"
    ]


def test_la_seccion_enlaza_al_repositorio(qapp, tmp_path):
    """Las instrucciones para patrocinar viven en GitHub, no en el programa."""
    from zonda import __acercade__
    from zonda.widgets.apoyo import WidgetSeccionPatrocinadores

    _escribir(tmp_path, [{"nombre": "Estudio Uno", "nivel": "oro"}])
    seccion = WidgetSeccionPatrocinadores(patrocinadores.cargar(tmp_path))

    textos = " ".join(label.text() for label in seccion.findChildren(QtWidgets.QLabel))
    assert __acercade__.__apoyo__ in textos


def test_la_seccion_muestra_oro_y_plata_pero_no_bronce(qapp, tmp_path):
    from zonda.widgets.apoyo import WidgetSeccionPatrocinadores

    _escribir(
        tmp_path,
        [
            {"nombre": "El de oro", "nivel": "oro"},
            {"nombre": "El de plata", "nivel": "plata"},
            {"nombre": "El de bronce", "nivel": "bronce"},
        ],
    )
    seccion = WidgetSeccionPatrocinadores(patrocinadores.cargar(tmp_path))

    textos = " ".join(label.text() for label in seccion.findChildren(QtWidgets.QLabel))
    assert "El de oro" in textos
    assert "El de plata" in textos
    # Bronce vive en el dialogo, que es donde entra una lista larga.
    assert "El de bronce" not in textos
