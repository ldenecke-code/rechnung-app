import io
from flask import Flask, render_template, request, send_file
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER

app = Flask(__name__)

# ── Feste Firmendaten ────────────────────────────────────────────────────────
FIRMA = {
    "name":       "Cleancare Systemreinigung UG",
    "adresse1":   "Aral Station",
    "adresse2":   "Krugkamp 10",
    "adresse3":   "37079 Göttingen",
    "kontakt":    "Steffen Jordan",
    "tel":        "0151 / 4075 0808",
    "email":      "cleancare@e.mail.de",
    "iban":       "DE90 2595 0130 0034 6518 36",
    "bic":        "NOLADE21HIK",
    "hrb":        "HRB 204423",
    "gericht":    "AG Braunschweig",
    "steuernr":   "21/203/6087",
    "glaeubiger": "DE72ZZZ00001723042",
    "gf":         "Armin Herbst",
}


def format_euro(value: float) -> str:
    return f"{value:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def build_pdf(data: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=15 * mm,
        bottomMargin=20 * mm,
    )

    W = A4[0] - 40 * mm  # usable width

    # ── Styles ────────────────────────────────────────────────────────────────
    def sty(name, **kw):
        base = ParagraphStyle(name)
        base.fontName = kw.get("font", "Helvetica")
        base.fontSize = kw.get("size", 10)
        base.leading = kw.get("leading", base.fontSize * 1.3)
        base.alignment = kw.get("align", TA_LEFT)
        base.textColor = kw.get("color", colors.black)
        base.spaceAfter = kw.get("after", 0)
        base.spaceBefore = kw.get("before", 0)
        return base

    s_firma_name  = sty("fn",  font="Helvetica-Bold", size=14)
    s_normal      = sty("n",   size=9)
    s_small       = sty("sm",  size=8)
    s_small_right = sty("smr", size=8,  align=TA_RIGHT)
    s_bold        = sty("b",   font="Helvetica-Bold", size=9)
    s_bold_right  = sty("br",  font="Helvetica-Bold", size=10, align=TA_RIGHT)
    s_title       = sty("t",   font="Helvetica-Bold", size=16, before=4*mm, after=2*mm)
    s_meta        = sty("m",   size=9)
    s_meta_right  = sty("mr",  size=9, align=TA_RIGHT)
    s_footer      = sty("f",   size=7.5, color=colors.HexColor("#444444"))
    s_footer_bold = sty("fb",  font="Helvetica-Bold", size=7.5)

    story = []

    # ── Kopfzeile: Firma links | Leer rechts ──────────────────────────────────
    firma_block = [
        Paragraph(FIRMA["name"], s_firma_name),
        Paragraph(FIRMA["adresse1"], s_normal),
        Paragraph(FIRMA["adresse2"], s_normal),
        Paragraph(FIRMA["adresse3"], s_normal),
        Spacer(1, 3 * mm),
        Paragraph(FIRMA["kontakt"], s_normal),
        Paragraph(f'Tel.: {FIRMA["tel"]}', s_normal),
        Paragraph(f'E-Mail: {FIRMA["email"]}', s_normal),
    ]

    header_table = Table(
        [[firma_block, ""]],
        colWidths=[W * 0.55, W * 0.45],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 6 * mm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cccccc")))
    story.append(Spacer(1, 4 * mm))

    # ── Empfänger links | Rechnungsinfo rechts ────────────────────────────────
    empfaenger_lines = (data.get("kunde", "") or "").strip().split("\n")
    empfaenger_paras = [Paragraph(line, s_normal) for line in empfaenger_lines if line.strip()]

    meta_right = []
    if data.get("einsatzort"):
        meta_right.append(Paragraph(f'Einsatzort: <b>{data["einsatzort"]}</b>', s_meta_right))
    meta_right.append(Paragraph(f'Rechnungsdatum: {data.get("datum", "")}', s_meta_right))
    meta_right.append(Paragraph(f'Rechnungsnummer: {data.get("rechnungsnr", "")}', s_meta_right))
    if data.get("kundennr"):
        meta_right.append(Paragraph(f'Kd.-Nr.: {data["kundennr"]}', s_meta_right))

    addr_table = Table(
        [[empfaenger_paras, meta_right]],
        colWidths=[W * 0.55, W * 0.45],
    )
    addr_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(addr_table)
    story.append(Spacer(1, 6 * mm))

    # ── Titel ─────────────────────────────────────────────────────────────────
    story.append(Paragraph("Rechnung", s_title))

    # ── Positionstabelle ──────────────────────────────────────────────────────
    col_w = [W * 0.52, W * 0.12, W * 0.18, W * 0.18]
    header_row = [
        Paragraph("Leistung", s_bold),
        Paragraph("Anzahl", s_bold),
        Paragraph("Einzelpreis", s_bold),
        Paragraph("Gesamtpreis", s_bold),
    ]
    rows = [header_row]

    netto = 0.0
    positionen = data.get("positionen", [])
    for pos in positionen:
        try:
            anzahl = float(str(pos.get("anzahl", "1")).replace(",", "."))
            einzelpreis = float(str(pos.get("einzelpreis", "0")).replace(",", "."))
        except ValueError:
            continue
        gesamt = anzahl * einzelpreis
        netto += gesamt

        leistung_str = pos.get("leistung", "")
        rows.append([
            Paragraph(leistung_str, s_normal),
            Paragraph(str(pos.get("anzahl", "1")), s_normal),
            Paragraph(format_euro(einzelpreis), s_normal),
            Paragraph(format_euro(gesamt), s_normal),
        ])

    pos_table = Table(rows, colWidths=col_w)
    pos_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
        ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4f8")]),
        ("GRID",        (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(pos_table)
    story.append(Spacer(1, 4 * mm))

    # ── Summenblock ───────────────────────────────────────────────────────────
    mwst_satz = float(data.get("mwst", "19"))
    mwst_betrag = netto * (mwst_satz / 100)
    gesamt_brutto = netto + mwst_betrag

    sum_rows = [
        [Paragraph("Gesamt Netto:", s_bold_right), Paragraph(format_euro(netto), s_bold_right)],
        [Paragraph(f"MwSt. {int(mwst_satz)}%:", s_meta_right),  Paragraph(format_euro(mwst_betrag), s_meta_right)],
        [Paragraph("GESAMT:", s_bold_right),        Paragraph(format_euro(gesamt_brutto), s_bold_right)],
    ]
    sum_table = Table(sum_rows, colWidths=[W * 0.75, W * 0.25])
    sum_table.setStyle(TableStyle([
        ("LINEABOVE",  (0, 2), (-1, 2), 1, colors.HexColor("#1a3a5c")),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(sum_table)
    story.append(Spacer(1, 6 * mm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cccccc")))
    story.append(Spacer(1, 4 * mm))

    # ── Fußzeile ──────────────────────────────────────────────────────────────
    footer_text = (
        "Bitte überweisen Sie den Rechnungsbetrag zeitnah auf das unten genannte Konto.&nbsp;&nbsp;"
        "Rechnungsdatum ist Leistungsdatum.&nbsp;&nbsp;"
        "<b>Vielen Dank für Ihren Auftrag!</b>"
    )
    story.append(Paragraph(footer_text, s_footer))
    story.append(Spacer(1, 3 * mm))

    bank_cols = [W * 0.5, W * 0.5]
    bank_rows = [
        [
            Paragraph(f'<b>IBAN:</b> {FIRMA["iban"]}', s_footer),
            Paragraph(f'<b>BIC:</b> {FIRMA["bic"]}', s_footer),
        ],
        [
            Paragraph(
                f'{FIRMA["name"]} ({FIRMA["hrb"]}, {FIRMA["gericht"]}) | '
                f'St.-Nr.: {FIRMA["steuernr"]} | GF: {FIRMA["gf"]}',
                s_footer
            ),
            Paragraph(f'Gläubiger-ID: {FIRMA["glaeubiger"]}', s_footer),
        ],
    ]
    bank_table = Table(bank_rows, colWidths=bank_cols)
    bank_table.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(bank_table)

    doc.build(story)
    buf.seek(0)
    return buf.read()


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/pdf", methods=["POST"])
def generate_pdf():
    form = request.form

    positionen = []
    leistungen = form.getlist("leistung[]")
    anzahlen   = form.getlist("anzahl[]")
    preise     = form.getlist("einzelpreis[]")

    for l, a, p in zip(leistungen, anzahlen, preise):
        if l.strip():
            positionen.append({"leistung": l, "anzahl": a, "einzelpreis": p})

    data = {
        "datum":       form.get("datum", ""),
        "rechnungsnr": form.get("rechnungsnr", ""),
        "kundennr":    form.get("kundennr", ""),
        "kunde":       form.get("kunde", ""),
        "einsatzort":  form.get("einsatzort", ""),
        "mwst":        form.get("mwst", "19"),
        "positionen":  positionen,
    }

    pdf_bytes = build_pdf(data)
    filename = f"Rechnung_{data['rechnungsnr'] or 'neu'}.pdf"

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
