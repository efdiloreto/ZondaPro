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

from PyQt6 import QtCore, QtWidgets

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


def test_la_seccion_invita_si_no_hay_nadie(qtbot):
    """Con lista vacía la columna invita en lugar de dejar el hueco."""
    from zonda.widgets.apoyo import (
        TEXTO_SIN_PATROCINADORES,
        WidgetSeccionPatrocinadores,
    )

    seccion = WidgetSeccionPatrocinadores(())
    qtbot.addWidget(seccion)

    textos = " ".join(label.text() for label in seccion.findChildren(QtWidgets.QLabel))
    assert TEXTO_SIN_PATROCINADORES in textos
    # El rótulo "Patrocinado por" sobre una columna vacía se leería como error.
    assert "Patrocinado por" not in textos
    assert [b.text() for b in seccion.findChildren(QtWidgets.QPushButton)] == [
        "Apoyá el proyecto"
    ]


def test_la_seccion_enlaza_al_repositorio(qtbot, tmp_path):
    """Las instrucciones para patrocinar viven en GitHub, no en el programa."""
    from zonda import __acercade__
    from zonda.widgets.apoyo import WidgetSeccionPatrocinadores

    _escribir(tmp_path, [{"nombre": "Estudio Uno", "nivel": "oro"}])
    seccion = WidgetSeccionPatrocinadores(patrocinadores.cargar(tmp_path))
    qtbot.addWidget(seccion)

    textos = " ".join(label.text() for label in seccion.findChildren(QtWidgets.QLabel))
    assert __acercade__.__apoyo__ in textos


def test_la_seccion_muestra_oro_y_plata_pero_no_bronce(qtbot, tmp_path):
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
    qtbot.addWidget(seccion)

    textos = " ".join(label.text() for label in seccion.findChildren(QtWidgets.QLabel))
    assert "El de oro" in textos
    assert "El de plata" in textos
    # Bronce vive en el dialogo, que es donde entra una lista larga.
    assert "El de bronce" not in textos


def test_solo_se_aceptan_webs_y_correos(tmp_path):
    """Estos enlaces terminan en `QDesktopServices.openUrl()`.

    Un `file://` ahí le abriría archivos del disco a quien usa el programa, así
    que todo lo que no sea una web o un correo se descarta al leer.
    """
    _escribir(
        tmp_path,
        [
            {"nombre": "Web", "nivel": "oro", "web": "https://ejemplo.com.ar"},
            {"nombre": "Correo", "nivel": "oro", "web": "mailto:hola@ejemplo.com"},
            {"nombre": "Archivo", "nivel": "oro", "web": "file:///etc/passwd"},
            {"nombre": "Script", "nivel": "oro", "web": "javascript:alert(1)"},
            {"nombre": "Sin esquema", "nivel": "oro", "web": "www.ejemplo.com"},
        ],
    )

    enlaces = {p.nombre: p.web for p in patrocinadores.cargar(tmp_path)}

    assert enlaces["Web"] == "https://ejemplo.com.ar"
    assert enlaces["Correo"] == "mailto:hola@ejemplo.com"
    # No se descarta al patrocinador: se lo muestra sin enlace.
    assert enlaces["Archivo"] == ""
    assert enlaces["Script"] == ""
    assert enlaces["Sin esquema"] == ""


def test_lee_los_datos_del_perfil_de_oro(tmp_path):
    _escribir(
        tmp_path,
        [
            {
                "nombre": "Estudio Uno",
                "nivel": "oro",
                "web": "https://uno.com.ar",
                "contacto": "mailto:info@uno.com.ar",
                "ciudad": "Rosario, Santa Fe",
                "rubro": "Cálculo estructural",
                "descripcion": "Dos líneas sobre el estudio.",
                "desde": "2026",
            }
        ],
    )

    uno = patrocinadores.cargar(tmp_path)[0]

    assert uno.contacto == "mailto:info@uno.com.ar"
    assert uno.ciudad == "Rosario, Santa Fe"
    assert uno.rubro == "Cálculo estructural"
    assert uno.descripcion == "Dos líneas sobre el estudio."
    assert uno.desde == "2026"


def test_una_entrada_minima_deja_el_perfil_vacio(tmp_path):
    """Bronce son dos campos, y el resto tiene que quedar en blanco sin fallar."""
    _escribir(tmp_path, [{"nombre": "Ing. Pérez", "nivel": "bronce"}])

    uno = patrocinadores.cargar(tmp_path)[0]

    assert (uno.web, uno.contacto, uno.ciudad, uno.rubro, uno.descripcion) == (
        "",
        "",
        "",
        "",
        "",
    )


def _escribir_colaboradores(directorio, entradas):
    (directorio / patrocinadores.NOMBRE_ARCHIVO_COLABORADORES).write_text(
        json.dumps({"colaboradores": entradas}), encoding="utf-8"
    )


def test_lee_los_colaboradores(tmp_path):
    _escribir_colaboradores(
        tmp_path,
        [
            {"nombre": "Natalia Alvarado", "aporte": "revisión reglamentaria"},
            {"nombre": "Sin aporte"},
            {"nombre": ""},
            "esto no es un objeto",
        ],
    )

    equipo = patrocinadores.colaboradores(tmp_path)

    assert [c.nombre for c in equipo] == ["Natalia Alvarado", "Sin aporte"]
    assert equipo[0].aporte == "revisión reglamentaria"
    assert equipo[1].aporte == ""


def test_sin_archivo_de_colaboradores_no_falla(tmp_path):
    assert patrocinadores.colaboradores(tmp_path) == ()


def test_el_perfil_de_oro_se_construye_con_lo_minimo_y_con_todo(qtbot, tmp_path):
    from zonda.widgets.apoyo import DialogoPatrocinador

    _escribir(
        tmp_path,
        [
            {
                "nombre": "Completo",
                "nivel": "oro",
                "web": "https://uno.com.ar",
                "contacto": "mailto:a@b.com",
                "ciudad": "Rosario",
                "rubro": "Cálculo",
                "descripcion": "Un párrafo.",
                "desde": "2026",
                "fundador": True,
            },
            {"nombre": "Mínimo", "nivel": "oro"},
        ],
    )
    padre = QtWidgets.QWidget()
    qtbot.addWidget(padre)

    for patrocinador in patrocinadores.cargar(tmp_path):
        dialogo = DialogoPatrocinador(padre, patrocinador)
        qtbot.addWidget(dialogo)
        assert dialogo.windowTitle() == patrocinador.nombre


def test_los_agradecimientos_se_construyen_sin_nadie(qtbot):
    from zonda.widgets.apoyo import DialogoAgradecimientos

    padre = QtWidgets.QWidget()
    qtbot.addWidget(padre)

    dialogo = DialogoAgradecimientos(padre)
    qtbot.addWidget(dialogo)

    assert dialogo.windowTitle() == "Agradecimientos"


def test_el_acerca_de_se_muestra_al_construirse(qtbot):
    """Los diálogos de Zonda se muestran solos en su constructor.

    Quien los abre hace `WidgetAcercaDe(self)` y nada más, así que si el
    `show()` se pierde el diálogo existe pero no lo ve nadie —y no falla ningún
    otro test, porque todo lo demás se construye igual—.
    """
    from zonda.widgets.custom import WidgetAcercaDe

    padre = QtWidgets.QWidget()
    qtbot.addWidget(padre)
    padre.show()

    dialogo = WidgetAcercaDe(padre)
    qtbot.addWidget(dialogo)

    assert dialogo.isVisible()
    assert [
        b.text()
        for b in dialogo.findChildren(QtWidgets.QPushButton)
        if b.text() == "Agradecimientos"
    ]


def test_los_dialogos_de_apoyo_se_muestran_al_construirse(qtbot, tmp_path):
    """Lo mismo para las dos ventanas nuevas."""
    from zonda.widgets.apoyo import DialogoAgradecimientos, DialogoPatrocinador

    _escribir(tmp_path, [{"nombre": "Estudio Uno", "nivel": "oro"}])
    padre = QtWidgets.QWidget()
    qtbot.addWidget(padre)
    padre.show()

    perfil = DialogoPatrocinador(padre, patrocinadores.cargar(tmp_path)[0])
    qtbot.addWidget(perfil)
    gracias = DialogoAgradecimientos(padre)
    qtbot.addWidget(gracias)

    assert perfil.isVisible()
    assert gracias.isVisible()


def test_el_logo_de_plata_abre_su_enlace(qtbot, tmp_path, monkeypatch):
    from zonda.widgets import apoyo

    (tmp_path / "logo.png").write_bytes(b"")
    _escribir(
        tmp_path,
        [
            {
                "nombre": "Grupo Delta",
                "nivel": "plata",
                "web": "https://delta.com.ar",
                "logo": "logo.png",
            }
        ],
    )
    abiertos: list[str] = []
    monkeypatch.setattr(apoyo, "abrir_enlace", abiertos.append)

    boton = apoyo._widget_patrocinador(patrocinadores.cargar(tmp_path)[0], 30)
    qtbot.addWidget(boton)
    boton.click()

    assert abiertos == ["https://delta.com.ar"]


def test_los_logos_se_alcanzan_con_el_tabulador(qtbot, tmp_path):
    """Un logo clickeable tiene que ser un botón, no un label con un clic.

    Un `QLabel` con `mousePressEvent` sólo responde al mouse: no entra en la
    cadena del tabulador ni lo anuncia un lector de pantalla.
    """
    from zonda.widgets import apoyo

    (tmp_path / "logo.png").write_bytes(b"")
    _escribir(
        tmp_path,
        [
            {"nombre": "Estudio Uno", "nivel": "oro", "logo": "logo.png"},
            {
                "nombre": "Grupo Delta",
                "nivel": "plata",
                "web": "https://delta.com.ar",
                "logo": "logo.png",
            },
        ],
    )

    for patrocinador in patrocinadores.cargar(tmp_path):
        widget = apoyo._widget_patrocinador(patrocinador, 30)
        qtbot.addWidget(widget)
        assert widget.focusPolicy() != QtCore.Qt.FocusPolicy.NoFocus
        assert widget.accessibleName()


def test_un_logo_sin_adonde_ir_no_parece_clickeable(qtbot, tmp_path):
    """Plata sin enlace válido se muestra, pero no como algo que se pueda tocar."""
    from zonda.widgets import apoyo

    (tmp_path / "logo.png").write_bytes(b"")
    _escribir(
        tmp_path,
        [
            {
                "nombre": "Sin enlace",
                "nivel": "plata",
                "logo": "logo.png",
                "web": "file:///etc/passwd",
            }
        ],
    )

    widget = apoyo._widget_patrocinador(patrocinadores.cargar(tmp_path)[0], 30)
    qtbot.addWidget(widget)

    assert not isinstance(widget, QtWidgets.QPushButton)


def test_el_logo_del_perfil_no_reabre_el_perfil(qtbot, tmp_path):
    """Dentro de la ventana, el logo ya está adentro de lo que abriría."""
    from zonda.widgets.apoyo import DialogoPatrocinador

    (tmp_path / "logo.png").write_bytes(b"")
    _escribir(tmp_path, [{"nombre": "Estudio Uno", "nivel": "oro", "logo": "logo.png"}])
    padre = QtWidgets.QWidget()
    qtbot.addWidget(padre)

    perfil = DialogoPatrocinador(padre, patrocinadores.cargar(tmp_path)[0])
    qtbot.addWidget(perfil)

    from zonda.widgets.apoyo import BotonLogo

    assert not perfil.findChildren(BotonLogo)
