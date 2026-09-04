"""Acceso a `steriflow_backup_file` (ledger de PDF ya respaldados) y
`steriflow_cycle` (ciclos con su dato de esterilización)."""

from __future__ import annotations

import datetime as dt
import sqlite3

from src.shared.db.iso import from_iso, to_iso
from src.logic.steriflow.sterilization.models import SterilizationCycle


def record_backup_file(conn: sqlite3.Connection, autoclave: str, filename: str, sha256: str) -> None:
    """Deja constancia de que este PDF ya completó el backup a servidor.

    INSERT OR IGNORE: si el fichero ya estaba registrado no se toca nada -es
    la foto del primer backup, no hace falta actualizarla en cada reejecución-.
    """
    conn.execute(
        "INSERT OR IGNORE INTO steriflow_backup_file"
        " (autoclave, filename, sha256, backed_up_at) VALUES (?, ?, ?, ?)",
        (autoclave, filename, sha256, to_iso(dt.datetime.now())),
    )


def pending_extraction(conn: sqlite3.Connection, autoclave: str) -> list[sqlite3.Row]:
    """PDF ya respaldados a los que aún no se les ha intentado leer el contenido."""
    return conn.execute(
        "SELECT id, filename FROM steriflow_backup_file"
        " WHERE autoclave = ? AND extracted_at IS NULL"
        " ORDER BY filename",
        (autoclave,),
    ).fetchall()


def mark_extracted(conn: sqlite3.Connection, backup_file_id: int, *, error: str | None = None) -> None:
    conn.execute(
        "UPDATE steriflow_backup_file SET extracted_at = ?, extraction_error = ? WHERE id = ?",
        (to_iso(dt.datetime.now()), error, backup_file_id),
    )


def save_cycle(conn: sqlite3.Connection, cycle: SterilizationCycle) -> tuple[int, bool]:
    """Guarda o actualiza un ciclo. Devuelve (id, era_nuevo).

    Reimportar el mismo ciclo lo actualiza en vez de duplicarlo (UNIQUE sobre
    autoclave_code + started_at).
    """
    fila = conn.execute(
        "SELECT id FROM steriflow_cycle WHERE autoclave_code = ? AND started_at = ?",
        (cycle.autoclave_code, to_iso(cycle.started_at)),
    ).fetchone()
    era_nuevo = fila is None

    conn.execute(
        "INSERT INTO steriflow_cycle("
        " autoclave_code, started_at, cycle_number, product, batch, cycles_counter,"
        " reported_at, source_filename, source_sha256,"
        " sterilization_start_ts, sterilization_end_ts, sterilization_duration_s,"
        " sterilization_temp_end_c, sterilization_temp_mean_c,"
        " sterilization_temp_min_c, sterilization_temp_max_c,"
        " needs_review, review_notes, imported_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(autoclave_code, started_at) DO UPDATE SET "
        " cycle_number=excluded.cycle_number, product=excluded.product,"
        " batch=excluded.batch, cycles_counter=excluded.cycles_counter,"
        " reported_at=excluded.reported_at, source_filename=excluded.source_filename,"
        " source_sha256=excluded.source_sha256,"
        " sterilization_start_ts=excluded.sterilization_start_ts,"
        " sterilization_end_ts=excluded.sterilization_end_ts,"
        " sterilization_duration_s=excluded.sterilization_duration_s,"
        " sterilization_temp_end_c=excluded.sterilization_temp_end_c,"
        " sterilization_temp_mean_c=excluded.sterilization_temp_mean_c,"
        " sterilization_temp_min_c=excluded.sterilization_temp_min_c,"
        " sterilization_temp_max_c=excluded.sterilization_temp_max_c,"
        " needs_review=excluded.needs_review, review_notes=excluded.review_notes,"
        " imported_at=excluded.imported_at",
        (
            cycle.autoclave_code, to_iso(cycle.started_at), cycle.cycle_number,
            cycle.product, cycle.batch, cycle.cycles_counter,
            to_iso(cycle.reported_at), cycle.source_filename, cycle.source_sha256,
            to_iso(cycle.sterilization_start_ts), to_iso(cycle.sterilization_end_ts),
            cycle.sterilization_duration_s,
            cycle.sterilization_temp_end_c, cycle.sterilization_temp_mean_c,
            cycle.sterilization_temp_min_c, cycle.sterilization_temp_max_c,
            int(cycle.needs_review), cycle.review_notes or None,
            to_iso(dt.datetime.now()),
        ),
    )
    cycle_id = conn.execute(
        "SELECT id FROM steriflow_cycle WHERE autoclave_code = ? AND started_at = ?",
        (cycle.autoclave_code, to_iso(cycle.started_at)),
    ).fetchone()["id"]
    return cycle_id, era_nuevo


def list_cycles(
    conn: sqlite3.Connection,
    *,
    autoclave_code: int | None = None,
    product_query: str | None = None,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    needs_review: bool | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[SterilizationCycle]:
    """Ciclos guardados, del más reciente al más antiguo.

    `limit`/`offset` pagina en la propia consulta: con miles de ciclos
    guardados, cargarlos todos en memoria para pintar una tabla que solo
    muestra una página a la vez es el cuello de botella, no la base de datos.
    """
    where, params = _build_filters(
        autoclave_code=autoclave_code, product_query=product_query,
        date_from=date_from, date_to=date_to, needs_review=needs_review,
    )
    sql = f"SELECT * FROM steriflow_cycle{where} ORDER BY started_at DESC"
    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        params = params + [limit, offset]

    return [_row_to_cycle(fila) for fila in conn.execute(sql, params).fetchall()]


def count_cycles(
    conn: sqlite3.Connection,
    *,
    autoclave_code: int | None = None,
    product_query: str | None = None,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    needs_review: bool | None = None,
) -> int:
    """Cuántos ciclos cumplen el filtro, para saber cuántas páginas hay."""
    where, params = _build_filters(
        autoclave_code=autoclave_code, product_query=product_query,
        date_from=date_from, date_to=date_to, needs_review=needs_review,
    )
    return conn.execute(f"SELECT COUNT(*) AS n FROM steriflow_cycle{where}", params).fetchone()["n"]


def _build_filters(
    *,
    autoclave_code: int | None,
    product_query: str | None,
    date_from: dt.date | None,
    date_to: dt.date | None,
    needs_review: bool | None = None,
) -> tuple[str, list]:
    clauses = []
    params: list = []

    if autoclave_code is not None:
        clauses.append("autoclave_code = ?")
        params.append(autoclave_code)
    if product_query:
        clauses.append("product LIKE ? ESCAPE '\\'")
        params.append(f"%{_escape_like(product_query)}%")
    if date_from is not None:
        clauses.append("started_at >= ?")
        params.append(to_iso(dt.datetime.combine(date_from, dt.time.min)))
    if date_to is not None:
        # Límite superior exclusivo al día siguiente: started_at lleva hora,
        # así que "<= date_to" por sí solo dejaría fuera los ciclos de ese
        # mismo día que empezaron después de medianoche en punto.
        siguiente = date_to + dt.timedelta(days=1)
        clauses.append("started_at < ?")
        params.append(to_iso(dt.datetime.combine(siguiente, dt.time.min)))
    if needs_review is not None:
        clauses.append("needs_review = ?")
        params.append(int(needs_review))

    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    return where, params


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _row_to_cycle(fila: sqlite3.Row) -> SterilizationCycle:
    return SterilizationCycle(
        id=fila["id"],
        autoclave_code=fila["autoclave_code"],
        started_at=from_iso(fila["started_at"]),
        cycle_number=fila["cycle_number"],
        product=fila["product"],
        batch=fila["batch"],
        cycles_counter=fila["cycles_counter"],
        reported_at=from_iso(fila["reported_at"]),
        source_filename=fila["source_filename"],
        source_sha256=fila["source_sha256"],
        sterilization_start_ts=from_iso(fila["sterilization_start_ts"]),
        sterilization_end_ts=from_iso(fila["sterilization_end_ts"]),
        sterilization_duration_s=fila["sterilization_duration_s"],
        sterilization_temp_end_c=fila["sterilization_temp_end_c"],
        sterilization_temp_mean_c=fila["sterilization_temp_mean_c"],
        sterilization_temp_min_c=fila["sterilization_temp_min_c"],
        sterilization_temp_max_c=fila["sterilization_temp_max_c"],
        needs_review=bool(fila["needs_review"]),
        review_notes=fila["review_notes"] or "",
    )
