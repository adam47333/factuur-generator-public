import os from flask import Flask, request, send_file, render_template_string, abort from fpdf import FPDF import io from datetime import datetime

app = Flask(name)

factuur_teller = 1

class FactuurPDF(FPDF): def init(self, logo_stream=None): super().init() self.logo_stream = logo_stream

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
    self.cell(0, 10, f"Aan:", ln=True)
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

@app.route('/', methods=['GET', 'POST']) def index(): global factuur_teller

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

html_content = '''
<!doctype html>
<html lang="nl">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>Snelfactuurtje 🚀</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins&display=swap" rel="stylesheet">
    <style>
        body { background-color: #f0f4f8; font-family: 'Poppins', sans-serif; margin: 0; padding: 0; }
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

if name == 'main': port = int(os.environ.get('PORT', 5000)) app.run(host='0.0.0.0', port=port)
