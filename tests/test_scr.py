import json
import zipfile
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest

from brazil_consumer_credit_risk import scr
from brazil_consumer_credit_risk.download import RemoteFile

DEFAULT_ROW = {
    "data_base": "2024-01-31",
    "uf": "SP",
    "segmento": "Banco",
    "cliente": "PF",
    "cnae_ocupacao": "Aposentado/pensionista",
    "porte": "Mais de 1 a 2 salários mínimos",
    "modalidade": "Empréstimos",
    "submodalidade": "Crédito pessoal - com consignação em folha de pagam.",
    "origem": "Sem destinação específica",
    "indexador": "Prefixado",
    "numero_de_operacoes": "12",
    **{m: "0,00" for m in scr.MEASURES},
}


def csv_bytes(rows: list[dict], header: list[str] = scr.HEADER) -> bytes:
    """A monthly file as BCB writes it: UTF-8 with a byte-order mark, ';', every value quoted."""
    lines = [";".join(header)]
    lines += [";".join(f'"{row[c]}"' for c in header) for row in rows]
    return ("\ufeff" + "\n".join(lines) + "\n").encode("utf-8")


def row(**changes) -> dict:
    return {**DEFAULT_ROW, **changes}


def convert(tmp_path: Path, rows: list[dict], month: str = "202401", **kwargs) -> dict:
    csv_path = tmp_path / f"scrdata_{month}.csv"
    csv_path.write_bytes(csv_bytes(rows, **kwargs))
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    return scr.convert_month(duckdb.connect(), csv_path, out, month)


def test_convert_month_types_and_values(tmp_path):
    stats = convert(
        tmp_path,
        [
            row(),
            row(
                uf=" RJ ",
                cliente="PJ",
                cnae_ocupacao="Comércio; reparação de veículos automotores e motocicletas",
                numero_de_operacoes="-1",
                carteira_ativa="633904,03",
            ),
        ],
    )
    con = duckdb.connect()
    parquet = tmp_path / "out" / "scrdata_202401.parquet"
    types = dict(
        con.execute(f"SELECT column_name, column_type FROM (DESCRIBE '{parquet}')").fetchall()
    )
    got = con.execute(
        f"SELECT data_base, uf, cnae_ocupacao, numero_de_operacoes, carteira_ativa "
        f"FROM '{parquet}' WHERE cliente = 'PJ'"
    ).fetchone()

    assert stats["rows"] == 2
    assert stats["whitespace"] == {"uf": 1}
    assert types["data_base"] == "DATE"
    assert types["numero_de_operacoes"] == "BIGINT"
    assert types["carteira_ativa"] == "DECIMAL(22,2)"
    assert str(got[0]) == "2024-01-31"
    assert got[1] == "RJ"
    assert got[2] == "Comércio; reparação de veículos automotores e motocicletas"
    assert got[3] == -1
    assert got[4] == Decimal("633904.03")


def test_convert_month_rejects_a_changed_header(tmp_path):
    header = [*scr.HEADER[:-1], "ativo_problematico_novo"]
    rows = [{**row(), "ativo_problematico_novo": "0,00"}]
    with pytest.raises(ValueError, match="header differs"):
        convert(tmp_path, rows, header=header)
    assert not list((tmp_path / "out").glob("*.parquet"))


def test_convert_month_rejects_a_measure_that_does_not_parse(tmp_path):
    with pytest.raises(ValueError, match="don't parse"):
        convert(tmp_path, [row(carteira_ativa="1.234,56")])


def test_convert_month_rejects_a_data_base_from_another_month(tmp_path):
    with pytest.raises(ValueError, match="don't match the file name"):
        convert(tmp_path, [row(data_base="2024-02-29")])


def make_archive(path: Path, members: dict[str, bytes], stored: bool = False) -> Path:
    method = zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED
    with zipfile.ZipFile(path, "w", method) as z:
        for name, content in members.items():
            z.writestr(name, content)
    return path


def test_verify_archive_accepts_monthly_members(tmp_path):
    archive = make_archive(
        tmp_path / "scrdata_2024.zip",
        {"scrdata_202401.csv": b"a", "scrdata_202402.csv": b"b"},
    )
    assert scr.verify_archive(archive) == scr.ArchiveCheck(2, "202401", "202402")


@pytest.mark.parametrize(
    "name",
    ["../scrdata_202401.csv", "planilha_202401.csv", "scrdata_2024.csv", "x/scrdata_202401.csv"],
)
def test_verify_archive_rejects_unexpected_member_names(tmp_path, name):
    archive = make_archive(tmp_path / "scrdata_2024.zip", {name: b"a"})
    with pytest.raises(ValueError, match="unexpected member"):
        scr.verify_archive(archive)


def test_verify_archive_detects_a_crc_mismatch(tmp_path):
    content = b"data_base;uf\n" * 20
    archive = make_archive(
        tmp_path / "scrdata_2024.zip", {"scrdata_202401.csv": content}, stored=True
    )
    raw = bytearray(archive.read_bytes())
    at = raw.index(content) + 5
    raw[at] ^= 0xFF
    archive.write_bytes(bytes(raw))
    with pytest.raises(ValueError, match="CRC check failed"):
        scr.verify_archive(archive)


def test_manifest_keeps_the_latest_row_per_archive(tmp_path):
    manifest = tmp_path / scr.MANIFEST
    base = dict.fromkeys(scr.MANIFEST_COLUMNS, "x")
    scr.append_manifest(manifest, {**base, "file": "scrdata_2024.zip", "last_modified": "Mon, 1"})
    scr.append_manifest(manifest, {**base, "file": "scrdata_2024.zip", "last_modified": "Tue, 2"})
    assert scr.read_manifest(manifest)["scrdata_2024.zip"]["last_modified"] == "Tue, 2"
    assert manifest.read_text().splitlines()[0].split("\t") == scr.MANIFEST_COLUMNS


def test_stage_archive_converts_each_month_once(tmp_path):
    archive = make_archive(
        tmp_path / "scrdata_2024.zip",
        {
            "scrdata_202401.csv": csv_bytes([row()]),
            "scrdata_202402.csv": csv_bytes([row(data_base="2024-02-29")]),
        },
    )
    out = tmp_path / "parquet"
    out.mkdir()
    con = duckdb.connect()

    first = scr.stage_archive(con, archive, out)
    second = scr.stage_archive(con, archive, out)

    assert first == (["202401", "202402"], [])
    assert second == ([], [])
    log = [json.loads(line) for line in (out / scr.CONVERSION_LOG).read_text().splitlines()]
    assert [entry["month"] for entry in log] == ["202401", "202402"]
    assert log[0]["source"] == "scrdata_2024.zip:scrdata_202401.csv"
    assert log[0]["archive_sha256"] == scr.sha256(archive)


def test_stage_archive_converts_again_when_the_archive_changes(tmp_path):
    archive = tmp_path / "scrdata_2024.zip"
    out = tmp_path / "parquet"
    out.mkdir()
    con = duckdb.connect()
    make_archive(archive, {"scrdata_202401.csv": csv_bytes([row(carteira_ativa="1,00")])})
    scr.stage_archive(con, archive, out)

    make_archive(archive, {"scrdata_202401.csv": csv_bytes([row(carteira_ativa="2,00")])})
    converted, failed = scr.stage_archive(con, archive, out)

    value = con.execute(f"SELECT carteira_ativa FROM '{out}/scrdata_202401.parquet'").fetchone()
    assert (converted, failed) == (["202401"], [])
    assert value[0] == Decimal("2.00")


def fake_head(size: int, last_modified: str):
    return lambda session, url: RemoteFile(url, size, last_modified)


def test_fetch_archive_downloads_verifies_and_records(tmp_path, monkeypatch):
    content = make_archive(tmp_path / "source.zip", {"scrdata_202401.csv": b"a"}).read_bytes()

    def fake_download(session, remote, dest, **kwargs):
        dest.write_bytes(content)

    monkeypatch.setattr(scr, "head", fake_head(len(content), "Mon, 01 Jan 2024 00:00:00 GMT"))
    monkeypatch.setattr(scr, "download", fake_download)
    raw = tmp_path / "raw"
    raw.mkdir()

    message = scr.fetch_archive(None, 2024, raw)

    recorded = scr.read_manifest(raw / scr.MANIFEST)["scrdata_2024.zip"]
    assert "CRC ok" in message
    assert recorded["last_modified"] == "Mon, 01 Jan 2024 00:00:00 GMT"
    assert recorded["sha256"] == scr.sha256(raw / "scrdata_2024.zip")


def test_fetch_archive_deletes_an_archive_that_fails_verification(tmp_path, monkeypatch):
    content = make_archive(tmp_path / "source.zip", {"evil.csv": b"a"}).read_bytes()
    monkeypatch.setattr(scr, "head", fake_head(len(content), "Mon"))
    monkeypatch.setattr(scr, "download", lambda s, r, dest, **k: dest.write_bytes(content))
    raw = tmp_path / "raw"
    raw.mkdir()

    with pytest.raises(ValueError, match="unexpected member"):
        scr.fetch_archive(None, 2024, raw)
    assert not (raw / "scrdata_2024.zip").exists()
    assert not (raw / "scrdata_2024.zip.download").exists()
    assert not (raw / scr.MANIFEST).exists()


def local_copy(tmp_path: Path, last_modified: str) -> Path:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "scrdata_2024.zip").write_bytes(b"x" * 10)
    base = dict.fromkeys(scr.MANIFEST_COLUMNS, "")
    scr.append_manifest(
        raw / scr.MANIFEST, {**base, "file": "scrdata_2024.zip", "last_modified": last_modified}
    )
    return raw


def refuse_download(*args, **kwargs):
    raise AssertionError("should not download")


def test_fetch_archive_skips_an_unchanged_archive(tmp_path, monkeypatch):
    raw = local_copy(tmp_path, "old")
    monkeypatch.setattr(scr, "download", refuse_download)
    monkeypatch.setattr(scr, "head", fake_head(10, "old"))
    assert scr.fetch_archive(None, 2024, raw) == "scrdata_2024.zip: already downloaded"


@pytest.mark.parametrize(("size", "last_modified"), [(10, "new"), (99, "old"), (99, "new")])
def test_fetch_archive_keeps_the_local_copy_when_bcb_republishes(
    tmp_path, monkeypatch, size, last_modified
):
    raw = local_copy(tmp_path, "old")
    monkeypatch.setattr(scr, "download", refuse_download)
    monkeypatch.setattr(scr, "head", fake_head(size, last_modified))

    message = scr.fetch_archive(None, 2024, raw)

    assert "BCB has republished it" in message
    assert "--refresh" in message
    assert (raw / "scrdata_2024.zip").read_bytes() == b"x" * 10


def test_fetch_archive_refresh_replaces_the_local_copy(tmp_path, monkeypatch):
    raw = local_copy(tmp_path, "old")
    content = make_archive(tmp_path / "source.zip", {"scrdata_202401.csv": b"a"}).read_bytes()
    monkeypatch.setattr(scr, "head", fake_head(len(content), "new"))
    monkeypatch.setattr(scr, "download", lambda s, r, dest, **k: dest.write_bytes(content))

    scr.fetch_archive(None, 2024, raw, refresh=True)

    assert (raw / "scrdata_2024.zip").read_bytes() == content
    assert scr.read_manifest(raw / scr.MANIFEST)["scrdata_2024.zip"]["last_modified"] == "new"


def test_fetch_archive_refresh_keeps_the_old_copy_if_the_new_one_is_bad(tmp_path, monkeypatch):
    raw = local_copy(tmp_path, "old")
    content = make_archive(tmp_path / "source.zip", {"evil.csv": b"a"}).read_bytes()
    monkeypatch.setattr(scr, "head", fake_head(len(content), "new"))
    monkeypatch.setattr(scr, "download", lambda s, r, dest, **k: dest.write_bytes(content))

    with pytest.raises(ValueError, match="unexpected member"):
        scr.fetch_archive(None, 2024, raw, refresh=True)

    assert (raw / "scrdata_2024.zip").read_bytes() == b"x" * 10
    assert scr.read_manifest(raw / scr.MANIFEST)["scrdata_2024.zip"]["last_modified"] == "old"
