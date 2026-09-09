"""Puentes entre hilos de trabajo y la interfaz: QObject con Signal que jamás
pintan nada (por eso no viven en ui/) ni tocan lógica de dominio directamente
desde el hilo de trabajo (por eso no viven en logic/, que no importa Qt).

Solo emiten señales; Qt las entrega ya en el hilo de la interfaz, que es
quien decide qué hacer con el resultado. Mismo patrón que
`src/modules/steriflow/tasks/`.
"""
