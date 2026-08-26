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

// El contorno es un color plano: no participa de la iluminación de la escena.
// Lo comparte el borde de las flechas, que es igual de plano (ver silueta.vert).
//
// `colorLinea` llega como vec3 en sRGB, no como uniforme de tipo color, porque
// esos Qt los pasa a espacio lineal y acá lo que se escribe va derecho al
// framebuffer (ver el comentario en Visor.qml).

void MAIN()
{
    FRAGCOLOR = vec4(colorLinea, 1.0);
}
