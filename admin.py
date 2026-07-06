import os
import json
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Definimos que la carpeta de archivos estáticos (HTML/CSS/JS) es 'app'
app = Flask(__name__, static_folder='app')
CORS(app)

# Configuración de Google Sheets
ID_HOJA = "1JlMh7lDpWuJekzi40QnnVCtFQMndEmS6s03a3u1WXMg"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Carga las credenciales desde la variable de entorno de Render
creds_dict = json.loads(os.environ['GOOGLE_CREDS'])
CREDS = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)

CLIENT = gspread.authorize(CREDS)
SHEET = CLIENT.open_by_key(ID_HOJA)

def normalizar(valor):
    return str(valor).strip() if valor is not None else ""

# --- RUTAS DE LA API ---

@app.route('/verificar', methods=['POST'])
def verificar():
    data = request.json
    clave_ingresada = normalizar(data.get("clave"))
    try:
        ws_user = SHEET.worksheet("Usuarios")
        valores = ws_user.get_all_values()
        for row in valores[1:]:
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
            if len(row) > 2 and row[1]: 
                nombre = normalizar(row[1])
                monto = int(row[2]) if row[2].isdigit() else 0
                compras[nombre] = compras.get(nombre, 0) + monto
    
    cashouts = {}
    if "CashOut" in [ws.title for ws in SHEET.worksheets()]:
        ws_co = SHEET.worksheet("CashOut").get_all_values()
        for row in ws_co[1:]:
            nombre = normalizar(row[0])
            if nombre and len(row) > 4:
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

# --- RUTA PRINCIPAL ---

@app.route('/')
def index():
    # Cambiamos 'index.html' por 'Admin.html' porque ese es el archivo que tienes
    return send_from_directory(app.static_folder, 'Admin.html')

# Permite cargar archivos CSS/JS si están en la carpeta 'app'
@app.route('/<path:path>')
def servir_static(path):
    return send_from_directory(app.static_folder, path)
    

if __name__ == '__main__':
    app.run()