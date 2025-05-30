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

# --- Конфигурация на Логването (ЗАПАЗВАМЕ ВАШАТА, ОТЛИЧНА Е) ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if Config.DEBUG else logging.INFO)
log_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'asmg_app.log')
file_handler = RotatingFileHandler(log_file_path, maxBytes=1024 * 1024 * 5, backupCount=5, encoding='utf-8')
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)
logger.info("Приложението ASMg се стартира...")

# --- Глобални Променливи (с възстановена пълна структура) ---
global_line_status_data =\
{
    "current_operator": None,
    "current_travel_lot": None,
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

    "turntable2": {
        "1": {"status": "status.idle", "moduleIds": [], "time": 0, "progress": 0},
        "2": {"status": "status.idle", "moduleIds": [], "time": 0, "progress": 0},
        "3": {"status": "status.idle", "moduleIds": [], "time": 0, "progress": 0},
        "4": {"status": "status.idle", "moduleIds": [], "time": 0, "progress": 0}
    },
    "trays": {
        "in": {"status": "status.empty"}, "out": {"status": "status.empty"}
    }
}

# --- Инициализация на Приложението (ОСТАВА СЪЩАТА) ---
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.config.from_object(Config)
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app, resources={r"/*": {"origins": "*"}})

# --- Зареждане на Преводи и API Клиент (ОСТАВАТ СЪЩИТЕ) ---
translations_path = os.path.join(os.path.dirname(__file__), 'translations')
translation_data = load_translations(translations_path)
traceability_api_client = TraceabilityAPI(
    base_url=Config.TRACEABILITY_API_URL,
    api_key=Config.TRACEABILITY_API_KEY,
    logger_func=logger
)


# --- Помощни Функции ---
# ПРЕМАХВАМЕ update_operator_status_app и get_current_operator_app.
# Тяхната логика ще се поеме от новите SocketIO хендлъри.
# Функцията add_log_message остава, тъй като е полезна.
# --- Помощни Функции ---
def add_log_message(message_key, level='info', **kwargs):
    """
    КОРИГИРАНА ВЕРСИЯ: Тази функция вече е безопасна за извикване отвсякъде.
    """
    lang_code = Config.DEFAULT_LANGUAGE

    # --- ТОВА Е КЛЮЧОВАТА ПРОМЯНА ---
    try:
        # Опитваме се да достъпим 'session', само ако сме в контекста на заявка.
        if request:
            lang_code = session.get('language', Config.DEFAULT_LANGUAGE)
    except RuntimeError:
        # Ако получим грешка 'Working outside of request context',
        # ние я "хващаме" и просто продължаваме, използвайки езика по подразбиране.
        # logger.debug("add_log_message извикана извън контекст, използва се език по подразбиране.")
        pass

    message_template = get_translation(message_key, lang_code, translation_data, fallback_lang=Config.DEFAULT_LANGUAGE)

    # Използваме try-except и за форматирането, за да избегнем други грешки
    try:
        final_message = message_template.format(**kwargs)
    except KeyError:
        final_message = message_template  # Връщаме шаблона, ако липсва ключ за форматиране

    log_level_map = {'debug': logging.DEBUG, 'info': logging.INFO, 'success': logging.INFO, 'warning': logging.WARNING,
                     'error': logging.ERROR}
    logger.log(log_level_map.get(level.lower(), logging.INFO), f"UI LOG [{lang_code.upper()}]: {final_message}")

    # Изпращаме съобщението към всички свързани клиенти
    socketio.emit('log_message', {'message': final_message, 'level': level})


# --- Инициализация на услугите ---
from backend.services.com_port_manager import ComPortManager

# КЛЮЧОВА ПРОМЯНА: Инициализираме ComPortManager с новия, прост конструктор.
com_port_scanner = ComPortManager(
    port=Config.BARCODE_SCANNER_PORT,
    baudrate=Config.BARCODE_SCANNER_BAUDRATE,
    socketio=socketio
)
logger.info(f"ComPortManager инициализиран за порт {Config.BARCODE_SCANNER_PORT} с новата опростена архитектура.")

# Симулаторът остава същият за момента
from backend.services.data_simulator import DataSimulatorThread

data_simulator = DataSimulatorThread(socketio, global_line_status_data, add_log_message)
logger.info("DataSimulatorThread инициализиран.")

# --- Регистриране на API Маршрути ---
from backend.api import register_api_routes

# ВАЖНО: Премахваме последния аргумент update_operator_status_app, тъй като функцията вече не съществува
register_api_routes(app, socketio, global_line_status_data, translation_data)
logger.info("API маршрутите са регистрирани.")


# Файл: backend/app.py

# Намерете тази функция в app.py и я заменете

@app.route('/')
def index():
    logger.debug(f"Заявка към '/' от {request.remote_addr}. Сесия: {session}")
    lang_code = session.get('language', Config.DEFAULT_LANGUAGE)
    current_translations = translation_data.get(lang_code, translation_data.get(Config.DEFAULT_LANGUAGE, {}))

    initial_render_data = {
        "overall_status": global_line_status_data.get("overall_status", "status.idle"),
        "robots": global_line_status_data.get("robots", {}),
        "turntable1": global_line_status_data.get("turntable1", {}),
        "turntable2": global_line_status_data.get("turntable2", {}),
        "trays": global_line_status_data.get("trays", {})
    }

    # --- ДОБАВЕН ЛОГ ЗА ДЕБЪГ ---
    logger.debug(f"Подаване на initial_data към index.html. Ключ 'turntable2' съществува: {'turntable2' in initial_render_data}")
    # logger.debug(f"ПЪЛНО СЪДЪРЖАНИЕ НА INITIAL_DATA: {json.dumps(initial_render_data, indent=2)}") # Разкоментирайте при нужда

    return render_template('index.html',
                           translations=current_translations,
                           current_lang=lang_code,
                           supported_languages=Config.SUPPORTED_LANGUAGES,
                           initial_data=initial_render_data)


@app.route('/set_language/<lang_code>')
def set_language_route(lang_code):
    # Тази функция остава същата.
    if lang_code in Config.SUPPORTED_LANGUAGES:
        session['language'] = lang_code
    return redirect(url_for('index'))


# --- SocketIO Събития ---
# ПРОМЕНЯМЕ ЛОГИКАТА ТУК

# Добавяме флаг, за да сме сигурни, че стартираме нишката само веднъж
com_reader_started = False


@socketio.on('connect')
def handle_connect():
    """
    Обработва свързването на нов клиент.
    При свързване на ПЪРВИЯ клиент, стартира фоновата задача за четене от COM порта.
    """
    global com_reader_started
    logger.info(f"Клиент {request.sid} се свърза.")

    # Синхронизираме достъпа до флага, за да няма проблеми при много бързи връзки
    with app.app_context():
        if not com_reader_started:
            if com_port_scanner and com_port_scanner.is_running:
                com_port_scanner.start_reading_task()
                com_reader_started = True
            else:
                logger.error("SocketIO client connected, but ComPortManager is not ready.")

    # При свързване, изпращаме нужните данни (преводи) на конкретния клиент
    handle_request_initial_data()


@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Клиент {request.sid} се разкачи.")


@socketio.on('request_initial_data')
def handle_request_initial_data():
    """
    Изпраща само базови данни към клиента при заявка - основно преводи.
    """
    lang_code = session.get('language', Config.DEFAULT_LANGUAGE)
    current_translations = translation_data.get(lang_code, translation_data.get(Config.DEFAULT_LANGUAGE, {}))

    emit('initial_data', {
        'translations': current_translations,
        'current_lang': lang_code,
        'supported_languages': Config.SUPPORTED_LANGUAGES
    })
    logger.debug(f"Изпратени са начални данни (преводи) на клиент {request.sid}")


# --- НОВИ ХЕНДЛЪРИ ЗА НОВАТА АРХИТЕКТУРА ---

@socketio.on('validate_operator')
def handle_validate_operator(data):
    """
    Получава баркод от JS, валидира го през API и връща резултат.
    Това е "мозъкът" на сървърната част за тази операция.
    """
    badge_id = data.get('barcode')
    if not badge_id:
        return

    logger.info(f"Получена заявка за валидация на оператор с бадж: {badge_id}")
    add_log_message("log.validatingOperator", "info", badge_id=badge_id)

    response = traceability_api_client.validate_operator_badge(reader_id=badge_id)

    is_valid = False
    operator_info = None

    if response and "VALUES" in response and isinstance(response.get("VALUES"), dict):
        api_data = response["VALUES"]
        if str(api_data.get("P_EXID")) == "0":
            is_valid = True
            operator_info = {
                "id": badge_id,
                "name": api_data.get("P_NAME", "N/A"),
                "employee_no": api_data.get("P_EMNO", badge_id)
            }
            # Запазваме логнатия оператор в глобалното състояние на сървъра
            global_line_status_data['current_operator'] = operator_info
            add_log_message("log.operatorLoggedIn", "success", operator_name=operator_info['name'])
        else:
            error_message = api_data.get("P_EXMES", "Unknown validation error")
            add_log_message("log.operatorApiValidationFailed", "warning", error=error_message)
    else:
        add_log_message("log.operatorApiError", "error", badge_id=badge_id)

    # Изпращаме резултата ОБРАТНО към клиента, който го поиска
    emit('operator_validation_result', {'is_valid': is_valid, 'operator_info': operator_info})


@socketio.on('language_changed')
def handle_language_changed(data):
    # Тази функция остава същата
    lang_code = data.get('lang')
    if lang_code in Config.SUPPORTED_LANGUAGES:
        session['language'] = lang_code
        logger.info(f"Клиент {request.sid} смени езика на {lang_code}")
        # Изпращаме му новите преводи
        handle_request_initial_data()


# ДОБАВЕТЕ ТОЗИ КОД ВЪВ ФАЙЛА backend/app.py

@socketio.on('logout_request')
def handle_logout_request():
    """
    Обработва заявка за изход от системата от страна на клиента.
    """
    logger.info(f"Клиент {request.sid} поиска изход от системата.")

    # Нулираме оператора в глобалното състояние
    logged_out_operator = global_line_status_data.get('current_operator')
    global_line_status_data['current_operator'] = None

    if logged_out_operator:
        add_log_message("log.operatorLoggedOut", "info", operator_name=logged_out_operator.get('name', ''))

    # Изпращаме същия тип събитие като при валидация, но с празни данни
    # за да може UI да се върне в начално състояние.
    emit('operator_validation_result', {'is_valid': False, 'operator_info': None})


# ДОБАВЕТЕ ТОЗИ КОД ВЪВ ФАЙЛА backend/app.py

# Намерете тази функция в backend/app.py и я заменете с този код

@socketio.on('validate_travel_lot')
def handle_validate_travel_lot(data):
    """
    Получава баркод на маршрутна карта, валидира го и регистрира нова поръчка.
    (ВЕРСИЯ С ПОДОБРЕНО ЛОГВАНЕ И ПРОВЕРКИ)
    """
    travel_lot_barcode = data.get('barcode')
    if not travel_lot_barcode:
        return

    current_operator = global_line_status_data.get('current_operator')
    if not current_operator:
        add_log_message("log.operatorLoginRequired", "error")
        emit('travel_lot_validation_result', {'is_valid': False, 'error': 'No operator logged in'})
        return

    workplace_id = Config.TRACEABILITY_WORKPLACE_ID
    employee_id = current_operator.get('employee_no')

    logger.info(f"Получена заявка за валидация на маршрутна карта: {travel_lot_barcode} от оператор ID: {employee_id}")

    # Извикваме API функцията
    response = traceability_api_client.ftpck_new_order(
        workplace_id=workplace_id,
        route_map=travel_lot_barcode,
        employee_id=employee_id
    )

    # 1. ПРОВЕРЯВАМЕ ДАЛИ ИЗОБЩО ИМАМЕ ОТГОВОР ОТ API-то
    if not response:
        logger.error("API клиентът върна None. Няма връзка или има грешка при заявката.")
        add_log_message("log.operatorApiError", "error",
                        badge_id=travel_lot_barcode)  # Може да се наложи нов ключ за превод
        emit('travel_lot_validation_result', {'is_valid': False, 'travel_lot_info': None})
        return

    # 2. ЛОГВАМЕ ЦЕЛИЯ ОТГОВОР, ЗА ДА ГО ВИДИМ
    logger.debug(f"Пълен отговор от API за ftpck_new_order: {response}")

    is_valid = False
    travel_lot_info = None

    # ВАЖНО: Вече е възможно отговорът да няма ключ "VALUES", затова го достъпваме безопасно
    api_values = response.get("VALUES", {})
    if not isinstance(api_values, dict):  # Уверяваме се, че VALUES е речник
        api_values = {}

    # 3. ИЗВЛИЧАМЕ P_EXID ПО-БЕЗОПАСНО
    p_exid_value = api_values.get("P_EXID")

    # 4. ЛОГВАМЕ ТИПА И СТОЙНОСТТА НА P_EXID
    logger.debug(f"Стойност на P_EXID: '{p_exid_value}', Тип на P_EXID: {type(p_exid_value)}")

    # 5. ПРАВИМ ПО-УСТОЙЧИВО СРАВНЕНИЕ
    # Това ще работи правилно, независимо дали p_exid_value е числото 0, низът "0", или дори None.
    if p_exid_value is not None and str(p_exid_value) == "0":
        logger.info("Условието за успех (P_EXID == 0) е изпълнено.")
        is_valid = True
        travel_lot_info = {
            "id": travel_lot_barcode,
            "productNumber": api_values.get("P_MITM", "N/A"),
            "description": "Описание от API"  # Може да се наложи да се вземе от друго поле
        }
        global_line_status_data['current_travel_lot'] = travel_lot_info
        add_log_message("log.travelLotIdentified", "success", lot_id=travel_lot_barcode,
                        item_number=travel_lot_info['productNumber'])
    else:
        logger.warning(f"Условието за успех (P_EXID == 0) НЕ е изпълнено. P_EXID = '{p_exid_value}'")
        error_message = response.get("P_EXMES", "Unknown error from API")
        add_log_message("log.travelLotApiError", "error", error=error_message)

    emit('travel_lot_validation_result', {'is_valid': is_valid, 'travel_lot_info': travel_lot_info})