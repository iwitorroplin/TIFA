"""Carga y guardado de la configuración de cada módulo.

Ferlo, Steriflow, Macona y Pasteurización no comparten ni un solo campo de
configuración entre sí, así que cada uno tiene su propio YAML en vez de
compartir uno (a diferencia de la base de datos, donde sí conviene un único
fichero): `appConfig/<modulo>Config.yaml` es el que edita la app y no se
versiona -cada instalación tiene rutas e IPs propias-, y
`appConfigDefault/<modulo>Config.default.yaml` sí se versiona y es el que se
copia la primera vez que `<modulo>Config.yaml` todavía no existe. El módulo
"app" (nombre, tema, formato de fecha) usa exactamente el mismo esquema.
"""
