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

"""Tests de la carpeta que recuerdan los diálogos de archivo.

Corren contra la configuración aislada que arma ``conftest.settings_aislados``,
así que cada test empieza sin ninguna carpeta recordada.
"""

from PyQt6 import QtCore

from zonda import carpetas


def _documentos() -> str:
    return QtCore.QStandardPaths.writableLocation(
        QtCore.QStandardPaths.StandardLocation.DocumentsLocation
    )


def test_sin_carpeta_recordada_se_usa_documentos(qapp):
    assert carpetas.ultima() == _documentos()


def test_recordar_y_leer(qapp, tmp_path):
    carpetas.recordar(tmp_path / "nave.zda")

    assert carpetas.ultima() == str(tmp_path.resolve())


def test_se_guarda_la_carpeta_no_el_archivo(qapp, tmp_path):
    carpeta = tmp_path / "proyectos"
    carpeta.mkdir()
    carpetas.recordar(carpeta / "nave.zda")

    assert carpetas.ultima() == str(carpeta)


def test_la_ultima_gana(qapp, tmp_path):
    primera = tmp_path / "una"
    segunda = tmp_path / "otra"
    primera.mkdir()
    segunda.mkdir()

    carpetas.recordar(primera / "uno.zda")
    carpetas.recordar(segunda / "dos.zda")

    assert carpetas.ultima() == str(segunda)


def test_una_carpeta_borrada_vuelve_a_documentos(qapp, tmp_path):
    carpeta = tmp_path / "temporal"
    carpeta.mkdir()
    carpetas.recordar(carpeta / "borrado.zda")
    carpeta.rmdir()

    assert carpetas.ultima() == _documentos()


def test_una_ruta_relativa_se_guarda_absoluta(qapp, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    carpetas.recordar("nave.zda")

    assert carpetas.ultima() == str(tmp_path.resolve())
