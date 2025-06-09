# app.py
import os
import io
import base64
from datetime import datetime
from flask import Flask, request, send_file, abort, render_template_string
from fpdf import FPDF

app = Flask(__name__)

class FactuurPDF(FPDF):
    def __init__(self, logo_stream=None, handtekening_stream=None):
        super().__init__()
        self.logo_stream = logo_stream
        self.handtekening_stream = handtekening_stream

    def header_custom(self, bedrijfsnaam, straat, postcode, plaats, land, kvk, btw, iban):
        if self.logo_stream:
            try:
                self.logo_stream.seek(0)
                with open("temp_logo.png", "wb") as f:
                    f.write(self.logo_stream.read())
                self.image("temp_logo.png", x=10, y=8, w=40)
                os.remove("temp_logo.png")
            except Exception as e:
                print(f"Logo laden mislukt: {e}")
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 10, bedrijfsnaam, ln=True, align='R')
        self.set_font('Helvetica', '', 11)
        self.cell(0, 8, straat, ln=True, align='R')
        self.cell(0, 8, f"{postcode} {plaats}", ln=True, align='R')
        self.cell(0, 8, land, ln=True, align='R')
        self.cell(0, 8, f"KvK: {kvk} | BTW: {btw}", ln=True, align='R')
        self.cell(0, 8, f"IBAN: {iban}", ln=True, align='R')
        self.ln(10)
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

        # Handtekening onderaan rechts
        if self.handtekening_stream:
            if self.get_y() > 250:
                self.add_page()
            self.ln(15)
            self.cell(0, 8, "Handtekening:", ln=True)
            with open("temp_handtekening.png", "wb") as f:
                f.write(self.handtekening_stream.getbuffer())
            self.image("temp_handtekening.png", x=140, y=self.get_y(), w=50)
            os.remove("temp_handtekening.png")

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

            pdf = FactuurPDF(logo_stream, handtekening_stream)
            pdf.add_page()
            pdf.header_custom(bedrijfsnaam, straat, postcode, plaats, land, kvk, btw, iban)
            pdf.factuur_body(factuurnummer, klantnaam, klant_straat, klant_postcode, klant_plaats, klant_land, diensten, bedrijfsnaam)

            pdf_data = pdf.output(dest='S').encode('latin-1')

            return send_file(
                io.BytesIO(pdf_data),
                as_attachment=True,
                download_name=f"{factuurnummer}.pdf",
                mimetype='application/pdf',
                conditional=False,
                cache_timeout=0
            )
        except Exception as e:
            abort(400, f"Fout bij verwerken factuur: {e}")

    html_content = '''
<!DOCTYPE html>
<html lang="nl">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Snelfactuurtje</title>
  <style>
    body { font-family: Arial, sans-serif; padding: 20px; max-width: 600px; margin: auto; background: #f0f8ff; }
    h1 { text-align: center; color: #007bff; }
    form { display: flex; flex-direction: column; gap: 10px; }
    label { font-weight: bold; margin-top: 10px; }
    input, select { padding: 8px; font-size: 1em; }
    .dienst { border: 1px solid #ccc; padding: 10px; border-radius: 8px; margin-top: 10px; }
    button { margin-top: 20px; padding: 12px; background-color: #007bff; border: none; color: white; font-weight: bold; cursor: pointer; border-radius: 8px; }
    canvas { border: 1px solid #ccc; margin-top: 10px; border-radius: 6px; }
  </style>
</head>
<body>
  <h1>Snelfactuurtje</h1>
  <form method="post" enctype="multipart/form-data" onsubmit="saveSignature()">
    <label>Factuurnummer</label>
    <input name="factuurnummer" required />

    <label>Bedrijfsnaam</label>
    <input name="bedrijfsnaam" required />
    <label>Straat en huisnummer</label>
    <input name="straat" required />
    <label>Postcode</label>
    <input name="postcode" required />
    <label>Plaats</label>
    <input name="plaats" required />
    <label>Land</label>
    <input name="land" required />
    <label>KvK-nummer</label>
    <input name="kvk" required />
    <label>BTW-nummer</label>
    <input name="btw" required />
    <label>IBAN-nummer</label>
    <input name="iban" required />
    <label>Upload logo (optioneel)</label>
    <input type="file" name="logo" accept="image/*" />

    <hr />

    <label>Klantnaam</label>
    <input name="klantnaam" required />
    <label>Straat en huisnummer klant</label>
    <input name="klant_straat" required />
    <label>Postcode klant</label>
    <input name="klant_postcode" required />
    <label>Plaats klant</label>
    <input name="klant_plaats" required />
    <label>Land klant</label>
    <input name="klant_land" required />

    <hr />

    <div id="diensten">
      <div class="dienst">
        <label>Dienst</label>
        <input name="dienst_0" required />
        <label>Aantal</label>
        <input type="number" name="aantal_0" value="1" min="1" required />
        <label>Prijs per stuk (EUR)</label>
        <input type="number" step="0.01" name="prijs_0" value="0.00" required />
        <label>BTW-percentage</label>
        <select name="btw_0">
          <option value="0">0%</option>
          <option value="9">9%</option>
          <option value="21" selected>21%</option>
        </select>
      </div>
    </div>
    <button type="button" onclick="addDienst()">Dienst toevoegen</button>

    <hr />

    <label>Handtekening</label>
    <canvas id="signature-pad" width="400" height="150"></canvas>
    <button type="button" onclick="clearSignature()">Handtekening wissen</button>
    <input type="hidden" name="handtekening" id="handtekening" />

    <button type="submit">Factuur downloaden</button>
  </form>

  <script src="https://cdn.jsdelivr.net/npm/signature_pad@4.0.0/dist/signature_pad.umd.min.js"></script>
  <script>
    let dienstIndex = 1;
    function addDienst() {
      const container = document.getElementById('diensten');
      const div = document.createElement('div');
      div.className = 'dienst';
      div.innerHTML = `
        <label>Dienst</label>
        <input name="dienst_${dienstIndex}" required />
        <label>Aantal</label>
        <input type="number" name="aantal_${dienstIndex}" value="1" min="1" required />
        <label>Prijs per stuk (EUR)</label>
        <input type="number" step="0.01" name="prijs_${dienstIndex}" value="0.00" required />
        <label>BTW-percentage</label>
        <select name="btw_${dienstIndex}">
          <option value="0">0%</option>
          <option value="9">9%</option>
          <option value="21" selected>21%</option>
        </select>
      `;
      container.appendChild(div);
      dienstIndex++;
    }

    const canvas = document.getElementById('signature-pad');
    const signaturePad = new SignaturePad(canvas);

    function clearSignature() {
      signaturePad.clear();
      document.getElementById('handtekening').value = '';
    }

    function saveSignature() {
      if (!signaturePad.isEmpty()) {
        document.getElementById('handtekening').value = signaturePad.toDataURL();
      }
    }
  </script>
</body>
</html>
'''
    return render_template_string(html_content)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
