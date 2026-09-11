# Telemetría de Zonda

El receptor de los pings anónimos que manda Zonda al arrancar. Es un
[Cloudflare Worker](https://developers.cloudflare.com/workers/)
con una base [D1](https://developers.cloudflare.com/d1/) que corre dentro del
free tier de Cloudflare.

Del lado de Zonda el modelo es opt-out a lo [Homebrew](https://docs.brew.sh/Analytics):
los pings salen por defecto, sin preguntar nada; el usuario los desactiva en
**Configuración → Telemetría** o con `ZONDA_SIN_TELEMETRIA=1`. El disclosure
está en el README y en "Acerca de".

## Estado del despliegue

El receptor de este repositorio ya está desplegado en
`https://zonda-telemetria.efdiloreto.workers.dev` (Worker `zonda-telemetria`,
base D1 `zonda-telemetria`, id `3dfdc97a-9ac9-4e4c-936d-a67bb466ef5c`), con
los secretos `TOKEN` y `SAL_IP` cargados. Para actualizar el código alcanza
con `wrangler deploy` desde esta carpeta, una vez autenticado.

## Qué se guarda

Una fila por sesión iniciada, con:

| Campo | De dónde sale |
| --- | --- |
| `dia`, `fecha` | El reloj del servidor (UTC) |
| `id` | El UUID anónimo que Zonda genera una vez y guarda en `QSettings` |
| `version` | La versión de Zonda |
| `so` | `windows`, `darwin` o `linux` |
| `pais` | Código ISO que Cloudflare deduce de la IP |
| `ip_dia` | SHA-256 truncado de IP + fecha + sal secreta |

La IP cruda **nunca se guarda**, y el hash diario no se puede cruzar entre
días. Nunca se reciben datos personales ni del contenido de los proyectos.

## Despliegue

Requiere [Node.js](https://nodejs.org/) con `npm`. Desde esta carpeta:

```bash
npm install -g wrangler     # o npx wrangler ...
wrangler login              # abre el navegador para autorizar la cuenta
wrangler d1 create zonda-telemetria
# Copiar el database_id que devuelve en wrangler.jsonc
wrangler d1 execute zonda-telemetria --remote --file=schema.sql
wrangler secret put TOKEN   # una cadena larga al azar, para leer /stats
wrangler secret put SAL_IP  # otra cadena larga al azar, para hashear la IP
wrangler deploy
```

Al terminar, `deploy` imprime la URL del Worker
(`https://zonda-telemetria.<cuenta>.workers.dev`). Copiarla en
`python/zonda/__acercade__.py`, constante `__telemetria__`: mientras esté
vacía, la telemetría queda desactivada y no sale ningún ping. Éste es el
camino para un fork que quiera su propio receptor.

## Consultar las métricas

```bash
curl -H "X-Stats-Token: <TOKEN>" https://zonda-telemetria.<cuenta>.workers.dev/stats
```

Devuelve JSON con: `sesiones` y `instalaciones` totales, `por_dia` (sesiones,
instalaciones activas e IPs únicas de los últimos 90 días), y los desgloses
`por_version`, `por_so` y `por_pais`.
