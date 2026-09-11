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

"""Tests de la instalación del servidor MCP en clientes.

Trabajan sobre archivos temporales: un ``Cliente`` de prueba con su
``archivo_config`` en ``tmp_path``, así que ningún test toca la configuración
real de quien los corre.
"""

import json
import sys

import pytest

from zonda.excepciones import ErrorConfiguracionMCP
from zonda.mcp import instalacion
from zonda.mcp.instalacion import CLIENTE_ZONDA, Cliente, EstadoCliente


@pytest.fixture
def cliente(tmp_path) -> Cliente:
    return Cliente(nombre="Prueba", archivo_config=tmp_path / "config.json")


def test_entrada_servidor():
    entrada = instalacion.entrada_servidor()
    assert entrada["command"] == sys.executable
    assert entrada["args"] == ["-m", "zonda.mcp"]


def test_entrada_servidor_opencode():
    entrada = instalacion.entrada_servidor("mcp")
    assert entrada["type"] == "local"
    assert entrada["command"] == [sys.executable, "-m", "zonda.mcp"]
    assert entrada["enabled"] is True


def test_prompt_instalacion():
    prompt = instalacion.prompt_instalacion()
    assert instalacion.CLIENTE_ZONDA in prompt
    assert "-m zonda.mcp" in prompt
    assert "calcular_edificio" in prompt
    assert "calcular_cartel" in prompt
    assert "calcular_cubierta_aislada" in prompt
    assert "llamada de prueba" in prompt


def test_estado_no_detectado(cliente):
    assert instalacion.estado(cliente) == EstadoCliente.NO_DETECTADO


def test_instalar(cliente):
    instalacion.instalar(cliente)
    assert instalacion.estado(cliente) == EstadoCliente.INSTALADO
    datos = json.loads(cliente.archivo_config.read_text(encoding="utf-8"))
    assert datos["mcpServers"][CLIENTE_ZONDA] == instalacion.entrada_servidor()


def test_instalar_preserva_las_demas_entradas(cliente):
    cliente.archivo_config.parent.mkdir(parents=True, exist_ok=True)
    cliente.archivo_config.write_text(
        json.dumps(
            {
                "otra_clave": 1,
                "mcpServers": {"otro-servidor": {"command": "otro"}},
            }
        ),
        encoding="utf-8",
    )
    instalacion.instalar(cliente)
    datos = json.loads(cliente.archivo_config.read_text(encoding="utf-8"))
    assert datos["otra_clave"] == 1
    assert datos["mcpServers"]["otro-servidor"] == {"command": "otro"}


def test_instalar_deja_respaldo(cliente):
    instalacion.instalar(cliente)
    primero = cliente.archivo_config.read_text(encoding="utf-8")
    instalacion.instalar(cliente)
    respaldo = cliente.archivo_config.with_name(cliente.archivo_config.name + ".bak")
    assert respaldo.read_text(encoding="utf-8") == primero


def test_desactualizado(cliente):
    instalacion.instalar(cliente)
    datos = json.loads(cliente.archivo_config.read_text(encoding="utf-8"))
    datos["mcpServers"][CLIENTE_ZONDA]["args"] = ["otra-cosa"]
    cliente.archivo_config.write_text(json.dumps(datos), encoding="utf-8")
    assert instalacion.estado(cliente) == EstadoCliente.DESACTUALIZADO
    instalacion.instalar(cliente)
    assert instalacion.estado(cliente) == EstadoCliente.INSTALADO


def test_desinstalar(cliente):
    instalacion.instalar(cliente)
    instalacion.desinstalar(cliente)
    datos = json.loads(cliente.archivo_config.read_text(encoding="utf-8"))
    assert CLIENTE_ZONDA not in datos["mcpServers"]
    assert instalacion.estado(cliente) == EstadoCliente.NO_INSTALADO


def test_archivo_vacio(cliente):
    """Un archivo vacío es una configuración en blanco, no un error.

    Antigravity crea su mcp_config.json vacío la primera vez que se abre su
    administrador de MCP: tiene que poder instalarse encima.
    """
    cliente.archivo_config.write_text("", encoding="utf-8")
    assert instalacion.estado(cliente) == EstadoCliente.NO_INSTALADO
    instalacion.instalar(cliente)
    assert instalacion.estado(cliente) == EstadoCliente.INSTALADO
    datos = json.loads(cliente.archivo_config.read_text(encoding="utf-8"))
    assert datos["mcpServers"][CLIENTE_ZONDA] == instalacion.entrada_servidor()


class TestRutasPorPlataforma:
    """La matriz de rutas de Claude Desktop, simulando cada plataforma."""

    def test_darwin(self, monkeypatch, tmp_path):
        monkeypatch.setattr(instalacion.sys, "platform", "darwin")
        monkeypatch.setattr(instalacion.Path, "home", lambda: tmp_path)
        (archivo,) = instalacion._archivos_claude_desktop()
        assert (
            archivo
            == tmp_path
            / "Library"
            / "Application Support"
            / "Claude"
            / "claude_desktop_config.json"
        )

    def test_win32(self, monkeypatch, tmp_path):
        monkeypatch.setattr(instalacion.sys, "platform", "win32")
        monkeypatch.setattr(instalacion.Path, "home", lambda: tmp_path)
        monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
        paquete = tmp_path / "local" / "Packages" / "Claude_abc123"
        (paquete / "LocalCache" / "Roaming" / "Claude").mkdir(parents=True)
        archivos = instalacion._archivos_claude_desktop()
        assert (
            archivos[0]
            == tmp_path / "appdata" / "Claude" / "claude_desktop_config.json"
        )
        assert (
            archivos[1]
            == paquete
            / "LocalCache"
            / "Roaming"
            / "Claude"
            / "claude_desktop_config.json"
        )

    def test_win32_sin_ms_store(self, monkeypatch, tmp_path):
        monkeypatch.setattr(instalacion.sys, "platform", "win32")
        monkeypatch.setattr(instalacion.Path, "home", lambda: tmp_path)
        monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
        monkeypatch.delenv("LOCALAPPDATA", raising=False)
        archivos = instalacion._archivos_claude_desktop()
        assert archivos == (
            tmp_path / "appdata" / "Claude" / "claude_desktop_config.json",
        )

    def test_linux(self, monkeypatch, tmp_path):
        monkeypatch.setattr(instalacion.sys, "platform", "linux")
        monkeypatch.setattr(instalacion.Path, "home", lambda: tmp_path)
        (archivo,) = instalacion._archivos_claude_desktop()
        assert archivo == tmp_path / ".config" / "Claude" / "claude_desktop_config.json"


def test_desinstalar_sin_instalar(cliente):
    instalacion.desinstalar(cliente)
    assert not cliente.archivo_config.exists()


def test_instalar_formato_opencode(tmp_path):
    cliente = Cliente(
        nombre="OpenCode",
        archivo_config=tmp_path / "opencode.json",
        raiz="mcp",
    )
    instalacion.instalar(cliente)
    assert instalacion.estado(cliente) == EstadoCliente.INSTALADO
    datos = json.loads(cliente.archivo_config.read_text(encoding="utf-8"))
    entrada = datos["mcp"][CLIENTE_ZONDA]
    assert entrada["type"] == "local"
    assert entrada["command"] == [sys.executable, "-m", "zonda.mcp"]
    instalacion.desinstalar(cliente)
    datos = json.loads(cliente.archivo_config.read_text(encoding="utf-8"))
    assert CLIENTE_ZONDA not in datos["mcp"]


def test_json_corrupto(cliente):
    cliente.archivo_config.write_text("{ no es json", encoding="utf-8")
    with pytest.raises(ErrorConfiguracionMCP):
        instalacion.instalar(cliente)


def test_estado_ilegible(cliente):
    """Un archivo con comentarios (JSONC) no se toca: el estado lo indica."""
    cliente.archivo_config.write_text(
        '{"mcpServers": { // comentario\n  "otro": {}}}',
        encoding="utf-8",
    )
    assert instalacion.estado(cliente) == EstadoCliente.ILEGIBLE
    with pytest.raises(ErrorConfiguracionMCP):
        instalacion.instalar(cliente)
    # El archivo queda intacto.
    assert "// comentario" in cliente.archivo_config.read_text(encoding="utf-8")


def test_no_disponible():
    cliente = Cliente(nombre="Fantasma", archivo_config=None)
    assert instalacion.estado(cliente) == EstadoCliente.NO_DISPONIBLE
    with pytest.raises(ErrorConfiguracionMCP):
        instalacion.instalar(cliente)


def test_clientes_conocidos():
    nombres = [c.nombre for c in instalacion.CLIENTES]
    assert nombres == ["Claude Desktop", "Claude Code", "Antigravity", "OpenCode"]
    raices = [c.raiz for c in instalacion.CLIENTES]
    assert raices == ["mcpServers", "mcpServers", "mcpServers", "mcp"]
