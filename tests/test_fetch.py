from datetime import date

import pytest
import requests
from test_scr import csv_bytes, make_archive, row

from brazil_consumer_credit_risk import fetch, scr


@pytest.mark.parametrize("years", [["2011", "2012"], ["2025", "2024"]])
def test_main_rejects_years_out_of_range(years):
    with pytest.raises(SystemExit):
        fetch.main(["--years", *years, "--no-sgs"])


def http_error(status: int) -> requests.HTTPError:
    response = requests.Response()
    response.status_code = status
    return requests.HTTPError(f"{status}", response=response)


def fail_with(error_for_year):
    def fetch_archive(session, year, raw_dir, refresh=False):
        raise error_for_year(year)

    return fetch_archive


def test_fetch_scr_treats_a_missing_archive_for_this_year_as_not_yet_published(
    tmp_path, monkeypatch
):
    this_year = date.today().year
    monkeypatch.setattr(scr, "fetch_archive", fail_with(lambda year: http_error(404)))
    assert fetch.fetch_scr(tmp_path, range(this_year, this_year + 1), jobs=1) == 0


def test_fetch_scr_counts_a_missing_archive_for_a_past_year_as_a_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(scr, "fetch_archive", fail_with(lambda year: http_error(404)))
    assert fetch.fetch_scr(tmp_path, range(2024, 2025), jobs=1) == 1


def test_fetch_scr_stages_the_local_archive_when_bcb_is_unreachable(tmp_path, monkeypatch):
    raw = tmp_path / "raw" / "zips"
    raw.mkdir(parents=True)
    make_archive(raw / "scrdata_2024.zip", {"scrdata_202401.csv": csv_bytes([row()])})
    monkeypatch.setattr(
        scr, "fetch_archive", fail_with(lambda year: requests.ConnectionError("offline"))
    )

    failures = fetch.fetch_scr(tmp_path, range(2024, 2025), jobs=1)

    assert failures == 1
    assert (tmp_path / "parquet" / "scrdata" / "scrdata_202401.parquet").exists()
