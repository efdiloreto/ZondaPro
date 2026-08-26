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

// Hincha la flecha para que asome un borde fino alrededor de su silueta.
//
// La malla que se dibuja con este shader es la misma flecha, pero con las caras
// de frente descartadas: lo que queda es su cara interna, o sea la flecha vista
// del revés. Corrida hacia afuera, asoma justo por el contorno de la que sí se
// ve, y la de adelante la tapa en todo el resto.
//
// El corrimiento se calcula después de proyectar y se mide en píxeles de
// pantalla, así el borde sale del mismo grosor esté la flecha cerca o lejos.
//
// Se corre sobre la normal suavizada que llega en COLOR y no sobre NORMAL: la de
// la malla es por cara —la flecha se ve facetada a propósito— y con ella el
// borde se abriría en cada arista dejando muescas.

void MAIN()
{
    vec4 vista = VIEW_MATRIX * MODEL_MATRIX * vec4(VERTEX, 1.0);

    // La flecha se escala parejo en los tres ejes y la vista es un movimiento
    // rígido, así que las mismas matrices sirven para la normal: alcanza con
    // volver a normalizarla.
    vec3 normal = normalize(mat3(VIEW_MATRIX * MODEL_MATRIX) * COLOR.xyz);

    vec4 aca = PROJECTION_MATRIX * vista;
    if (aca.w <= 0.0) {  // el vértice quedó detrás de la cámara
        POSITION = aca;
        return;
    }

    // Hacia dónde apunta la normal en pantalla: se proyecta un segundo punto
    // corrido sobre ella. El paso es una fracción de la distancia a la cámara
    // para que no se vaya de la escena ni se pierda en la precisión.
    vec4 alla = PROJECTION_MATRIX
                * vec4(vista.xyz + normal * length(vista.xyz) * 0.01, 1.0);
    if (alla.w <= 0.0) {
        POSITION = aca;
        return;
    }

    // De coordenadas normalizadas a píxeles: el rango [-1, 1] cubre el viewport.
    vec2 media = viewport * 0.5;
    vec2 direccion = (alla.xy / alla.w - aca.xy / aca.w) * media;
    float largo = length(direccion);

    // Una normal que mira derecho a la cámara no tiene dirección en pantalla, y
    // ese vértice tampoco está en la silueta: se lo deja donde estaba.
    if (largo > 1e-4) {
        // Vuelta a coordenadas de recorte, multiplicando por w porque la
        // división en perspectiva viene después.
        aca.xy += ((direccion / largo) * grosor / media) * aca.w;
    }
    POSITION = aca;
}
