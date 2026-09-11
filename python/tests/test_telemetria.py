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

"""La telemetría: el ping del arranque y la casilla para apagarlo.

Como con las actualizaciones, nada de acá sale a internet: se prueba la
decisión de mandar o no mandar —que es lo que importa— y no la red. El
modelo es opt-out: participa por defecto y sólo la baja explícita, por la
casilla de Configuración o por la variable de entorno, frena el ping.
"""

import json

from PyQt6 import QtNetwork, QtWidgets

from zonda import __acercade__, telemetria

URL_RECEPTOR = "https://telemetria.ejemplo.workers.dev/ping"


# --- La URL del receptor ------------------------------------------------


def test_con_receptor_la_url_lleva_el_ping(monkeypatch):
    monkeypatch.setattr(
        __acercade__, "__telemetria__", "https://telemetria.ejemplo.workers.dev"
    )

    assert telemetria.url_ping() == URL_RECEPTOR


def test_sin_receptor_la_url_es_vacia(monkeypatch):
    """Un fork sin receptor desplegado no tiene por qué mandar nada."""
    monkeypatch.setattr(__acercade__, "__telemetria__", "")

    assert telemetria.url_ping() == ""


# --- La decisión de participar ------------------------------------------


def test_por_defecto_participa(qapp, monkeypatch):
    """Sin configuración previa y sin variable de entorno, el ping sale."""
    monkeypatch.delenv("ZONDA_SIN_TELEMETRIA", raising=False)

    assert telemetria.participa() is True


def test_la_variable_de_entorno_apaga_la_telemetria(qapp, monkeypatch):
    monkeypatch.setenv("ZONDA_SIN_TELEMETRIA", "1")

    assert telemetria.participa() is False


def test_la_respuesta_persiste(qapp):
    telemetria.setear_participa(True)
    assert telemetria.participa() is True

    telemetria.setear_participa(False)
    assert telemetria.participa() is False


def test_el_id_anonimo_no_cambia_entre_llamadas(qapp):
    uno = telemetria.id_anonimo()
    dos = telemetria.id_anonimo()

    assert uno == dos
    # Un UUID: 32 dígitos y 4 guiones.
    assert len(uno) == 36


def test_la_carga_lleva_solo_lo_minimo(qapp):
    """Ni un campo de más: lo que viaja es lo que está en el README."""
    carga = telemetria.carga()

    assert set(carga) == {"id", "version", "so"}
    assert carga["version"] == __acercade__.__version__
    assert carga["so"] in ("windows", "darwin", "linux")


# --- El ping del arranque -----------------------------------------------


def _espiar_post(monkeypatch):
    """Reemplaza el ``post`` del manager por un registro de lo recibido."""
    llamadas = []

    def post(self, pedido, cuerpo):
        llamadas.append(json.loads(bytes(cuerpo).decode()))
        return None

    monkeypatch.setattr(QtNetwork.QNetworkAccessManager, "post", post)
    return llamadas


def test_sin_participar_no_sale_ningun_ping(qapp, monkeypatch):
    telemetria.setear_participa(False)
    llamadas = _espiar_post(monkeypatch)
    monkeypatch.setattr(telemetria, "url_ping", lambda: URL_RECEPTOR)

    telemetria.Telemetria().registrar_sesion()

    assert llamadas == []


def test_con_la_variable_de_entorno_no_sale_ningun_ping(qapp, monkeypatch):
    monkeypatch.setenv("ZONDA_SIN_TELEMETRIA", "1")
    llamadas = _espiar_post(monkeypatch)
    monkeypatch.setattr(telemetria, "url_ping", lambda: URL_RECEPTOR)

    telemetria.Telemetria().registrar_sesion()

    assert llamadas == []


def test_sin_receptor_no_sale_ningun_ping(qapp, monkeypatch):
    llamadas = _espiar_post(monkeypatch)
    monkeypatch.setattr(telemetria, "url_ping", lambda: "")

    telemetria.Telemetria().registrar_sesion()

    assert llamadas == []


def test_por_defecto_sale_el_ping_con_la_carga(qapp, monkeypatch):
    """El caso normal: arranque sin tocar nada y un POST con el payload mínimo."""
    monkeypatch.delenv("ZONDA_SIN_TELEMETRIA", raising=False)
    llamadas = _espiar_post(monkeypatch)
    monkeypatch.setattr(telemetria, "url_ping", lambda: URL_RECEPTOR)

    telemetria.Telemetria().registrar_sesion()

    assert llamadas == [telemetria.carga()]


# --- La casilla de Configuración ----------------------------------------


def test_la_configuracion_no_ofrece_telemetria_sin_receptor(qtbot, monkeypatch):
    """Con el módulo inerte, una casilla muerta sólo haría preguntas sin respuesta."""
    from zonda.widgets.dialogos import DialogoConfiguracion

    monkeypatch.setattr(telemetria, "url_ping", lambda: "")
    dialogo = DialogoConfiguracion(None)
    qtbot.addWidget(dialogo)

    assert dialogo._checkbox_telemetria is None


def test_la_casilla_refleja_que_se_participa_por_defecto(qapp, monkeypatch):
    from zonda.widgets.dialogos import DialogoConfiguracion

    monkeypatch.setattr(telemetria, "url_ping", lambda: URL_RECEPTOR)

    dialogo = DialogoConfiguracion(None)
    dialogo.deleteLater()

    assert dialogo._checkbox_telemetria is not None
    assert dialogo._checkbox_telemetria.isChecked()


def test_desmarcar_y_aceptar_guarda_la_baja(qapp, monkeypatch):
    """La baja es directa pero confirmada: desmarcar, Sí al aviso y listo."""
    from zonda.widgets.dialogos import DialogoConfiguracion

    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "question",
        lambda *a, **k: QtWidgets.QMessageBox.StandardButton.Yes,
    )
    monkeypatch.setattr(telemetria, "url_ping", lambda: URL_RECEPTOR)
    telemetria.setear_participa(True)

    dialogo = DialogoConfiguracion(None)
    caja = dialogo._checkbox_telemetria
    assert caja is not None

    caja.setChecked(False)
    dialogo.accept()

    assert telemetria.participa() is False


def test_responder_no_al_aviso_mantiene_la_participacion(qapp, monkeypatch):
    """El "No" del cartel se arrepiente en el acto: la casilla se remarca."""
    from zonda.widgets.dialogos import DialogoConfiguracion

    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "question",
        lambda *a, **k: QtWidgets.QMessageBox.StandardButton.No,
    )
    monkeypatch.setattr(telemetria, "url_ping", lambda: URL_RECEPTOR)
    telemetria.setear_participa(True)

    dialogo = DialogoConfiguracion(None)
    caja = dialogo._checkbox_telemetria
    assert caja is not None

    caja.setChecked(False)

    assert caja.isChecked()
    dialogo.accept()
    assert telemetria.participa() is True


def test_marcar_y_aceptar_guarda_la_participacion(qapp, monkeypatch):
    """Quien la había apagado puede volver a encenderla del mismo lugar."""
    from zonda.widgets.dialogos import DialogoConfiguracion

    monkeypatch.setattr(telemetria, "url_ping", lambda: URL_RECEPTOR)
    telemetria.setear_participa(False)

    dialogo = DialogoConfiguracion(None)
    caja = dialogo._checkbox_telemetria
    assert caja is not None

    caja.setChecked(True)
    dialogo.accept()

    assert telemetria.participa() is True
