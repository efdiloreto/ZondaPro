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

"""Tests del servidor MCP.

Como el resto de la suite, son smoke tests: cada herramienta corre de punta a
punta (cálculo, serialización y coordenadas) y la respuesta es JSON estricto,
con las claves de las zonas alineadas con las de las filas de resultados.
"""

import asyncio
import json

import pytest

from zonda.enums import (
    DireccionVientoCubiertaAislada,
    DireccionVientoMetodoDireccionalSprfv,
    ParedEdificioSprfv,
    ZonaComponenteCubiertaAislada,
)
from zonda.mcp import herramientas
from zonda.mcp.serializacion import serializar_valor


def _json_estricto(respuesta: dict) -> str:
    """Serializa la respuesta como JSON estricto, sin NaN ni tipos raros.

    Args:
        respuesta: La respuesta de una herramienta.

    Returns:
        El texto JSON.

    Raises:
        AssertionError: Cuando algún valor no se puede serializar.
    """
    return json.dumps(respuesta, allow_nan=False)


class TestSerializacion:
    def test_enum_por_nombre(self):
        from zonda.enums import TipoCubierta

        assert serializar_valor(TipoCubierta.DOS_AGUAS) == "DOS_AGUAS"

    def test_tupla_a_lista(self):
        assert serializar_valor((1.0, 2.0)) == [1.0, 2.0]

    def test_dataclass_a_dict(self):
        from zonda.cirsoc.resultados import PresionVelocidad

        q = PresionVelocidad(altura=10, kz=1.0, kzt=1.0, valor=500)
        assert serializar_valor(q) == {
            "altura": 10,
            "kz": 1.0,
            "kzt": 1.0,
            "valor": 500,
            "ke": 1.0,
        }

    def test_dict_con_clave_enum(self):
        from zonda.enums import ParedEdificioSprfv

        serializado = serializar_valor({ParedEdificioSprfv.BARLOVENTO: 1.0})
        assert serializado == {"BARLOVENTO": 1.0}


class TestCalcularEdificio:
    def test_respuesta_json_estricto(self, edificio):
        respuesta = herramientas.calcular_edificio(
            ancho=edificio.ancho,
            longitud=edificio.longitud,
            altura_alero=edificio.altura_alero,
            altura_cumbrera=edificio.altura_cumbrera,
            tipo_cubierta="DOS_AGUAS",
            cerramiento="CERRADO",
            velocidad=edificio.velocidad,
            categoria_exp="B",
            componentes_paredes={"Viga": 10.0},
            componentes_cubierta={"Correa": 5.0},
        )
        _json_estricto(respuesta)

    def test_estructura_de_la_respuesta(self, edificio):
        respuesta = herramientas.calcular_edificio(
            ancho=edificio.ancho,
            longitud=edificio.longitud,
            altura_alero=edificio.altura_alero,
            altura_cumbrera=edificio.altura_cumbrera,
            tipo_cubierta="DOS_AGUAS",
            cerramiento="CERRADO",
            velocidad=edificio.velocidad,
            categoria_exp="B",
        )
        assert respuesta["estructura"] == "EDIFICIO"
        assert respuesta["unidades"]["presion"] == "N/m2"
        assert respuesta["entrada"]["tipo_cubierta"] == "DOS_AGUAS"
        assert respuesta["resultados_sprfv"]
        assert respuesta["referencias_sprfv"]

    def test_fila_edificio(self, edificio):
        respuesta = herramientas.calcular_edificio(
            ancho=edificio.ancho,
            longitud=edificio.longitud,
            altura_alero=edificio.altura_alero,
            altura_cumbrera=edificio.altura_cumbrera,
            tipo_cubierta="DOS_AGUAS",
            cerramiento="CERRADO",
            velocidad=edificio.velocidad,
            categoria_exp="B",
        )
        fila = respuesta["resultados_sprfv"][0]
        assert fila["zona"] == "PAREDES"
        assert fila["sistema"] == "SPRFV"
        assert set(fila["q"]) == {"altura", "kz", "kzt", "valor", "ke"}
        assert isinstance(fila["pos"], float)
        assert isinstance(fila["neg"], float)
        assert fila["referencia"]

    def test_contrato_fila_zona_paredes(self, edificio):
        """Cada pared que aparece en las filas tiene su coordenada."""
        respuesta = herramientas.calcular_edificio(
            ancho=edificio.ancho,
            longitud=edificio.longitud,
            altura_alero=edificio.altura_alero,
            altura_cumbrera=edificio.altura_cumbrera,
            tipo_cubierta="DOS_AGUAS",
            cerramiento="CERRADO",
            velocidad=edificio.velocidad,
            categoria_exp="B",
        )
        paredes = respuesta["zonas"]["sprfv"]["paredes"]
        for direccion in DireccionVientoMetodoDireccionalSprfv:
            filas = {
                fila["pared"]
                for fila in respuesta["resultados_sprfv"]
                if fila["zona"] == "PAREDES" and fila["direccion"] == direccion.name
            }
            coordenadas = set(paredes[direccion.name])
            assert filas <= coordenadas

    def test_componentes_sin_error(self, edificio):
        respuesta = herramientas.calcular_edificio(
            ancho=edificio.ancho,
            longitud=edificio.longitud,
            altura_alero=edificio.altura_alero,
            altura_cumbrera=edificio.altura_cumbrera,
            tipo_cubierta="DOS_AGUAS",
            cerramiento="CERRADO",
            velocidad=edificio.velocidad,
            categoria_exp="B",
            componentes_paredes={"Viga": 10.0},
            componentes_cubierta={"Correa": 5.0},
        )
        assert respuesta["resultados_componentes"]
        assert respuesta["referencias_componentes"]
        assert "error_componentes" not in respuesta

    def test_contrato_fila_zona_componentes_paredes(self, edificio):
        """Las zonas negativas de pared, las que tienen coordenada propia, están en las coordenadas.

        El positivo de pared es único para toda la pared y viaja en una fila
        con ``TODAS``, que no tiene coordenada propia: cubre a todas.
        """
        respuesta = herramientas.calcular_edificio(
            ancho=edificio.ancho,
            longitud=edificio.longitud,
            altura_alero=edificio.altura_alero,
            altura_cumbrera=edificio.altura_cumbrera,
            tipo_cubierta="DOS_AGUAS",
            cerramiento="CERRADO",
            velocidad=edificio.velocidad,
            categoria_exp="B",
            componentes_paredes={"Viga": 10.0},
        )
        coordenadas = respuesta["zonas"]["componentes"]["paredes"]
        zonas_coords = {zona for pared in coordenadas.values() for zona in pared}
        zonas_filas = {
            fila["zona_componente"]
            for fila in respuesta["resultados_componentes"]
            if fila["zona"] == "PAREDES" and fila["tipo_presion"] == "NEGATIVA"
        }
        assert zonas_filas <= zonas_coords
        positivas = {
            fila["zona_componente"]
            for fila in respuesta["resultados_componentes"]
            if fila["zona"] == "PAREDES" and fila["tipo_presion"] == "POSITIVA"
        }
        assert positivas == {"TODAS"}

    def test_contrato_fila_zona_componentes_cubierta(self, edificio):
        respuesta = herramientas.calcular_edificio(
            ancho=edificio.ancho,
            longitud=edificio.longitud,
            altura_alero=edificio.altura_alero,
            altura_cumbrera=edificio.altura_cumbrera,
            tipo_cubierta="DOS_AGUAS",
            cerramiento="CERRADO",
            velocidad=edificio.velocidad,
            categoria_exp="B",
            componentes_cubierta={"Correa": 5.0},
        )
        coordenadas = respuesta["zonas"]["componentes"]["cubierta"]
        zonas_filas = {
            fila["zona_componente"]
            for fila in respuesta["resultados_componentes"]
            if fila["zona"] == "CUBIERTA" and fila["zona_componente"] != "TODAS"
        }
        assert zonas_filas <= set(coordenadas)

    def test_error_componentes(self, edificio_con_parapeto):
        """Con parapeto de cubierta plana y sin área efectiva, componentes no aparece y el error sí.

        El parapeto de C&R es de la Figura 5.4-1 (cubierta plana, Art. 5.6):
        sin su área efectiva de viento el núcleo lanza ErrorLineamientos y la
        respuesta lo reporta, mientras el SPRFV sigue completo.
        """
        respuesta = herramientas.calcular_edificio(
            ancho=30,
            longitud=40,
            altura_alero=10,
            altura_cumbrera=10,
            tipo_cubierta="PLANA",
            cerramiento="CERRADO",
            velocidad=45,
            categoria_exp="B",
            parapeto=1,
            componentes_paredes={"Viga": 10.0},
            componentes_cubierta={"Correa": 5.0},
        )
        assert respuesta["error_componentes"]["tipo"] == "ErrorLineamientos"
        assert "resultados_componentes" not in respuesta
        assert "componentes" not in respuesta["zonas"]
        assert respuesta["resultados_sprfv"]

    def test_zonas_sprfv_cubren_direcciones(self, edificio):
        respuesta = herramientas.calcular_edificio(
            ancho=edificio.ancho,
            longitud=edificio.longitud,
            altura_alero=edificio.altura_alero,
            altura_cumbrera=edificio.altura_cumbrera,
            tipo_cubierta="DOS_AGUAS",
            cerramiento="CERRADO",
            velocidad=edificio.velocidad,
            categoria_exp="B",
        )
        assert set(respuesta["zonas"]["sprfv"]["paredes"]) == {
            direccion.name for direccion in DireccionVientoMetodoDireccionalSprfv
        }

    def test_zonas_sprfv_parapeto(self, edificio_plana_con_parapeto):
        respuesta = herramientas.calcular_edificio(
            ancho=edificio_plana_con_parapeto.ancho,
            longitud=edificio_plana_con_parapeto.longitud,
            altura_alero=edificio_plana_con_parapeto.altura_alero,
            altura_cumbrera=edificio_plana_con_parapeto.altura_cumbrera,
            tipo_cubierta="PLANA",
            cerramiento="CERRADO",
            velocidad=edificio_plana_con_parapeto.velocidad,
            categoria_exp="B",
            parapeto=1,
            area_parapeto=2,
            componentes_paredes={"Viga": 10.0},
            componentes_cubierta={"Correa": 5.0},
        )
        parapeto = respuesta["zonas"]["sprfv"]["parapeto"]
        assert parapeto
        for direccion in DireccionVientoMetodoDireccionalSprfv:
            assert set(parapeto[direccion.name]) == {
                pared.name
                for pared in (
                    ParedEdificioSprfv.BARLOVENTO,
                    ParedEdificioSprfv.SOTAVENTO,
                )
            }

    def test_valor_invalido(self, edificio):
        with pytest.raises(ValueError, match="categoria_exp"):
            herramientas.calcular_edificio(
                ancho=edificio.ancho,
                longitud=edificio.longitud,
                altura_alero=edificio.altura_alero,
                altura_cumbrera=edificio.altura_cumbrera,
                tipo_cubierta="DOS_AGUAS",
                cerramiento="CERRADO",
                velocidad=edificio.velocidad,
                categoria_exp="X",
            )


class TestCalcularCartel:
    def test_respuesta(self, cartel):
        respuesta = herramientas.calcular_cartel(
            ancho=cartel.ancho,
            altura_inferior=cartel.altura_inferior,
            altura_superior=cartel.altura_superior,
            profundidad=cartel.profundidad,
            velocidad=cartel.velocidad,
            categoria_exp="B",
        )
        _json_estricto(respuesta)
        casos = {fila["caso"] for fila in respuesta["resultados"]}
        assert casos == {"CASO_A", "CASO_B", "CASO_C"}
        regiones = [
            fila for fila in respuesta["resultados"] if fila["caso"] == "CASO_C"
        ]
        assert regiones
        assert all(fila["region"] for fila in regiones)
        assert all(
            fila["region"] is None
            for fila in respuesta["resultados"]
            if fila["caso"] != "CASO_C"
        )
        assert all(
            fila["excentricidad"] is not None
            for fila in respuesta["resultados"]
            if fila["caso"] == "CASO_B"
        )

    def test_zonas(self, cartel):
        respuesta = herramientas.calcular_cartel(
            ancho=cartel.ancho,
            altura_inferior=cartel.altura_inferior,
            altura_superior=cartel.altura_superior,
            profundidad=cartel.profundidad,
            velocidad=cartel.velocidad,
            categoria_exp="B",
        )
        assert len(respuesta["zonas"]["caras"]) == 5
        assert respuesta["zonas"]["cara_barlovento"]
        assert respuesta["zonas"]["regiones_caso_c"]


class TestCalcularCubiertaAislada:
    def test_respuesta(self, cubierta_aislada_con_componentes):
        respuesta = herramientas.calcular_cubierta_aislada(
            ancho=cubierta_aislada_con_componentes.ancho,
            longitud=cubierta_aislada_con_componentes.longitud,
            altura_alero=cubierta_aislada_con_componentes.altura_alero,
            altura_cumbrera=cubierta_aislada_con_componentes.altura_cumbrera,
            tipo_cubierta="DOS_AGUAS",
            velocidad=cubierta_aislada_con_componentes.velocidad,
            categoria_exp="B",
            componentes={"Chapa": 0.5, "Correa": 2.0},
        )
        _json_estricto(respuesta)
        direcciones = {fila["direccion"] for fila in respuesta["resultados"]}
        assert direcciones == {d.name for d in DireccionVientoCubiertaAislada}
        assert respuesta["resultados_componentes"]
        assert respuesta["referencias_componentes"]

    def test_contrato_zonas_componentes(self, cubierta_aislada_con_componentes):
        respuesta = herramientas.calcular_cubierta_aislada(
            ancho=cubierta_aislada_con_componentes.ancho,
            longitud=cubierta_aislada_con_componentes.longitud,
            altura_alero=cubierta_aislada_con_componentes.altura_alero,
            altura_cumbrera=cubierta_aislada_con_componentes.altura_cumbrera,
            tipo_cubierta="DOS_AGUAS",
            velocidad=cubierta_aislada_con_componentes.velocidad,
            categoria_exp="B",
            componentes={"Chapa": 0.5, "Correa": 2.0},
        )
        coordenadas = respuesta["zonas"]["componentes"]
        zonas_filas = {
            fila["zona_componente"] for fila in respuesta["resultados_componentes"]
        }
        assert zonas_filas <= {z.name for z in ZonaComponenteCubiertaAislada}
        assert zonas_filas <= set(coordenadas)

    def test_sin_componentes(self, cubierta_aislada):
        respuesta = herramientas.calcular_cubierta_aislada(
            ancho=cubierta_aislada.ancho,
            longitud=cubierta_aislada.longitud,
            altura_alero=cubierta_aislada.altura_alero,
            altura_cumbrera=cubierta_aislada.altura_cumbrera,
            tipo_cubierta="DOS_AGUAS",
            velocidad=cubierta_aislada.velocidad,
            categoria_exp="B",
        )
        assert "componentes" not in respuesta["zonas"]
        assert "resultados_componentes" not in respuesta


class TestServidor:
    def test_herramientas_registradas(self):
        from fastmcp import Client

        from zonda.mcp.servidor import mcp

        async def correr():
            async with Client(mcp) as cliente:
                return [t.name for t in await cliente.list_tools()]

        assert sorted(asyncio.run(correr())) == [
            "calcular_cartel",
            "calcular_cubierta_aislada",
            "calcular_edificio",
        ]

    def test_llamada_por_el_protocolo(self, cartel):
        """Una llamada MCP de punta a punta devuelve la respuesta como datos."""
        from fastmcp import Client

        from zonda.mcp.servidor import mcp

        async def correr():
            async with Client(mcp) as cliente:
                return await cliente.call_tool(
                    "calcular_cartel",
                    {
                        "ancho": cartel.ancho,
                        "altura_inferior": cartel.altura_inferior,
                        "altura_superior": cartel.altura_superior,
                        "profundidad": cartel.profundidad,
                        "velocidad": cartel.velocidad,
                        "categoria_exp": "B",
                    },
                )

        resultado = asyncio.run(correr())
        datos = resultado.data
        assert datos["estructura"] == "CARTEL"
        assert datos["resultados"]
        assert datos["zonas"]["regiones_caso_c"]

    def test_restricciones_de_los_parametros(self):
        """El esquema rechaza valores físicamente imposibles antes de calcular."""
        from fastmcp import Client

        from zonda.mcp.servidor import mcp

        async def correr():
            async with Client(mcp) as cliente:
                await cliente.call_tool(
                    "calcular_edificio",
                    {
                        "ancho": -30,
                        "longitud": 40,
                        "altura_alero": 10,
                        "altura_cumbrera": 10,
                        "tipo_cubierta": "PLANA",
                        "cerramiento": "CERRADO",
                        "velocidad": 40,
                        "categoria_exp": "B",
                    },
                )

        with pytest.raises(Exception, match="greater than 0"):
            asyncio.run(correr())

    def test_esquema_con_restricciones(self):
        """Las restricciones físicas viajan en el esquema que ve el cliente."""
        from zonda.mcp.servidor import mcp

        async def correr():
            herramienta = await mcp.get_tool("calcular_cubierta_aislada")
            return herramienta.parameters["properties"]["bloqueo"]

        bloqueo = asyncio.run(correr())
        assert bloqueo["minimum"] == 0
        assert bloqueo["maximum"] == 100
