import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Solar Monitoring API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "past_data"
STATIC_DIR = Path(__file__).parent.parent / "frontend" / "dist"


def _col_to_idx(col: str) -> int:
    idx = 0
    for c in col.upper():
        idx = idx * 26 + (ord(c) - ord("A") + 1)
    return idx - 1


def _read_xlsx(path: Path) -> list[list]:
    with zipfile.ZipFile(path) as z:
        strings: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml").decode("utf-8"))
            ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
            for si in root.iter(f"{{{ns}}}si"):
                texts = [t.text or "" for t in si.iter(f"{{{ns}}}t")]
                strings.append("".join(texts))

        root = ET.fromstring(z.read("xl/worksheets/sheet1.xml").decode("utf-8"))
        ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
        result = []
        for row in root.iter(f"{{{ns}}}row"):
            cells: dict[int, str | None] = {}
            max_col = 0
            for cell in row.iter(f"{{{ns}}}c"):
                ref = cell.get("r", "")
                col_str = re.sub(r"\d", "", ref)
                if not col_str:
                    continue
                col_idx = _col_to_idx(col_str)
                max_col = max(max_col, col_idx)
                t = cell.get("t", "")
                v_el = cell.find(f"{{{ns}}}v")
                if t == "s" and v_el is not None and v_el.text:
                    val: str | None = strings[int(v_el.text)]
                elif t == "inlineStr":
                    t_el = cell.find(f".//{{{ns}}}t")
                    val = t_el.text if t_el is not None else ""
                elif v_el is not None:
                    val = v_el.text
                else:
                    val = None
                cells[col_idx] = val
            result.append([cells.get(i) for i in range(max_col + 1)])
        return result


def _to_float(v) -> float | None:
    if v is None or str(v).strip() in ("", "-"):
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _parse_file(site_id: str, year: int, month: int, path: Path) -> list[dict]:
    try:
        rows = _read_xlsx(path)
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return []

    result = []
    for row in rows[2:]:  # row[0]=header, row[1]=monthly average
        if not row or len(row) < 3:
            continue
        day_str = row[1] if len(row) > 1 else None
        if not day_str:
            continue
        m = re.match(r"(\d+)", str(day_str))
        if not m:
            continue
        day = int(m.group(1))
        result.append(
            {
                "date": f"{year:04d}-{month:02d}-{day:02d}",
                "year": year,
                "month": month,
                "day": day,
                "site_id": site_id,
                "generation_kwh": _to_float(row[2] if len(row) > 2 else None),
                "generation_hours": _to_float(row[4] if len(row) > 4 else None),
            }
        )
    return result


_cache: list[dict] | None = None


def _load() -> list[dict]:
    global _cache
    if _cache is not None:
        return _cache
    all_data: list[dict] = []
    for site_dir in sorted(DATA_DIR.iterdir()):
        if not site_dir.is_dir():
            continue
        for xlsx in sorted(site_dir.glob("*.xlsx")):
            m = re.match(r"(\d{4})-(\d{2})-\d{2}\.xlsx", xlsx.name)
            if not m:
                continue
            all_data.extend(
                _parse_file(site_dir.name, int(m.group(1)), int(m.group(2)), xlsx)
            )
    _cache = all_data
    return _cache


@app.get("/api/data")
def get_data():
    return _load()


@app.post("/api/reload")
def reload_data():
    global _cache
    _cache = None
    data = _load()
    return {"status": "ok", "count": len(data)}


@app.get("/api/health")
def health():
    return {"status": "ok", "records": len(_load())}


# Serve React build in production
if STATIC_DIR.exists():
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        return FileResponse(str(STATIC_DIR / "index.html"))
