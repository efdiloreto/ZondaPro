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

    // Ancho de las líneas en píxeles lógicos. El shader las mide en píxeles de
    // dispositivo, así que abajo va multiplicado por el devicePixelRatio, y por
    // eso el viewport se calcula en las mismas unidades.
    readonly property real grosorContorno: 2
    // El borde de las flechas va más fino que los contornos: la flecha es un
    // cuerpo chico y ahí una línea de dos píxeles se la come.
    readonly property real grosorSilueta: 1
    readonly property vector2d viewportEnPixeles: Qt.vector2d(
        vista.width * Screen.devicePixelRatio, vista.height * Screen.devicePixelRatio)
    // Cuánto se acerca cada línea a la cámara, como fracción de su distancia,
    // para no pelear en Z con la cara a la que pertenece.
    readonly property real acercamientoContorno: 0.008

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
                // Los Model no son pickable por omisión, y sin esto no anda el
                // rayo que decide si una etiqueta de presión quedó tapada. La
                // medición no usa pick: ver candidatoEn().
                pickable: true
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

        // Flechas de presión
        Repeater3D {
            model: raiz.escena ? raiz.escena.presiones : []
            Node {
                id: nodoFlecha
                position: modelData.posicion
                rotation: modelData.rotacion
                visible: modelData.visible && modelData.largo > 0

                // La malla mide 1 y el largo es el valor de la presión.
                readonly property vector3d escala: Qt.vector3d(
                    modelData.largo, modelData.largo, modelData.largo)

                Model {
                    geometry: raiz.escena.mallaFlecha
                    scale: nodoFlecha.escala
                    materials: PrincipledMaterial {
                        baseColor: "#fafafa"
                        roughness: 0.5
                        emissiveFactor: Qt.vector3d(0.35, 0.35, 0.35)
                        // La malla usa COLOR para llevarle la normal suavizada al
                        // shader del borde, y los colores de vértice vienen
                        // prendidos: sin esto el material multiplicaría el blanco
                        // por una normal y la flecha saldría de cualquier color.
                        vertexColorsEnabled: false
                    }
                }

                // El borde. Casi blanca contra un fondo claro, la flecha se
                // pierde: lo que la separa del fondo es este contorno y no su
                // sombreado. Es la misma malla hinchada unos píxeles y dibujada
                // del revés, así asoma sólo por el canto (ver silueta.vert).
                Model {
                    geometry: raiz.escena.mallaFlecha
                    scale: nodoFlecha.escala
                    materials: CustomMaterial {
                        shadingMode: CustomMaterial.Unshaded
                        // Descartar las caras de frente deja la cara interna, que
                        // es la que la flecha de adelante tapa en todas partes
                        // menos en el borde que sobresale.
                        cullMode: Material.FrontFaceCulling
                        vertexShader: "silueta.vert"
                        // El fragmento es el mismo que el de las líneas: un color
                        // plano, sin iluminación (ver contorno.frag).
                        fragmentShader: "contorno.frag"
                        property vector2d viewport: raiz.viewportEnPixeles
                        property real grosor: raiz.grosorSilueta * Screen.devicePixelRatio
                        property vector3d colorLinea: Qt.vector3d(raiz.colorContorno.r,
                                                                  raiz.colorContorno.g,
                                                                  raiz.colorContorno.b)
                    }
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
            // punta de la flecha pega contra algo, la etiqueta está atrás. Sólo
            // las caras son pickable, que es justo lo que tapa.
            readonly property bool tapada: {
                if (!enPantalla)
                    return false
                const resultado = vista.pick(proyeccion.x, proyeccion.y)
                if (!resultado.objectHit)
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
