-- Active: 1785757943785@@127.0.0.1@3306
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    machine TEXT,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS measurements_raw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    machine TEXT,
    date_raw TEXT,
    time_raw TEXT,
    temperature_raw TEXT,
    pressure_raw TEXT,

    FOREIGN KEY (file_id) REFERENCES files(id)
);

CREATE INDEX IF NOT EXISTS idx_measurements_raw_file_id
ON measurements_raw(file_id);

-- Fase 3 (formatter): datos ya formateados (fecha+hora unidas, temp/pres
-- como numero). NULL en temperature/pressure = valor crudo no interpretable
-- (vacio o simbolo tipo '<<<<<<<<').
CREATE TABLE IF NOT EXISTS measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_id INTEGER NOT NULL,
    file_id INTEGER NOT NULL,
    machine TEXT,
    timestamp TEXT NOT NULL,
    temperature REAL,
    pressure REAL,

    FOREIGN KEY (raw_id) REFERENCES measurements_raw(id),
    FOREIGN KEY (file_id) REFERENCES files(id)
);

CREATE INDEX IF NOT EXISTS idx_measurements_file_id
ON measurements(file_id);

CREATE INDEX IF NOT EXISTS idx_measurements_timestamp
ON measurements(timestamp);

CREATE INDEX IF NOT EXISTS idx_measurements_machine
ON measurements(machine);