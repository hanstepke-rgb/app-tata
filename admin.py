from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__, static_folder=r"C:\Tata\app")
CORS(app)

# Configuración de Google Sheets
ID_HOJA = "1JlMh7lDpWuJekzi40QnnVCtFQMndEmS6s03a3u1WXMg"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDS = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", SCOPE)
CLIENT = gspread.authorize(CREDS)
SHEET = CLIENT.open_by_key(ID_HOJA)

def normalizar(valor):
    return str(valor).strip() if valor is not None else ""

@app.route('/verificar', methods=['POST'])
def verificar():
    data = request.json
    clave_ingresada = normalizar(data.get("clave"))
    try:
        ws_user = SHEET.worksheet("Usuarios")
        valores = ws_user.get_all_values()
        for row in valores[1:]: # Saltar cabecera
            if normalizar(row[0]).lower() == "admin" and normalizar(row[2]) == clave_ingresada:
                return jsonify({"status": "ok"})
        return jsonify({"status": "error"}), 401
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/datos-admin', methods=['GET'])
def datos_admin():
    compras = {}
    if "Registro" in [ws.title for ws in SHEET.worksheets()]:
        ws_reg = SHEET.worksheet("Registro").get_all_values()
        for row in ws_reg[1:]:
            if row[1]: 
                nombre = normalizar(row[1])
                monto = int(row[2]) if row[2].isdigit() else 0
                compras[nombre] = compras.get(nombre, 0) + monto
    
    cashouts = {}
    if "CashOut" in [ws.title for ws in SHEET.worksheets()]:
        ws_co = SHEET.worksheet("CashOut").get_all_values()
        for row in ws_co[1:]:
            nombre = normalizar(row[0])
            if nombre:
                cashouts[nombre] = {"cashout": int(row[3]) if row[3].isdigit() else 0, "saldo": int(row[4]) if row[4].isdigit() else 0}
    return jsonify({"compras": compras, "cashouts": cashouts})

@app.route('/pendientes', methods=['GET'])
def obtener_pendientes():
    ws_reg = SHEET.worksheet("Registro")
    data = ws_reg.get_all_values()
    pendientes = []
    for idx, row in enumerate(data[1:], start=2):
        if len(row) > 4 and normalizar(row[4]) == "Pendiente":
            pendientes.append({"id": idx, "nombre": normalizar(row[1]), "monto": row[2]})
    return jsonify(pendientes)

@app.route('/marcar-entregado', methods=['POST'])
def marcar_entregado():
    idx = request.json.get("id")
    ws_reg = SHEET.worksheet("Registro")
    ws_reg.update_cell(idx, 5, "Entregado")
    return jsonify({"status": "ok"})

@app.route('/cashout', methods=['POST'])
def cashout():
    data = request.json
    nombre = normalizar(data.get("nombre"))
    monto_cashout = int(data.get("monto"))
    ws_reg = SHEET.worksheet("Registro")
    datos_reg = ws_reg.get_all_values()
    
    total_comprado = sum(int(r[2]) for r in datos_reg[1:] if normalizar(r[1]) == nombre)
    telefono = next((normalizar(r[0]) for r in datos_reg[1:] if normalizar(r[1]) == nombre), "N/A")
    
    ws_co = SHEET.worksheet("CashOut")
    ws_co.append_row([nombre, telefono, total_comprado, monto_cashout, total_comprado - monto_cashout])
    return jsonify({"status": "ok"})

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'admin.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9001, debug=True)