"""ISO country labels must not become ranked measurement inputs."""

import pytest

from generator.field_queries import query_group_fields, query_vector_fields
from generator.field_queries_matrix import query_matrix_fields
from tests.test_category_filter.conftest import make_field_conn


@pytest.mark.parametrize("kind", ["MATRIX", "VECTOR"])
def test_iso_country_label_not_a_series_but_country_measurements_survive(kind):
    conn = make_field_conn()
    rows = [
        ("pv20_country_code_1965", "ISO country code for the data."),
        ("opaque_code", "  iSo CoUnTrY CoDe for the observation."),
        ("pv13_revere_country", "Country code"),
        ("plain_code_punctuation", "  CoUnTrY CoDe.  "),
        ("pv13_revere_city", "City code"),
        ("city_code_punctuation", "  CiTy CoDe.  "),
        ("pv13_revere_level", "Level of the sector within the hierarchy"),
        ("opaque_depth", "  LEVEL OF THE SECTOR WITHIN THE HIERARCHY.  "),
        ("price_level", "Closing price level"),
        ("sector_return", "Return at the sector level"),
        ("city_adjusted_return", "City code adjusted returns"),
        ("city_growth", "Growth in aggregate traded value for the city."),
        ("code_adjusted_return", "Country code adjusted returns"),
        ("country_exposure", "Exposure to the country return factor."),
        ("country_adjusted_return", "Return adjusted using ISO country code membership."),
        ("unknown_measurement", None),
        ("security_price_currency_code", "Currency code of the cash distribution"),
        ("equity_settlement_currency", "The currency in which the equity security is traded or settled."),
        ("currency_measurement", "Currency code adjusted returns"),
        ("exchange_rate", "Exchange rate for the quoted currency"),
    ]
    try:
        conn.executemany(
            "INSERT INTO data_fields VALUES (?, 'pv20', 'pv', 'USA', 0, 'TOP3000', ?, 0.9, 0.9, 42, ?)",
            [(field, kind, description) for field, description in rows],
        )
        if kind == "MATRIX":
            by_dataset, _ = query_matrix_fields(conn, "USA", 0, "TOP3000")
            loaded = {field for fields in by_dataset.values() for field in fields}
        else:
            loaded = set(query_vector_fields(conn, "USA", 0, "TOP3000"))
        assert (
            not {
                "pv20_country_code_1965",
                "opaque_code",
                "pv13_revere_country",
                "plain_code_punctuation",
                "pv13_revere_city",
                "city_code_punctuation",
            }
            & loaded
        )
        assert not {"pv13_revere_level", "opaque_depth"} & loaded
        assert {"price_level", "sector_return"} <= loaded
        assert not {"security_price_currency_code", "equity_settlement_currency"} & loaded
        assert {"currency_measurement", "exchange_rate"} <= loaded
        assert {
            "country_exposure",
            "country_adjusted_return",
            "unknown_measurement",
            "code_adjusted_return",
            "city_adjusted_return",
            "city_growth",
        } <= loaded
    finally:
        conn.close()


@pytest.mark.parametrize(
    "description",
    [
        "ISO country code for the data.",
        "Country code",
        "City code",
        "Level of the sector within the hierarchy",
        "Currency code of the cash distribution",
        "The currency in which the equity security is traded or settled.",
    ],
)
def test_iso_country_label_remains_available_as_a_group(description):
    conn = make_field_conn()
    try:
        conn.execute(
            "INSERT INTO data_fields VALUES ('country_partition', 'pv20', 'pv', 'USA', 0, "
            "'TOP3000', 'GROUP', 0.9, 0.9, 42, ?)",
            [description],
        )
        assert "country_partition" in query_group_fields(conn, "USA", 0, "TOP3000")
    finally:
        conn.close()
