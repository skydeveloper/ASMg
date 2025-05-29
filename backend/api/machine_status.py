# backend/api/machine_status.py

def register_machine_status_routes(app, socketio, line_status_data, translations_data):
    """
    Регистрира маршрути, свързани със статуса на машината, ако са необходими API ендпойнтове.
    В момента повечето актуализации на статуса се извършват чрез SocketIO.
    """
    # Пример:
    # @app.route('/api/machine/command', methods=['POST'])
    # def machine_command():
    #     # Логика за изпращане на команди към PLC/машината
    #     return jsonify({"status": "command_sent"})
    pass