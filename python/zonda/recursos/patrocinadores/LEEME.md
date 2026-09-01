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
      "web": "https://estudiofernandez.com.ar",
      "logo": "estudio-fernandez.png",
      "fundador": true
    }
  ]
}
```

| Campo | Obligatorio | Qué es |
| --- | --- | --- |
| `nombre` | sí | El nombre del estudio o de la persona |
| `nivel` | sí | `oro`, `plata` o `bronce` |
| `web` | no | A dónde lleva el logo. Sin esto, no linkea |
| `logo` | no | El archivo, en este mismo directorio. Sin esto, se muestra el nombre |
| `fundador` | no | El distintivo de los primeros. Se otorga una vez y no vence |

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
