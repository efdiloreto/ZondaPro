// Copyright (c) 2023, Eduardo Di Loreto <efdiloreto@gmail.com>

// This file is part of Zonda.

// Zonda is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

// Zonda is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.

// You should have received a copy of the GNU General Public License
// along with Zonda.  If not, see <https://www.gnu.org/licenses/>.

// Abre cada arista del contorno hasta un ancho fijo en píxeles.
//
// Los vértices llegan de a cuatro por arista y todos nacen pegados sobre los
// extremos: el rectángulo no está en la malla, se arma acá. Cada vértice trae en
// COLOR el otro extremo de su arista (xyz) y de qué lado abrirse (w).
//
// El corrimiento se calcula después de proyectar, medido en píxeles de pantalla,
// y por eso el ancho no depende de la distancia a la cámara.

void MAIN()
{
    vec4 vista_aca = VIEW_MATRIX * MODEL_MATRIX * vec4(VERTEX, 1.0);
    vec4 vista_alla = VIEW_MATRIX * MODEL_MATRIX * vec4(COLOR.xyz, 1.0);

    // Se acerca el contorno a la cámara para que no pelee en Z con su propia
    // cara. En espacio de vista la cámara está en el origen, así que escalar la
    // posición acerca el punto sin depender de hacia dónde crece la profundidad
    // en cada backend. Y mover un porcentaje de la distancia en lugar de una
    // cantidad fija acompaña la precisión del buffer de profundidad.
    //
    // Acercarse a la cámara, en lugar de correrse sobre la normal de la cara
    // como haría una separación en metros, es lo que hace que el contorno se vea
    // igual desde los dos lados: las caras se dibujan sin descarte.
    vista_aca.xyz *= 1.0 - acercamiento;
    vista_alla.xyz *= 1.0 - acercamiento;

    vec4 aca = PROJECTION_MATRIX * vista_aca;
    vec4 alla = PROJECTION_MATRIX * vista_alla;

    // Si algún extremo cae detrás de la cámara la proyección no sirve: se deja
    // el vértice donde estaba y esa arista sale fina en lugar de deformarse.
    if (aca.w <= 0.0 || alla.w <= 0.0) {
        POSITION = aca;
        return;
    }

    // De coordenadas normalizadas a píxeles: el rango [-1, 1] cubre el viewport.
    vec2 media = viewport * 0.5;
    vec2 px_aca = (aca.xy / aca.w) * media;
    vec2 px_alla = (alla.xy / alla.w) * media;

    vec2 direccion = px_alla - px_aca;
    float largo = length(direccion);
    direccion = largo > 0.0 ? direccion / largo : vec2(1.0, 0.0);
    vec2 perpendicular = vec2(-direccion.y, direccion.x);

    // Media mitad hacia el costado da el ancho. La otra, hacia afuera de la
    // arista, es la tapa cuadrada que rellena la muesca de las esquinas.
    float mitad = grosor * 0.5;
    vec2 corrimiento = perpendicular * COLOR.w * mitad - direccion * mitad;

    // Vuelta a coordenadas de recorte. Se multiplica por w porque la división en
    // perspectiva viene después.
    aca.xy += (corrimiento / media) * aca.w;
    POSITION = aca;
}
