import os
from typing import Optional

from PyQt5 import QtWidgets


class AvisoError(QtWidgets.QMessageBox):
    def __init__(
        self,
        parent,
        texto: str,
        titulo_ventana: str,
        ruta_archivo_error: Optional[str] = None,
    ):
        super().__init__(parent, text=texto)
        self.setWindowTitle(titulo_ventana)

        self._ruta_archivo_error = ruta_archivo_error

        if ruta_archivo_error is not None:
            boton_archivo_error = QtWidgets.QPushButton("Visualizar Archivo")
            boton_archivo_error.clicked.connect(self._abrir_archivo)
            self.addButton(boton_archivo_error, QtWidgets.QMessageBox.ActionRole)

        self.show()

    def _abrir_archivo(self):
        if self._ruta_archivo_error is not None:
            os.startfile(self._ruta_archivo_error, "open")
