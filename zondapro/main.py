import sys

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import QFontDatabase, QIcon

from zondapro import __acercade__, recursos, sistema
from zondapro.widgets.dialogos import DialogoAutenticacion
from zondapro.widgets.zonda import WidgetBienvenida


# def my_exception_hook(exctype, value, traceback):
#     # Print the error and traceback
#     print(exctype, value, traceback)
#     # Call the normal Exception hook after
#     sys._excepthook(exctype, value, traceback)
#     sys.exit(1)
#
#
# # Back up the reference to the exceptionhook
# sys._excepthook = sys.excepthook
#
# # Set the exception hook to our wrapping function
# sys.excepthook = my_exception_hook


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName(__acercade__.__compania__)
    app.setOrganizationDomain(__acercade__.__web_compania__)
    app.setApplicationName(__acercade__.__nombre__)
    app.setWindowIcon(QIcon(":/iconos/zonda.ico"))
    app.setAttribute(QtCore.Qt.AA_DisableWindowContextHelpButton)
    app.setStyle("fusion")

    QFontDatabase.addApplicationFont(":/fuentes/Oswald-VariableFont_wght.ttf")

    qss = QtCore.QFile(":/qss/zonda.qss")
    if qss.open(QtCore.QFile.ReadOnly):
        app.setStyleSheet(qss.readAll().data().decode("utf-8"))

    dialogo_autenticacion = DialogoAutenticacion()
    dialogo_autenticacion.destroyed.connect(lambda: print("destruido"))

    if dialogo_autenticacion.exec_():
        sistema.PSS = dialogo_autenticacion.codigo_validacion
        datos_licencia = dialogo_autenticacion.datos_licencia
        dialogo_autenticacion.destroy()  # En windows 8.1 el dialogo sigue visible por alguna razón. Acá nos aseguramos de destruirlo.
        widget = WidgetBienvenida(datos_licencia)
    else:
        pass

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
