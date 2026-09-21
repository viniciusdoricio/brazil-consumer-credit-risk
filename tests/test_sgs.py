from datetime import date

import duckdb
import pytest

from brazil_consumer_credit_risk import sgs


class FakeResponse:
    def __init__(self, status_code: int, payload=None):
        self.status_code = status_code
        self.payload = payload

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses: list[FakeResponse]):
        self.responses = list(responses)
        self.calls = 0

    def get(self, url, params, timeout):
        self.calls += 1
        return self.responses.pop(0)


def test_parse_series_reads_dates_and_decimal_points():
    records = [{"data": "01/01/2024", "valor": "3.45"}, {"data": "01/02/2024", "valor": "3.5"}]
    assert sgs.parse_series(21084, records) == [
        (21084, date(2024, 1, 1), 3.45),
        (21084, date(2024, 2, 1), 3.5),
    ]


def test_parse_series_rejects_a_missing_value():
    with pytest.raises(ValueError):
        sgs.parse_series(433, [{"data": "01/01/2024", "valor": ""}])


def test_fetch_series_retries_a_server_error():
    payload = [{"data": "01/01/2024", "valor": "1412.00"}]
    session = FakeSession([FakeResponse(503), FakeResponse(200, payload)])
    assert sgs.fetch_series(session, 1619, sleep=lambda _: None) == payload
    assert session.calls == 2


def test_fetch_series_gives_up_after_the_last_attempt():
    session = FakeSession([FakeResponse(503)] * 2)
    with pytest.raises(OSError, match="failed after 2 attempts"):
        sgs.fetch_series(session, 1619, attempts=2, sleep=lambda _: None)


def test_write_parquet_orders_rows_by_series_and_date(tmp_path):
    path = tmp_path / "sgs.parquet"
    sgs.write_parquet(
        [
            (433, date(2024, 2, 1), 0.83),
            (433, date(2024, 1, 1), 0.42),
            (1619, date(2024, 1, 1), 1412.0),
        ],
        path,
    )
    rows = duckdb.connect().execute(f"SELECT code, date, value FROM '{path}'").fetchall()
    assert rows == [
        (433, date(2024, 1, 1), 0.42),
        (433, date(2024, 2, 1), 0.83),
        (1619, date(2024, 1, 1), 1412.0),
    ]
