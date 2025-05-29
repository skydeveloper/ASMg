import serial
import threading
import time
import logging  # Ще използваме логера, конфигуриран в app.py

# Вземане на логера, конфигуриран в app.py
# Това ще работи, ако app.py е импортиран и е конфигурирал logging.getLogger(__name__)
# или ако използваме root логера. За по-голяма сигурност, може да се подаде логер инстанция.
logger = logging.getLogger("backend.app")  # Използваме името на логера от app.py

VALID_TRAVEL_LOTS = {  # Това може да остане или също да се интегрира с API
    "TL-001": {
        "id": "TL-001",
        "productNumber": "PROD-XYZ-001",
        "description": "Модул за контрол на осветление",
        "orderNumber": "ORD-98765",
        "quantity": 1000
    },
    "TL-002": {
        "id": "TL-002",
        "productNumber": "PROD-ABC-002",
        "description": "Захранващ блок",
        "orderNumber": "ORD-12345",
        "quantity": 500
    }
}


class ComPortManager:
    def __init__(self, port, baudrate, socketio, add_log_message_func,
                 update_operator_callback, get_current_operator_callback,
                 traceability_api, workplace_id):
        self.port_name = port
        self.baudrate = baudrate
        self.serial_port = None
        self.is_running = False
        self.thread = None
        self.socketio = socketio
        self.add_log_message = add_log_message_func
        self.update_operator_callback = update_operator_callback
        self.get_current_operator_callback = get_current_operator_callback
        self.traceability_api = traceability_api
        self.workplace_id = workplace_id
        # Използваме add_log_message с force_default_lang=True, тъй като това е извън request контекст
        self.add_log_message("log.comManagerInit", "debug", force_default_lang=True, port=self.port_name,
                             baudrate=self.baudrate)
        logger.info(
            f"ComPortManager initialized for port {self.port_name} at {self.baudrate} baud. Workplace ID: {self.workplace_id}")

    def open_port(self):
        try:
            self.add_log_message("log.comPortOpening", "debug", force_default_lang=True, port=self.port_name)
            logger.debug(f"Attempting to open serial port: {self.port_name}")
            self.serial_port = serial.Serial(self.port_name, self.baudrate, timeout=1)
            self.is_running = True
            self.thread = threading.Thread(target=self._read_from_port, daemon=True)
            self.thread.start()
            self.add_log_message("log.comPortOpened", "success", force_default_lang=True, port=self.port_name)
            logger.info(f"Successfully opened serial port {self.port_name}")
            return True
        except serial.SerialException as e:
            self.add_log_message("log.comPortOpenError", "error", force_default_lang=True, port=self.port_name,
                                 error=str(e))
            logger.error(f"SerialException opening port {self.port_name}: {e}")
            return False
        except Exception as e:
            self.add_log_message("log.comPortOpenErrorGeneric", "error", force_default_lang=True, port=self.port_name,
                                 error=str(e))
            logger.error(f"Generic error opening port {self.port_name}: {e}")
            return False

    def _read_from_port(self):
        buffer = ""
        self.add_log_message("log.comReaderStarted", "debug", force_default_lang=True, port=self.port_name)
        logger.info(f"Starting to read from {self.port_name}...")
        while self.is_running:
            if not self.serial_port or not self.serial_port.is_open:
                self.add_log_message("log.comPortNotOpenOrClosed", "warning", force_default_lang=True,
                                     port=self.port_name)
                logger.warning(f"Serial port {self.port_name} is not open or closed. Stopping reader thread.")
                self.is_running = False  # Спираме нишката, ако портът е затворен неочаквано
                break
            try:
                if self.serial_port.in_waiting > 0:
                    data_bytes = self.serial_port.read(self.serial_port.in_waiting)
                    try:
                        data = data_bytes.decode('utf-8').strip()
                        if not data and data_bytes:  # Ако strip е върнал празен стринг, но е имало байтове (напр. само CR/LF)
                            logger.debug(
                                f"Received whitespace/control characters from {self.port_name}: {data_bytes.hex()}")
                            continue  # Пропусни обработката на празни низове
                    except UnicodeDecodeError:
                        data = data_bytes.decode('ascii', errors='ignore').strip()
                        self.add_log_message("log.barcodeDecodeError", "warning", force_default_lang=True,
                                             data_hex=data_bytes.hex())
                        logger.warning(f"UnicodeDecodeError on port {self.port_name}, data (hex): {data_bytes.hex()}")
                        if not data:  # Ако и след ASCII декодиране и strip е празно
                            continue

                    if data:
                        logger.debug(f"Raw data received from {self.port_name}: '{data}'")
                        # Няма нужда от buffer += data и последваща обработка на буфера, ако .strip() е достатъчен
                        # и очакваме всяко сканиране да завършва с CR/LF.
                        self.socketio.sleep(0)  # Дава възможност на други събития да се обработят
                        self._process_barcode_data(data)
                else:
                    time.sleep(0.05)  # Малка пауза, ако няма данни, за да не товари CPU-то

            except serial.SerialException as e:
                self.add_log_message("log.comPortError", "error", force_default_lang=True, port=self.port_name,
                                     error=str(e))
                logger.error(f"Serial port error on {self.port_name} while reading: {e}")
                self.is_running = False
                break  # Излизаме от цикъла при грешка с порта
            except Exception as e:
                self.add_log_message("log.comPortReadError", "error", force_default_lang=True, port=self.port_name,
                                     error=str(e))
                logger.error(f"Unexpected error reading from serial port {self.port_name}: {e}", exc_info=True)
                time.sleep(0.1)  # Пауза при неочаквана грешка

        self.add_log_message("log.comReaderStopped", "info", force_default_lang=True, port=self.port_name)
        logger.info(f"Stopped reading from {self.port_name}.")

    def _process_barcode_data(self, data):
        self.add_log_message("log.barcodeReceived", "info",
                             barcodeData=data)  # Този лог ще използва езика на сесията, ако е наличен
        logger.info(f"Processing barcode: {data}")
        current_op = self.get_current_operator_callback()

        if not current_op:
            self.add_log_message("log.validatingOperator", "debug", badge_id=data)
            logger.debug(f"Validating operator badge ID: {data} via API. Workplace: {self.workplace_id}")
            response = self.traceability_api.validate_operator_badge(reader_id=data)  # reader_id е баркода на баджа

            if response:
                logger.debug(f"API Response for badge {data}: {response}")
                # API-то връща VALUES като речник директно, не като списък от речници
                if "VALUES" in response and isinstance(response["VALUES"], dict):
                    operator_api_data = response["VALUES"]

                    # Уверете се, че P_EXID се сравнява като стринг, ако API го връща така
                    if str(operator_api_data.get("P_EXID")) == "0":  # Успешна валидация
                        operator_name = operator_api_data.get("P_NAME", "N/A")
                        employee_no_from_api = operator_api_data.get("P_EMNO", data)  # P_EMNO е вътрешният номер

                        operator_info = {
                            "id": data,  # Сканиран ID на баджа
                            "name": operator_name,
                            "employee_no": employee_no_from_api  # Служебен номер от API
                        }
                        self.update_operator_callback(operator_info)  # Това ще извика и add_log_message в app.py
                        logger.info(f"Operator validated: {operator_name} ({data})")
                    else:
                        # Валидацията е неуспешна според API (P_EXID != "0" или липсва)
                        error_message = operator_api_data.get("P_EXMES", "Unknown API validation error")
                        self.add_log_message("log.operatorApiValidationFailed", "warning", badge_id=data,
                                             error=error_message)
                        logger.warning(
                            f"Operator API validation failed for badge {data}: {error_message} (P_EXID: {operator_api_data.get('P_EXID')})")
                        self.update_operator_callback({"id": data, "name": None})
                elif response.get("ERROR_STACK"):
                    self.add_log_message("log.operatorApiErrorDetailed", "error", badge_id=data,
                                         error_details=response.get("ERROR_STACK"))
                    logger.error(f"API Error for operator badge {data}: {response.get('ERROR_STACK')}")
                    self.update_operator_callback({"id": data, "name": None})
                else:
                    # Неочакван формат на отговора от API
                    self.add_log_message("log.operatorApiNoData", "warning", badge_id=data)
                    logger.warning(
                        f"No valid data (VALUES or ERROR_STACK) in API response for operator badge {data}: {response}")
                    self.update_operator_callback({"id": data, "name": None})
            else:
                # Грешка при комуникация с API (send_request е върнал None)
                self.add_log_message("log.operatorApiError", "error", badge_id=data)
                logger.error(f"No response or communication error with API for operator badge {data}")
                self.update_operator_callback({"id": data, "name": None})
        else:
            # Операторът е логнат, обработваме други баркодове (напр. пътна карта)
            self.add_log_message("log.processingTravelCard", "debug", barcodeData=data)
            logger.debug(
                f"Operator {current_op['name']} logged in. Processing barcode as potential travel card: {data}")

            # TODO: Интегрирайте с Traceability API за пътни карти
            # response_travel_lot = self.traceability_api.get_travel_lot_info(data, self.workplace_id)
            # if response_travel_lot and ... :
            # ...
            # else:
            #    self.add_log_message("log.travelLotApiError", "warning", barcode=data)

            if data in VALID_TRAVEL_LOTS:  # Временно, докато не се интегрира API за пътни карти
                travel_lot_info = VALID_TRAVEL_LOTS[data]
                try:
                    from backend.app import global_line_status_data
                    global_line_status_data['current_travel_lot'] = travel_lot_info
                    self.socketio.emit('travel_lot_update', {'travel_lot': travel_lot_info})
                    self.add_log_message("log.travelLotIdentified", "info", lot_id=data,
                                         item_number=travel_lot_info['productNumber'])
                    logger.info(f"Travel lot identified (local): {data}")
                except ImportError:
                    self.add_log_message("log.appImportError", "error")
                    logger.error("Could not import global_line_status_data from backend.app in _process_barcode_data")
            else:
                self.add_log_message("log.unknownBarcodeAfterLogin", "warning", barcodeData=data)
                logger.warning(f"Unknown barcode scanned after login: {data}")

    def close_port(self):
        self.add_log_message("log.comPortClosing", "debug", force_default_lang=True, port=self.port_name)
        logger.info(f"Attempting to close COM port {self.port_name}")
        self.is_running = False
        if self.thread and self.thread.is_alive():
            try:
                self.thread.join(timeout=2.0)  # Увеличено време за изчакване
                if self.thread.is_alive():
                    logger.warning(f"COM port reader thread for {self.port_name} did not terminate gracefully.")
            except RuntimeError:
                logger.warning(f"RuntimeError while joining COM port reader thread for {self.port_name}.")
                pass
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
                self.add_log_message("log.comPortClosed", "info", force_default_lang=True, port=self.port_name)
                logger.info(f"Serial port {self.port_name} closed.")
            except Exception as e:
                self.add_log_message("log.comPortCloseError", "error", force_default_lang=True, port=self.port_name,
                                     error=str(e))
                logger.error(f"Error closing serial port {self.port_name}: {e}")
        self.serial_port = None  # Нулираме обекта
        self.add_log_message("log.comManagerStopped", "info", force_default_lang=True, port=self.port_name)
        logger.info(f"COM Port Manager stopped for port {self.port_name}.")

    def send_data(self, data_to_send):
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write(data_to_send.encode('utf-8'))
                self.add_log_message("log.comDataSent", "debug", port=self.port_name, data=data_to_send)
                logger.debug(f"Sent to {self.port_name}: {data_to_send}")
                return True
            except Exception as e:
                self.add_log_message("log.comPortWriteError", "error", port=self.port_name, error=str(e))
                logger.error(f"Error writing to serial port {self.port_name}: {e}")
                return False
        else:
            self.add_log_message("log.comPortNotOpenWrite", "warning", port=self.port_name)
            logger.warning(f"Serial port {self.port_name} is not open. Cannot send data.")
            return False