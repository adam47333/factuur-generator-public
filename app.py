
1 van 3.899
(geen onderwerp)
Inbox

Adam
Bijlagen
01:49 (1 minuut geleden)
aan mij

 1 bijlage
  • Gescand door Gmail
from flask import Flask, render_template, request, send_file, redirect, url_for
import io
from fpdf import FPDF
from datetime import datetime

app = Flask(__name__)

factuur_teller = 1

class FactuurPDF(FPDF):
    def __init__(self, logo_stream=None):
        super().__init__()
        self.logo_stream = logo_stream
        self.add_font('DejaVu', '', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', uni=True)
        self.set_font('DejaVu', '', 12)

    def header_custom(self, bedrijfsnaam, straat, postcode, plaats, land, kvk, btw, iban):
        if self.logo_stream:
            self.image(self.logo_stream, x=90, y=10, w=30)
            self.ln(30)
        self.set_font('DejaVu', 'B', 14)
        self.cell(0, 10, bedrijfsnaam, ln=True, align='L')
        self.set_font('DejaVu', '', 10)
        self.cell(0, 6, straat, ln=True, align='L')
        self.cell(0, 6, f"{postcode} {plaats}", ln=True, align='L')
        self.cell(0, 6, land, ln=True, align='L')
        self.cell(0, 6, f"KvK: {kvk}", ln=True, align='L')
        self.cell(0, 6, f"BTW: {btw}", ln=True, align='L')
        self.cell(0, 6, f"IBAN: {iban}", ln=True, align='L')
        self.ln(5)

    def factuur_body(self, factuurnummer, klantnaam, klant_straat, klant_postcode, klant_plaats, klant_land, diensten, bedrijfsnaam):
        self.set_font('DejaVu', '', 10)
        self.set_fill_color(240, 240, 240)
        self.cell(95, 8, 'Factuurnummer:', border=1, fill=True)
        self.cell(95, 8, factuurnummer, border=1, ln=True)
        self.cell(95, 8, 'Datum:', border=1, fill=True)
        self.cell(95, 8, datetime.today().strftime('%d-%m-%Y'), border=1, ln=True)
        self.ln(10)
        self.set_font('DejaVu', 'B', 12)
        self.cell(0, 10, 'Factuur aan:', ln=True)
        self.set_font('DejaVu', '', 10)
        self.cell(0, 6, klantnaam, ln=True)
        self.cell(0, 6, klant_straat, ln=True)
        self.cell(0, 6, f"{klant_postcode} {klant_plaats}", ln=True)
        self.cell(0, 6, klant_land, ln=True)
        self.ln(10)
        self.set_font('DejaVu', 'B', 10)
        self.cell(80, 8, 'Omschrijving', border=1, align='C')
        self.cell(20, 8, 'Aantal', border=1, align='C')
        self.cell(30, 8, 'Prijs', border=1, align='C')
        self.cell(20, 8, 'BTW%', border=1, align='C')
        self.cell(30, 8, 'Bedrag', border=1, align='C', ln=True)

        self.set_font('DejaVu', '', 10)
        subtotaal = 0
        totaal_btw = 0
        for dienst, aantal, prijs, btw_percentage in diensten:
            bedrag_excl = aantal * prijs
            btw_bedrag = bedrag_excl * (btw_percentage / 100)
            self.cell(80, 8, dienst, border=1)
            self.cell(20, 8, str(aantal), border=1, align='C')
            self.cell(30, 8, f"{prijs:.2f}", border=1, align='C')
            self.cell(20, 8, f"{btw_percentage}%", border=1, align='C')
            self.cell(30, 8, f"{(bedrag_excl + btw_bedrag):.2f}", border=1, align='C', ln=True)
            subtotaal += bedrag_excl
            totaal_btw += btw_bedrag

        totaal = subtotaal + totaal_btw
        self.ln(5)
        self.cell(150, 8, 'Subtotaal (excl. BTW):', border=0, align='R')
        self.cell(30, 8, f"{subtotaal:.2f} €", border=1, align='C', ln=True)
        self.cell(150, 8, 'Totaal BTW:', border=0, align='R')
        self.cell(30, 8, f"{totaal_btw:.2f} €", border=1, align='C', ln=True)
        self.cell(150, 8, 'Totaal (incl. BTW):', border=0, align='R')
        self.set_font('DejaVu', 'B', 10)
        self.cell(30, 8, f"{totaal:.2f} €", border=1, align='C', ln=True)
        self.ln(20)
        self.set_font('DejaVu', 'I', 8)
        self.cell(0, 10, "Gelieve binnen 14 dagen te betalen.", ln=True)
        self.cell(0, 10, "Factuur gegenereerd via Snelfactuurtje 🚀", ln=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Dummy endpoint: normally validate PayPal payment
        return redirect(url_for('generate_invoice'))

    return render_template('index.html')

@app.route('/generate-invoice', methods=['POST'])
def generate_invoice():
    global factuur_teller
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
    user_factuurnummer = request.form.get('factuurnummer', '').strip()
    diensten = []

    index = 0
    while f'dienst_{index}' in request.form:
        dienst = request.form.get(f'dienst_{index}')
        aantal = int(request.form.get(f'aantal_{index}', 1))
        prijs = float(request.form.get(f'prijs_{index}', 0))
        btw_percentage = float(request.form.get(f'btw_{index}', 21))
        diensten.append((dienst, aantal, prijs, btw_percentage))
        index += 1

    if user_factuurnummer:
        factuurnummer = user_factuurnummer
    else:
        factuurnummer = f"SNLF-{datetime.today().year}-{factuur_teller:04d}"
        factuur_teller += 1

    pdf = FactuurPDF()
    pdf.add_page()
    pdf.header_custom(bedrijfsnaam, straat, postcode, plaats, land, kvk, btw, iban)
    pdf.factuur_body(factuurnummer, klantnaam, klant_straat, klant_postcode, klant_plaats, klant_land, diensten, bedrijfsnaam)

    pdf_output = io.BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)

    return send_file(
        pdf_output,
        as_attachment=True,
        download_name=f'{factuurnummer}.pdf',
        mimetype='application/pdf'
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
