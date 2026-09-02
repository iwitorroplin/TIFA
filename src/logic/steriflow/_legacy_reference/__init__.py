"""Steriflow: lectura de informes PDF de ciclo.

Paquete deliberadamente autocontenido y sin relacion con el de Ferlo. Un ciclo
Steriflow NO es una `core.models.Series` con fases detectadas por el analisis:
es un informe que la maquina ya trae resumido fase a fase, y por ahora el
sistema solo lo lee y lo muestra -sin letalidad, sin cobertura, sin veredicto y
sin programa asignado-.

Lo unico que comparte con Ferlo es la carcasa: la conexion a la base de datos,
el fichero de configuracion y la ventana principal. Sus tablas
(`steriflow_cycle`, `steriflow_phase`) no tienen ninguna clave ajena contra las
de Ferlo.
"""
