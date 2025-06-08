import os
from flask import Flask, request, send_file, render_template_string, abort
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
            try:
                self.image(self.logo_stream, x=10, y=8, w=30)
            except Exception as e:
                print(f"Fout bij laden van logo: {e}")
        self.set_font('Helvetica', 'B', 18)
        self.cell(0, 10, bedrijfsnaam, ln=True, align='R')
        self.set_font('Helvetica', '', 12)
        self.cell(0, 10, straat, ln=True, align='R')
        self.cell(0, 10, f"{postcode} {plaats}", ln=True, align='R')
        self.cell(0, 10, land, ln=True, align='R')
        self.cell(0, 10, f"KvK: {kvk} | BTW: {btw}", ln=True, align='R')
        self.cell(0, 10, f"IBAN: {iban}", ln=True, align='R')
        self.ln(20)

    def factuur_body(self, factuurnummer, klantnaam, klant_straat, klant_postcode, klant_plaats, klant_land, diensten, bedrijfsnaam):
        self.set_font('Helvetica', '', 12)
        self.cell(0, 10, f"Factuurnummer: {factuurnummer}", ln=True)
        self.cell(0, 10, f"Datum: {datetime.today().strftime('%d-%m-%Y')}", ln=True)
        self.ln(5)
        self.cell(0, 10, "Aan:", ln=True)
        self.cell(0, 10, klantnaam, ln=True)
        self.cell(0, 10, klant_straat, ln=True)
        self.cell(0, 10, f"{klant_postcode} {klant_plaats}", ln=True)
        self.cell(0, 10, klant_land, ln=True)
        self.ln(10)

        self.set_font('Helvetica', 'B', 12)
        self.cell(60, 10, "Omschrijving", border=1, align='C')
        self.cell(20, 10, "Aantal", border=1, align='C')
        self.cell(30, 10, "Prijs", border=1, align='C')
        self.cell(20, 10, "BTW%", border=1, align='C')
        self.cell(30, 10, "Bedrag", border=1, align='C', ln=True)

        self.set_font('Helvetica', '', 12)
        subtotaal = 0
        totaal_btw = 0
        for dienst, aantal, prijs, btw_percentage in diensten:
            bedrag_excl = aantal * prijs
            btw_bedrag = bedrag_excl * (btw_percentage / 100)
            self.cell(60, 10, dienst, border=1)
            self.cell(20, 10, str(aantal), border=1, align='C')
            self.cell(30, 10, f"{prijs:.2f}", border=1, align='C')
            self.cell(20, 10, f"{btw_percentage}%", border=1, align='C')
            self.cell(30, 10, f"{(bedrag_excl + btw_bedrag):.2f}", border=1, align='C', ln=True)
            subtotaal += bedrag_excl
            totaal_btw += btw_bedrag

        totaal = subtotaal + totaal_btw
        self.ln(5)
        self.cell(130, 10, "Subtotaal (excl. BTW):", align='R')
        self.cell(30, 10, f"{subtotaal:.2f} EUR", ln=True, align='R')
        self.cell(130, 10, "Totaal BTW:", align='R')
        self.cell(30, 10, f"{totaal_btw:.2f} EUR", ln=True, align='R')
        self.cell(130, 10, "Totaal (incl. BTW):", align='R')
        self.set_font('Helvetica', 'B', 12)
        self.cell(30, 10, f"{totaal:.2f} EUR", ln=True, align='R')
        self.ln(20)
        self.set_font('Helvetica', '', 12)
        self.cell(0, 10, "Met vriendelijke groet,", ln=True)
        self.cell(0, 10, bedrijfsnaam, ln=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    global factuur_teller

    if request.method == 'POST':
        try:
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
                try:
                    aantal = int(request.form.get(f'aantal_{index}', 1))
                    prijs = float(request.form.get(f'prijs_{index}', 0))
                    btw_percentage = float(request.form.get(f'btw_{index}', 21))
                except ValueError:
                    return "Ongeldige invoer voor aantal, prijs of btw-percentage", 400
                diensten.append((dienst, aantal, prijs, btw_percentage))
                index += 1

            factuurnummer = f"SNLF-{datetime.today().year}-{factuur_teller:04d}"
            factuur_teller += 1

            logo_file = request.files.get('logo')
            logo_stream = None
            if logo_file and logo_file.filename:
                logo_stream = io.BytesIO(logo_file.read())
                logo_stream.name = 'logo.png'

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
        except Exception as e:
            abort(400, description=f"Fout bij verwerken van factuur: {e}")

    html_content = """<!doctype html>
<html lang='nl'>
<head>
<meta charset='utf-8'>
<title>Snelfactuurtje</title>
</head>
<body>
<h1>Factuur Generator</h1>
<form method="POST" enctype="multipart/form-data">
  <h2>Bedrijfsgegevens</h2>
  <input name="bedrijfsnaam" placeholder="Bedrijfsnaam" required><br>
  <input name="straat" placeholder="Straat" required><br>
  <input name="postcode" placeholder="Postcode" required><br>
  <input name="plaats" placeholder="Plaats" required><br>
  <input name="land" placeholder="Land" required><br>
  <input name="kvk" placeholder="KvK" required><br>
  <input name="btw" placeholder="BTW" required><br>
  <input name="iban" placeholder="IBAN" required><br>

  <h2>Klantgegevens</h2>
  <input name="klantnaam" placeholder="Klantnaam" required><br>
  <input name="klant_straat" placeholder="Straat" required><br>
  <input name="klant_postcode" placeholder="Postcode" required><br>
  <input name="klant_plaats" placeholder="Plaats" required><br>
  <input name="klant_land" placeholder="Land" required><br>

  <h2>Diensten</h2>
  <div id="diensten"></div>
  <button type="button" onclick="voegDienstToe()">Dienst toevoegen</button><br><br>

  <input type="file" name="logo"><br><br>

  <button type="submit">Download Factuur</button>
</form>

<script>
let dienstIndex = 0;
function voegDienstToe() {
  const container = document.getElementById('diensten');
  const html = `
    <div>
      <input name="dienst_${dienstIndex}" placeholder="Dienst" required>
      <input name="aantal_${dienstIndex}" placeholder="Aantal" type="number" required>
      <input name="prijs_${dienstIndex}" placeholder="Prijs" type="number" step="0.01" required>
      <select name="btw_${dienstIndex}">
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
</html>"""
    return render_template_string(html_content)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
