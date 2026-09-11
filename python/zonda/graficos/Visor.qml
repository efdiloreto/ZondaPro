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

// La vista 3D de las presiones de viento.
//
// La escena la provee Python como la propiedad de contexto `escenaPython`
// (ver zonda/graficos/escena.py). Este archivo no calcula geometría: instancia
// un Model por cada actor y proyecta las etiquetas a 2D.

import QtQuick
import QtQuick3D
import QtQuick3D.Helpers

Item {
    id: raiz

    // Se copia la propiedad de contexto en una del root para poder escribir
    // `raiz.escena` y para que los bindings sean null-safe: QML los evalúa antes
    // de que Python termine de armar la escena.
    property var escena: escenaPython

    property bool conica: true

    readonly property color colorTinta: "#000000"
    readonly property color colorFondo: "#ededed"
    readonly property color colorMedicion: "#e800e8"
    readonly property color colorContorno: "#404040"
    readonly property color colorGlow: "#e800e8"

    // La zona de presión que se tocó. La selección es estado puro de la
    // vista: la escena no sabe nada de esto. El glow rodea a la zona y a su
    // flecha, y el panel fijo de la esquina muestra el detalle del cálculo.
    property var zonaSeleccionada: null

    // Ancho de las líneas en píxeles lógicos. El shader las mide en píxeles de
    // dispositivo, así que abajo va multiplicado por el devicePixelRatio, y por
    // eso el viewport se calcula en las mismas unidades.
    readonly property real grosorContorno: 2
    // Las aristas de las flechas van más finas que los contornos: la flecha es
    // un cuerpo chico y ahí una línea de dos píxeles se la come.
    readonly property real grosorAristasFlecha: 1
    readonly property vector2d viewportEnPixeles: Qt.vector2d(
        vista.width * Screen.devicePixelRatio, vista.height * Screen.devicePixelRatio)
    // Cuánto se acerca cada línea a la cámara, como fracción de su distancia,
    // para no pelear en Z con la cara a la que pertenece.
    readonly property real acercamientoContorno: 0.008
    // Las capas del glow van un poco más cerca de la cámara todavía: el halo
    // tiene que quedar delante de la línea nítida del contorno, no detrás.
    readonly property real acercamientoGlow: 0.018

    readonly property real radioEscena: escena ? escena.radio : 1

    // A cuántos píxeles de distancia un vértice se lleva el clic. Es un radio en
    // pantalla y no en metros a propósito: lo que el usuario juzga como "estoy
    // sobre el vértice" es lo que ve, y eso no depende del zoom.
    readonly property real radioEnganchePx: 18

    // La medición proyectada a la pantalla: los dos extremos, su largo en
    // píxeles y la perpendicular a la regla, que es sobre la que se corren las
    // marcas y la etiqueta. Es null si no hay medición o si algún extremo quedó
    // atrás de la cámara.
    //
    // Como mapFrom3DScene es una función, el binding tiene que leer la
    // transformación de la cámara y el tamaño de la vista para que QML sepa
    // cuándo recalcular; ver las etiquetas de presión, que hacen lo mismo.
    readonly property var proyeccionMedicion: {
        const _pos = vista.camera.scenePosition
        const _rot = vista.camera.sceneRotation
        const _ancho = vista.width
        const _alto = vista.height
        const _mag = camaraOrtografica.verticalMagnification
        const extremos = medicion.extremos
        if (extremos.length !== 2)
            return null
        const a = vista.mapFrom3DScene(extremos[0])
        const b = vista.mapFrom3DScene(extremos[1])
        if (a.z <= 0 || b.z <= 0)
            return null
        const largoPx = Math.hypot(b.x - a.x, b.y - a.y)
        if (largoPx < 1)
            return {a: a, b: b, largoPx: largoPx, nx: 0, ny: -1}
        return {a: a, b: b, largoPx: largoPx,
                nx: -(b.y - a.y) / largoPx, ny: (b.x - a.x) / largoPx}
    }

    // Cuánto se le perdona a una etiqueta antes de darla por tapada. Alcanza con
    // absorber el ruido del cálculo: la etiqueta vive separada de su cara, así
    // que cuando se la mira de frente el rayo llega a ella bastante antes.
    readonly property real toleranciaOclusion: radioEscena * 1e-4

    // --- Escena 3D ----------------------------------------------------------

    View3D {
        id: vista
        anchors.fill: parent
        camera: raiz.conica ? camaraConica : camaraOrtografica

        environment: SceneEnvironment {
            clearColor: raiz.colorFondo
            backgroundMode: SceneEnvironment.Color
            antialiasingMode: SceneEnvironment.MSAA
            antialiasingQuality: SceneEnvironment.High
        }

        // El OrbitCameraController impone este esquema: la cámara es hija de un
        // nodo origen y se aleja sobre su +Z local. Las vistas fijas rotan el
        // origen; el zoom mueve la cámara sobre ese eje.
        Node {
            id: origen

            PerspectiveCamera {
                id: camaraConica
                fieldOfView: 60
                clipNear: 0.01
                clipFar: 10000
                // La luz va colgada de la cámara, así la escena siempre queda
                // iluminada de frente.
                DirectionalLight { brightness: 1.0 }
            }

            OrthographicCamera {
                id: camaraOrtografica
                clipNear: 0.01
                clipFar: 10000
                DirectionalLight { brightness: 1.0 }
            }
        }

        // Relleno desde atrás: Qt Quick 3D no ilumina las caras traseras.
        DirectionalLight {
            eulerRotation.x: 25
            eulerRotation.y: 180
            brightness: 0.5
        }

        // Caras
        Repeater3D {
            model: raiz.escena ? raiz.escena.caras : []
            Model {
                geometry: modelData.malla
                visible: modelData.visible
                // Los Model no son pickable por omisión, y sin esto no anda
                // ni el rayo que decide si una etiqueta de presión quedó tapada
                // ni la selección de zonas al tocarlas. La medición no usa
                // pick: ver candidatoEn().
                pickable: true
                // La zona que este Model representa: el pick del toque la
                // consulta para saber qué seleccionar.
                property var zona: modelData
                materials: PrincipledMaterial {
                    baseColor: modelData.color
                    roughness: 0.8
                    metalness: 0
                    // No hay luz ambiente global: sin este piso de emisión una
                    // cara de canto a las luces queda negra y se pierde el
                    // color, que en esta vista es el dato.
                    emissiveFactor: Qt.vector3d(modelData.color.r * 0.45,
                                                modelData.color.g * 0.45,
                                                modelData.color.b * 0.45)
                    // Las caras se ven de los dos lados, como corresponde a un
                    // corte de la estructura.
                    cullMode: Material.NoCulling
                }
            }
        }

        // Contornos de las caras. El grosor lo fabrica contorno.vert, porque
        // ninguna API gráfica moderna rasteriza líneas de más de un píxel (ver
        // MallaContorno en mallas.py).
        Repeater3D {
            model: raiz.escena ? raiz.escena.caras : []
            Model {
                geometry: modelData.contorno
                visible: modelData.visible
                // Un material por contorno y no uno compartido: cada cara se
                // muestra y se oculta por separado. Qt compila el shader una
                // sola vez igual, porque la fuente es la misma.
                materials: CustomMaterial {
                    shadingMode: CustomMaterial.Unshaded
                    cullMode: Material.NoCulling
                    vertexShader: "contorno.vert"
                    fragmentShader: "contorno.frag"
                    property vector2d viewport: raiz.viewportEnPixeles
                    property real grosor: raiz.grosorContorno * Screen.devicePixelRatio
                    property real acercamiento: raiz.acercamientoContorno
                    property real opacidad: 1.0
                    // Va como vector y no como color a propósito: Qt convierte
                    // los uniformes de tipo color a espacio lineal, y en modo
                    // Unshaded lo que escribe el shader va derecho al
                    // framebuffer, que guarda sRGB. Así el gris sale gris.
                    property vector3d colorLinea: Qt.vector3d(raiz.colorContorno.r,
                                                              raiz.colorContorno.g,
                                                              raiz.colorContorno.b)
                }
            }
        }

        // El glow de la zona seleccionada: el trazo a inglete de su contorno,
        // en dos capas translúcidas de distinto ancho. Es sólo una decisión de
        // la vista: la escena no sabe que hay una selección.
        Repeater3D {
            model: raiz.escena ? raiz.escena.caras : []
            Model {
                geometry: modelData.trazo
                visible: modelData.visible && raiz.zonaSeleccionada === modelData
                materials: materialGlowCercano
            }
        }

        Repeater3D {
            model: raiz.escena ? raiz.escena.caras : []
            Model {
                geometry: modelData.trazo
                visible: modelData.visible && raiz.zonaSeleccionada === modelData
                materials: materialGlowLejano
            }
        }

        // Líneas sueltas: los soportes de las cubiertas aisladas. Mismo shader
        // que los contornos, porque el problema es el mismo: de un píxel de
        // ancho una diagonal sale punteada.
        Repeater3D {
            model: raiz.escena ? raiz.escena.lineas : []
            Model {
                geometry: modelData.malla
                visible: modelData.visible
                materials: CustomMaterial {
                    shadingMode: CustomMaterial.Unshaded
                    cullMode: Material.NoCulling
                    vertexShader: "contorno.vert"
                    fragmentShader: "contorno.frag"
                    property vector2d viewport: raiz.viewportEnPixeles
                    property real grosor: raiz.grosorContorno * Screen.devicePixelRatio
                    property real acercamiento: raiz.acercamientoContorno
                    property real opacidad: 1.0
                    property vector3d colorLinea: Qt.vector3d(modelData.color.r,
                                                              modelData.color.g,
                                                              modelData.color.b)
                }
            }
        }

        // Cuerpos con malla propia: el soporte del cartel
        Repeater3D {
            model: raiz.escena ? raiz.escena.solidos : []
            Model {
                geometry: modelData.malla
                visible: modelData.visible
                materials: PrincipledMaterial {
                    baseColor: modelData.color
                    roughness: 0.85
                    emissiveFactor: Qt.vector3d(0.35, 0.35, 0.35)
                    cullMode: Material.NoCulling
                }
            }
        }

        // Flechas de presión. La flecha son dos cuerpos: el vastago, un prisma
        // de largo 1 que se estira sólo en Y —la sección queda constante—, y
        // la punta, de tamaño fijo, apoyada donde el vastago termina. Así la
        // presión le cambia el largo a la flecha sin agrandarle punta ni grosor.
        Repeater3D {
            model: raiz.escena ? raiz.escena.presiones : []
            Node {
                id: nodoFlecha
                position: modelData.posicion
                rotation: modelData.rotacion
                visible: modelData.visible && modelData.largo > 0

                // El vastago mide 1 y su largo es el valor de la presión.
                readonly property vector3d escalaVastago: Qt.vector3d(
                    1, modelData.largo, 1)
                // La punta arranca donde termina el vastago.
                readonly property vector3d posicionPunta: Qt.vector3d(
                    0, modelData.largo, 0)

                // Un material por cuerpo y otro por las aristas, compartidos
                // por los cuatro Model: la flecha se muestra y se oculta entera,
                // junto con su nodo.
                PrincipledMaterial {
                    id: materialFlecha
                    baseColor: "#fafafa"
                    roughness: 0.5
                    emissiveFactor: Qt.vector3d(0.35, 0.35, 0.35)
                }

                CustomMaterial {
                    id: materialAristasFlecha
                    shadingMode: CustomMaterial.Unshaded
                    cullMode: Material.NoCulling
                    vertexShader: "contorno.vert"
                    fragmentShader: "contorno.frag"
                    property vector2d viewport: raiz.viewportEnPixeles
                    property real grosor: raiz.grosorAristasFlecha * Screen.devicePixelRatio
                    property real acercamiento: raiz.acercamientoContorno
                    property real opacidad: 1.0
                    // Va como vector y no como color a propósito: Qt convierte
                    // los uniformes de tipo color a espacio lineal, y en modo
                    // Unshaded lo que escribe el shader va derecho al
                    // framebuffer, que guarda sRGB. Así el gris sale gris.
                    property vector3d colorLinea: Qt.vector3d(raiz.colorContorno.r,
                                                              raiz.colorContorno.g,
                                                              raiz.colorContorno.b)
                }

                Model {
                    geometry: raiz.escena.mallaVastagoFlecha
                    scale: nodoFlecha.escalaVastago
                    materials: materialFlecha
                    // Pickable para poder seleccionar la zona tocando la
                    // flecha, no sólo su cara. `zona` apunta al actor dueño.
                    pickable: true
                    property var zona: modelData.actor
                    property bool esFlecha: true
                }

                Model {
                    geometry: raiz.escena.mallaPuntaFlecha
                    position: nodoFlecha.posicionPunta
                    materials: materialFlecha
                    pickable: true
                    property var zona: modelData.actor
                    property bool esFlecha: true
                }

                // El glow de la flecha seleccionada: la silueta del conjunto
                // (cantos del vastago, base y cantos de la punta), en dos
                // capas translúcidas que acompañan la escala y la orientación.
                Model {
                    geometry: raiz.escena.trazoVastagoFlecha
                    scale: nodoFlecha.escalaVastago
                    visible: raiz.zonaSeleccionada === modelData.actor
                    materials: materialGlowCercano
                }

                Model {
                    geometry: raiz.escena.trazoVastagoFlecha
                    scale: nodoFlecha.escalaVastago
                    visible: raiz.zonaSeleccionada === modelData.actor
                    materials: materialGlowLejano
                }

                Model {
                    geometry: raiz.escena.trazoPuntaFlecha
                    position: nodoFlecha.posicionPunta
                    visible: raiz.zonaSeleccionada === modelData.actor
                    materials: materialGlowCercano
                }

                Model {
                    geometry: raiz.escena.trazoPuntaFlecha
                    position: nodoFlecha.posicionPunta
                    visible: raiz.zonaSeleccionada === modelData.actor
                    materials: materialGlowLejano
                }

                // Las aristas, con el mismo shader de líneas gruesas de los
                // contornos de las caras. Todas las caras de la flecha son
                // planas, así que van todas: los cantos del vastago y de la
                // pirámide y los cuadrados que los unen. Con el perfil hecho
                // de aristas alcanza para separar la flecha del fondo.
                Model {
                    geometry: raiz.escena.aristasVastagoFlecha
                    scale: nodoFlecha.escalaVastago
                    materials: materialAristasFlecha
                }

                Model {
                    geometry: raiz.escena.aristasPuntaFlecha
                    position: nodoFlecha.posicionPunta
                    materials: materialAristasFlecha
                }
            }
        }

        // Vértices marcados por la herramienta de medición
        Repeater3D {
            model: medicion.puntos
            Model {
                source: "#Sphere"
                position: modelData
                // Las primitivas de Qt Quick 3D miden 100 unidades, de ahí el /100.
                scale: {
                    const s = raiz.radioEscena * 0.018 / 100
                    return Qt.vector3d(s, s, s)
                }
                materials: PrincipledMaterial {
                    baseColor: raiz.colorMedicion
                    lighting: PrincipledMaterial.NoLighting
                }
            }
        }
    }

    // --- Materiales del glow ------------------------------------------------

    // El halo de selección: dos pasadas del mismo shader de líneas gruesas de
    // los contornos, con más ancho y transparencia. Con el blending en alpha
    // el material va al pase transparente, así que cada capa se suma sobre lo
    // que ya está dibujado y el borde externo se difumina como un glow.
    CustomMaterial {
        id: materialGlowCercano
        shadingMode: CustomMaterial.Unshaded
        cullMode: Material.NoCulling
        vertexShader: "glow.vert"
        fragmentShader: "contorno.frag"
        property vector2d viewport: raiz.viewportEnPixeles
        property real grosor: raiz.grosorContorno * 1.8 * Screen.devicePixelRatio
        property real acercamiento: raiz.acercamientoGlow
        property real opacidad: 0.55
        sourceBlend: CustomMaterial.SrcAlpha
        destinationBlend: CustomMaterial.OneMinusSrcAlpha
        // Mismo criterio que los contornos: color como vector para que no lo
        // muevan a espacio lineal.
        property vector3d colorLinea: Qt.vector3d(raiz.colorGlow.r,
                                                  raiz.colorGlow.g,
                                                  raiz.colorGlow.b)
    }

    CustomMaterial {
        id: materialGlowLejano
        shadingMode: CustomMaterial.Unshaded
        cullMode: Material.NoCulling
        vertexShader: "glow.vert"
        fragmentShader: "contorno.frag"
        property vector2d viewport: raiz.viewportEnPixeles
        property real grosor: raiz.grosorContorno * 3.0 * Screen.devicePixelRatio
        property real acercamiento: raiz.acercamientoGlow * 1.8
        property real opacidad: 0.15
        sourceBlend: CustomMaterial.SrcAlpha
        destinationBlend: CustomMaterial.OneMinusSrcAlpha
        property vector3d colorLinea: Qt.vector3d(raiz.colorGlow.r,
                                                  raiz.colorGlow.g,
                                                  raiz.colorGlow.b)
    }

    // --- Interacción --------------------------------------------------------

    OrbitCameraController {
        anchors.fill: parent
        origin: origen
        camera: vista.camera
        automaticClipping: false
        // Mientras se mide, orbitar con el mismo botón haría que cada clic
        // moviera la cámara.
        mouseEnabled: !medicion.activa
    }

    QtObject {
        id: medicion
        property bool activa: false
        property var puntos: []

        // El vértice que hay debajo del cursor, o null si no hay ninguno cerca.
        property var candidato: null

        // Los dos extremos que hay que dibujar. Con un solo punto fijado, el
        // segundo es el candidato: así la regla sigue al cursor y el valor se
        // lee antes de hacer el segundo clic.
        readonly property var extremos: {
            if (puntos.length === 2)
                return puntos
            if (puntos.length === 1 && candidato)
                return [puntos[0], candidato]
            return []
        }

        readonly property real distancia: extremos.length === 2
            ? extremos[0].minus(extremos[1]).length() : 0
    }

    // El candidato se recalcula al mover el mouse para que lo que se ve marcado
    // sea exactamente lo que va a fijar el clic.
    HoverHandler {
        enabled: medicion.activa
        cursorShape: Qt.CrossCursor
        onPointChanged: {
            // Con el cursor afuera la posición que trae el punto no sirve, y
            // preguntar por ella marcaría un vértice cualquiera.
            medicion.candidato = hovered
                ? raiz.candidatoEn(point.position.x, point.position.y) : null
        }
    }

    TapHandler {
        enabled: medicion.activa
        gesturePolicy: TapHandler.WithinBounds
        onTapped: (punto) => {
            // Se recalcula en vez de usar el candidato del hover porque con
            // pantalla táctil no hay hover que lo haya dejado puesto.
            const vertice = raiz.candidatoEn(punto.position.x, punto.position.y)
            // Sin un vértice cerca el clic no hace nada: sólo se mide de
            // vértice a vértice.
            if (!vertice)
                return
            medicion.candidato = vertice
            const acumulados = medicion.puntos.length >= 2 ? [] : medicion.puntos.slice()
            acumulados.push(vertice)
            medicion.puntos = acumulados
        }
    }

    // La selección de zonas de presión: un toque sobre una cara o sobre su
    // flecha la selecciona; un toque afuera, o sobre la misma zona, la
    // suelta. Con DragThreshold un arrastre para orbitar no cuenta como
    // toque: sólo se selecciona cuando el dedo (o el mouse) no se movió.
    TapHandler {
        enabled: !medicion.activa
        acceptedButtons: Qt.LeftButton
        gesturePolicy: TapHandler.DragThreshold
        onTapped: (punto) => raiz.seleccionarEn(punto.position.x, punto.position.y)
    }

    Shortcut {
        sequences: ["Esc"]
        enabled: raiz.zonaSeleccionada !== null
        onActivated: raiz.deseleccionar()
    }

    // --- Superposición 2D ---------------------------------------------------

    // Etiquetas de presión. Se proyecta la posición 3D a la pantalla y se dibuja
    // un Text encima, así el texto siempre mira a la cámara y respeta el DPI.
    Repeater {
        model: raiz.escena ? raiz.escena.presiones : []

        Rectangle {
            // mapFrom3DScene es una función, no una propiedad: hay que leer la
            // transformación de la cámara y el tamaño de la vista para que QML
            // sepa que tiene que recalcular esto cuando algo se mueve.
            readonly property vector3d proyeccion: {
                const _pos = vista.camera.scenePosition
                const _rot = vista.camera.sceneRotation
                const _ancho = vista.width
                const _alto = vista.height
                const _z = vista.camera.z
                const _mag = camaraOrtografica.verticalMagnification
                return vista.mapFrom3DScene(modelData.posicionEtiqueta)
            }

            readonly property bool enPantalla: modelData.visible
                                              && modelData.largo > 0
                                              && proyeccion.z > 0

            // Las etiquetas van encima de la vista 3D, así que el buffer de
            // profundidad no las esconde: sin esto, la de una cara trasera flota
            // sobre la pared que la tapa y se lee como si fuera de esa pared. El
            // test es el mismo rayo que usa la medición: si antes de llegar a la
            // punta de la flecha pega contra algo, la etiqueta está atrás. Las
            // flechas son pickable para la selección, pero no cuentan: la
            // etiqueta vive junto a la punta de su propia flecha y el rayo la
            // encuentra antes que a la cara que pueda taparla de verdad.
            readonly property bool tapada: {
                if (!enPantalla)
                    return false
                const resultado = vista.pick(proyeccion.x, proyeccion.y)
                if (!resultado.objectHit)
                    return false
                if (resultado.objectHit.esFlecha === true)
                    return false
                return raiz.profundidad(resultado.scenePosition)
                       < raiz.profundidad(modelData.posicionEtiqueta) - raiz.toleranciaOclusion
            }

            visible: enPantalla && !tapada
            x: proyeccion.x - width / 2
            y: proyeccion.y - height
            width: texto.implicitWidth + 10
            height: texto.implicitHeight + 6
            color: raiz.colorFondo
            border.color: raiz.colorTinta
            border.width: 1

            // Tocar la etiqueta selecciona la zona, igual que tocar su cara o
            // su flecha: es el objetivo más fácil de acertar.
            TapHandler {
                enabled: !medicion.activa
                gesturePolicy: TapHandler.DragThreshold
                onTapped: raiz.seleccionarZona(modelData.actor)
            }

            Text {
                id: texto
                anchors.centerIn: parent
                text: modelData.texto
                color: raiz.colorTinta
                font.pointSize: modelData.tamanioTexto
            }
        }
    }

    // Título de la escena
    Text {
        x: 12
        y: 10
        width: parent.width - 24
        elide: Text.ElideRight
        text: raiz.escena ? raiz.escena.titulo : ""
        color: raiz.colorTinta
        font.pointSize: 11
    }

    // Barra con la escala de colores. Se dibuja como bandas sólidas: la escala
    // también es discreta y así no hay que crear GradientStop desde JavaScript.
    Row {
        x: 12
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 14
        spacing: 6
        visible: raiz.escena && raiz.escena.paradasEscala.length > 0

        Rectangle {
            width: 24
            height: 200
            border.color: raiz.colorTinta
            border.width: 1

            Column {
                anchors.fill: parent
                anchors.margins: 1
                Repeater {
                    model: raiz.escena ? raiz.escena.paradasEscala : []
                    Rectangle {
                        width: parent.width
                        height: parent.height / Math.max(1, raiz.escena.paradasEscala.length)
                        color: modelData.color
                    }
                }
            }
        }

        Item {
            width: 110
            height: 200
            Repeater {
                model: raiz.escena ? raiz.escena.etiquetasEscala : []
                Text {
                    readonly property int cantidad: raiz.escena.etiquetasEscala.length
                    y: (200 - implicitHeight) * index / Math.max(1, cantidad - 1)
                    text: modelData
                    color: raiz.colorTinta
                    font.pointSize: 9
                }
            }
        }
    }

    // Que la herramienta está activa. El color por sí solo no comunica, así que
    // el modo siempre va escrito; el valor de la medición vive sobre la regla.
    Text {
        anchors.right: parent.right
        anchors.rightMargin: 12
        anchors.top: parent.top
        anchors.topMargin: 10
        visible: medicion.activa
        text: "Modo Medición"
        color: raiz.colorMedicion
        font.pointSize: 9
        font.bold: true
    }

    // La regla: la línea de la medición proyectada a 2D, con topes en los
    // extremos y graduaciones, más la marca de lo que engancharía el clic.
    //
    // Va en 2D y no como malla en la escena porque una regla tiene que leerse
    // igual de lejos que de cerca —el ancho de la línea y el largo de las
    // marcas son píxeles, no metros— y porque nunca la tiene que tapar la
    // estructura que se está midiendo.
    Canvas {
        id: lienzoMedicion
        anchors.fill: parent
        visible: medicion.activa
        renderStrategy: Canvas.Immediate
        onPaint: {
            const ctx = getContext("2d")
            ctx.reset()
            if (!medicion.activa)
                return
            raiz.dibujarRegla(ctx)
            raiz.dibujarEnganche(ctx)
        }

        Connections {
            target: raiz
            function onProyeccionMedicionChanged() { lienzoMedicion.requestPaint() }
        }
        Connections {
            target: medicion
            function onPuntosChanged() { lienzoMedicion.requestPaint() }
            function onCandidatoChanged() { lienzoMedicion.requestPaint() }
        }
    }

    // El valor, sobre el medio de la regla. Es un Text y no texto de Canvas para
    // que respete la fuente y el DPI como el resto de las etiquetas.
    Rectangle {
        readonly property var proyeccion: raiz.proyeccionMedicion
        // Corrida sobre la perpendicular a la regla, del lado de arriba: si se
        // la corriera siempre en Y, una medición vertical la tendría encima.
        readonly property real corrimiento: proyeccion && proyeccion.ny > 0 ? -18 : 18

        visible: medicion.activa && proyeccion !== null
        x: proyeccion
           ? (proyeccion.a.x + proyeccion.b.x) / 2 + proyeccion.nx * corrimiento - width / 2
           : 0
        y: proyeccion
           ? (proyeccion.a.y + proyeccion.b.y) / 2 + proyeccion.ny * corrimiento - height / 2
           : 0
        width: textoMedicion.implicitWidth + 10
        height: textoMedicion.implicitHeight + 6
        color: raiz.colorFondo
        border.color: raiz.colorMedicion
        border.width: 1

        Text {
            id: textoMedicion
            anchors.centerIn: parent
            text: medicion.distancia.toFixed(2) + " m"
            color: raiz.colorMedicion
            font.pointSize: 9
            font.bold: true
        }
    }

    // El detalle del cálculo de la zona seleccionada, fijo arriba a la
    // derecha como el título. Se muestra al tocar una zona (con su glow) y
    // se cierra con Esc o tocando afuera; en modo medición se oculta para no
    // pisar su rótulo, que va en la misma esquina.
    //
    // El cuerpo son dos columnas de Text posicionadas a mano: las etiquetas a
    // la izquierda y los valores —que arrancan con el igual— en una segunda
    // columna corrida al ancho de la etiqueta más larga. Los anchos se miden
    // sobre los Texts mismos y no sobre el implicit de una Column: con
    // contenido que llega tarde, el de la Column no se recalcula; el de cada
    // Text, sí.
    Rectangle {
        id: panelDetalle

        readonly property var contenido: raiz.zonaSeleccionada
            ? raiz.zonaSeleccionada.detalle : null

        readonly property var filas: contenido ? contenido.filas : []

        // El alto de una fila: el que da la fuente de 12 puntos, que es la
        // de las dos columnas. Lo da TextMetrics para no amarrarlo a nada.
        readonly property real altoLinea: metricasFila.height

        readonly property real anchoEtiquetas: _ancho_de(columnaEtiquetas)
        readonly property real anchoValores: _ancho_de(columnaValores)
        readonly property real anchoContenido:
            8 + anchoEtiquetas + 6 + anchoValores

        // El ancho que aporta un grupo de Texts: el de su texto más ancho.
        function _ancho_de(columna) {
            var maximo = 0
            var hijos = columna.children
            for (var i = 0; i < hijos.length; i++) {
                var ancho = hijos[i].implicitWidth
                if (ancho !== undefined && ancho > maximo)
                    maximo = ancho
            }
            return maximo
        }

        visible: contenido !== null
                 && raiz.zonaSeleccionada.visible
                 && !medicion.activa
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.topMargin: 8
        anchors.rightMargin: 12
        // El título puede ser más ancho que las columnas ("Cubierta 0.00 a
        // 5.00 m"); si aun así no entra en la vista, corta en dos líneas.
        width: Math.min(
                   Math.max(tituloDetalle.implicitWidth, anchoContenido) + 16,
                   raiz.width - 24)
        height: columnaEtiquetas.y + filas.length * altoLinea + 8
        color: raiz.colorFondo
        border.color: raiz.colorTinta
        border.width: 2
        radius: 3

        TextMetrics {
            id: metricasFila
            font.pointSize: 12
            text: "Ag"
        }

        Text {
            id: tituloDetalle
            x: 8
            y: 6
            width: parent.width - 16
            wrapMode: Text.Wrap
            text: panelDetalle.contenido ? panelDetalle.contenido.titulo : ""
            color: raiz.colorTinta
            font.pointSize: 13
            font.bold: true
        }

        Item {
            id: columnaEtiquetas
            x: 8
            y: tituloDetalle.y + tituloDetalle.implicitHeight + 4

            Repeater {
                model: panelDetalle.filas
                Text {
                    y: index * panelDetalle.altoLinea
                    text: modelData[0]
                    visible: text !== ""
                    color: raiz.colorTinta
                    font.pointSize: 12
                }
            }
        }

        Item {
            id: columnaValores
            x: 8 + panelDetalle.anchoEtiquetas + 6
            y: columnaEtiquetas.y

            Repeater {
                model: panelDetalle.filas
                Text {
                    y: index * panelDetalle.altoLinea
                    text: modelData[1]
                    visible: text !== ""
                    color: raiz.colorTinta
                    font.pointSize: 12
                }
            }
        }
    }

    // --- Conexión con la escena de Python -----------------------------------

    Connections {
        target: raiz.escena
        ignoreUnknownSignals: true

        function onCamaraCambiada(datos) {
            origen.rotation = datos.rotacion
            origen.position = datos.centro
            camaraConica.z = datos.distancia
            camaraOrtografica.z = datos.distancia
            camaraOrtografica.horizontalMagnification = datos.magnificacion
            camaraOrtografica.verticalMagnification = datos.magnificacion
        }

        function onMedicionPedida(estado) {
            medicion.activa = estado
            if (!estado) {
                medicion.puntos = []
                medicion.candidato = null
            }
        }

        function onActoresCambiados() {
            reencuadrar.restart()
            // Si la escena se rearma, la zona que estaba tocada puede ya no
            // existir: la selección se suelta antes de que su actor quede
            // huérfano.
            raiz.deseleccionar()
        }
    }

    onWidthChanged: reencuadrar.restart()
    onHeightChanged: reencuadrar.restart()

    // Se espera a que la ventana pare de moverse: recalcular el encuadre en cada
    // píxel de un resize es trabajo tirado.
    Timer {
        id: reencuadrar
        interval: 120
        onTriggered: if (raiz.escena)
            raiz.escena.reencuadrar(Math.max(1, vista.width), Math.max(1, vista.height))
    }

    // Qué tan lejos está un punto medido sobre el eje de la cámara. Se compara
    // esto y no la distancia al ojo porque con la cámara ortográfica cada rayo
    // arranca en un punto distinto del plano de la cámara, y ahí las distancias
    // al ojo no son comparables entre sí.
    function profundidad(punto) {
        return punto.minus(vista.camera.scenePosition).dotProduct(vista.camera.forward)
    }

    // --- Medición -----------------------------------------------------------

    // Qué vértice tomaría un clic en (x, y) de la pantalla, o null si ahí no hay
    // ninguno a mano: sólo se mide de vértice a vértice, así que un punto suelto
    // sobre una cara no es candidato.
    //
    // El enganche se decide en pantalla y no en el espacio: el vértice más
    // cercano en metros puede estar del otro lado de la estructura y a media
    // pantalla de distancia, y engancharse ahí se lee como que la herramienta
    // falló.
    //
    // El rayo lo resuelve la escena y no View3D.pick(): pick no engancha las
    // caras que se ven de dorso, que acá son la mitad. Ver Escena3D.caraBajoRayo.
    function candidatoEn(x, y) {
        if (!raiz.escena)
            return null
        // mapTo3DScene toma la posición en la vista y, como z, la distancia
        // desde el plano de recorte cercano. Dos puntos del rayo dan su
        // dirección, con cámara cónica y con ortográfica por igual.
        const cerca = vista.mapTo3DScene(Qt.vector3d(x, y, 0))
        const lejos = vista.mapTo3DScene(Qt.vector3d(x, y, 1))
        const golpe = raiz.escena.caraBajoRayo(cerca, lejos.minus(cerca))
        if (!golpe)
            return null
        const p = vista.mapFrom3DScene(golpe.vertice)
        if (p.z <= 0 || Math.hypot(p.x - x, p.y - y) > raiz.radioEnganchePx)
            return null
        return golpe.vertice
    }

    // --- Selección ----------------------------------------------------------

    // Qué zona de presión hay bajo un toque, y qué hacer con ella: si es
    // nueva se selecciona, si ya estaba se suelta, y si no hay ninguna se
    // limpia.
    //
    // El pick de la vista alcanza para las caras y para las flechas, que son
    // los dos cuerpos pickable de la escena. Los actores de geometría no
    // llevan fila: su detalle es null y con eso se los descarta.
    function seleccionarEn(x, y) {
        const resultado = vista.pick(x, y)
        const zona = resultado.objectHit ? resultado.objectHit.zona : null
        if (!zona || zona.detalle === null) {
            raiz.deseleccionar()
            return
        }
        raiz.seleccionarZona(zona)
    }

    // Selecciona una zona (o la suelta si ya estaba seleccionada).
    function seleccionarZona(zona) {
        if (zona === raiz.zonaSeleccionada) {
            raiz.deseleccionar()
            return
        }
        raiz.zonaSeleccionada = zona
    }

    function deseleccionar() {
        raiz.zonaSeleccionada = null
    }

    // El paso "redondo" —1, 2 o 5 por una potencia de diez— que deja del orden
    // de diez graduaciones a lo largo de la regla.
    function pasoRegla(distancia) {
        const crudo = distancia / 10
        const potencia = Math.pow(10, Math.floor(Math.log(crudo) / Math.LN10))
        const normalizado = crudo / potencia
        const paso = normalizado <= 1 ? 1 : normalizado <= 2 ? 2
                   : normalizado <= 5 ? 5 : 10
        return paso * potencia
    }

    function dibujarRegla(ctx) {
        const proyeccion = raiz.proyeccionMedicion
        if (!proyeccion)
            return
        const a = proyeccion.a
        const b = proyeccion.b
        const largoPx = proyeccion.largoPx
        if (largoPx < 1)
            return
        // La perpendicular a la regla en pantalla: sobre ella van las marcas.
        const nx = proyeccion.nx
        const ny = proyeccion.ny

        ctx.strokeStyle = raiz.colorMedicion
        ctx.lineWidth = 2
        // El tramo que todavía sigue al cursor va punteado: así se distingue de
        // una medición ya fijada.
        if (ctx.setLineDash)
            ctx.setLineDash(medicion.puntos.length === 2 ? [] : [6, 4])
        ctx.beginPath()
        ctx.moveTo(a.x, a.y)
        ctx.lineTo(b.x, b.y)
        ctx.stroke()
        if (ctx.setLineDash)
            ctx.setLineDash([])

        // Topes de los extremos
        for (const extremo of [a, b]) {
            ctx.beginPath()
            ctx.moveTo(extremo.x - nx * 7, extremo.y - ny * 7)
            ctx.lineTo(extremo.x + nx * 7, extremo.y + ny * 7)
            ctx.stroke()
        }

        // Graduaciones. Cada una se proyecta por separado en vez de repartir el
        // largo en pantalla: con la cámara cónica el reparto no es uniforme.
        const distancia = medicion.distancia
        const paso = raiz.pasoRegla(distancia)
        if (distancia <= 0 || largoPx * paso / distancia < 7)
            return
        const extremos = medicion.extremos
        const delta = extremos[1].minus(extremos[0])
        ctx.lineWidth = 1.5
        for (let i = 1; i * paso < distancia; i++) {
            const q = vista.mapFrom3DScene(
                extremos[0].plus(delta.times(i * paso / distancia)))
            if (q.z <= 0)
                continue
            const largoMarca = i % 5 === 0 ? 7 : 4
            ctx.beginPath()
            ctx.moveTo(q.x, q.y)
            ctx.lineTo(q.x + nx * largoMarca, q.y + ny * largoMarca)
            ctx.stroke()
        }
    }

    // La marca del vértice que engancharía el clic: un cuadrado, que es el
    // símbolo habitual de enganche en CAD.
    function dibujarEnganche(ctx) {
        if (!medicion.candidato)
            return
        const p = vista.mapFrom3DScene(medicion.candidato)
        if (p.z <= 0)
            return
        ctx.strokeStyle = raiz.colorMedicion
        ctx.lineWidth = 2
        if (ctx.setLineDash)
            ctx.setLineDash([])
        ctx.strokeRect(p.x - 5, p.y - 5, 10, 10)
    }

    function acercar(factor) {
        if (raiz.conica)
            camaraConica.z /= factor
        else {
            camaraOrtografica.horizontalMagnification *= factor
            camaraOrtografica.verticalMagnification *= factor
        }
    }
}
