# -*- coding: utf-8 -*-
import os
from flask import Flask, request, send_file, render_template_string, abort
from fpdf import FPDF
import io
from datetime import datetime
import base64

app = Flask(__name__)

@app.after_request
def add_header(response):
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    return response

class FactuurPDF(FPDF):
    def __init__(self, logo_stream=None):
        super().__init__()
        self.logo_stream = logo_stream
        self.set_auto_page_break(auto=True, margin=20)

    def header_custom(self, bedrijfsnaam, straat, postcode, plaats, land, kvk, btw, iban):
        if self.logo_stream:
            try:
                self.logo_stream.seek(0)
                temp_logo_path = 'temp_logo.png'
                with open(temp_logo_path, 'wb') as f:
                    f.write(self.logo_stream.read())
                self.image(temp_logo_path, x=10, y=10, w=40)
                os.remove(temp_logo_path)
            except Exception as e:
                print(f"Fout bij laden van logo: {e}")

        self.set_font('Helvetica', 'B', 12)
        self.set_xy(150, 10)
        self.multi_cell(50, 5, f"{bedrijfsnaam.upper()}", align='R')
        self.set_font('Helvetica', '', 10)
        self.set_x(150)
        self.multi_cell(50, 5, f"{straat.upper()}\n{postcode} {plaats.upper()}\n{land.upper()}", align='R')
        self.set_x(150)
        self.multi_cell(50, 5, f"KvK: {kvk}\nBTW: {btw}\nIBAN: {iban}", align='R')
        self.ln(15)
        self.set_line_width(0.8)
        self.line(10, 40, 200, 40)
        self.ln(10)

    def factuur_body(self, factuurnummer, klantnaam, klant_straat, klant_postcode, klant_plaats, klant_land, diensten, bedrijfsnaam, handtekening_stream=None):
        self.set_font('Helvetica', '', 10)
        self.set_fill_color(240, 240, 240)
        self.cell(90, 8, "Factuurgegevens", 0, 0, 'L', 1)
        self.cell(0, 8, "Klantgegevens", 0, 1, 'L', 1)

        self.set_font('Helvetica', '', 10)
        self.cell(90, 8, f"Factuurnummer: {factuurnummer}", 0, 0)
        self.cell(0, 8, klantnaam.upper(), 0, 1)
        self.cell(90, 8, f"Datum: {datetime.today().strftime('%d-%m-%Y')}", 0, 0)
        self.cell(0, 8, klant_straat.upper(), 0, 1)
        self.cell(90, 8, "", 0, 0)
        self.cell(0, 8, f"{klant_postcode} {klant_plaats.upper()}", 0, 1)
        self.cell(90, 8, "", 0, 0)
        self.cell(0, 8, klant_land.upper(), 0, 1)
        self.ln(10)

        self.set_fill_color(200, 220, 255)
        self.set_font('Helvetica', 'B', 10)
        self.cell(70, 10, "Omschrijving", 1, 0, 'C', 1)
        self.cell(20, 10, "Aantal", 1, 0, 'C', 1)
        self.cell(30, 10, "Prijs", 1, 0, 'C', 1)
        self.cell(20, 10, "BTW%", 1, 0, 'C', 1)
        self.cell(30, 10, "Bedrag", 1, 1, 'C', 1)

        self.set_font('Helvetica', '', 10)

        subtotaal = 0
        totaal_btw = 0

        for dienst, aantal, prijs, btw_percentage in diensten:
            bedrag_excl = aantal * prijs
            btw_bedrag = bedrag_excl * (btw_percentage / 100)
            bedrag_incl = bedrag_excl + btw_bedrag

            self.cell(70, 10, dienst, 1)
            self.cell(20, 10, str(aantal), 1, 0, 'C')
            self.cell(30, 10, f"{prijs:.2f} €", 1, 0, 'R')
            self.cell(20, 10, f"{btw_percentage}%", 1, 0, 'C')
            self.cell(30, 10, f"{bedrag_incl:.2f} €", 1, 1, 'R')

            subtotaal += bedrag_excl
            totaal_btw += btw_bedrag

        totaal = subtotaal + totaal_btw
        self.ln(5)

        self.set_font('Helvetica', 'B', 11)
        self.set_fill_color(240, 240, 240)
        self.cell(140, 8, "", 0, 0)
        self.cell(30, 8, "Subtotaal:", 1, 0, 'R', 1)
        self.cell(0, 8, f"{subtotaal:.2f} €", 1, 1, 'R')
        self.cell(140, 8, "", 0, 0)
        self.cell(30, 8, "Totaal BTW:", 1, 0, 'R', 1)
        self.cell(0, 8, f"{totaal_btw:.2f} €", 1, 1, 'R')
        self.cell(140, 8, "", 0, 0)
        self.cell(30, 8, "Totaal:", 1, 0, 'R', 1)
        self.cell(0, 8, f"{totaal:.2f} €", 1, 1, 'R')
        self.ln(15)

        self.set_font('Helvetica', '', 11)
        self.cell(0, 8, "Met vriendelijke groet,", ln=True)
        self.cell(0, 8, bedrijfsnaam.upper(), ln=True)

        if handtekening_stream:
            if self.get_y() > 230:
                self.add_page()
            self.ln(10)
            temp_handtekening_path = 'temp_handtekening.png'
            with open(temp_handtekening_path, 'wb') as f:
                f.write(handtekening_stream.getbuffer())
            self.image(temp_handtekening_path, x=10, y=self.get_y(), w=60)
            os.remove(temp_handtekening_path)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f"Pagina {self.page_no()}/{{nb}}", align='C')

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
                logo_stream.seek(0)

            handtekening_data = request.form.get('handtekening')
            handtekening_stream = None
            if handtekening_data and handtekening_data.startswith("data:image/png;base64,"):
                header, encoded = handtekening_data.split(",", 1)
                handtekening_bytes = base64.b64decode(encoded)
                handtekening_stream = io.BytesIO(handtekening_bytes)

            pdf = FactuurPDF(logo_stream)
            pdf.alias_nb_pages()
            pdf.add_page()
            pdf.header_custom(bedrijfsnaam, straat, postcode, plaats, land, kvk, btw, iban)
            pdf.factuur_body(factuurnummer, klantnaam, klant_straat, klant_postcode, klant_plaats, klant_land, diensten, bedrijfsnaam, handtekening_stream)

            pdf_data = pdf.output(dest='S').encode('latin-1')

            return send_file(
                io.BytesIO(pdf_data),
                as_attachment=True,
                download_name=f'{factuurnummer}.pdf',
                mimetype='application/pdf'
            )
        except Exception as e:
            abort(400, description=f"Fout bij verwerken van factuur: {e}")

    html_content = '''
<!doctype html>
<html lang="nl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Snelfactuurtje</title>
  <link href="https://fonts.googleapis.com/css2?family=Poppins&display=swap" rel="stylesheet">
  <style>/* CSS code hier zoals je originele */</style>
</head>
<body>
  <!-- HTML Formulier code hier -->
</body>
</html>
'''
    return render_template_string(html_content)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
