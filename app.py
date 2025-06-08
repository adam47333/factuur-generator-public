import os
import io
import base64
from flask import Flask, request, send_file, render_template_string, abort
from fpdf import FPDF
from datetime import datetime

app = Flask(__name__)

class FactuurPDF(FPDF):
    def __init__(self, logo_stream=None):
        super().__init__()
        self.logo_stream = logo_stream

    def header_custom(self, bedrijfsnaam, straat, postcode, plaats, land, kvk, btw, iban):
        if self.logo_stream:
            try:
                self.image(self.logo_stream, x=10, y=8, w=40)
            except Exception as e:
                print(f"Fout bij laden van logo: {e}")
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 10, bedrijfsnaam, ln=True, align='R')
        self.set_font('Helvetica', '', 11)
        self.cell(0, 8, straat, ln=True, align='R')
        self.cell(0, 8, f"{postcode} {plaats}", ln=True, align='R')
        self.cell(0, 8, land, ln=True, align='R')
        self.cell(0, 8, f"KvK: {kvk} | BTW: {btw}", ln=True, align='R')
        self.cell(0, 8, f"IBAN: {iban}", ln=True, align='R')
        self.ln(5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(10)

    def factuur_body(self, factuurnummer, klantnaam, klant_straat, klant_postcode, klant_plaats, klant_land, diensten, bedrijfsnaam):
        self.set_font('Helvetica', '', 11)
        self.cell(0, 8, f"Factuurnummer: {factuurnummer}", ln=True)
        self.cell(0, 8, f"Datum: {datetime.today().strftime('%d-%m-%Y')}", ln=True)
        self.ln(5)
        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 8, "Factuur aan:", ln=True)
        self.set_font('Helvetica', '', 11)
        self.cell(0, 8, klantnaam, ln=True)
        self.cell(0, 8, klant_straat, ln=True)
        self.cell(0, 8, f"{klant_postcode} {klant_plaats}", ln=True)
        self.cell(0, 8, klant_land, ln=True)
        self.ln(10)

        self.set_fill_color(230, 230, 250)
        self.set_font('Helvetica', 'B', 11)
        self.cell(80, 10, "Omschrijving", border=1, align='C', fill=True)
        self.cell(20, 10, "Aantal", border=1, align='C', fill=True)
        self.cell(30, 10, "Prijs", border=1, align='C', fill=True)
        self.cell(20, 10, "BTW%", border=1, align='C', fill=True)
        self.cell(30, 10, "Bedrag", border=1, align='C', fill=True)
        self.ln()

        self.set_font('Helvetica', '', 11)
        subtotaal = 0
        totaal_btw = 0
        for dienst, aantal, prijs, btw_percentage in diensten:
            bedrag_excl = aantal * prijs
            btw_bedrag = bedrag_excl * (btw_percentage / 100)
            bedrag_incl = bedrag_excl + btw_bedrag
            self.cell(80, 10, dienst, border=1)
            self.cell(20, 10, str(aantal), border=1, align='C')
            self.cell(30, 10, f"{prijs:.2f}", border=1, align='R')
            self.cell(20, 10, f"{btw_percentage}%", border=1, align='C')
            self.cell(30, 10, f"{bedrag_incl:.2f}", border=1, align='R')
            self.ln()
            subtotaal += bedrag_excl
            totaal_btw += btw_bedrag

        totaal = subtotaal + totaal_btw
        self.ln(5)
        self.set_font('Helvetica', 'B', 12)
        self.cell(150, 10, "Subtotaal (excl. BTW):", align='R')
        self.cell(30, 10, f"{subtotaal:.2f} EUR", ln=True, align='R')
        self.cell(150, 10, "Totaal BTW:", align='R')
        self.cell(30, 10, f"{totaal_btw:.2f} EUR", ln=True, align='R')
        self.cell(150, 10, "Totaal (incl. BTW):", align='R')
        self.cell(30, 10, f"{totaal:.2f} EUR", ln=True, align='R')
        self.ln(20)
        self.set_font('Helvetica', '', 11)
        self.cell(0, 8, "Met vriendelijke groet,", ln=True)
        self.cell(0, 8, bedrijfsnaam, ln=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            factuurnummer = request.form['factuurnummer']
            bedrijfsnaam = request.form['bedrijfsnaam']
            straat = request.form['straat']
            postcode = request.form['postcode']
            plaats = request.form['plaats']
            land = request.form['land']
            kvk = request.form['kvk']
            btw = request.form['btw']
            iban = request.form['iban']

            klantnaam = request.form['klantnaam']
            klant_straat = request.form['klant_straat']
            klant_postcode = request.form['klant_postcode']
            klant_plaats = request.form['klant_plaats']
            klant_land = request.form['klant_land']

            diensten = []
            index = 0
            while f'dienst_{index}' in request.form:
                dienst = request.form.get(f'dienst_{index}')
                aantal = int(request.form.get(f'aantal_{index}', 1))
                prijs = float(request.form.get(f'prijs_{index}', 0))
                btw_percentage = float(request.form.get(f'btw_{index}', 21))
                diensten.append((dienst, aantal, prijs, btw_percentage))
                index += 1

            logo_file = request.files.get('logo')
            logo_stream = None
            if logo_file and logo_file.filename:
                logo_stream = io.BytesIO(logo_file.read())
                logo_stream.name = 'logo.png'

            handtekening_data = request.form.get('handtekening')
            handtekening_stream = None
            if handtekening_data and ',' in handtekening_data:
                header, encoded = handtekening_data.split(",", 1)
                handtekening_bytes = base64.b64decode(encoded)
                handtekening_stream = io.BytesIO(handtekening_bytes)
                handtekening_stream.name = 'handtekening.png'

            pdf = FactuurPDF(logo_stream)
            pdf.add_page()
            pdf.header_custom(bedrijfsnaam, straat, postcode, plaats, land, kvk, btw, iban)
            pdf.factuur_body(factuurnummer, klantnaam, klant_straat, klant_postcode, klant_plaats, klant_land, diensten, bedrijfsnaam)

            if handtekening_stream:
                pdf.ln(10)
                pdf.set_font('Helvetica', 'B', 12)
                pdf.cell(0, 10, "Handtekening:", ln=True)
                pdf.image(handtekening_stream, x=10, y=pdf.get_y(), w=50)

            pdf_data = pdf.output(dest='S').encode('latin-1')

            return send_file(
                io.BytesIO(pdf_data),
                as_attachment=True,
                download_name=f'{factuurnummer}.pdf',
                mimetype='application/pdf'
            )
        except Exception as e:
            abort(400, description=f"Fout bij verwerken van factuur: {e}")

    # Volgende stap: HTML string
