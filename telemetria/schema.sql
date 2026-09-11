-- Copyright (c) 2018-2026, Eduardo Di Loreto <efdiloreto@gmail.com>
--
-- This file is part of Zonda.
--
-- Zonda is free software: you can redistribute it and/or modify
-- it under the terms of the GNU General Public License as published by
-- the Free Software Foundation, either version 3 of the License, or
-- (at your option) any later version.
--
-- Zonda is distributed in the hope that it will be useful,
-- but WITHOUT ANY WARRANTY; without even the implied warranty of
-- MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
-- GNU General Public License for more details.
--
-- You should have received a copy of the GNU General Public License
-- along with Zonda.  If not, see <https://www.gnu.org/licenses/>.

-- Una fila por sesión iniciada de Zonda: cada ping del arranque inserta una.
-- Se aplica con:
--   npx wrangler d1 execute zonda-telemetria --remote --file=schema.sql

CREATE TABLE IF NOT EXISTS pings (
  -- La fecha UTC de la sesión, en columnas separadas para que las consultas
  -- de agregados por día no dependan de substr() sobre el timestamp.
  dia TEXT NOT NULL,
  fecha TEXT NOT NULL,
  -- El UUID anónimo que Zonda genera una vez y guarda en QSettings. No está
  -- atado a ninguna cuenta ni a ninguna persona.
  id TEXT NOT NULL,
  version TEXT NOT NULL,
  so TEXT NOT NULL,
  -- El código de país ISO que agrega Cloudflare a partir de la IP. Puede
  -- venir vacío.
  pais TEXT,
  -- El hash truncado de IP + fecha + sal secreta. Permite contar IPs únicas
  -- por día; la IP cruda nunca se guarda, y el hash de otro día no se puede
  -- cruzar con éste.
  ip_dia TEXT
);

CREATE INDEX IF NOT EXISTS idx_pings_dia ON pings (dia);
