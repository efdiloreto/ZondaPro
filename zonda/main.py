import sys
from os.path import dirname
sys.path.append(dirname(dirname(__file__)))

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import QFontDatabase, QIcon

from zonda import __acercade__, recursos
from zonda.widgets.zonda import WidgetBienvenida


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

    widget = WidgetBienvenida()

    app.exec_()


if __name__ == "__main__":
    main()
