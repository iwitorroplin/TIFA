# TIFA
description: Thermal Integration & F₀ Analysis

---

# Structure

- assets: componentes visuales
- config: configuracion de la app y los modulos 
- logs: logs de la app y de los modulos
- data: only for develop, sera la ruta default para los backup y lo que sea necesario
- src: codigo fuente

**future features**
- feature_1: base de datos sqlite para guardar los datos
- feature_2: server para visualizar datos de la db
- feature_3: adicion de algunos datos aparte
- feature_4: unir con mc33 o almenos facilitar algunos procesos


# assets: .ico and .svg

**icons** : only file .ico
**images** : only file .svg

# config: .yaml

config app:
- appConfig.yaml
- appConfig.default.yaml

config module steriflow:
- steriflowConfig.yaml
- steriflowConfig.default.yaml

config module ferlo:
- ferloConfig.yaml
- ferloConfig.default.yaml

config module macona:
- maconaConfig.yaml
- maconaConfig.default.yaml

config module pasteurization:
- pasteurizationConfig.yaml
- pasteurizationConfig.default.yaml
