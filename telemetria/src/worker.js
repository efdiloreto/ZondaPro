/*
 * Copyright (c) 2018-2026, Eduardo Di Loreto <efdiloreto@gmail.com>
 *
 * This file is part of Zonda.
 *
 * Zonda is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Zonda is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Zonda.  If not, see <https://www.gnu.org/licenses/>.
 */

/**
 * El receptor de la telemetría de Zonda.
 *
 * Dos caminos y nada más:
 *
 * - `POST /ping`: lo manda Zonda una vez por arranque, con el identificador
 *   anónimo de la instalación, la versión y el sistema operativo. El Worker
 *   le agrega el país (que Cloudflare deduce de la IP) y el hash diario de la
 *   IP, y guarda una fila en D1. La IP cruda nunca se guarda.
 * - `GET /stats`: las métricas agregadas, para el que mantiene el proyecto.
 *   Exige el encabezado `X-Stats-Token` con el valor del secreto `TOKEN`.
 *
 * Todo falla en silencio del lado de Zonda, así que acá tampoco hace falta
 * ninguna sofisticación: lo que no se pueda validar se rechaza y listo.
 */

const LARGO_ID = 36;
const LARGO_TEXTO = 20;
const CARACTERES_HASH = 16;
const DIAS_EN_ESTADISTICAS = 90;

/**
 * Devuelve el valor sólo si es una cadena no vacía de largo razonable.
 */
function validarTexto(valor, maximo) {
  if (typeof valor !== "string" || valor.length === 0 || valor.length > maximo) {
    return null;
  }
  return valor;
}

/**
 * El identificador anónimo del pedido para contar IPs únicas.
 *
 * Mezcla la IP con la fecha y una sal secreta, y se queda con un pedazo del
 * hash: alcanza para distinguir redes dentro de un día, y no alcanza para
 * reidentificar a nadie ni para cruzar días. Si no hay sal configurada
 * devuelve cadena vacía: se pierde esa métrica, nunca se guarda la IP.
 */
async function ipDelDia(ip, dia, sal) {
  if (!ip || !sal) {
    return "";
  }
  const datos = new TextEncoder().encode(`${sal}:${ip}:${dia}`);
  const hash = await crypto.subtle.digest("SHA-256", datos);
  const hexadecimal = Array.from(new Uint8Array(hash))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
  return hexadecimal.slice(0, CARACTERES_HASH);
}

/**
 * Guarda un ping. Responde 204 aunque la fila ya exista: cada arranque es
 * una sesión y todas cuentan.
 */
async function recibirPing(request, env) {
  if (!env.DB) {
    return new Response("Base de datos no configurada\n", { status: 500 });
  }

  let datos;
  try {
    datos = await request.json();
  } catch {
    return new Response("Cuerpo inválido\n", { status: 400 });
  }

  const id = validarTexto(datos?.id, LARGO_ID);
  const version = validarTexto(datos?.version, LARGO_TEXTO);
  const so = validarTexto(datos?.so, LARGO_TEXTO);
  if (!id || !version || !so) {
    return new Response("Payload inválido\n", { status: 400 });
  }

  const ahora = new Date();
  const dia = ahora.toISOString().slice(0, 10);
  const pais = typeof request.cf?.country === "string" ? request.cf.country : "";
  const ip = request.headers.get("CF-Connecting-IP") ?? "";
  const ipDia = await ipDelDia(ip, dia, env.SAL_IP);

  await env.DB.prepare(
    "INSERT INTO pings (dia, fecha, id, version, so, pais, ip_dia) VALUES (?, ?, ?, ?, ?, ?, ?)"
  )
    .bind(dia, ahora.toISOString(), id, version, so, pais, ipDia)
    .run();

  return new Response(null, { status: 204 });
}

/**
 * Las métricas agregadas. Nada por instalación: los únicos datos crudos que
 * hay en la base ya son anónimos, pero acá ni siquiera viajan.
 */
async function estadisticas(request, env) {
  if (!env.DB) {
    return new Response("Base de datos no configurada\n", { status: 500 });
  }
  if (!env.TOKEN || request.headers.get("X-Stats-Token") !== env.TOKEN) {
    return new Response("No autorizado\n", { status: 401 });
  }

  const resultados = await env.DB.batch([
    env.DB.prepare("SELECT COUNT(*) AS valor FROM pings"),
    env.DB.prepare("SELECT COUNT(DISTINCT id) AS valor FROM pings"),
    env.DB.prepare(
      `SELECT dia,
              COUNT(*) AS sesiones,
              COUNT(DISTINCT id) AS instalaciones,
              COUNT(DISTINCT NULLIF(ip_dia, '')) AS ips
       FROM pings GROUP BY dia ORDER BY dia DESC LIMIT ${DIAS_EN_ESTADISTICAS}`
    ),
    env.DB.prepare(
      "SELECT version, COUNT(DISTINCT id) AS instalaciones FROM pings GROUP BY version ORDER BY instalaciones DESC"
    ),
    env.DB.prepare(
      "SELECT so, COUNT(DISTINCT id) AS instalaciones FROM pings GROUP BY so ORDER BY instalaciones DESC"
    ),
    env.DB.prepare(
      "SELECT pais, COUNT(DISTINCT id) AS instalaciones FROM pings WHERE pais != '' GROUP BY pais ORDER BY instalaciones DESC"
    ),
  ]);

  const [sesiones, instalaciones, porDia, porVersion, porSo, porPais] =
    resultados.map((resultado) => resultado.results);

  return Response.json({
    sesiones: sesiones[0]?.valor ?? 0,
    instalaciones: instalaciones[0]?.valor ?? 0,
    por_dia: porDia,
    por_version: porVersion,
    por_so: porSo,
    por_pais: porPais,
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "POST" && url.pathname === "/ping") {
      return recibirPing(request, env);
    }
    if (request.method === "GET" && url.pathname === "/stats") {
      return estadisticas(request, env);
    }
    return new Response("No encontrado\n", { status: 404 });
  },
};
