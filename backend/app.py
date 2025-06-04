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
from backend.services.device_communicator import DeviceCommunicator  # Уверете се, че импортът е тук

# --- Конфигурация на Логването ---
logger = logging.getLogger(__name__)  # Използвайте __name__ за логера на този модул
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
    # Може да добавите и ключ за active_tests, ако искате да ги следите:
    # "active_tests": {}
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
    logger_func=logger  # Подаваме основния логер
)
logger.info("TraceabilityAPI client initialized.")

device_communicator = DeviceCommunicator() # <--- ПРЕМАХВАМЕ logger_func=logger
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

    # Логваме и към файла чрез стандартния логер
    log_level_map = {'debug': logging.DEBUG, 'info': logging.INFO, 'success': logging.INFO, 'warning': logging.WARNING,
                     'error': logging.ERROR}
    logger.log(log_level_map.get(level.lower(), logging.INFO), f"UI LOG TARGET: [{lang_code.upper()}] {final_message}")

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
    # Синхронизацията с app.app_context() вече не е нужна тук, ако com_port_scanner.is_running се проверява правилно
    if not com_reader_started:
        if com_port_scanner and com_port_scanner.is_running:  # Проверка дали портът е успешно отворен
            com_port_scanner.start_reading_task()
            com_reader_started = True
        elif com_port_scanner and not com_port_scanner.is_running:
            logger.warning(
                "COM Port reader not started because com_port_scanner.is_running is False (port likely not opened).")
        else:
            logger.error("SocketIO client connected, but ComPortManager is not initialized or port not open.")

    handle_request_initial_data()  # Изпращане на данни на свързания клиент


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
    })


# Премахваме дублирания @socketio.on('update_status') - вече го имаме в data_simulator
# @socketio.on('update_status')
# def handle_status_updates(data):
#     socketio.emit('status_updated', data) # По-добре е да е 'update_status', както е в JS

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
            operator_info = {"id": badge_id, "name": api_data.get("P_NAME", "N/A"),
                             "employee_no": api_data.get("P_EMNO", badge_id)}
            global_line_status_data['current_operator'] = operator_info
            add_log_message("log.operatorLoggedIn", "success", operator_name=operator_info['name'])
    emit('operator_validation_result', {'is_valid': is_valid, 'operator_info': operator_info})


# Само една дефиниция на handle_validate_travel_lot
@socketio.on('validate_travel_lot')
def handle_validate_travel_lot(data):
    travel_lot_barcode = data.get('barcode')
    current_operator = global_line_status_data.get('current_operator')
    if not (travel_lot_barcode and current_operator):
        if not current_operator:
            add_log_message("log.operatorLoginRequired", "error")  # Добавяме лог, ако няма оператор
        emit('travel_lot_validation_result',
             {'is_valid': False, 'error': 'No operator logged in or no travel lot barcode'})
        return

    workplace_id = Config.TRACEABILITY_WORKPLACE_ID
    employee_id = current_operator.get('employee_no')

    logger.info(f"Получена заявка за валидация на маршрутна карта: {travel_lot_barcode} от оператор ID: {employee_id}")
    add_log_message("log.processingTravelCard", "info", barcodeData=travel_lot_barcode)  # Използваме съществуващия ключ

    response = traceability_api_client.ftpck_new_order(
        workplace_id=workplace_id,
        route_map=travel_lot_barcode,
        employee_id=employee_id
    )
    is_valid, travel_lot_info = False, None
    if not response:
        logger.error("API клиентът (ftpck_new_order) върна None.")
        add_log_message("log.travelLotApiError", "error", error="No response from API")  # По-добър ключ
    elif response.get("VALUES"):  # Проверка дали VALUES съществува
        api_values = response.get("VALUES", {})
        p_exid_value = api_values.get("P_EXID")
        logger.debug(f"Отговор от API за ftpck_new_order: {response}, P_EXID: {p_exid_value}")
        if p_exid_value is not None and str(p_exid_value) == "0":
            is_valid = True
            travel_lot_info = {"id": travel_lot_barcode, "productNumber": api_values.get("P_MITM", "N/A")}
            global_line_status_data['current_travel_lot'] = travel_lot_info
            add_log_message("log.travelLotIdentified", "success", lot_id=travel_lot_barcode,
                            item_number=travel_lot_info['productNumber'])
        else:
            error_message = response.get("P_EXMES", "Unknown API error for travel lot")
            add_log_message("log.travelLotApiError", "error", error=error_message)
    else:  # Ако няма VALUES, но има отговор, вероятно е грешка
        error_message = response.get("P_EXMES") or response.get("MESSAGE", "Unknown API structure error for travel lot")
        add_log_message("log.travelLotApiError", "error", error=error_message)

    emit('travel_lot_validation_result', {'is_valid': is_valid, 'travel_lot_info': travel_lot_info})


# Само една дефиниция на handle_logout_request
@socketio.on('logout_request')
def handle_logout_request():
    logged_out_operator = global_line_status_data.get('current_operator')
    global_line_status_data['current_operator'] = None
    if logged_out_operator:
        add_log_message("log.operatorLoggedOut", "info", operator_name=logged_out_operator.get('name', ''))
    emit('operator_validation_result', {'is_valid': False, 'operator_info': None})


@socketio.on('language_changed')
def handle_language_changed(data):
    lang_code = data.get('lang')
    if lang_code in Config.SUPPORTED_LANGUAGES:
        session['language'] = lang_code
        handle_request_initial_data()


# Новият хендлър, който добавихте
@socketio.on('trigger_start_test_on_device')
def handle_trigger_start_test(data):
    module_id = data.get('module_id')
    device_ip = data.get('device_ip')
    device_port = data.get('device_port', 8000)
    test_name = data.get('test_name')

    if not all([module_id, device_ip, test_name]):
        logger.error(f"Липсват данни за trigger_start_test_on_device: {data}")
        emit('ui_notification', {'message': 'Липсват данни за стартиране на тест!', 'level': 'error'})
        return

    logger.info(
        f"Опит за стартиране на тест '{test_name}' на устройство {device_ip}:{device_port} за модул {module_id}")
    # Предполагаме, че имате такъв ключ за превод
    add_log_message("log.initiatingTest", "info", test_name=test_name, device_ip=device_ip)

    response = device_communicator.start_test_on_device(device_ip, device_port, module_id, test_name)

    if response and response.get('status') == 'test_initiated':
        task_id = response.get('task_id', 'N/A')
        logger.info(f"Тест '{test_name}' успешно стартиран на {device_ip}. Task ID: {task_id}")
        add_log_message("log.testInitiatedSuccess", "success", test_name=test_name, device_ip=device_ip,
                        task_id=task_id)
        emit('test_initiation_result', {'success': True, 'message': f"Тест '{test_name}' стартиран. ID: {task_id}"})
    else:
        logger.error(f"Неуспешно стартиране на тест '{test_name}' на {device_ip}. Отговор: {response}")
        add_log_message("log.testInitiatedFail", "error", test_name=test_name, device_ip=device_ip)
        emit('test_initiation_result', {'success': False, 'message': f"Неуспешно стартиране на тест '{test_name}'"})


# Добавете този код в backend/app.py (ако вече го нямате)
# или го редактирайте, за да подава правилните преводи

@app.route('/test_device_interface')
def test_device_interface_page():
    lang_code = session.get('language', Config.DEFAULT_LANGUAGE)
    # Взимаме основните преводи
    current_translations = translation_data.get(lang_code, translation_data.get(Config.DEFAULT_LANGUAGE, {}))

    # Дефинираме ключове, специфични за тестовата страница, ако ги няма в основните файлове
    # (по-добре е да са в JSON файловете за пълнота)
    test_interface_specific_keys = {
        "testInterface.title": "ASMg - Тестов Интерфейс за Устройства",
        "testInterface.header": "Тестов Интерфейс за Device Clients",
        "testInterface.sendCommandTitle": "Изпрати команда към Device Client",
        "testInterface.deviceIp": "IP на Устройство:",
        "testInterface.devicePort": "Порт на Устройство:",
        "testInterface.itemName": "Име/ID на Изделие (за DeviceClient):",
        "testInterface.taskDetails": "Детайли за Задачата/Фърмуер:",
        "testInterface.serialNumbersTitle": "Серийни номера (до 4):",
        "testInterface.slotActive": "Гнездо активно",
        "testInterface.sendStartCommand": "Изпрати Команда към Device Client (чрез ASMg)",
        "testInterface.logTitle": "Лог на Тестовия Интерфейс:",
        "testInterface.logWaiting": "Очаквам събития..."
    }

    # Обединяваме ги, като тези от файла translations_data имат предимство, ако съществуват
    final_translations_for_test_page = {**test_interface_specific_keys, **current_translations}

    return render_template('test_interface.html',
                           translations=final_translations_for_test_page,
                           current_lang=lang_code,
                           supported_languages=Config.SUPPORTED_LANGUAGES)


# В backend/app.py
@socketio.on('trigger_task_on_device_client')  # Променено име на събитието, за да съвпада с JS
def handle_trigger_task_on_device_client(data):
    logger.info(f"ASMg: Получена UI заявка за стартиране на задача на DeviceClient: {data}")

    device_ip = data.get('device_ip')
    device_port = data.get('device_port')

    # Събираме payload-а, който DeviceClientApp очаква
    # Имената на ключовете тук трябва да съвпадат с тези, които DeviceClientApp очаква
    # на своя /api/start_task ендпойнт
    task_payload_for_dc = {
        "module_serial_numbers": data.get("serial_numbers"),
        "active_slots": data.get("active_slots"),
        "item_name": data.get("item_name"),
        "firmware_details": data.get("task_details")
    }

    if not all([device_ip, device_port, task_payload_for_dc.get("item_name")]):  # Проверяваме основните
        emit('ui_notification', {'message': get_translation('error.missingTestData'), 'level': 'error'},
             room=request.sid)
        return

    add_log_message("log.initiatingTest", "info", test_name=task_payload_for_dc.get("item_name"), device_ip=device_ip)

    response_from_device = device_communicator.send_task_to_device_client(
        device_ip,
        device_port,
        task_payload_for_dc
    )

    if response_from_device and response_from_device.get('status') == 'task_accepted_by_device_client':
        logger.info(f"Командата към DeviceClient ({device_ip}) е приета: {response_from_device}")
        emit('test_initiation_result', {'success': True, 'message': f"Команда към DeviceClient ({device_ip}) приета."},
             room=request.sid)
    else:
        logger.error(f"Грешка при изпращане на команда към DeviceClient ({device_ip}). Отговор: {response_from_device}")
        emit('test_initiation_result',
             {'success': False, 'message': f"Грешка при команда към DeviceClient ({device_ip})."}, room=request.sid)

logger.info("Конфигурацията на Flask приложението и SocketIO е завършена.")