# Copyright (c) 2023, Eduardo Di Loreto <efdiloreto@gmail.com>

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

"""Los avisos de la aplicación: los errores y las operaciones que salieron bien."""

from PyQt6 import QtCore, QtGui, QtWidgets


class _Aviso(QtWidgets.QMessageBox):
    """Base de los avisos: un mensaje y, opcionalmente, un archivo para abrir."""

    def __init__(
        self,
        parent: QtWidgets.QWidget | None,
        texto: str,
        titulo_ventana: str,
        ruta_archivo: str | None = None,
        texto_boton_archivo: str = "Visualizar Archivo",
    ):
        super().__init__(parent)
        self.setText(texto)
        self.setWindowTitle(titulo_ventana)

        self._ruta_archivo = ruta_archivo

        # Sin esto el único botón sería el de abrir el archivo, y no habría
        # forma de cerrar el aviso sin abrirlo: QMessageBox se cierra con
        # cualquiera de sus botones.
        self.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)

        if ruta_archivo is not None:
            boton_archivo = QtWidgets.QPushButton(texto_boton_archivo)
            boton_archivo.clicked.connect(self._abrir_archivo)
            self.addButton(boton_archivo, QtWidgets.QMessageBox.ButtonRole.ActionRole)

    def _abrir_archivo(self):
        # QDesktopServices se lo pide al sistema operativo que corresponda; antes
        # acá había un os.startfile(), que existe sólo en Windows y hacía que el
        # botón tirara AttributeError en macOS y en Linux.
        if self._ruta_archivo is not None:
            QtGui.QDesktopServices.openUrl(
                QtCore.QUrl.fromLocalFile(self._ruta_archivo)
            )


class AvisoError(_Aviso):
    def __init__(
        self,
        parent: QtWidgets.QWidget | None,
        texto: str,
        titulo_ventana: str,
        ruta_archivo_error: str | None = None,
    ):
        super().__init__(parent, texto, titulo_ventana, ruta_archivo_error)
        self.show()


class AvisoExito(_Aviso):
    """Avisa que la operación terminó bien y ofrece abrir el archivo resultante."""

    def __init__(
        self,
        parent: QtWidgets.QWidget | None,
        texto: str,
        titulo_ventana: str,
        ruta_archivo: str | None = None,
    ):
        super().__init__(
            parent, texto, titulo_ventana, ruta_archivo, texto_boton_archivo="Abrir"
        )
        self.setIcon(QtWidgets.QMessageBox.Icon.Information)
        self.show()
