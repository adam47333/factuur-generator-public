import os
from flask import Flask, request, send_file
from fpdf import FPDF
import io
from datetime import datetime

app = Flask(__name__)

factuur_teller = 1

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
        self.cell(0, 10, 'Factuur', ln=True, align='C')
        self.ln(20)

    def factuur_body(self, factuurnummer, bedrijfsnaam, klantnaam, diensten):
        self.set_font('Helvetica', '', 12)
        self.cell(0, 10, f"Factuurnummer: {factuurnummer}", ln=True)
        self.cell(0, 10, f"Datum: {datetime.today().strftime('%d-%m-%Y')}", ln=True)
        self.cell(0, 10, f"Van: {bedrijfsnaam}", ln=True)
        self.cell(0, 10, f"Aan: {klantnaam}", ln=True)
        self.ln(10)

        # Tabel koppen
        self.set_font('Helvetica', 'B', 12)
        self.cell(120, 10, "Omschrijving", border=1)
        self.cell(40, 10, "Prijs (EUR)", border=1, ln=True)

        # Tabel inhoud
        self.set_font('Helvetica', '', 12)
        totaal = 0
        for dienst, prijs in diensten:
            self.cell(120, 10, dienst, border=1)
            self.cell(40, 10, f"{prijs:.2f}", border=1, ln=True)
            totaal += prijs

        # Totaal
        self.set_font('Helvetica', 'B', 12)
        self.cell(120, 10, 'Totaal', border='T')
        self.cell(40, 10, f"{totaal:.2f}", border='T', ln=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    global factuur_teller

    if request.method == 'POST':
        bedrijfsnaam = request.form['bedrijfsnaam']
        klantnaam = request.form['klantnaam']
        diensten = []

        dienst_1 = request.form['dienst_1']
        prijs_1 = float(request.form['prijs_1'])
        diensten.append((dienst_1, prijs_1))

        dienst_2 = request.form.get('dienst_2')
        prijs_2 = request.form.get('prijs_2')

        if dienst_2 and prijs_2:
            diensten.append((dienst_2, float(prijs_2)))

        factuurnummer = f"FACT-{datetime.today().year}{factuur_teller:04d}"
        factuur_teller += 1

        logo_file = request.files.get('logo')
        logo_stream = None
        if logo_file and logo_file.filename:
            logo_stream = io.BytesIO(logo_file.read())

        pdf = FactuurPDF(logo_stream)
        pdf.add_page()
        pdf.factuur_body(factuurnummer, bedrijfsnaam, klantnaam, diensten)

        pdf_data = pdf.output(dest='S').encode('latin-1')

        return send_file(
            io.BytesIO(pdf_data),
            as_attachment=True,
            download_name=f'{factuurnummer}.pdf',
            mimetype='application/pdf'
        )

    return '''
    <!doctype html>
    <html lang="nl">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <title>Factuur Generator</title>
        <style>
            body {
                background-color: #f4f6f8;
                font-family: 'Open Sans', sans-serif;
            }
            .container {
                width: 400px;
                margin: 50px auto;
                background: white;
                padding: 20px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
                border-radius: 10px;
            }
            h1 {
                text-align: center;
                color: #333;
            }
            label {
                display: block;
                margin-top: 15px;
                color: #555;
            }
            input[type="text"], input[type="number"], input[type="file"] {
                width: 100%;
                padding: 8px;
                margin-top: 5px;
                border: 1px solid #ccc;
                border-radius: 5px;
            }
            button {
                width: 100%;
                background-color: #007bff;
                color: white;
                border: none;
                padding: 10px;
                margin-top: 20px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
            }
            button:hover {
                background-color: #0056b3;
            }
        </style>
      </head>
      <body>
        <div class="container">
            <h1>Factuur Generator</h1>
            <form method="POST" enctype="multipart/form-data">
              <label>Bedrijfsnaam:</label>
              <input type="text" name="bedrijfsnaam" required>

              <label>Klantnaam:</label>
              <input type="text" name="klantnaam" required>

              <label>Dienst 1:</label>
              <input type="text" name="dienst_1" required>
              <label>Prijs 1:</label>
              <input type="number" step="0.01" name="prijs_1" required>

              <label>Dienst 2 (optioneel):</label>
              <input type="text" name="dienst_2">
              <label>Prijs 2:</label>
              <input type="number" step="0.01" name="prijs_2">

              <label>Upload jouw logo (optioneel):</label>
              <input type="file" name="logo">

              <button type="submit">Genereer Factuur</button>
            </form>
        </div>
      </body>
    </html>
    '''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
