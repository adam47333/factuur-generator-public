import os
from flask import Flask, request, send_file, render_template_string
from fpdf import FPDF
import io
from datetime import datetime

app = Flask(__name__)

factuur_teller = 1

class FactuurPDF(FPDF):
    def __init__(self, logo_stream=None):
        super().__init__()
        self.logo_stream = logo_stream

    def header_custom(self, bedrijfsnaam, straat, postcode, plaats, land, kvk, btw, iban):
        if self.logo_stream:
            self.image(self.logo_stream, x=90, y=10, w=30)
            self.ln(30)
        self.set_font('Helvetica', 'B', 14)
        self.cell(0, 10, bedrijfsnaam, ln=True, align='L')
        self.set_font('Helvetica', '', 10)
        self.cell(0, 6, straat, ln=True, align='L')
        self.cell(0, 6, f"{postcode} {plaats}", ln=True, align='L')
        self.cell(0, 6, land, ln=True, align='L')
        self.cell(0, 6, f"KvK: {kvk}", ln=True, align='L')
        self.cell(0, 6, f"BTW: {btw}", ln=True, align='L')
        self.cell(0, 6, f"IBAN: {iban}", ln=True, align='L')
        self.ln(5)

    def factuur_body(self, factuurnummer, klantnaam, klant_straat, klant_postcode, klant_plaats, klant_land, diensten, bedrijfsnaam):
        self.set_font('Helvetica', '', 10)
        self.set_fill_color(240, 240, 240)
        self.cell(95, 8, 'Factuurnummer:', border=1, fill=True)
        self.cell(95, 8, factuurnummer, border=1, ln=True)
        self.cell(95, 8, 'Datum:', border=1, fill=True)
        self.cell(95, 8, datetime.today().strftime('%d-%m-%Y'), border=1, ln=True)
        self.ln(10)
        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 10, 'Factuur aan:', ln=True)
        self.set_font('Helvetica', '', 10)
        self.cell(0, 6, klantnaam, ln=True)
        self.cell(0, 6, klant_straat, ln=True)
        self.cell(0, 6, f"{klant_postcode} {klant_plaats}", ln=True)
        self.cell(0, 6, klant_land, ln=True)
        self.ln(10)
        self.set_font('Helvetica', 'B', 10)
        self.cell(80, 8, 'Omschrijving', border=1, align='C')
        self.cell(20, 8, 'Aantal', border=1, align='C')
        self.cell(30, 8, 'Prijs', border=1, align='C')
        self.cell(20, 8, 'BTW%', border=1, align='C')
        self.cell(30, 8, 'Bedrag', border=1, align='C', ln=True)

        self.set_font('Helvetica', '', 10)
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
        self.cell(30, 8, f"{subtotaal:.2f} EUR", border=1, align='C', ln=True)
        self.cell(150, 8, 'Totaal BTW:', border=0, align='R')
        self.cell(30, 8, f"{totaal_btw:.2f} EUR", border=1, align='C', ln=True)
        self.cell(150, 8, 'Totaal (incl. BTW):', border=0, align='R')
        self.set_font('Helvetica', 'B', 10)
        self.cell(30, 8, f"{totaal:.2f} EUR", border=1, align='C', ln=True)
        self.ln(20)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, "Gelieve binnen 14 dagen te betalen.", ln=True)
        self.cell(0, 10, "Factuur gegenereerd via Snelfactuurtje 🚀", ln=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    global factuur_teller

    if request.method == 'POST':
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

        logo_file = request.files.get('logo')
        logo_stream = None
        if logo_file and logo_file.filename:
            logo_stream = io.BytesIO(logo_file.read())

        pdf = FactuurPDF(logo_stream)
        pdf.add_page()
        pdf.header_custom(bedrijfsnaam, straat, postcode, plaats, land, kvk, btw, iban)
        pdf.factuur_body(factuurnummer, klantnaam, klant_straat, klant_postcode, klant_plaats, klant_land, diensten, bedrijfsnaam)

        pdf_data = pdf.output(dest='S').encode('latin-1')

        return send_file(
            io.BytesIO(pdf_data),
            as_attachment=True,
            download_name=f'{factuurnummer}.pdf',
            mimetype='application/pdf'
        )

    html_content = '''
    <!doctype html>
    <html lang="nl">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <title>Snelfactuurtje 🚀</title>
        <style>
            body { background-color: #f0f4f8; font-family: 'Arial', sans-serif; margin: 0; padding: 0; }
            .container { max-width: 700px; margin: 50px auto; background: white; padding: 30px;
                         box-shadow: 0 4px 12px rgba(0,0,0,0.1); border-radius: 15px; }
            h1 { text-align: center; color: #007bff; font-size: 28px; margin-bottom: 30px; }
            h2 { font-size: 18px; margin-top: 20px; margin-bottom: 10px; color: #333; }
            .block { padding: 20px; border-radius: 12px; margin-bottom: 20px; }
            .bedrijf { background-color: #e0f0ff; }
            .klant { background-color: #ffe6cc; }
            label { display: block; margin-top: 10px; color: #333; font-weight: 500; }
            input, select { width: 100%; padding: 10px; margin-top: 5px; border: 1px solid #ccc; border-radius: 8px; box-sizing: border-box; }
            button { width: 100%; background-color: #007bff; color: white; border: none; padding: 12px;
                     margin-top: 20px; border-radius: 30px; cursor: pointer; font-size: 18px; font-weight: 600; }
            button:hover { background-color: #0056b3; }
        </style>
      </head>
      <body>
        <div class="container">
            <h1>Snelfactuurtje 🚀</h1>
            <form method="POST" enctype="multipart/form-data" id="factuurForm">
              <label>Factuurnummer (optioneel):</label>
              <input type="text" name="factuurnummer" placeholder="Laat leeg voor automatisch nummer">
              <div class="block bedrijf">
                <h2>🏢 Bedrijfsgegevens</h2>
                <label>Bedrijfsnaam:</label>
                <input type="text" name="bedrijfsnaam" required>
                <label>Straat en huisnummer:</label>
                <input type="text" name="straat" required>
                <label>Postcode:</label>
                <input type="text" name="postcode" required>
                <label>Plaats:</label>
                <input type="text" name="plaats" required>
                <label>Land:</label>
                <input type="text" name="land" required>
                <label>KvK-nummer:</label>
                <input type="text" name="kvk" required>
                <label>BTW-nummer:</label>
                <input type="text" name="btw" required>
                <label>IBAN-nummer:</label>
                <input type="text" name="iban" required>
              </div>

              <div class="block klant">
                <h2>👤 Klantgegevens</h2>
                <label>Klantnaam:</label>
                <input type="text" name="klantnaam" required>
                <label>Straat en huisnummer:</label>
                <input type="text" name="klant_straat" required>
                <label>Postcode:</label>
                <input type="text" name="klant_postcode" required>
                <label>Plaats:</label>
                <input type="text" name="klant_plaats" required>
                <label>Land:</label>
                <input type="text" name="klant_land" required>
              </div>

              <div id="diensten"></div>

              <button type="button" onclick="voegDienstToe()">➕ Dienst toevoegen</button>

              <label>Upload jouw logo (optioneel):</label>
              <input type="file" name="logo">

              <button type="submit">📄 Factuur Downloaden</button>
            </form>
        </div>

        <script>
          let dienstIndex = 0;
          function voegDienstToe() {
              const container = document.getElementById('diensten');
              const html = `
                  <div>
                      <label>Dienst:</label>
                      <input type="text" name="dienst_${dienstIndex}" required>
                      <label>Aantal:</label>
                      <input type="number" name="aantal_${dienstIndex}" required>
                      <label>Prijs per stuk:</label>
                      <input type="number" step="0.01" name="prijs_${dienstIndex}" required>
                      <label>BTW-percentage:</label>
                      <select name="btw_${dienstIndex}" required>
                          <option value="0">0%</option>
                          <option value="9">9%</option>
                          <option value="21" selected>21%</option>
                      </select>
                  </div>
              `;
              container.insertAdjacentHTML('beforeend', html);
              dienstIndex++;
          }
          window.onload = voegDienstToe;
        </script>
      </body>
    </html>
    '''
    return render_template_string(html_content)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
