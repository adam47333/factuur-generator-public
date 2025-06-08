import os
from flask import Flask, request, send_file, render_template_string, abort
from fpdf import FPDF
import io
from datetime import datetime
import base64

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

    def factuur_body(self, factuurnummer, klantnaam, klant_straat, klant_postcode, klant_plaats, klant_land, diensten, bedrijfsnaam, handtekening_stream=None):
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

        if handtekening_stream:
            self.ln(20)
            self.cell(0, 8, "Handtekening:", ln=True)
            self.image(handtekening_stream, x=10, y=self.get_y(), w=60)

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
            if handtekening_data and handtekening_data.startswith("data:image/png;base64,"):
                header, encoded = handtekening_data.split(",", 1)
                handtekening_bytes = base64.b64decode(encoded)
                handtekening_stream = io.BytesIO(handtekening_bytes)
                handtekening_stream.name = 'handtekening.png'

            pdf = FactuurPDF(logo_stream)
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

    # Volledige HTML komt hier
    html_content = """
<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <title>Snelfactuurtje</title>
  <link href="https://fonts.googleapis.com/css2?family=Poppins&display=swap" rel="stylesheet">
  <style>
    body {
      background-color: #f0f4f8;
      font-family: 'Poppins', sans-serif;
      margin: 0;
      padding: 20px;
    }
    .container {
      max-width: 700px;
      margin: auto;
      background: white;
      padding: 30px;
      border-radius: 15px;
      box-shadow: 0 0 10px rgba(0,0,0,0.1);
    }
    h1 {
      text-align: center;
      color: #007bff;
    }
    .block {
      padding: 20px;
      border-radius: 12px;
      margin-bottom: 20px;
    }
    .bedrijf {
      background-color: #e0f0ff;
    }
    .klant {
      background-color: #ffe6cc;
    }
    label {
      display: block;
      margin-top: 10px;
      font-weight: 500;
    }
    input, select {
      width: 100%;
      padding: 10px;
      margin-top: 5px;
      border-radius: 8px;
      border: 1px solid #ccc;
    }
    .dienst-block {
      border: 1px solid #ccc;
      padding: 10px;
      border-radius: 10px;
      margin-top: 10px;
      position: relative;
    }
    .remove-btn {
      position: absolute;
      top: 10px;
      right: 10px;
      background-color: red;
      color: white;
      border: none;
      border-radius: 50%;
      width: 25px;
      height: 25px;
      cursor: pointer;
    }
    button {
      width: 100%;
      padding: 12px;
      margin-top: 20px;
      border: none;
      border-radius: 30px;
      background-color: #007bff;
      color: white;
      font-size: 18px;
      font-weight: bold;
      cursor: pointer;
    }
    button:hover {
      background-color: #0056b3;
    }
    canvas {
      border: 1px solid #ccc;
      border-radius: 8px;
      margin-top: 10px;
      width: 100%;
      height: 150px;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>Snelfactuurtje 🚀</h1>
    <form method="POST" enctype="multipart/form-data">
      <label>Factuurnummer:</label>
      <input name="factuurnummer" placeholder="Bijv. FACT-2025-001" required>

      <div class="block bedrijf">
        <h2>🏢 Bedrijfsgegevens</h2>
        <label>Bedrijfsnaam:</label>
        <input name="bedrijfsnaam" required>
        <label>Straat en huisnummer:</label>
        <input name="straat" required>
        <label>Postcode:</label>
        <input name="postcode" required>
        <label>Plaats:</label>
        <input name="plaats" required>
        <label>Land:</label>
        <input name="land" required>
        <label>KvK-nummer:</label>
        <input name="kvk" required>
        <label>BTW-nummer:</label>
        <input name="btw" required>
        <label>IBAN-nummer:</label>
        <input name="iban" required>
      </div>

      <div class="block klant">
        <h2>🧑‍💼 Klantgegevens</h2>
        <label>Klantnaam:</label>
        <input name="klantnaam" required>
        <label>Straat en huisnummer:</label>
        <input name="klant_straat" required>
        <label>Postcode:</label>
        <input name="klant_postcode" required>
        <label>Plaats:</label>
        <input name="klant_plaats" required>
        <label>Land:</label>
        <input name="klant_land" required>
      </div>

      <div id="diensten"></div>
      <button type="button" onclick="voegDienstToe()">➕ Dienst toevoegen</button>

      <label>Upload jouw logo (optioneel):</label>
      <input type="file" name="logo">

      <h2>✍️ Handtekening</h2>
      <canvas id="signature-pad"></canvas>
      <button type="button" onclick="clearSignature()">🗑️ Handtekening wissen</button>
      <input type="hidden" id="handtekening" name="handtekening">

      <button type="submit">📄 Factuur Downloaden</button>
    </form>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/signature_pad@4.0.0/dist/signature_pad.umd.min.js"></script>
  <script>
    let dienstIndex = 0;
    function voegDienstToe() {
      const container = document.getElementById('diensten');
      const div = document.createElement('div');
      div.className = 'dienst-block';
      div.innerHTML = `
        <button type='button' class='remove-btn' onclick='this.parentNode.remove()'>×</button>
        <label>Dienst:</label>
        <input name='dienst_${dienstIndex}' required>
        <label>Aantal:</label>
        <input name='aantal_${dienstIndex}' type='number' required>
        <label>Prijs per stuk:</label>
        <input name='prijs_${dienstIndex}' type='number' step='0.01' required>
        <label>BTW-percentage:</label>
        <select name='btw_${dienstIndex}'>
          <option value='0'>0%</option>
          <option value='9'>9%</option>
          <option value='21' selected>21%</option>
        </select>
      `;
      container.appendChild(div);
      dienstIndex++;
    }

    var canvas = document.getElementById('signature-pad');
    var signaturePad = new SignaturePad(canvas);

    function saveSignature() {
      if (!signaturePad.isEmpty()) {
        var dataURL = signaturePad.toDataURL();
        document.getElementById('handtekening').value = dataURL;
      }
    }

    function clearSignature() {
      signaturePad.clear();
    }

    document.querySelector("form").addEventListener("submit", saveSignature);
  </script>
</body>
</html>
"""  # Placeholder nu
    return render_template_string(html_content)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
