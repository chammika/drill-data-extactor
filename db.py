import json
import re
import sqlite3
from pathlib import Path

from pydantic import BaseModel

from schema import DrillLogRow, OtherSection, PumpTest, Summary

DB = Path("drill_data.db")
SUMMARY_COLS = [c for c in Summary.model_fields if c != "well_no"]
CHILDREN = {  # table -> (model, path to its list in the extraction)
    "drill_log_rows": (DrillLogRow, ("drill_log", "rows")),
    "pump_tests": (PumpTest, ("pump_tests",)),
    "other_sections": (OtherSection, ("other_sections",)),
}


def columns(model, prefix=""):
    """Flat column names: nested models are prefixed, lists become one JSON column."""
    out = []
    for name, field in model.model_fields.items():
        ann = field.annotation
        if isinstance(ann, type) and issubclass(ann, BaseModel):
            out += columns(ann, f"{prefix}{name}_")
        else:
            out.append(prefix + name)
    return out


def flatten(d, prefix=""):
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out.update(flatten(v, f"{prefix}{k}_"))
        else:
            out[prefix + k] = json.dumps(v) if isinstance(v, list) else v
    return out


def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    text = lambda cols: ", ".join(f'"{c}" TEXT' for c in cols)
    con.execute(f"""CREATE TABLE IF NOT EXISTS wells (
        well_no TEXT PRIMARY KEY, {text(SUMMARY_COLS)},
        reviewed INTEGER DEFAULT 0, data TEXT, raw TEXT,
        input_tokens INTEGER, output_tokens INTEGER, updated_at TEXT)""")
    con.execute("CREATE TABLE IF NOT EXISTS files (hash TEXT PRIMARY KEY, path TEXT, well_no TEXT)")
    for table, (model, _) in CHILDREN.items():
        con.execute(f"CREATE TABLE IF NOT EXISTS {table} (well_no TEXT, seq INTEGER, {text(columns(model))})")
    return con


def norm_well_no(s):
    return re.sub(r"[\s/\\-]+", "-", s.strip())


def _write_children(con, old_well_no, well_no, data):
    for table, (model, path) in CHILDREN.items():
        con.execute(f"DELETE FROM {table} WHERE well_no = ?", (old_well_no,))
        items = data
        for p in path:
            items = items[p]
        cols = columns(model)
        sql = f"INSERT INTO {table} VALUES ({', '.join('?' * (len(cols) + 2))})"
        for seq, item in enumerate(items):
            flat = flatten(item)
            con.execute(sql, [well_no, seq] + [flat.get(c, "") for c in cols])


def add_extraction(con, file_hash, path, data, input_tokens, output_tokens):
    """Stores a new extraction. If the well already exists, the file is linked to the existing record."""
    well_no = norm_well_no(data["summary"]["well_no"]) or Path(path).stem
    data["summary"]["well_no"] = well_no
    with con:
        if not con.execute("SELECT 1 FROM wells WHERE well_no = ?", (well_no,)).fetchone():
            js = json.dumps(data)
            con.execute(
                f"INSERT INTO wells (well_no, {', '.join(SUMMARY_COLS)}, data, raw, input_tokens, output_tokens, updated_at) "
                f"VALUES ({', '.join('?' * (len(SUMMARY_COLS) + 5))}, datetime('now'))",
                [well_no] + [data["summary"][c] for c in SUMMARY_COLS] + [js, js, input_tokens, output_tokens],
            )
            _write_children(con, well_no, well_no, data)
        con.execute("INSERT INTO files VALUES (?, ?, ?)", (file_hash, path, well_no))
    return well_no


def save(con, old_well_no, data, reviewed):
    well_no = norm_well_no(data["summary"]["well_no"]) or old_well_no
    data["summary"]["well_no"] = well_no
    with con:
        con.execute(
            f"UPDATE wells SET well_no = ?, {', '.join(c + ' = ?' for c in SUMMARY_COLS)}, "
            "reviewed = ?, data = ?, updated_at = datetime('now') WHERE well_no = ?",
            [well_no] + [data["summary"][c] for c in SUMMARY_COLS] + [int(reviewed), json.dumps(data), old_well_no],
        )
        con.execute("UPDATE files SET well_no = ? WHERE well_no = ?", (well_no, old_well_no))
        _write_children(con, old_well_no, well_no, data)


def well_for_hash(con, file_hash):
    return con.execute(
        "SELECT w.* FROM files f JOIN wells w ON w.well_no = f.well_no WHERE f.hash = ?", (file_hash,)
    ).fetchone()
