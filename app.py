
from flask import Flask, render_template, request, send_file
from fpdf import FPDF
import io
import os
from datetime import datetime

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

factuur_teller = 1

class FactuurPDF(FPDF):
    def __init__(self, logo_path=None):
        super().__init__()
        self.logo_path = logo_path

    def header(self):
        if self.logo_path and os.path.exists(self.logo_path):
            self.image(self.logo_path, 10, 8, 33)
            self.set_xy(50, 10)
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'Factuur', ln=True, align='C')
        self.ln(20)

    def factuur_body(self, factuurnummer, bedrijfsnaam, klantnaam, diensten):
        self.set_font('Arial', '', 12)
        self.cell(0, 10, f'Factuurnummer: {factuurnummer}', ln=True)
        self.cell(0, 10, f'Datum: {datetime.today().strftime("%d-%m-%Y")}', ln=True)
        self.cell(0, 10, f'Van: {bedrijfsnaam}', ln=True)
        self.cell(0, 10, f'Aan: {klantnaam}', ln=True)
        self.ln(10)

        totaal = 0
        for dienst, prijs in diensten:
            self.cell(0, 10, f'{dienst}: €{prijs:.2f}', ln=True)
            totaal += prijs

        self.ln(10)
        self.cell(0, 10, f'Totaal: €{totaal:.2f}', ln=True)

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
        logo_path = None

        if logo_file and logo_file.filename != '':
            logo_path = os.path.join(app.config['UPLOAD_FOLDER'], logo_file.filename)
            logo_file.save(logo_path)

        pdf = FactuurPDF(logo_path)
        pdf.add_page()
        pdf.factuur_body(factuurnummer, bedrijfsnaam, klantnaam, diensten)

        pdf_output = io.BytesIO()
        pdf.output(pdf_output)
        pdf_output.seek(0)

        return send_file(pdf_output, as_attachment=True, download_name=f'{factuurnummer}.pdf')

    return '''
    <!doctype html>
    <html lang="nl">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <title>Factuurgenerator</title>
      </head>
      <body>
        <h1>Factuur Generator</h1>
        <form method="POST" enctype="multipart/form-data">
          <label>Bedrijfsnaam:</label><br>
          <input type="text" name="bedrijfsnaam" required><br><br>

          <label>Klantnaam:</label><br>
          <input type="text" name="klantnaam" required><br><br>

          <label>Dienst 1:</label><br>
          <input type="text" name="dienst_1" required><br>
          <label>Prijs 1:</label><br>
          <input type="number" step="0.01" name="prijs_1" required><br><br>

          <label>Dienst 2 (optioneel):</label><br>
          <input type="text" name="dienst_2"><br>
          <label>Prijs 2:</label><br>
          <input type="number" step="0.01" name="prijs_2"><br><br>

          <label>Upload jouw logo (optioneel):</label><br>
          <input type="file" name="logo"><br><br>

          <button type="submit">Genereer Factuur</button>
        </form>
      </body>
    </html>
    '''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
