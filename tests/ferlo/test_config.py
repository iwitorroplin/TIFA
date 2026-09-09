"""Fase 3 (D7): `logic/config.py` lee y escribe
`config/appConfig/ferloConfig.yaml`, con el default versionado en
`config/appConfigDefault/ferloConfig.default.yaml`.

Toca el fichero real de configuracion de la instalacion -no hay forma de
probar `ensure_config_file`/`load_config`/`save_config` sin hacerlo, y
`config/appConfig/` esta gitignored precisamente porque es estado local-, asi
que cada test lo deja como lo encontro.
"""

from __future__ import annotations

import pytest

from src.modules.ferlo.logic.config import (
    DEFAULT_SETTINGS,
    SETTINGS_SCHEMA,
    config_path,
    load_settings,
    save_settings,
    validate_settings,
)


@pytest.fixture(autouse=True)
def _sin_dejar_rastro():
    path = config_path()
    existia_antes = path.exists()
    contenido_antes = path.read_bytes() if existia_antes else None
    yield
    if existia_antes:
        path.write_bytes(contenido_antes)
    else:
        path.unlink(missing_ok=True)


def test_primer_arranque_crea_el_yaml_con_los_defaults():
    config_path().unlink(missing_ok=True)
    settings = load_settings()
    assert config_path().exists()
    assert settings.acceptance["acceptance_tolerance_c"] == 0.50
    assert settings.sterilization_phase["exit_debounce_s"] == 60
    assert settings.criteria_snapshot()["acceptance_tolerance_c"] == 0.50


def test_guardar_y_releer_conserva_el_cambio():
    settings = load_settings()
    settings.acceptance["acceptance_tolerance_c"] = 0.75
    save_settings(settings)

    releido = load_settings()
    assert releido.acceptance["acceptance_tolerance_c"] == 0.75
    # el resto de secciones no se ha movido
    assert releido.cycle_detection == DEFAULT_SETTINGS["cycle_detection"]


def test_un_yaml_incompleto_se_completa_con_los_defaults():
    """Anadir un umbral nuevo en el codigo no debe obligar a borrar el yaml
    de una instalacion existente (ver `_merge_defaults`)."""
    from src.shared.config.manager import save_config

    save_config("ferlo", {"acceptance": {"acceptance_tolerance_c": 0.10}})
    settings = load_settings()
    assert settings.acceptance["acceptance_tolerance_c"] == 0.10
    assert settings.sterilization_phase == DEFAULT_SETTINGS["sterilization_phase"]


def test_esquema_de_campos_cubre_todo_default_settings():
    """Cada umbral numerico de DEFAULT_SETTINGS tiene su FieldSpec: si se
    anade uno sin declararlo en SETTINGS_SCHEMA, la pestana de ajustes
    (Fase 4) no podria dibujarlo. `paths` queda fuera a proposito: son rutas
    de carpeta (D1), no umbrales -se editan como tal, no con un spinbox-."""
    declarados = {(f.section, f.key) for _, f in
                  [(s, f) for s in SETTINGS_SCHEMA for f in s.fields]}
    for seccion, campos in DEFAULT_SETTINGS.items():
        if seccion == "paths":
            continue
        for clave in campos:
            assert (seccion, clave) in declarados, f"falta FieldSpec para {seccion}.{clave}"


def test_paths_por_defecto():
    from src.modules.ferlo.logic.config import default_settings
    s = default_settings()
    assert s.paths["entrada"] == "data/ferlo/entrada"
    assert s.paths["archivo"] == "data/ferlo/archivo"
    assert s.entrada_dir.name == "entrada"
    assert s.archivo_dir.name == "archivo"


def test_valor_fuera_de_rango_avisa_sin_bloquear():
    avisos = validate_settings({"acceptance": {"acceptance_tolerance_c": 999.0}})
    assert avisos
    assert "999" in avisos[0]
