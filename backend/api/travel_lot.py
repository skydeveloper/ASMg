from flask import request, jsonify
# from backend.app import global_line_status_data, add_log_message # Не импортирайте директно

def register_travel_lot_routes(app, socketio, translations, line_status_data_ref):
    """
    Регистрира маршрути, свързани с пътни карти.
    line_status_data_ref е референция към global_line_status_data от app.py
    """
    from backend.app import add_log_message # Късен импорт

    @app.route('/api/travel_lot/scan', methods=['POST'])
    def api_scan_travel_lot():
        data = request.get_json()
        lot_id = data.get('lot_id')

        if not lot_id:
            return jsonify({"status": "error", "message": "Travel lot ID is required"}), 400

        # Примерна логика за обработка на пътна карта
        # В реално приложение, тук ще има заявка към база данни или ERP система
        if lot_id == "TL-001":
            travel_lot_info = {
                "id": lot_id,
                "productNumber": "PROD-XYZ-001",
                "description": "Модул за контрол на осветление ( от API )",
                "orderNumber": "ORD-98765",
                "quantity": 1000
            }
        elif lot_id == "TL-002":
            travel_lot_info = {
                "id": lot_id,
                "productNumber": "PROD-ABC-002",
                "description": "Захранващ блок (от API)",
                "orderNumber": "ORD-12345",
                "quantity": 500
            }
        else:
            add_log_message("log.travelLotNotFound", "error", lot_id=lot_id)
            return jsonify({"status": "error", "message": f"Travel lot {lot_id} not found"}), 404

        line_status_data_ref['current_travel_lot'] = travel_lot_info
        socketio.emit('travel_lot_update', {'travel_lot': travel_lot_info})
        add_log_message("log.travelLotIdentified", "info", lot_id=lot_id, item_number=travel_lot_info['productNumber'])
        return jsonify({"status": "success", "message": "Travel lot processed", "data": travel_lot_info}), 200

    @socketio.on('clear_travel_card_request')
    def handle_clear_travel_card():
        from backend.app import add_log_message # Късен импорт
        line_status_data_ref['current_travel_lot'] = None
        socketio.emit('travel_lot_update', {'travel_lot': None})
        add_log_message("log.travelCardCleared", "info")