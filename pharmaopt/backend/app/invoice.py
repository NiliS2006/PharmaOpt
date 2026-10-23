"""Invoice-to-inventory: OCR (optional) + validated line parser."""
import calendar
import datetime as dt
import io
import re

LINE = re.compile(
    r"^(?P<name>.+?)\s+(?P<batch>[A-Z0-9][A-Z0-9/-]{2,})\s+"
    r"(?P<qty>[+-]?\d+)\s+"
    r"(?P<exp>\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}|\d{1,2}/\d{4})$",
    re.IGNORECASE,
)
DOSAGE_SUFFIXES = {"tab", "tabs", "tablet", "tablets", "cap", "caps", "capsule", "capsules"}


def norm_date(value):
    """Convert supported invoice dates to ISO, rejecting impossible dates."""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return dt.date.fromisoformat(value).isoformat()
    if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", value):
        day, month, year = (int(part) for part in value.split("/"))
        return dt.date(year, month, day).isoformat()
    if re.fullmatch(r"\d{1,2}/\d{4}", value):
        month, year = (int(part) for part in value.split("/"))
        return dt.date(year, month, calendar.monthrange(year, month)[1]).isoformat()
    raise ValueError("Expiry must be YYYY-MM-DD, DD/MM/YYYY, or MM/YYYY.")


def _normalise_name(value):
    value = re.sub(r"(?<=\d)\s+(?=(?:mg|mcg|g|ml|iu)\b)", "", value.lower())
    words = re.sub(r"[^a-z0-9]+", " ", value).split()
    while words and words[-1] in DOSAGE_SUFFIXES:
        words.pop()
    return " ".join(words)


def read_text(raw: bytes, filename: str) -> str:
    if filename.lower().endswith((".png", ".jpg", ".jpeg")):
        try:
            import pytesseract
            from PIL import Image
            return pytesseract.image_to_string(Image.open(io.BytesIO(raw)))
        except Exception as exc:
            raise RuntimeError("Could not read invoice image. Check that OCR is installed and the image is valid.") from exc
    return raw.decode("utf-8", "ignore")


def parse(text, known):
    known_names = {_normalise_name(name): name for name in known}
    rows, errors = [], []
    for line_number, original in enumerate(text.splitlines(), start=1):
        line = original.strip()
        if not line:
            continue
        normalized = re.sub(r"[|\t]+", " ", line)
        match = LINE.fullmatch(normalized)
        if not match:
            errors.append({"line": line_number, "message": "Could not read medicine, batch, quantity, and expiry fields."})
            continue
        try:
            quantity = int(match["qty"])
            if quantity <= 0:
                raise ValueError("Quantity must be a positive whole number.")
            expiry = norm_date(match["exp"])
        except ValueError as exc:
            errors.append({"line": line_number, "message": str(exc)})
            continue
        name = match["name"].strip()
        matched_name = known_names.get(_normalise_name(name))
        rows.append({
            "medicine": matched_name or name,
            "matched": bool(matched_name),
            "batch": match["batch"],
            "qty": quantity,
            "expiry": expiry,
        })
    return {"rows": rows, "errors": errors}
