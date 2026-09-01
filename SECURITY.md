# Política de seguridad

## Versiones con soporte

Se dan por soportadas las correcciones sobre la última versión publicada. Zonda
es una aplicación de escritorio y no se mantienen ramas de versiones anteriores:
la vía de corrección es siempre actualizar a la última
[release](https://github.com/efdiloreto/ZondaPro/releases/latest).

| Versión | Soportada          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reportar una vulnerabilidad

**No abras un issue público.** Reportala en privado por
[GitHub Security Advisories](https://github.com/efdiloreto/ZondaPro/security/advisories/new),
o escribiendo a **efdiloreto@gmail.com**.

Incluí, en lo posible:

- La versión de Zonda y el sistema operativo.
- Los pasos para reproducirlo, y el archivo que lo dispara si hay uno.
- El impacto que le ves.

Vas a tener una primera respuesta dentro de los 7 días. Si el reporte se
confirma, se trabaja la corrección en privado y se publica en una release, con
el crédito correspondiente salvo que preferís mantenerte anónimo.

## Qué cuenta como vulnerabilidad acá

Zonda es una aplicación de escritorio sin servidor ni cuentas de usuario, así
que la superficie es acotada. Interesan sobre todo:

- **Archivos `.zda` maliciosos:** que abrir un archivo de proyecto pueda
  ejecutar código o escribir fuera del directorio elegido.
- **Generación de reportes:** que el contenido de un proyecto pueda inyectar
  algo en la plantilla Jinja2 o en la invocación de pandoc.
- **Instaladores y empaquetado:** problemas de integridad o de permisos en el
  `.msi`, el `.dmg` o el `.flatpak`.
- **Dependencias:** vulnerabilidades conocidas en las librerías que Zonda
  distribuye dentro de sus instaladores.

**Un resultado de cálculo equivocado no es una vulnerabilidad, pero sí es un
error grave:** reportalo como issue con la plantilla "Resultado de cálculo
dudoso", que es pública y así lo puede ver cualquiera que haya usado ese
resultado.
