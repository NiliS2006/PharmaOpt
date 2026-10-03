import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app import invoice
def test_parse():
    rows = invoice.parse("Paracetamol 500mg  B123  500  2027-03-31\nORS Sachet  X77  100  03/2027\nFoo Bar  Z99  5  2027-01-01", ["Paracetamol 500mg", "ORS Sachet"])
    assert [r["matched"] for r in rows] == [True, True, False] and rows[1]["expiry"] == "2027-03-28" and rows[0]["qty"] == 500
