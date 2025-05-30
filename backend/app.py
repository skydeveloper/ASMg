# Файл: ASMg/backend/app.py
import os
import json
import time
import logging
from logging.handlers import RotatingFileHandler

from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, emit
from flask_cors import CORS

from backend.config import Config
from backend.translations.translation_manager import load_translations, get_translation
from backend.services.traceability_api import TraceabilityAPI

# --- Конфигурация на Логването ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if Config.DEBUG else logging.INFO)
log_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'asmg_app.log')
file_handler = RotatingFileHandler(log_file_path, maxBytes=1024 * 1024 * 5, backupCount=5, encoding='utf-8')
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)
logger.info("Приложението ASMg се стартира...")

# --- Глобални Променливи (ПЪЛНА И КОРЕКТНА ВЕРСИЯ) ---
global_line_status_data = {
    "overall_status": "status.idle",
    "robots": {
        "1": {"status": "status.idle"}, "2": {"status": "status.idle"}, "3": {"status": "status.idle"}
    },
    "turntable1": {
        "1": {"status": "status.idle", "moduleId": "--"},
        "2": {"status": "status.idle", "moduleId": "--"},
        "3": {"status": "status.idle", "moduleId": "--"},
        "4": {"status": "status.idle", "moduleId": "--"}
    },
    "turntable2": {
        "1": {"status": "status.idle", "moduleIds": []},
        "2": {"status": "status.idle", "moduleIds": []},
        "3": {"status": "status.idle", "moduleIds": []},
        "4": {"status": "status.idle", "moduleIds": []}
    },
    "trays": {
        "in": {"status": "status.empty"}, "out": {"status": "status.empty"}
    },
    "current_operator": None,
    "current_travel_lot": None
}

# --- Инициализация на Приложението ---
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.config.from_object(Config)
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app, resources={r"/*": {"origins": "*"}})

# --- Зареждане на Преводи и API Клиент ---
translations_path = os.path.join(os.path.dirname(__file__), 'translations')
translation_data = load_translations(translations_path)
traceability_api_client = TraceabilityAPI(
    base_url=Config.TRACEABILITY_API_URL,
    api_key=Config.TRACEABILITY_API_KEY,
    logger_func=logger
)

# --- Помощни Функции ---
def add_log_message(message_key, level='info', **kwargs):
    lang_code = Config.DEFAULT_LANGUAGE
    try:
        if request:
            lang_code = session.get('language', Config.DEFAULT_LANGUAGE)
    except RuntimeError:
        pass
    message_template = get_translation(message_key, lang_code, translation_data, fallback_lang=Config.DEFAULT_LANGUAGE)
    try:
        final_message = message_template.format(**kwargs)
    except KeyError:
        final_message = message_template
    socketio.emit('log_message', {'message': final_message, 'level': level})

# --- Инициализация на Услугите ---
from backend.services.com_port_manager import ComPortManager
from backend.services.data_simulator import DataSimulatorThread
from backend.api import register_api_routes

com_port_scanner = ComPortManager(port=Config.BARCODE_SCANNER_PORT, baudrate=Config.BARCODE_SCANNER_BAUDRATE, socketio=socketio)
data_simulator = DataSimulatorThread(socketio, global_line_status_data, add_log_message)
register_api_routes(app, socketio, global_line_status_data, translation_data)

# --- Основни Маршрути на Приложението ---
@app.route('/')
def index():
    lang_code = session.get('language', Config.DEFAULT_LANGUAGE)
    current_translations = translation_data.get(lang_code, translation_data.get(Config.DEFAULT_LANGUAGE, {}))
    return render_template('index.html',
                           translations=current_translations,
                           current_lang=lang_code,
                           supported_languages=Config.SUPPORTED_LANGUAGES,
                           initial_data=global_line_status_data)

@app.route('/set_language/<lang_code>')
def set_language_route(lang_code):
    if lang_code in Config.SUPPORTED_LANGUAGES:
        session['language'] = lang_code
    return redirect(url_for('index'))

# --- SocketIO Събития ---
com_reader_started = False

@socketio.on('connect')
def handle_connect():
    global com_reader_started
    logger.info(f"Клиент {request.sid} се свърза.")
    if not com_reader_started:
        if com_port_scanner and com_port_scanner.is_running:
            com_port_scanner.start_reading_task()
            com_reader_started = True
    handle_request_initial_data()

@socketio.on('request_initial_data')
def handle_request_initial_data():
    lang_code = session.get('language', Config.DEFAULT_LANGUAGE)
    emit('initial_data', {
        'translations': translation_data.get(lang_code, {}),
        'current_lang': lang_code,
        'supported_languages': Config.SUPPORTED_LANGUAGES,
        'line_status': global_line_status_data
    })

@socketio.on('update_status')
def handle_status_updates(data):
    socketio.emit('status_updated', data)

@socketio.on('validate_operator')
def handle_validate_operator(data):
    badge_id = data.get('barcode')
    if not badge_id: return
    response = traceability_api_client.validate_operator_badge(reader_id=badge_id)
    is_valid, operator_info = False, None
    if response and "VALUES" in response and isinstance(response.get("VALUES"), dict):
        api_data = response["VALUES"]
        if str(api_data.get("P_EXID")) == "0":
            is_valid = True
            operator_info = {"id": badge_id, "name": api_data.get("P_NAME", "N/A"), "employee_no": api_data.get("P_EMNO", badge_id)}
            global_line_status_data['current_operator'] = operator_info
            add_log_message("log.operatorLoggedIn", "success", operator_name=operator_info['name'])
    emit('operator_validation_result', {'is_valid': is_valid, 'operator_info': operator_info})

@socketio.on('validate_travel_lot')
def handle_validate_travel_lot(data):
    travel_lot_barcode = data.get('barcode')
    current_operator = global_line_status_data.get('current_operator')
    if not (travel_lot_barcode and current_operator): return
    response = traceability_api_client.ftpck_new_order(
        workplace_id=Config.TRACEABILITY_WORKPLACE_ID,
        route_map=travel_lot_barcode,
        employee_id=current_operator.get('employee_no')
    )
    is_valid, travel_lot_info = False, None
    if response:
        api_values = response.get("VALUES", {})
        p_exid_value = api_values.get("P_EXID")
        if p_exid_value is not None and str(p_exid_value) == "0":
            is_valid = True
            travel_lot_info = {"id": travel_lot_barcode, "productNumber": api_values.get("P_MITM", "N/A")}
            global_line_status_data['current_travel_lot'] = travel_lot_info
            add_log_message("log.travelLotIdentified", "success", lot_id=travel_lot_barcode, item_number=travel_lot_info['productNumber'])
    emit('travel_lot_validation_result', {'is_valid': is_valid, 'travel_lot_info': travel_lot_info})

@socketio.on('logout_request')
def handle_logout_request():
    logged_out_operator = global_line_status_data.get('current_operator')
    global_line_status_data['current_operator'] = None
    if logged_out_operator:
        add_log_message("log.operatorLoggedOut", "info", operator_name=logged_out_operator.get('name', ''))
    emit('operator_validation_result', {'is_valid': False, 'operator_info': None})