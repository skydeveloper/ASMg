from flask import request, jsonify
# from backend.app import current_operator, update_operator_status # Не импортирайте директно така, предавайте като аргумент

def register_operator_routes(app, socketio, translations, update_operator_callback_func):
    """
    Регистрира маршрути, свързани с оператора.
    update_operator_callback_func е функция, която се извиква за актуализиране на статуса на оператора.
    """

    @app.route('/api/operator/login', methods=['POST'])
    def api_operator_login():
        data = request.get_json()
        operator_id = data.get('operator_id')
        # Тук бихте имали логика за валидиране на операторския ID, може би от база данни
        # За демонстрация, приемаме всяко ID
        if operator_id:
            # Симулираме намиране на име на оператор
            operator_name = f"Operator {operator_id}" # В реално приложение, това ще идва от база данни
            operator_info = {"id": operator_id, "name": operator_name}
            update_operator_callback_func(operator_info)
            return jsonify({"status": "success", "message": "Operator logged in", "operator": operator_info}), 200
        return jsonify({"status": "error", "message": "Operator ID is required"}), 400

    @app.route('/api/operator/logout', methods=['POST'])
    def api_operator_logout():
        update_operator_callback_func(None) # Изчиства текущия оператор
        return jsonify({"status": "success", "message": "Operator logged out"}), 200

    @socketio.on('operator_logout_request')
    def handle_operator_logout_request():
        from backend.app import add_log_message # Късен импорт за избягване на кръгови зависимости
        # Достъп до current_operator от app.py или го предайте по друг начин, ако е необходимо
        # Засега предполагаме, че com_port_manager ще се справи с това
        # Тук само изпращаме съобщение за излизане, com_port_manager ще нулира current_operator
        # и ще изпрати operator_status_update
        update_operator_callback_func(None) # Изчиства текущия оператор
        add_log_message("log.operatorLoggedOut", "info")
        socketio.emit('operator_status_update', {'operator': None})


    # Добавете други маршрути, свързани с оператора, ако е необходимо