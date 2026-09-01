# Patrocinadores

La lista que Zonda muestra en la pantalla de bienvenida y en el diálogo de
apoyo. Viaja empaquetada con cada versión: sumar a alguien es copiar su logo
acá, agregarle una entrada a `patrocinadores.json` y publicar una release.

## Agregar un patrocinador

```json
{
  "patrocinadores": [
    {
      "nombre": "Estudio Fernández",
      "nivel": "oro",
      "logo": "estudio-fernandez.png",
      "web": "https://estudiofernandez.com.ar",
      "contacto": "mailto:info@estudiofernandez.com.ar",
      "rubro": "Cálculo estructural y dirección de obra",
      "ciudad": "Rosario, Santa Fe",
      "descripcion": "Dos o tres oraciones que escriben ellos.",
      "desde": "2026",
      "fundador": true
    }
  ]
}
```

| Campo | Obligatorio | Qué es |
| --- | --- | --- |
| `nombre` | sí | El nombre del estudio o de la persona |
| `nivel` | sí | `oro`, `plata` o `bronce` |
| `logo` | no | El archivo, en este mismo directorio. Sin esto, se muestra el nombre |
| `web` | no | A dónde lleva el logo. Sin esto, no linkea |
| `contacto` | no | Un segundo enlace, normalmente un `mailto:`. Sólo en el perfil de oro |
| `rubro` | no | A qué se dedican, en una línea. Sólo en el perfil de oro |
| `ciudad` | no | Dónde están. Sólo en el perfil de oro |
| `descripcion` | no | El párrafo que escriben ellos. Sólo en el perfil de oro |
| `desde` | no | Desde qué año patrocinan |
| `fundador` | no | El distintivo de los primeros. Se otorga una vez y no vence |

**Los enlaces sólo pueden ser `http`, `https` o `mailto`.** Cualquier otra cosa
—un `file://`, por ejemplo— se descarta al leer: estos enlaces terminan en
`QDesktopServices.openUrl()`, que le pide al sistema operativo que abra lo que
sea, y eso incluiría archivos de la máquina de quien usa el programa.

Qué se ve de cada nivel:

- **Oro**: logo primero en la columna; al tocarlo se abre su ventana con todos
  los campos que tenga cargados.
- **Plata**: logo debajo; al tocarlo se abre su `web`.
- **Bronce**: no aparece en la columna, sólo en Agradecimientos.

Una entrada mal escrita —sin nombre, con un nivel que no existe, con un logo
que no está— se ignora sola. Nunca hace fallar al programa.

## Los logos

- **PNG con fondo transparente**, o SVG.
- Al **doble de la altura final** con la que se muestran, para que se vean
  bien en pantallas HiDPI: 68 px de alto para oro, 52 px para plata.
- **Sobre fondo gris claro**: la sección de la bienvenida es `#e6e6e6`. Un
  logo blanco, o con fondo blanco recortado, desaparece ahí. Si el que te
  mandan es para fondo oscuro, pedí la variante para fondo claro.
- Nombre de archivo en minúsculas y con guiones: `estudio-fernandez.png`.

## Licencia

**Los logos de este directorio no están cubiertos por la licencia de Zonda.**
Cada uno es marca de su titular y se incluye con su permiso, al solo efecto de
reconocer su apoyo al proyecto. Quien haga un fork tiene que sacarlos, salvo
que cuente con ese permiso.

## `colaboradores.json`

Quienes aportan tiempo al proyecto, para la ventana de Agradecimientos. Se
mantiene a mano y no se saca del historial de git a propósito: los aportes que
más importan —revisar un cálculo contra el Reglamento, reportar un resultado
dudoso, probar un instalador— no dejan ningún commit.

```json
{
  "colaboradores": [
    { "nombre": "Natalia Alvarado", "aporte": "revisión reglamentaria" },
    { "nombre": "Ing. Marta Ruiz" }
  ]
}
```

`aporte` es opcional; sin él se muestra sólo el nombre.
