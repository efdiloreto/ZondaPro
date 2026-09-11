// Copyright (c) 2018-2026, Eduardo Di Loreto <efdiloreto@gmail.com>

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

// El trazo a inglete del glow de selección.
//
// A diferencia de contorno.vert —un rectángulo por arista, con tapas cuadradas
// que en un trazo translúcido se superponen y acumulan color en las esquinas—
// acá cada esquina abre hacia los dos lados de su inglete: no hay tapas ni
// solapes, así que el glow queda parejo.
//
// Cada vértice trae en COLOR la esquina *previa* (xyz) y el lado por el que
// abrirse (w), y en NORMAL la esquina *siguiente*: con las direcciones de los
// dos tramos que concurren a la esquina sale el inglete, proyectado a píxeles
// de pantalla, igual que en contorno.vert.
//
// En los extremos de un trazo abierto la esquina que falta repite al propio
// vértice, así que uno de los dos tramos mide cero y el inglete cae en la
// perpendicular pura del tramo que hay: tope recto.

void MAIN()
{
    vec4 aca = VIEW_MATRIX * MODEL_MATRIX * vec4(VERTEX, 1.0);
    vec4 previa = VIEW_MATRIX * MODEL_MATRIX * vec4(COLOR.xyz, 1.0);
    vec4 siguiente = VIEW_MATRIX * MODEL_MATRIX * vec4(NORMAL, 1.0);

    // Mismo acercamiento a la cámara que los contornos, para no pelear en Z
    // con la cara a la que pertenece el trazo.
    aca.xyz *= 1.0 - acercamiento;
    previa.xyz *= 1.0 - acercamiento;
    siguiente.xyz *= 1.0 - acercamiento;

    vec4 proy = PROJECTION_MATRIX * aca;
    vec4 proy_previa = PROJECTION_MATRIX * previa;
    vec4 proy_siguiente = PROJECTION_MATRIX * siguiente;

    // Si algún punto cae detrás de la cámara la proyección no sirve: se deja
    // el vértice donde estaba en lugar de deformar el trazo.
    if (proy.w <= 0.0 || proy_previa.w <= 0.0 || proy_siguiente.w <= 0.0) {
        POSITION = proy;
        return;
    }

    vec2 media = viewport * 0.5;
    vec2 px = (proy.xy / proy.w) * media;
    vec2 px_previa = (proy_previa.xy / proy_previa.w) * media;
    vec2 px_siguiente = (proy_siguiente.xy / proy_siguiente.w) * media;

    vec2 d1 = px - px_previa;
    vec2 d2 = px_siguiente - px;
    float l1 = length(d1);
    float l2 = length(d2);

    vec2 n1 = l1 > 0.0 ? vec2(-d1.y, d1.x) / l1 : vec2(0.0);
    vec2 n2 = l2 > 0.0 ? vec2(-d2.y, d2.x) / l2 : vec2(0.0);

    vec2 inglete;
    if (l1 < 0.001 && l2 < 0.001) {
        POSITION = proy;
        return;
    } else if (l1 < 0.001) {
        inglete = n2;
    } else if (l2 < 0.001) {
        inglete = n1;
    } else {
        inglete = n1 + n2;
        float largo = length(inglete);
        // Esquina de 180 grados (el trazo vuelve sobre sí): perpendicular pura.
        inglete = largo > 0.0 ? inglete / largo : n1;
        // El inglete se abre más que la perpendicular para mantener el ancho
        // del trazo en la esquina. En una esquina muy aguda ese crecimiento se
        // dispara: se corta a 2.5 anchos y la esquina queda apenas redonda.
        float coseno = max(abs(dot(inglete, n1)), 0.4);
        inglete /= coseno;
    }

    px += inglete * (COLOR.w * grosor * 0.5);

    // Vuelta a coordenadas de recorte, multiplicando por w porque la división
    // en perspectiva viene después.
    proy.xy = (px / media) * proy.w;
    POSITION = proy;
}
