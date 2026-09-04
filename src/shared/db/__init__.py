"""Base de datos compartida de TIFA.

Un único fichero SQLite para Ferlo, Steriflow, Macona y Pasteurización. Cada
módulo define sus propias tablas en su propio paquete (sin claves ajenas
cruzadas entre módulos) y las registra en `db.schema.ensure_schema`; este
paquete solo aporta la conexión y ese punto de registro común.
"""
