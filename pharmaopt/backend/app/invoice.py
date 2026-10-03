"""Invoice-to-inventory: OCR (optional) + line parser. Output is always shown to the pharmacist for verification."""
import re, io
LINE = re.compile(r"^(?P<name>[A-Za-z][A-Za-z0-9 .\-]+?)\s+(?P<batch>[A-Z0-9\-]{3,})\s+(?P<qty>\d+)\s+(?P<exp>\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}/\d{4})\b")

def norm_date(s):
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s): return s
    p = s.split("/")
    return f"{p[2]}-{p[1]}-{p[0]}" if len(p) == 3 else f"{p[1]}-{p[0]}-28"

def read_text(raw: bytes, filename: str) -> str:
    if filename.lower().endswith((".png", ".jpg", ".jpeg")):
        try:
            import pytesseract; from PIL import Image
            return pytesseract.image_to_string(Image.open(io.BytesIO(raw)))
        except Exception: return ""
    return raw.decode("utf-8", "ignore")

def parse(text, known):
    k = {n.lower(): n for n in known}; rows = []
    for line in text.splitlines():
        m = LINE.match(line.strip())
        if m:
            name = k.get(m["name"].strip().lower())
            rows.append(dict(medicine=name or m["name"].strip(), matched=bool(name), batch=m["batch"], qty=int(m["qty"]), expiry=norm_date(m["exp"])))
    return rows
