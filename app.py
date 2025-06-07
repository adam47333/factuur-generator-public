import os
from flask import Flask, request, send_file, render_template_string
from fpdf import FPDF
import io
from datetime import datetime

app = Flask(__name__)

factuur_teller = 1

# Bedrijfsgegevens
BEDRIJFSNAAM = "Jouw Bedrijf BV"
BEDRIJF_ADRES = "Adresstraat 1, 1234 AB Stad"
KVK_NUMMER = "12345678"
BTW_NUMMER = "NL123456789B01"
IBAN = "NL00BANK0123456789"

class FactuurPDF(FPDF):
    def __init__(self, logo_stream=None):
        super().__init__()
        self.logo_stream = logo_stream

    def header(self):
        if self.logo_stream:
            try:
                self.image(self.logo_stream, x=10, y=8, w=33, type='PNG')
            except Exception as e:
                print(f"Fout bij laden van logo: {e}")
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 10, BEDRIJFSNAAM, ln=True)
        self.set_font('Helvetica', '', 12)
        self.cell(0, 10, BEDRIJF_ADRES, ln=True)
        self.cell(0, 10, f"KvK: {KVK_NUMMER} | BTW: {BTW_NUMMER}", ln=True)
        self.cell(0, 10, f"IBAN: {IBAN}", ln=True)
        self.ln(10)

    def factuur_body(self, factuurnummer, klantnaam, klantadres, diensten):
        self.set_font('Helvetica', '', 12)
        self.cell(0, 10, f"Factuurnummer: {factuurnummer}    Datum: {datetime.today().strftime('%d-%m-%Y')}", ln=True)
        self.ln(5)
        self.cell(0, 10, f"Aan:", ln=True)
        self.cell(0, 10, klantnaam, ln=True)
        self.cell(0, 10, klantadres, ln=True)
        self.ln(10)

        self.set_font('Helvetica', 'B', 12)
        self.cell(80, 10, "Omschrijving", border=1)
        self.cell(30, 10, "Aantal", border=1, align='C')
        self.cell(30, 10, "Prijs", border=1, align='C')
        self.cell(30, 10, "Bedrag", border=1, align='C', ln=True)

        self.set_font('Helvetica', '', 12)
        subtotaal = 0
        for dienst, aantal, prijs in diensten:
            bedrag = aantal * prijs
            self.cell(80, 10, dienst, border=1)
            self.cell(30, 10, str(aantal), border=1, align='C')
            self.cell(30, 10, f"{prijs:.2f}", border=1, align='C')
            self.cell(30, 10, f"{bedrag:.2f}", border=1, align='C', ln=True)
            subtotaal += bedrag

        btw = subtotaal * 0.21
        totaal = subtotaal + btw
        self.ln(5)
        self.cell(140, 10, "Subtotaal:", align='R')
        self.cell(30, 10, f"{subtotaal:.2f} EUR", ln=True, align='R')
        self.cell(140, 10, "BTW (21%):", align='R')
        self.cell(30, 10, f"{btw:.2f} EUR", ln=True, align='R')
        self.cell(140, 10, "Totaal:", align='R')
        self.set_font('Helvetica', 'B', 12)
        self.cell(30, 10, f"{totaal:.2f} EUR", ln=True, align='R')
        self.ln(20)
        self.set_font('Helvetica', '', 12)
        self.cell(0, 10, "Met vriendelijke groet,", ln=True)
        self.cell(0, 10, BEDRIJFSNAAM, ln=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    global factuur_teller

    if request.method == 'POST':
        klantnaam = request.form['klantnaam']
        klantadres = request.form['klantadres']
        diensten = []

        index = 0
        while f'dienst_{index}' in request.form:
            dienst = request.form.get(f'dienst_{index}')
            aantal = int(request.form.get(f'aantal_{index}', 1))
            prijs = float(request.form.get(f'prijs_{index}', 0))
            diensten.append((dienst, aantal, prijs))
            index += 1

        factuurnummer = f"FACT-{datetime.today().year}-{factuur_teller:04d}"
        factuur_teller += 1

        logo_file = request.files.get('logo')
        logo_stream = None
        if logo_file and logo_file.filename:
            logo_stream = io.BytesIO(logo_file.read())

        pdf = FactuurPDF(logo_stream)
        pdf.add_page()
        pdf.factuur_body(factuurnummer, klantnaam, klantadres, diensten)

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
        <title>Factuur Generator - Onbeperkt Diensten</title>
        <style>
            body { background-color: #f4f6f8; font-family: 'Open Sans', sans-serif; }
            .container { width: 400px; margin: 50px auto; background: white; padding: 20px;
                         box-shadow: 0 0 10px rgba(0,0,0,0.1); border-radius: 10px; }
            h1 { text-align: center; color: #333; }
            label { display: block; margin-top: 15px; color: #555; }
            input[type="text"], input[type="number"], input[type="file"] {
                width: 100%; padding: 8px; margin-top: 5px; border: 1px solid #ccc; border-radius: 5px;
            }
            button { width: 100%; background-color: #007bff; color: white; border: none; padding: 10px;
                     margin-top: 20px; border-radius: 5px; cursor: pointer; font-size: 16px; }
            button:hover { background-color: #0056b3; }
        </style>
      </head>
      <body>
        <div class="container">
            <h1>Factuur Generator</h1>
            <form method="POST" enctype="multipart/form-data" id="factuurForm">
              <label>Klantnaam:</label>
              <input type="text" name="klantnaam" required>

              <label>Klantadres:</label>
              <input type="text" name="klantadres" required>

              <div id="diensten"></div>

              <button type="button" onclick="voegDienstToe()">Dienst toevoegen</button>

              <label>Upload jouw logo (optioneel):</label>
              <input type="file" name="logo">

              <button type="submit">Genereer Factuur</button>
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
                  </div>
              `;
              container.insertAdjacentHTML('beforeend', html);
              dienstIndex++;
          }
          // Voeg standaard 1 dienst toe
          window.onload = voegDienstToe;
        </script>
      </body>
    </html>
    '''
    return render_template_string(html_content)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
