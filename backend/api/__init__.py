from flask import jsonify
# Коригирани относителни импорти
from .operator_routes import register_operator_routes
from .travel_lot import register_travel_lot_routes
# from .machine_status import register_machine_status_routes # Този ред може да бъде коментиран, ако нямате такива маршрути все още

def register_api_routes(app, socketio, line_status_data, translations_data, update_operator_callback):
    """
    Регистрира всички API маршрути към Flask приложението.
    """
    # Регистриране на маршрут за преводи
    @app.route('/api/translations/<lang_code>')
    def get_translations_api(lang_code): # Преименувах функцията, за да избегна конфликт с глобалната get_translation
        from backend.config import Config # Импортираме тук, за да избегнем кръгови зависимости при стартиране
        if lang_code in translations_data:
            return jsonify(translations_data[lang_code])
        elif Config.DEFAULT_LANGUAGE in translations_data: # Връщане на езика по подразбиране, ако исканият не е намерен
            return jsonify(translations_data[Config.DEFAULT_LANGUAGE])
        return jsonify({"error": f"Language '{lang_code}' not found and no default translations available."}), 404

    # Извикване на функциите за регистрация на маршрути от другите модули
    register_operator_routes(app, socketio, translations_data, update_operator_callback)
    register_travel_lot_routes(app, socketio, translations_data, line_status_data) # Подаваме и line_status_data
    # register_machine_status_routes(app, socketio, line_status_data, translations_data)