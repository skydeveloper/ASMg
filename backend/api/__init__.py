# Файл: backend/api/__init__.py
from flask import jsonify
# Коригирани относителни импорти
from .operator_routes import register_operator_routes
from .travel_lot import register_travel_lot_routes


# from .machine_status import register_machine_status_routes

# 1. ПРЕМАХВАМЕ 'update_operator_callback' от дефиницията на функцията
def register_api_routes(app, socketio, line_status_data, translations_data):
    """
    Регистрира всички API маршрути към Flask приложението.
    """

    # Регистриране на маршрут за преводи
    @app.route('/api/translations/<lang_code>')
    def get_translations_api(lang_code):
        from backend.config import Config
        if lang_code in translations_data:
            return jsonify(translations_data[lang_code])
        elif Config.DEFAULT_LANGUAGE in translations_data:
            return jsonify(translations_data[Config.DEFAULT_LANGUAGE])
        return jsonify({"error": f"Language '{lang_code}' not found."}), 404

    # Извикване на функциите за регистрация на маршрути от другите модули

    # 2. ПРЕМАХВАМЕ 'update_operator_callback' и от извикването на тази функция
    register_operator_routes(app, socketio, translations_data)

    register_travel_lot_routes(app, socketio, translations_data, line_status_data)
    # register_machine_status_routes(app, socketio, line_status_data, translations_data)