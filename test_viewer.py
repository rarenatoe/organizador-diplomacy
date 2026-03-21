"""
test_viewer.py — Unit tests for viewer.py (Flask backend).

Covers:
  - _parse_report_sections: splits .txt into named sections
  - _parse_registro: extracts key→value pairs from REGISTRO section
  - _parse_detalle: extracts mesas + waiting list from DETALLE section
  - _parse_proyeccion: extracts projection rows
  - _build_chain: builds ordered chain from data/ directory
  - API routes: /api/chain, /api/csv/<f>, /api/report/<f>, /api/csvs
  - /api/run validation (unknown script, invalid csv name)
"""
from __future__ import annotations

import csv
import json
import textwrap
from pathlib import Path

import pytest

import viewer
from viewer import (
    _parse_detalle,
    _parse_proyeccion,
    _parse_registro,
    _parse_report_sections,
    app,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

SEP = "═" * 44


def _make_report(
    tmp_path: Path,
    *,
    leido: str = "jugadores_0001.csv",
    escrito: str = "jugadores_0002.csv",
    filename: str | None = None,
    mesas: int = 2,
    en_espera: int = 0,
) -> Path:
    """Creates a minimal but structurally valid report .txt file."""
    copypaste_lines = []
    detalle_lines = [f"  SE GENERARON {mesas} PARTIDA(S)", "─" * 40]
    for m in range(1, mesas + 1):
        detalle_lines.append(f"\n[ Partida {m} ]  Nuevos: 1  Antiguos: 6  GM: GM_{m}")
        for i in range(1, 8):
            exp = "Nuevo" if i == 1 else f"Antiguo ({i} juegos)"
            detalle_lines.append(f"  {i}. Player_{m}_{i}  —  {exp}")

    proyeccion_lines = [
        "  Jugador     Actual  +Juega  +GM  Proyectado",
        "  " + "-" * 45,
        "  Player_1_1       0       1    0           1",
        "  Player_2_1       0       1    0           1",
    ]

    registro_lines = [
        "  Generado:      2026-03-21 10:00:00",
        f"  Partidas:      {mesas}  ({mesas*7} solicitados, {mesas*7} disponibles)",
        f"  En espera:     {en_espera} jugador(es)",
        "  Intentos:      1 de 200",
        f"  Leído de:      {leido}",
        f"  Escrito en:    {escrito}",
    ]

    def section(title: str, lines: list[str]) -> str:
        return "\n" + SEP + f"\n  {title}\n" + SEP + "\n" + "\n".join(lines)

    content = (
        section("LISTO PARA COMPARTIR", copypaste_lines)
        + section("DETALLE DEL EVENTO", detalle_lines)
        + section("PROYECCIÓN JUEGOS_ESTE_AÑO", proyeccion_lines)
        + section("REGISTRO", registro_lines)
        + "\n"
    )
    fname = filename or "reporte_2026-03-21_10-00-00.txt"
    path = tmp_path / fname
    path.write_text(content, encoding="utf-8")
    return path


def _make_csv(tmp_path: Path, name: str, rows: int = 5) -> Path:
    path = tmp_path / name
    fields = ["Nombre", "Experiencia", "Juegos_Este_Ano", "Prioridad", "Partidas_Deseadas", "Partidas_GM"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i in range(rows):
            w.writerow({
                "Nombre": f"Jugador_{i}",
                "Experiencia": "Antiguo" if i % 2 == 0 else "Nuevo",
                "Juegos_Este_Ano": str(i),
                "Prioridad": "False",
                "Partidas_Deseadas": "1",
                "Partidas_GM": "0",
            })
    return path


# ── _parse_report_sections ────────────────────────────────────────────────────

class TestParseReportSections:
    def test_returns_four_sections(self, tmp_path):
        rpt = _make_report(tmp_path)
        text = rpt.read_text(encoding="utf-8")
        sections = _parse_report_sections(text)
        assert set(sections) == {
            "LISTO PARA COMPARTIR",
            "DETALLE DEL EVENTO",
            "PROYECCIÓN JUEGOS_ESTE_AÑO",
            "REGISTRO",
        }

    def test_registro_section_contains_generado(self, tmp_path):
        rpt = _make_report(tmp_path)
        text = rpt.read_text(encoding="utf-8")
        sections = _parse_report_sections(text)
        assert "Generado" in sections["REGISTRO"]

    def test_empty_string_returns_empty_dict(self):
        assert _parse_report_sections("") == {}

    def test_single_section(self):
        text = f"\n{SEP}\n  MI SECCIÓN\n{SEP}\ncontenido aquí\n"
        sections = _parse_report_sections(text)
        assert "MI SECCIÓN" in sections
        assert sections["MI SECCIÓN"] == "contenido aquí"


# ── _parse_registro ───────────────────────────────────────────────────────────

class TestParseRegistro:
    def test_leido_de_extracted(self):
        text = "  Leído de:      jugadores_0001.csv\n  Escrito en:    jugadores_0002.csv\n"
        r = _parse_registro(text)
        assert r["Leído de"] == "jugadores_0001.csv"
        assert r["Escrito en"] == "jugadores_0002.csv"

    def test_generado_extracted(self):
        text = "  Generado:      2026-03-21 10:00:00\n"
        r = _parse_registro(text)
        assert r["Generado"] == "2026-03-21 10:00:00"

    def test_empty_text_returns_empty(self):
        assert _parse_registro("") == {}

    def test_line_without_colon_skipped(self):
        text = "  no colon here\n  Key: value\n"
        r = _parse_registro(text)
        assert "no colon here" not in r
        assert r["Key"] == "value"

    def test_value_with_colon_kept_intact(self):
        text = "  Generado:      2026-03-21 10:00:00\n"
        r = _parse_registro(text)
        assert "10:00:00" in r["Generado"]


# ── _parse_detalle ────────────────────────────────────────────────────────────

class TestParseDetalle:
    def test_mesa_count(self, tmp_path):
        rpt = _make_report(tmp_path, mesas=3)
        text = rpt.read_text(encoding="utf-8")
        sections = _parse_report_sections(text)
        detalle = _parse_detalle(sections["DETALLE DEL EVENTO"])
        assert len(detalle["mesas"]) == 3

    def test_mesa_has_numero_and_gm(self, tmp_path):
        rpt = _make_report(tmp_path, mesas=2)
        text = rpt.read_text(encoding="utf-8")
        sections = _parse_report_sections(text)
        detalle = _parse_detalle(sections["DETALLE DEL EVENTO"])
        mesa = detalle["mesas"][0]
        assert mesa["numero"] == 1
        assert mesa["gm"] == "GM_1"

    def test_each_mesa_has_seven_players(self, tmp_path):
        rpt = _make_report(tmp_path, mesas=2)
        text = rpt.read_text(encoding="utf-8")
        sections = _parse_report_sections(text)
        detalle = _parse_detalle(sections["DETALLE DEL EVENTO"])
        for mesa in detalle["mesas"]:
            assert len(mesa["jugadores"]) == 7

    def test_player_nombre_and_etiqueta(self, tmp_path):
        rpt = _make_report(tmp_path, mesas=1)
        text = rpt.read_text(encoding="utf-8")
        sections = _parse_report_sections(text)
        detalle = _parse_detalle(sections["DETALLE DEL EVENTO"])
        first = detalle["mesas"][0]["jugadores"][0]
        assert first["nombre"] == "Player_1_1"
        assert first["etiqueta"] == "Nuevo"

    def test_waiting_list_empty_by_default(self, tmp_path):
        rpt = _make_report(tmp_path, mesas=1)
        text = rpt.read_text(encoding="utf-8")
        sections = _parse_report_sections(text)
        detalle = _parse_detalle(sections["DETALLE DEL EVENTO"])
        assert detalle["waiting_list"] == []

    def test_waiting_list_parsed(self):
        text = textwrap.dedent("""\
            [ Partida 1 ]  Nuevos: 0  Antiguos: 7  GM: Alguien

            ════════════════════════════════════════════
              JUGADORES EN LISTA DE ESPERA
            ════════════════════════════════════════════
              - Juan  (1 cupo sin asignar)
              - Ana  (2 cupos sin asignar)
        """)
        detalle = _parse_detalle(text)
        assert len(detalle["waiting_list"]) == 2
        assert detalle["waiting_list"][0]["nombre"] == "Juan"
        assert detalle["waiting_list"][1]["cupos"] == "2 cupos sin asignar"


# ── _parse_proyeccion ─────────────────────────────────────────────────────────

class TestParseProyeccion:
    def test_rows_extracted(self, tmp_path):
        rpt = _make_report(tmp_path, mesas=2)
        text = rpt.read_text(encoding="utf-8")
        sections = _parse_report_sections(text)
        rows = _parse_proyeccion(sections["PROYECCIÓN JUEGOS_ESTE_AÑO"])
        assert len(rows) == 2

    def test_row_fields_present(self, tmp_path):
        rpt = _make_report(tmp_path, mesas=2)
        text = rpt.read_text(encoding="utf-8")
        sections = _parse_report_sections(text)
        rows = _parse_proyeccion(sections["PROYECCIÓN JUEGOS_ESTE_AÑO"])
        row = rows[0]
        assert "nombre" in row
        assert "actual" in row
        assert "jugadas" in row
        assert "gm" in row
        assert "proyectado" in row

    def test_empty_section_returns_empty(self):
        assert _parse_proyeccion("") == []


# ── Flask routes ──────────────────────────────────────────────────────────────

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(viewer, "DATA", tmp_path)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestApiChain:
    def test_empty_data_returns_empty_nodes(self, client):
        resp = client.get("/api/chain")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["nodes"] == []

    def test_csv_only_chain(self, client, tmp_path, monkeypatch):
        """A single CSV with no reports appears as a root node."""
        monkeypatch.setattr(viewer, "DATA", tmp_path)
        _make_csv(tmp_path, "jugadores_0001.csv", rows=3)
        resp = client.get("/api/chain")
        data = json.loads(resp.data)
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["type"] == "csv"
        assert data["nodes"][0]["player_count"] == 3

    def test_chain_with_report_linked(self, client, tmp_path, monkeypatch):
        """csv_0001 → report → csv_0002 is ordered correctly via DFS."""
        monkeypatch.setattr(viewer, "DATA", tmp_path)
        _make_csv(tmp_path, "jugadores_0001.csv")
        _make_csv(tmp_path, "jugadores_0002.csv")
        _make_report(tmp_path, leido="jugadores_0001.csv", escrito="jugadores_0002.csv")
        resp = client.get("/api/chain")
        data = json.loads(resp.data)
        types = [n["type"] for n in data["nodes"]]
        assert types == ["csv", "report", "csv"]

    def test_second_report_from_same_csv_ordered_correctly(self, client, tmp_path, monkeypatch):
        """
        When csv_0001 produces two reports in sequence (report_A → csv_0002,
        report_B → csv_0003), the chain follows temporal order:
          csv_0001 → report_A → csv_0002 → report_B → csv_0003
        rather than placing report_B at the end by filename order alone.
        """
        monkeypatch.setattr(viewer, "DATA", tmp_path)
        _make_csv(tmp_path, "jugadores_0001.csv")
        _make_csv(tmp_path, "jugadores_0002.csv")
        _make_csv(tmp_path, "jugadores_0003.csv")
        _make_report(
            tmp_path,
            leido="jugadores_0001.csv",
            escrito="jugadores_0002.csv",
            filename="reporte_2026-01-01_00-00-01.txt",
        )
        _make_report(
            tmp_path,
            leido="jugadores_0001.csv",
            escrito="jugadores_0003.csv",
            filename="reporte_2026-01-01_00-00-02.txt",
        )
        resp = client.get("/api/chain")
        data = json.loads(resp.data)
        filenames = [n["filename"] for n in data["nodes"]]
        assert filenames.index("jugadores_0001.csv") < filenames.index("reporte_2026-01-01_00-00-01.txt")
        assert filenames.index("reporte_2026-01-01_00-00-01.txt") < filenames.index("jugadores_0002.csv")
        assert filenames.index("jugadores_0002.csv") < filenames.index("reporte_2026-01-01_00-00-02.txt")
        assert filenames.index("reporte_2026-01-01_00-00-02.txt") < filenames.index("jugadores_0003.csv")

    def test_notion_sync_csv_is_a_new_root(self, client, tmp_path, monkeypatch):
        """
        A CSV with no parent report (created by notion_sync) is a root node.
        It should appear in the chain even if not reachable from other CSVs.
        """
        monkeypatch.setattr(viewer, "DATA", tmp_path)
        _make_csv(tmp_path, "jugadores_0001.csv")
        _make_csv(tmp_path, "jugadores_0002.csv")
        _make_report(tmp_path, leido="jugadores_0001.csv", escrito="jugadores_0002.csv")
        # csv_0003 created by notion_sync — no parent report
        _make_csv(tmp_path, "jugadores_0003.csv")
        resp = client.get("/api/chain")
        data = json.loads(resp.data)
        filenames = [n["filename"] for n in data["nodes"]]
        assert "jugadores_0003.csv" in filenames
        # csv_0003 must appear after csv_0002 in the list (appended after DFS)
        assert filenames.index("jugadores_0002.csv") < filenames.index("jugadores_0003.csv")

    def test_pending_flag_detected(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(viewer, "DATA", tmp_path)
        _make_csv(tmp_path, "jugadores_0001.csv")
        (tmp_path / ".pending").touch()
        resp = client.get("/api/chain")
        data = json.loads(resp.data)
        assert data["pending"] is True

    def test_pending_false_when_no_flag(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(viewer, "DATA", tmp_path)
        _make_csv(tmp_path, "jugadores_0001.csv")
        resp = client.get("/api/chain")
        data = json.loads(resp.data)
        assert data["pending"] is False


class TestApiCsv:
    def test_returns_rows(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(viewer, "DATA", tmp_path)
        _make_csv(tmp_path, "jugadores_0001.csv", rows=4)
        resp = client.get("/api/csv/jugadores_0001.csv")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data["rows"]) == 4

    def test_invalid_filename_returns_400(self, client):
        # Flask's URL routing normalises path traversal before the view runs;
        # the regex guard in the view handles names like 'jugadores_abc.csv'.
        resp = client.get("/api/csv/jugadores_bad_name.csv")
        assert resp.status_code == 400

    def test_nonexistent_file_returns_404(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(viewer, "DATA", tmp_path)
        resp = client.get("/api/csv/jugadores_9999.csv")
        assert resp.status_code == 404

    def test_row_has_expected_columns(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(viewer, "DATA", tmp_path)
        _make_csv(tmp_path, "jugadores_0001.csv", rows=1)
        resp = client.get("/api/csv/jugadores_0001.csv")
        row = json.loads(resp.data)["rows"][0]
        assert "Nombre" in row
        assert "Experiencia" in row
        assert "Juegos_Este_Ano" in row


class TestApiReport:
    def test_returns_structured_data(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(viewer, "DATA", tmp_path)
        _make_report(tmp_path)
        resp = client.get("/api/report/reporte_2026-03-21_10-00-00.txt")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "registro" in data
        assert "detalle" in data
        assert "copypaste" in data

    def test_invalid_filename_returns_400(self, client):
        # Flask normalises path traversal at the routing level.
        # The regex guard in the view rejects non-matching filenames.
        resp = client.get("/api/report/not_a_valid_report_name.txt")
        assert resp.status_code == 400

    def test_nonexistent_file_returns_404(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(viewer, "DATA", tmp_path)
        resp = client.get("/api/report/reporte_9999-99-99_00-00-00.txt")
        assert resp.status_code == 404

    def test_mesas_count_in_response(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(viewer, "DATA", tmp_path)
        _make_report(tmp_path, mesas=3)
        resp = client.get("/api/report/reporte_2026-03-21_10-00-00.txt")
        data = json.loads(resp.data)
        assert len(data["detalle"]["mesas"]) == 3


class TestApiCsvs:
    def test_lists_csvs_in_order(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(viewer, "DATA", tmp_path)
        _make_csv(tmp_path, "jugadores_0003.csv")
        _make_csv(tmp_path, "jugadores_0001.csv")
        resp = client.get("/api/csvs")
        data = json.loads(resp.data)
        assert data["csvs"] == ["jugadores_0001.csv", "jugadores_0003.csv"]

    def test_empty_when_no_csvs(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(viewer, "DATA", tmp_path)
        resp = client.get("/api/csvs")
        data = json.loads(resp.data)
        assert data["csvs"] == []


class TestApiRun:
    def test_unknown_script_returns_400(self, client):
        resp = client.post("/api/run/evil_script")
        assert resp.status_code == 400

    def test_invalid_csv_name_returns_400(self, client):
        resp = client.post(
            "/api/run/organizar",
            data=json.dumps({"csv": "../../etc/passwd"}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_valid_csv_name_pattern_accepted(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(viewer, "DATA", tmp_path)
        # We don't actually run the subprocess — just check it doesn't 400
        # Patch subprocess.run to avoid side effects
        import subprocess
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "ok", "stderr": ""})())
        resp = client.post(
            "/api/run/organizar",
            data=json.dumps({"csv": "jugadores_0001.csv"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
