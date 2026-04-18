import io
import os
import sys
from pathlib import Path
from flask import Flask, render_template, request, send_file, jsonify
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas as rl_canvas


def resource_path(relative: str) -> str:
    """Absoluter Pfad zu einer Ressource – funktioniert sowohl im Dev-Modus
    als auch in einer PyInstaller-gebündelten .exe."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative)


app = Flask(
    __name__,
    template_folder=resource_path("templates"),
    static_folder=resource_path("static"),
)
LOGO_PATH = resource_path(os.path.join("static", "logo.png"))

# ── Page geometry ─────────────────────────────────────────────────────────────
PW, PH = A4          # 595.28 × 841.89 pt
LM = 20 * mm         # left margin  (56.7 pt)
RM = 20 * mm         # right margin
CX  = LM             # content left x
CXR = PW - RM        # content right x
CW  = CXR - CX       # content width  ≈ 481.9 pt

# ── Brand colours ─────────────────────────────────────────────────────────────
DARK_BLUE  = colors.HexColor("#1a3a5c")
LIGHT_BLUE = colors.HexColor("#d6e4f0")
TABLE_BLUE = colors.HexColor("#3a7abf")
GRAY       = colors.HexColor("#cccccc")
TEXT_GRAY  = colors.HexColor("#555555")

# ── Fixed company data ────────────────────────────────────────────────────────
FIRMA = dict(
    name    = "Cleancare Systemreinigung UG",
    add1    = "Krugkamp 10",
    add2    = "38723, Seesen",
    tel     = "0151 / 4075 0808",
    email   = "cleancare@e.mail.de",
    sender1 = "Aral Staion",
    sender2 = "Steffen Jordan",
    iban    = "DE 90 2595 0130 0034 6518 36",
    bic     = "NOLADE 21 HIK",
    hrb     = "HRB 204423",
    gericht = "AG Braunschweig",
    steuernr= "21/203/6087",
    glaub   = "DE72 ZZZ 0000 1723 042",
    gf      = "Armin Herbst",
)


def num(n: float) -> str:
    """German number format without € (e.g. '344,00')."""
    return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def build_pdf(data: dict) -> bytes:
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)

    # ── Drawing helpers ──────────────────────────────────────────────────────
    # y_top: distance from page TOP (increases downward), converted to RL y.
    def rl(y_top: float) -> float:
        return PH - y_top

    def txt(x: float, y_top: float, text: str,
            font="Helvetica", size=9,
            color=colors.black, align="left") -> None:
        c.setFillColor(color)
        c.setFont(font, size)
        ry = rl(y_top)
        if align == "right":
            c.drawRightString(x, ry, text)
        elif align == "center":
            c.drawCentredString(x, ry, text)
        else:
            c.drawString(x, ry, text)
        c.setFillColor(colors.black)

    def hline(y_top: float, x0=CX, x1=CXR,
              color=GRAY, lw=0.5) -> None:
        c.setStrokeColor(color)
        c.setLineWidth(lw)
        c.line(x0, rl(y_top), x1, rl(y_top))

    def filled_rect(x: float, y_top: float, w: float, h: float,
                    fill=None, stroke=None, lw=0.4) -> None:
        c.setLineWidth(lw)
        if fill:
            c.setFillColor(fill)
        if stroke:
            c.setStrokeColor(stroke)
        c.rect(x, rl(y_top + h), w, h,
               fill=1 if fill else 0,
               stroke=1 if stroke else 0)
        c.setFillColor(colors.black)

    # ── 0. DECORATIVE CORNER ELEMENTS (drawn first, behind content) ───────────
    # Bottom-left: single solid circle
    c.setFillColor(TABLE_BLUE)
    c.circle(0, 0, 105, fill=1, stroke=0)

    # Top-right: single solid circle, same blue
    c.setFillColor(TABLE_BLUE)
    c.circle(PW, PH, 60, fill=1, stroke=0)

    # ── 1. LOGO — small, top-left corner ──────────────────────────────────────
    LOGO_H = 78                          # pt — height of logo image
    LOGO_W = LOGO_H * (512 / 135)       # maintain aspect ratio ≈ 296 pt
    LOGO_TOP = 10 * mm                  # distance from top of page

    if os.path.exists(LOGO_PATH):
        c.drawImage(LOGO_PATH, CX, rl(LOGO_TOP + LOGO_H), LOGO_W, LOGO_H,
                    preserveAspectRatio=False, mask="auto")

    Y = LOGO_TOP + LOGO_H + 10 * mm     # content starts below logo + gap

    # ── 2. ADDRESS SECTION ────────────────────────────────────────────────────
    # Right column: company details (fixed height = 5 lines × 13 pt)
    RIGHT_LINES = [
        (FIRMA["name"],  "Helvetica-Bold", 9.5),
        (FIRMA["add1"],  "Helvetica",      9),
        (FIRMA["add2"],  "Helvetica",      9),
        (FIRMA["tel"],   "Helvetica",      9),
        (FIRMA["email"], "Helvetica",      9),
    ]
    for i, (text, font, size) in enumerate(RIGHT_LINES):
        txt(CXR, Y + 9 + i * 13, text, font=font, size=size, align="right")

    # Left column: customer address only (dynamic)
    kunde_lines = [l for l in (data.get("kunde") or "").split("\n") if l.strip()]
    cust_y = Y + 9
    for line in kunde_lines[:5]:
        txt(CX, cust_y, line.strip(), size=9)
        cust_y += 13

    addr_section_h = max(9 + 4 * 13, cust_y - Y - 1) + 6 * mm
    Y += addr_section_h

    # ── 3. RECHNUNG TITLE + METADATA ─────────────────────────────────────────
    txt(CX,  Y + 14, "Rechnung", font="Helvetica-Bold", size=16)
    txt(CXR, Y + 14, data.get("datum") or "", size=9.5, align="right")
    Y += 20

    txt(CX,  Y + 11, data.get("rechnungsnr") or "", font="Helvetica-Bold", size=10)
    if data.get("kundennr"):
        txt(CXR, Y + 11, f'Kd. Nr. {data["kundennr"]}', size=9.5, align="right")
    Y += 18

    # ── 4. EINSATZORT (optional) ──────────────────────────────────────────────
    einsatz_parts = []
    if data.get("einsatzort_name"):
        einsatz_parts.append(data["einsatzort_name"].strip())
    if data.get("einsatzort_strasse"):
        einsatz_parts.append(data["einsatzort_strasse"].strip())
    plz = (data.get("einsatzort_plz") or "").strip()
    ort = (data.get("einsatzort_ort") or "").strip()
    if plz or ort:
        einsatz_parts.append(f"{plz} {ort}".strip())

    if einsatz_parts:
        txt(CX, Y + 9, "Einsatzort:", font="Helvetica-Bold", size=8.5, color=TEXT_GRAY)
        Y += 12
        txt(CX + 4, Y + 9, einsatz_parts[0], size=9)
        Y += 12
        if len(einsatz_parts) > 1:
            addr_line = ", ".join(einsatz_parts[1:])
            txt(CX + 4, Y + 9, addr_line, size=9)
            Y += 12
        Y += 4 * mm

    Y += 2 * mm    # small gap before table

    # ── 5. TABLE ─────────────────────────────────────────────────────────────
    # Column x boundaries
    c_leis_w = CW * 0.50
    c_anz_w  = CW * 0.11
    c_ep_w   = CW * 0.195
    c_gp_w   = CW * 0.195

    x_anz = CX  + c_leis_w
    x_ep  = x_anz + c_anz_w
    x_gp  = x_ep  + c_ep_w   # = CXR

    # Text x positions (left-pad 5pt, or right-pad 5pt for right-align)
    TX_LEIS = CX    + 5   # Leistung: left-aligned
    TX_ANZ  = x_anz + 5   # Anzahl:   left-aligned
    TX_EP_R = x_gp  - 5   # Einzelpreis: right-aligned to RIGHT edge of EP column
    TX_GP_R = CXR   - 5   # Gesamtpreis: right-aligned to right edge of table

    HEADER_H = 10 * mm
    ROW_H    = 9.5 * mm

    def draw_col_separators(y_top: float, h: float) -> None:
        c.setStrokeColor(GRAY)
        c.setLineWidth(0.3)
        for sx in (x_anz, x_ep, x_gp):
            c.line(sx, rl(y_top), sx, rl(y_top + h))

    # Header row
    filled_rect(CX, Y, CW, HEADER_H, fill=TABLE_BLUE)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    hy = rl(Y + HEADER_H * 0.62)
    c.drawString(TX_LEIS,    hy, "Leistung")
    c.drawString(TX_ANZ,     hy, "Anzahl")
    c.drawRightString(TX_EP_R, hy, "Einzelpreis €")
    c.drawRightString(TX_GP_R, hy, "Gesamtpreis €")
    c.setFillColor(colors.black)
    draw_col_separators(Y, HEADER_H)
    Y += HEADER_H

    # Service rows
    positionen = data.get("positionen") or []
    netto = 0.0

    for i, pos in enumerate(positionen):
        try:
            anzahl = float(str(pos.get("anzahl") or "1").replace(",", "."))
            ep     = float(str(pos.get("einzelpreis") or "0").replace(",", "."))
        except ValueError:
            anzahl, ep = 1.0, 0.0
        gp = anzahl * ep
        netto += gp

        bg = LIGHT_BLUE if i % 2 == 0 else colors.white
        filled_rect(CX, Y, CW, ROW_H, fill=bg)
        hline(Y + ROW_H, color=GRAY, lw=0.3)
        draw_col_separators(Y, ROW_H)

        ty = Y + ROW_H * 0.60
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 9)
        c.drawString(TX_LEIS,       rl(ty), pos.get("leistung") or "")
        c.drawString(TX_ANZ,        rl(ty), str(pos.get("anzahl") or ""))
        c.drawRightString(TX_EP_R,  rl(ty), num(ep))
        c.drawRightString(TX_GP_R,  rl(ty), num(gp))
        Y += ROW_H

    # Gesamt-Netto row (inside table)
    mwst_satz    = float(data.get("mwst") or "19")
    mwst_betrag  = netto * mwst_satz / 100
    brutto       = netto + mwst_betrag

    filled_rect(CX, Y, CW, ROW_H, fill=colors.white)
    hline(Y + ROW_H, color=GRAY, lw=0.3)
    draw_col_separators(Y, ROW_H)
    ty = Y + ROW_H * 0.60
    c.setFont("Helvetica", 9)
    c.drawString(TX_LEIS,      rl(ty), "Gesamt Netto")
    c.drawRightString(TX_EP_R, rl(ty), num(netto))
    c.drawRightString(TX_GP_R, rl(ty), num(netto))
    Y += ROW_H

    # MwSt row (inside table)
    filled_rect(CX, Y, CW, ROW_H, fill=LIGHT_BLUE)
    hline(Y + ROW_H, color=GRAY, lw=0.3)
    draw_col_separators(Y, ROW_H)
    ty = Y + ROW_H * 0.60
    c.setFont("Helvetica", 9)
    c.drawString(TX_LEIS,      rl(ty), f"Mwst. {int(mwst_satz)}%")
    c.drawString(TX_ANZ,       rl(ty), "1")
    c.drawRightString(TX_GP_R, rl(ty), num(mwst_betrag))
    Y += ROW_H

    # Table outer border
    table_total_h = HEADER_H + (len(positionen) + 2) * ROW_H
    c.setStrokeColor(GRAY)
    c.setLineWidth(0.5)
    c.rect(CX, rl(Y), CW, table_total_h, fill=0, stroke=1)

    Y += 6 * mm

    # ── 6. GESAMT ─────────────────────────────────────────────────────────────
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(DARK_BLUE)
    c.drawString(TX_EP_R - 40,  rl(Y + 10), "GESAMT")
    c.drawRightString(TX_GP_R,  rl(Y + 10), num(brutto))
    c.setFillColor(colors.black)

    # Blue underline below GESAMT
    c.setStrokeColor(TABLE_BLUE)
    c.setLineWidth(2)
    c.line(TX_EP_R - 45, rl(Y + 14), CXR, rl(Y + 14))

    Y += 22 * mm

    # ── 7. FOOTER ─────────────────────────────────────────────────────────────
    # Always anchored at bottom; separator line at y=635 from top (RL y≈207)
    FOOTER_SEP_Y = 635    # pdfplumber-style distance from top

    hline(FOOTER_SEP_Y, color=GRAY, lw=0.5)

    footer_items = [
        ("Bitte überweisen Sie den Rechnungsbetrag zeitnah auf das unten genannte Konto."
         "  Rechnungsdatum ist Leistungsdatum.", "Helvetica", 8.5),
        ("Vielen Dank für Ihren Auftrag !", "Helvetica-Bold", 8.5),
        ("", None, 0),
        (f"CleanCare Systemreinigung UG (haftungsbeschränkt)  "
         f"{FIRMA['hrb']} {FIRMA['gericht']}", "Helvetica", 8),
        (f"Bankverbindung : IBAN: {FIRMA['iban']}  -  BIC {FIRMA['bic']}",
         "Helvetica", 8),
        ("", None, 0),
        (f"Gerichtsstand: {FIRMA['gericht']}  -  Steuernummer: {FIRMA['steuernr']}",
         "Helvetica", 8),
        (f"Gläubiger ID : {FIRMA['glaub']}", "Helvetica", 8),
        (f"Geschäftsführer : {FIRMA['gf']}", "Helvetica", 8),
    ]

    fy = FOOTER_SEP_Y + 8
    for text, font, size in footer_items:
        if text:
            txt(CX, fy, text, font=font, size=size)
        fy += 11

    c.save()
    buf.seek(0)
    return buf.read()


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/pdf", methods=["POST"])
def generate_pdf():
    form = request.form
    positionen = []
    for l, a, p in zip(
        form.getlist("leistung[]"),
        form.getlist("anzahl[]"),
        form.getlist("einzelpreis[]"),
    ):
        if l.strip():
            positionen.append({"leistung": l, "anzahl": a, "einzelpreis": p})

    # Convert ISO date (2026-04-18) → German format (18.04.2026)
    datum_raw = form.get("datum", "")
    if datum_raw and len(datum_raw) == 10 and datum_raw[4] == "-":
        y, m, d = datum_raw.split("-")
        datum_fmt = f"{d}.{m}.{y}"
    else:
        datum_fmt = datum_raw

    data = {
        "datum":              datum_fmt,
        "rechnungsnr":        form.get("rechnungsnr", ""),
        "kundennr":           form.get("kundennr", ""),
        "kunde":              form.get("kunde", ""),
        "einsatzort_name":    form.get("einsatzort_name", ""),
        "einsatzort_strasse": form.get("einsatzort_strasse", ""),
        "einsatzort_plz":     form.get("einsatzort_plz", ""),
        "einsatzort_ort":     form.get("einsatzort_ort", ""),
        "mwst":               form.get("mwst", "19"),
        "positionen":         positionen,
    }

    pdf_bytes = build_pdf(data)
    filename = f"Rechnung_{data['rechnungsnr'] or 'neu'}.pdf"

    # Desktop-Modus (PyInstaller .exe): PDF direkt in Downloads speichern
    if getattr(sys, "frozen", False):
        downloads = Path.home() / "Downloads"
        downloads.mkdir(exist_ok=True)
        filepath = downloads / filename
        with open(filepath, "wb") as fh:
            fh.write(pdf_bytes)
        return jsonify({"success": True, "filename": filename, "path": str(filepath)})

    # Browser-Modus: PDF als Download streamen
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
