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

"""Tests del historial de proyectos recientes.

Corren contra la configuración aislada que arma ``conftest.settings_aislados``,
así que cada test empieza con el historial vacío.
"""

from PyQt6 import QtCore

from zonda import recientes


def _proyecto(tmp_path, nombre: str):
    archivo = tmp_path / nombre
    archivo.write_text("{}", encoding="utf-8")
    return archivo


def test_sin_historial_la_lista_es_vacia(qapp):
    assert recientes.listar() == ()


def test_registrar_y_listar(qapp, tmp_path):
    archivo = _proyecto(tmp_path, "nave.zda")

    recientes.registrar(archivo)

    assert recientes.listar() == (archivo,)


def test_el_ultimo_registrado_queda_primero(qapp, tmp_path):
    primero = _proyecto(tmp_path, "primero.zda")
    segundo = _proyecto(tmp_path, "segundo.zda")

    recientes.registrar(primero)
    recientes.registrar(segundo)

    assert recientes.listar() == (segundo, primero)


def test_registrar_de_nuevo_sube_en_vez_de_duplicar(qapp, tmp_path):
    uno = _proyecto(tmp_path, "uno.zda")
    dos = _proyecto(tmp_path, "dos.zda")

    recientes.registrar(uno)
    recientes.registrar(dos)
    recientes.registrar(uno)

    assert recientes.listar() == (uno, dos)


def test_no_se_guardan_mas_del_maximo(qapp, tmp_path):
    archivos = [
        _proyecto(tmp_path, f"proyecto-{i}.zda") for i in range(recientes.MAXIMO + 3)
    ]

    for archivo in archivos:
        recientes.registrar(archivo)

    listados = recientes.listar()
    assert len(listados) == recientes.MAXIMO
    # Se descartan los más viejos, no los últimos.
    assert listados[0] == archivos[-1]


def test_un_proyecto_borrado_no_se_ofrece(qapp, tmp_path):
    archivo = _proyecto(tmp_path, "borrado.zda")
    recientes.registrar(archivo)

    archivo.unlink()

    assert recientes.listar() == ()


def test_un_proyecto_que_vuelve_reaparece(qapp, tmp_path):
    """No se lo borra del historial: puede estar en un disco desconectado."""
    archivo = _proyecto(tmp_path, "en-el-disco-externo.zda")
    recientes.registrar(archivo)
    archivo.unlink()
    assert recientes.listar() == ()

    archivo.write_text("{}", encoding="utf-8")

    assert recientes.listar() == (archivo,)


def test_una_ruta_relativa_se_guarda_absoluta(qapp, tmp_path, monkeypatch):
    """La bienvenida no comparte el directorio de trabajo con el módulo."""
    archivo = _proyecto(tmp_path, "relativo.zda")
    monkeypatch.chdir(tmp_path)

    recientes.registrar("relativo.zda")

    assert recientes.listar() == (archivo.resolve(),)


def test_un_historial_de_uno_no_se_lee_por_caracter(qapp, tmp_path):
    """QSettings devuelve una lista de un elemento como cadena suelta."""
    archivo = _proyecto(tmp_path, "solo.zda")
    settings = QtCore.QSettings()
    settings.beginGroup(recientes.GRUPO_SETTINGS)
    settings.setValue(recientes.CLAVE, [str(archivo)])
    settings.endGroup()
    settings.sync()

    assert recientes.listar() == (archivo,)


def test_olvidar_todo(qapp, tmp_path):
    recientes.registrar(_proyecto(tmp_path, "uno.zda"))

    recientes.olvidar_todo()

    assert recientes.listar() == ()


def test_la_ventana_no_exige_mas_de_lo_que_abre(qtbot):
    """El mínimo lo fija el contenido y el inicial está escrito a mano.

    Si alguien alarga una descripción de módulo, ensancha la columna de
    patrocinadores o suma texto largo al pie, el mínimo sube y la ventana
    abriría más chica de lo que su propio contenido exige. Qt la agranda sola,
    pero el tamaño escrito deja de significar nada.
    """
    from zonda.widgets.zonda import WidgetBienvenida

    ventana = WidgetBienvenida()
    qtbot.addWidget(ventana)
    ventana.show()

    assert ventana.minimumSize().width() <= ventana.TAMANIO_INICIAL.width()
    assert ventana.minimumSize().height() <= ventana.TAMANIO_INICIAL.height()
