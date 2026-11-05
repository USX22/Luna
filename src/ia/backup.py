"""Backups, integrity checks and restore for Luna's state (LUNA_HOME)."""
from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path


def verify(home: Path) -> list[str]:
    """Return a list of problems found (empty list = healthy)."""
    problems = []
    for db in home.glob("*.sqlite"):
        try:
            ok = sqlite3.connect(db).execute("PRAGMA integrity_check").fetchone()[0]
            if ok != "ok":
                problems.append(f"{db.name}: {ok}")
        except sqlite3.DatabaseError as exc:
            problems.append(f"{db.name}: {exc}")
    for js in home.glob("*.json"):
        try:
            json.loads(js.read_text("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            problems.append(f"{js.name}: {exc}")
    for jl in home.glob("*.jsonl"):
        for n, line in enumerate(jl.read_text("utf-8").splitlines(), 1):
            if line.strip():
                try:
                    json.loads(line)
                except json.JSONDecodeError:
                    problems.append(f"{jl.name}: línea {n} corrupta")
    return problems


def make_backup(home: Path, dest: Path, keep: int = 14) -> Path:
    """Consistent snapshot (SQLite backup API) zipped into dest; keep the last `keep`."""
    dest.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    target = dest / f"luna-{stamp}.zip"
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        for item in home.iterdir():
            if item.is_dir():
                continue
            if item.suffix == ".sqlite":
                src, dst = sqlite3.connect(item), sqlite3.connect(tmpdir / item.name)
                with dst:
                    src.backup(dst)
                src.close()
                dst.close()
            else:
                shutil.copy2(item, tmpdir / item.name)
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(tmpdir.iterdir()):
                zf.write(f, f.name)
    backups = sorted(dest.glob("luna-*.zip"))
    for old in backups[:-keep] if keep > 0 else []:
        old.unlink()
    return target


def restore(archive: Path, home: Path) -> Path | None:
    """Move the current state aside (never deleted) and extract the backup."""
    moved = None
    if home.exists() and any(home.iterdir()):
        moved = home.with_name(f"{home.name}.antes-{datetime.now():%Y%m%d-%H%M%S}")
        home.rename(moved)
    home.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        for name in zf.namelist():
            if "/" in name or "\\" in name or name.startswith(".."):
                raise ValueError(f"ruta sospechosa en el respaldo: {name}")
        zf.extractall(home)
    return moved
