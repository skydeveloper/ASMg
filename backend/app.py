# Файл: ASMg/backend/app.py

import os
import json
import threading
import time
import logging  # Нов импорт за логване
from logging.handlers import RotatingFileHandler  # За ротация на лог файловете

from flask import Flask, jsonify, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, emit
from flask_cors import CORS

# Импорти от вашия проект
from backend.config import Config
from backend.translations.translation_manager import load_translations, get_translation
from backend.services.traceability_api import TraceabilityAPI

# --- Конфигурация на Логването ---
# Създаваме логер
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if Config.DEBUG else logging.INFO)  # Ниво на логване

# Handler за запис във файл
log_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'asmg_app.log')  # В коренната папка на проекта
file_handler = RotatingFileHandler(log_file_path, maxBytes=1024 * 1024 * 5, backupCount=5,
                                   encoding='utf-8')  # 5MB на файл, 5 бекъпа
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Handler за конзолата (ако искате и стандартното Python логване в конзолата, освен print)
# console_handler = logging.StreamHandler()
# console_handler.setFormatter(file_formatter) # Може да използва същия или друг формат
# logger.addHandler(console_handler)

logger.info("Приложението ASMg се стартира...")  # Първо лог съобщение

# --- Глобални Променливи ---
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
    "turntable2": {
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
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Зареждане на Преводи ---
translations_path = os.path.join(os.path.dirname(__file__), 'translations')
translation_data = load_translations(translations_path)
logger.debug(f"Заредени езици за превод: {list(translation_data.keys())}")

# --- Инициализация на Traceability API клиента ---
traceability_api_client = TraceabilityAPI(
    base_url=Config.TRACEABILITY_API_URL,
    api_key=Config.TRACEABILITY_API_KEY,
    logger_func=logger  # Подаваме логера на API клиента
)
logger.info(f"Traceability API клиент инициализиран за URL: {Config.TRACEABILITY_API_URL}")


# --- Помощни Функции ---
def add_log_message(message_key_or_raw_msg, level='info', force_default_lang=False, is_raw_message=False, **kwargs):
    """
    Генерира и изпраща лог съобщение към клиента и го записва във файл.
    message_key_or_raw_msg: Ключ за превод или директно съобщение (ако is_raw_message=True).
    kwargs се използват за форматиране на съобщението, ако е ключ.
    force_default_lang: Ако е True или ако сме извън request контекст, винаги използва езика по подразбиране.
    """
    lang_code = Config.DEFAULT_LANGUAGE
    final_message = ""

    if is_raw_message:
        final_message = message_key_or_raw_msg
    else:
        if not force_default_lang:
            try:
                if request:  # Проверява дали request обектът е наличен
                    lang_code = session.get('language', Config.DEFAULT_LANGUAGE)
            except RuntimeError:
                # Извън контекст на заявка, lang_code остава Config.DEFAULT_LANGUAGE
                pass

        message_template = get_translation(message_key_or_raw_msg, lang_code, translation_data,
                                           fallback_lang=Config.DEFAULT_LANGUAGE)
        try:
            final_message = message_template.format(**kwargs)
        except KeyError as e:
            logger.error(
                f"KeyError при форматиране на лог съобщение: {e} за ключ '{message_key_or_raw_msg}' с аргументи {kwargs}. Шаблон: '{message_template}'")
            final_message = f"{message_key_or_raw_msg} (translation/formatting error)"

    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    log_entry_socket = {  # За SocketIO към клиента
        'timestamp': timestamp,
        'message': final_message,
        'level': level
    }
    socketio.emit('log_message', log_entry_socket)

    # Логване във файл чрез стандартния logging модул
    log_level_map = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }
    logger.log(log_level_map.get(level.lower(), logging.INFO), f"[{lang_code.upper()}] {final_message}")


def update_operator_status_app(operator_info):
    """Актуализира статуса на оператора и изпраща съобщение до клиента."""
    global_line_status_data['current_operator'] = operator_info
    socketio.emit('operator_status_update', {'operator': operator_info})

    if operator_info:
        if operator_info.get("name"):
            log_message_key = "log.operatorLoggedIn"
            log_args = {"operator_id": operator_info.get("id", "N/A"),
                        "operator_name": operator_info.get("name", "Unknown")}
        else:
            log_message_key = "log.operatorScanFailed"
            log_args = {"operator_id": operator_info.get("id", "N/A")}
    else:
        log_message_key = "log.operatorLoggedOut"
        log_args = {}
    add_log_message(log_message_key, 'info', force_default_lang=True, **log_args)


def get_current_operator_app():
    """Връща информация за текущия логнат оператор."""
    return global_line_status_data['current_operator']


# --- Инициализация на услугите ---
from backend.services.com_port_manager import ComPortManager

com_port_scanner = ComPortManager(
    port=Config.BARCODE_SCANNER_PORT,
    baudrate=Config.BARCODE_SCANNER_BAUDRATE,
    socketio=socketio,
    # translations=translation_data, # Вече не е нужно, тъй като add_log_message се справя
    add_log_message_func=add_log_message,
    update_operator_callback=update_operator_status_app,
    get_current_operator_callback=get_current_operator_app,
    traceability_api=traceability_api_client,
    workplace_id=Config.TRACEABILITY_WORKPLACE_ID
)
logger.info(f"ComPortManager инициализиран за порт {Config.BARCODE_SCANNER_PORT}")

from backend.services.data_simulator import DataSimulatorThread

data_simulator = DataSimulatorThread(socketio, global_line_status_data, add_log_message)  # Премахваме translations
logger.info("DataSimulatorThread инициализиран.")

# --- Регистриране на API Маршрути ---
from backend.api import register_api_routes

register_api_routes(app, socketio, global_line_status_data, translation_data, update_operator_status_app)
logger.info("API маршрутите са регистрирани.")


# --- Основни Маршрути на Приложението (Views) ---
@app.route('/')
def index():
    logger.debug(f"Заявка към '/' от {request.remote_addr}. Сесия: {session}")
    lang_code = session.get('language', Config.DEFAULT_LANGUAGE)
    default_translations = translation_data.get(Config.DEFAULT_LANGUAGE, {})
    current_translations = translation_data.get(lang_code, default_translations)

    initial_render_data = {
        key: global_line_status_data[key] for key in [
            "overall_status", "robots", "turntable1", "turntable2", "trays",
            "current_operator", "current_travel_lot"
        ]
    }
    return render_template('index.html',
                           translations=current_translations,
                           initial_data=initial_render_data,
                           current_lang=lang_code,
                           supported_languages=Config.SUPPORTED_LANGUAGES)


@app.route('/set_language/<lang_code>')
def set_language_route(lang_code):
    if lang_code in Config.SUPPORTED_LANGUAGES:
        session['language'] = lang_code
        logger.info(f"Езикът е сменен на {lang_code} за сесия {session.sid if session.sid else 'N/A'}")
    else:
        logger.warning(f"Опит за смяна на език с невалиден код: {lang_code}")
    return redirect(url_for('index'))


# --- SocketIO Събития ---
@socketio.on('connect')
def handle_connect():
    logger.info(f"Клиент {request.sid} се свърза от {request.remote_addr}")
    add_log_message('socket.connected', 'success', force_default_lang=True)  # Този лог е за всички клиенти
    socketio.emit('request_initial_data', room=request.sid)  # Изпращаме само на новия клиент


@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Клиент {request.sid} се разкачи.")
    # add_log_message('socket.disconnected', 'info', force_default_lang=True) # Това ще се опита да изпрати до всички


@socketio.on('request_initial_data')
def handle_request_initial_data(data=None):
    lang_code = Config.DEFAULT_LANGUAGE
    if data and 'lang' in data and data['lang'] in Config.SUPPORTED_LANGUAGES:
        lang_code = data['lang']
    elif 'language' in session and session['language'] in Config.SUPPORTED_LANGUAGES:
        lang_code = session.get('language')

    session['language'] = lang_code
    logger.debug(f"Клиент {request.sid} поиска начални данни. Език: {lang_code}")

    current_state_snapshot = {
        key: global_line_status_data[key] for key in [
            "overall_status", "robots", "turntable1", "turntable2", "trays",
            "current_operator", "current_travel_lot"
        ]
    }
    default_translations = translation_data.get(Config.DEFAULT_LANGUAGE, {})
    current_translations = translation_data.get(lang_code, default_translations)

    emit('initial_data', {
        'line_status': current_state_snapshot,
        'translations': current_translations,
        'current_lang': lang_code,
        'supported_languages': Config.SUPPORTED_LANGUAGES
    }, room=request.sid)  # Изпращаме само на клиента, който е поискал

    if not global_line_status_data['current_operator']:
        emit('require_operator_login', room=request.sid)


@socketio.on('language_changed')
def handle_language_changed(data):
    lang_code = data.get('lang')
    if lang_code in Config.SUPPORTED_LANGUAGES:
        session['language'] = lang_code
        logger.info(f"Клиент {request.sid} смени езика на {lang_code}")
        handle_request_initial_data({'lang': lang_code})
    else:
        logger.warning(f"Клиент {request.sid} опита да смени езика с невалиден код: {lang_code}")


logger.info("Конфигурацията на Flask приложението и SocketIO е завършена.")