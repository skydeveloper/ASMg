# Файл: backend/app.py
import os
import json
import time
import logging
from logging.handlers import RotatingFileHandler

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit
from flask_cors import CORS

from backend.config import Config
from backend.translations.translation_manager import load_translations, get_translation
from backend.services.traceability_api import TraceabilityAPI
from backend.services.device_communicator import DeviceCommunicator

# --- Конфигурация на Логването ---
logger = logging.getLogger("ASMg_App")  # Използваме едно и също име за логера навсякъде
logger.setLevel(logging.DEBUG if Config.DEBUG else logging.INFO)
log_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'asmg_app.log')
file_handler = RotatingFileHandler(log_file_path, maxBytes=1024 * 1024 * 5, backupCount=5, encoding='utf-8')
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
if not logger.hasHandlers():
    logger.addHandler(file_handler)
logger.info("Приложението ASMg се стартира...")

# --- Глобални Променливи (ПЪЛНА И КОРЕКТНА ВЕРСИЯ) ---
global_line_status_data = {
    "overall_status": "status.idle",
    "robots": {
        "1": {"status": "status.idle"}, "2": {"status": "status.idle"}, "3": {"status": "status.idle"}
    },
    "turntable1": {
        "1": {"status": "status.idle", "moduleId": "--", "time": 0},
        "2": {"status": "status.idle", "moduleId": "--", "time": 0},
        "3": {"status": "status.idle", "moduleId": "--", "time": 0},
        "4": {"status": "status.idle", "moduleId": "--", "time": 0}
    },
    "turntable2": {  # Уверете се, че тази секция е РАЗКОМЕНТИРАНА и пълна
        "1": {"status": "status.idle", "moduleIds": [], "time": 0, "progress": 0},
        "2": {"status": "status.idle", "moduleIds": [], "time": 0, "progress": 0},
        "3": {"status": "status.idle", "moduleIds": [], "time": 0, "progress": 0},
        "4": {"status": "status.idle", "moduleIds": [], "time": 0, "progress": 0}
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

# --- Зареждане на Преводи и API Клиенти ---
translations_path = os.path.join(os.path.dirname(__file__), 'translations')
translation_data = load_translations(translations_path)

traceability_api_client = TraceabilityAPI(
    base_url=Config.TRACEABILITY_API_URL,
    api_key=Config.TRACEABILITY_API_KEY,
    logger_func=logger
)
logger.info("TraceabilityAPI client initialized.")

device_communicator = DeviceCommunicator()
logger.info("DeviceCommunicator initialized.")



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

    log_level_map_std = {'debug': logging.DEBUG, 'info': logging.INFO, 'success': logging.INFO,
                         'warning': logging.WARNING, 'error': logging.ERROR}
    # Логваме и към файла чрез стандартния логер на app.py
    logger.log(log_level_map_std.get(level.lower(), logging.INFO),
               f"AppLog (UI Target): [{lang_code.upper()}] {final_message}")

    socketio.emit('log_message', {'message': final_message, 'level': level})


# --- Инициализация на Услугите ---
from backend.services.com_port_manager import ComPortManager
from backend.services.data_simulator import DataSimulatorThread
from backend.api import register_api_routes

com_port_scanner = ComPortManager(port=Config.BARCODE_SCANNER_PORT, baudrate=Config.BARCODE_SCANNER_BAUDRATE,
                                  socketio=socketio)
logger.info(f"ComPortManager инициализиран за порт {Config.BARCODE_SCANNER_PORT}.")

data_simulator = DataSimulatorThread(socketio, global_line_status_data, add_log_message)
logger.info("DataSimulatorThread инициализиран.")

# Уверете се, че register_api_routes в backend/api/__init__.py е коригиран
register_api_routes(app, socketio, global_line_status_data, translation_data)
logger.info("API маршрутите са регистрирани.")


# --- Основни Маршрути на Приложението ---
@app.route('/')
def index():
    lang_code = session.get('language', Config.DEFAULT_LANGUAGE)
    current_translations = translation_data.get(lang_code, translation_data.get(Config.DEFAULT_LANGUAGE, {}))
    return render_template('index.html',
                           translations=current_translations,
                           current_lang=lang_code,
                           supported_languages=Config.SUPPORTED_LANGUAGES,
                           initial_data=global_line_status_data)  # Подаваме пълния global_line_status_data


@app.route('/set_language/<lang_code>')
def set_language_route(lang_code):
    if lang_code in Config.SUPPORTED_LANGUAGES:
        session['language'] = lang_code
    return redirect(url_for('index'))


@app.route('/test_device_interface')
def test_device_interface_page():
    lang_code = session.get('language', Config.DEFAULT_LANGUAGE)
    # Вече не дефинираме твърдо кодиран речник тук.
    # Просто зареждаме правилния превод от JSON файловете.
    current_translations = translation_data.get(lang_code, translation_data.get(Config.DEFAULT_LANGUAGE, {}))

    return render_template('test_interface.html',
                           translations=current_translations, # Подаваме стандартния речник
                           current_lang=lang_code,
                           supported_languages=Config.SUPPORTED_LANGUAGES)


# --- SocketIO Събития ---
com_reader_started = False


@socketio.on('connect')
def handle_connect():
    global com_reader_started
    logger.info(f"Клиент {request.sid} се свърза.")
    if not com_reader_started:  # Стартираме четенето от COM порта само веднъж
        if com_port_scanner and com_port_scanner.is_running:  # Проверяваме дали портът е отворен
            com_port_scanner.start_reading_task()
            com_reader_started = True
        elif com_port_scanner and not com_port_scanner.is_running:
            logger.warning(
                "COM Port reader task not started because com_port_scanner.is_running is False (port may not be open).")
        else:
            logger.error("COM Port reader task not started because com_port_scanner is None or port not initialized.")
    handle_request_initial_data()


@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Клиент {request.sid} се разкачи.")


@socketio.on('request_initial_data')
def handle_request_initial_data():
    lang_code = session.get('language', Config.DEFAULT_LANGUAGE)
    current_translations = translation_data.get(lang_code, translation_data.get(Config.DEFAULT_LANGUAGE, {}))
    emit('initial_data', {
        'translations': current_translations,
        'current_lang': lang_code,
        'supported_languages': Config.SUPPORTED_LANGUAGES,
        'line_status': global_line_status_data
    }, room=request.sid)  # Изпращаме само на клиента, който е поискал


@socketio.on('validate_operator')
def handle_validate_operator(data):
    badge_id = data.get('barcode')
    if not badge_id:
        emit('operator_validation_result', {'is_valid': False, 'operator_info': None})
        return

    add_log_message("log.validatingOperator", "info", badge_id=badge_id)
    response = traceability_api_client.validate_operator_badge(reader_id=badge_id)
    is_valid, operator_info = False, None

    if response and "VALUES" in response and isinstance(response.get("VALUES"), dict):
        api_data = response["VALUES"]
        if str(api_data.get("P_EXID")) == "0":
            is_valid = True
            operator_info = {"id": badge_id, "name": api_data.get("P_NAME", "N/A"),
                             "employee_no": api_data.get("P_EMNO", badge_id)}
            global_line_status_data['current_operator'] = operator_info
            add_log_message("log.operatorLoggedIn", "success", operator_name=operator_info['name'])
        else:
            error_message = api_data.get("P_EXMES", "Operator validation failed (API)")
            add_log_message("log.operatorApiValidationFailed", "warning", error=error_message, badge_id=badge_id)
    else:
        add_log_message("log.operatorApiError", "error", badge_id=badge_id)
    emit('operator_validation_result', {'is_valid': is_valid, 'operator_info': operator_info})


@socketio.on('validate_travel_lot')
def handle_validate_travel_lot(data):
    travel_lot_barcode = data.get('barcode')
    current_operator = global_line_status_data.get('current_operator')

    if not current_operator:
        add_log_message("log.operatorLoginRequired", "error")
        emit('travel_lot_validation_result',
             {'is_valid': False, 'error': 'No operator logged in', 'travel_lot_info': None})
        return
    if not travel_lot_barcode:
        add_log_message("log.travelLotScanRequired", "error")
        emit('travel_lot_validation_result',
             {'is_valid': False, 'error': 'No travel lot barcode scanned', 'travel_lot_info': None})
        return

    add_log_message("log.processingTravelCard", "info", barcodeData=travel_lot_barcode)
    response = traceability_api_client.ftpck_new_order(
        workplace_id=Config.TRACEABILITY_WORKPLACE_ID,
        route_map=travel_lot_barcode,
        employee_id=current_operator.get('employee_no')
    )
    is_valid, travel_lot_info = False, None
    if not response:
        logger.error("API call ftpck_new_order returned None.")
        add_log_message("log.travelLotApiError", "error", error="No response from API for travel lot")
    elif response.get("VALUES") is not None:  # Проверяваме дали VALUES съществува
        api_values = response.get("VALUES", {})
        p_exid_value = api_values.get("P_EXID")
        logger.debug(f"Пълен отговор от API за ftpck_new_order: {response}")
        logger.debug(f"Стойност на P_EXID: '{p_exid_value}', Тип на P_EXID: {type(p_exid_value)}")
        if p_exid_value is not None and str(p_exid_value) == "0":
            is_valid = True
            travel_lot_info = {"id": travel_lot_barcode, "productNumber": api_values.get("P_MITM", "N/A")}
            global_line_status_data['current_travel_lot'] = travel_lot_info
            add_log_message("log.travelLotIdentified", "success", lot_id=travel_lot_barcode,
                            item_number=travel_lot_info['productNumber'])
        else:
            error_message = response.get("P_EXMES") or response.get("MESSAGE", "Travel lot validation failed (API)")
            add_log_message("log.travelLotApiError", "error", error=error_message)
    else:  # Отговорът не съдържа ключ "VALUES"
        error_message = response.get("P_EXMES") or response.get("MESSAGE", "Unknown API structure error for travel lot")
        add_log_message("log.travelLotApiError", "error", error=error_message)

    emit('travel_lot_validation_result', {'is_valid': is_valid, 'travel_lot_info': travel_lot_info})


@socketio.on('logout_request')
def handle_logout_request():
    logged_out_operator = global_line_status_data.get('current_operator')
    global_line_status_data['current_operator'] = None
    global_line_status_data['current_travel_lot'] = None
    if logged_out_operator:
        add_log_message("log.operatorLoggedOut", "info", operator_name=logged_out_operator.get('name', 'N/A'))
    emit('operator_validation_result', {'is_valid': False, 'operator_info': None})


@socketio.on('language_changed')
def handle_language_changed(data):
    lang_code = data.get('lang')
    if lang_code in Config.SUPPORTED_LANGUAGES:
        session['language'] = lang_code
        handle_request_initial_data()


@socketio.on('trigger_task_on_device_client')
def handle_trigger_task_on_device_client(data):
    logger.info(f"ASMg: Получена UI заявка за стартиране на задача на DeviceClient: {data}")
    device_ip = data.get('device_ip')
    device_port = data.get('device_port')
    task_payload_for_dc = {
        "module_serial_numbers": data.get("serial_numbers"),
        "active_slots": data.get("active_slots"),
        "item_name": data.get("item_name"),
        "firmware_details": data.get("task_details")
    }
    if not all([device_ip, device_port, task_payload_for_dc.get("item_name")]):
        lang_code = session.get('language', Config.DEFAULT_LANGUAGE)
        error_translations = translation_data.get(lang_code, {})
        emit('ui_notification',
             {'message': get_translation('error.missingTestData', error_translations), 'level': 'error'},
             room=request.sid)
        return

    add_log_message("log.initiatingTest", "info", test_name=task_payload_for_dc.get("item_name"), device_ip=device_ip)
    response_from_device = device_communicator.send_task_to_device_client(device_ip, device_port, task_payload_for_dc)

    if response_from_device and response_from_device.get('status') == 'task_accepted_by_device_client':
        task_id_from_device = response_from_device.get('task_id', 'N/A')
        add_log_message("log.testInitiatedSuccess", "success", test_name=task_payload_for_dc.get("item_name"),
                        device_ip=device_ip, task_id=task_id_from_device)
        emit('test_initiation_result', {'success': True,
                                        'message': f"Задача '{task_payload_for_dc.get('item_name')}' стартирана към {device_ip}. ID: {task_id_from_device}"},
             room=request.sid)
    else:
        add_log_message("log.testInitiatedFail", "error", test_name=task_payload_for_dc.get("item_name"),
                        device_ip=device_ip)
        emit('test_initiation_result', {'success': False,
                                        'message': f"Неуспешно стартиране на задача '{task_payload_for_dc.get('item_name')}' към {device_ip}"},
             room=request.sid)

# ДОБАВЕТЕ ТОЗИ КОД В backend/app.py

@app.route('/api/device/report', methods=['POST'])
def handle_device_report():
    """
    Това е новият REST API ендпойнт, който "слуша" за доклади
    от подчинените приложения (DeviceClientApp).
    """
    # 1. Получаваме данните, изпратени като JSON
    data = request.get_json()
    if not data:
        logger.warning(f"Получена е празна заявка към /api/device/report от IP: {request.remote_addr}")
        return jsonify({"status": "error", "message": "No data received"}), 400

    # 2. Извличаме информацията, която очакваме
    device_id = data.get('device_id', 'UnknownDevice')
    report_type = data.get('report_type', 'generic') # напр. 'test_started', 'test_result', 'error_report'
    message = data.get('message', 'No details provided.')
    payload = data.get('payload', {}) # Допълнителни данни, напр. резултати от тест

    # 3. Логваме информацията на сървъра за дебъгване
    logger.info(f"Получен доклад от устройство '{device_id}' (Тип: {report_type}): {message}")
    if payload:
        logger.debug(f"Допълнителни данни (payload) от '{device_id}': {payload}")

    # 4. КЛЮЧОВА СТЪПКА: Излъчваме събитие към браузъра чрез SocketIO
    # Това ще позволи на test_interface.html да се актуализира в реално време.
    socketio.emit('device_report_received', {
        'device_id': device_id,
        'report_type': report_type,
        'message': message,
        'payload': payload
    })

    # 5. Връщаме отговор на DeviceClientApp, че сме получили доклада успешно
    return jsonify({"status": "report_received_ok"}), 200


logger.info("Конфигурацията на Flask приложението и SocketIO е завършена.")