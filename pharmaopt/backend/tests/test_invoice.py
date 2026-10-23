import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app import invoice


def test_parse_supported_invoice_formats():
    parsed = invoice.parse(
        "Paracetamol 500 mg\tTAB | B123 | 500 | 2027-03-31\n"
        "ORS Sachet  X77  100  03/2027\n"
        "Foo Bar  Z99  5  2027-01-01",
        ["Paracetamol 500mg", "ORS Sachet"],
    )
    assert [row["matched"] for row in parsed["rows"]] == [True, True, False]
    assert parsed["rows"][0]["qty"] == 500
    assert parsed["rows"][1]["expiry"] == "2027-03-31"
    assert parsed["errors"] == []


def test_invalid_dates_and_nonpositive_quantities_are_rejected():
    parsed = invoice.parse(
        "Paracetamol 500mg B123 5 13/13/2027\n"
        "Paracetamol 500mg B124 -1 2027-12-01\n"
        "Paracetamol 500mg B125 0 2027-12-01",
        ["Paracetamol 500mg"],
    )
    assert parsed["rows"] == []
    assert len(parsed["errors"]) == 3


def test_norm_date_rejects_impossible_calendar_dates():
    for value in ("2027-02-30", "13/13/2027", "00/2027"):
        try:
            invoice.norm_date(value)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected invalid date {value!r} to be rejected")


def test_two_digit_day_month_expiry_uses_last_day_of_month():
    assert invoice.norm_date("02/2028") == "2028-02-29"
