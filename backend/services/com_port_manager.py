# Файл: backend/services/com_port_manager.py
import serial
import time
import logging

logger = logging.getLogger("ASMg_App")  # Уверете се, че името съвпада с това в app.py


class ComPortManager:
    def __init__(self, port, baudrate, socketio):
        self.port_name = port
        self.baudrate = baudrate
        self.serial_port = None
        self.is_running = False  # Показва дали портът е отворен и готов
        self.socketio = socketio
        logger.info(f"ComPortManager initialized for port {self.port_name} at {self.baudrate} baud.")

    def open_port(self):
        try:
            logger.debug(f"Attempting to open serial port: {self.port_name}")
            self.serial_port = serial.Serial(self.port_name, self.baudrate, timeout=1)
            self.is_running = True  # Маркираме, че портът е отворен
            logger.info(f"Successfully opened serial port {self.port_name}")
            self.socketio.emit('log_message',
                               {'message': f"COM порт {self.port_name} е успешно отворен.", 'level': 'success'})
            return True
        except serial.SerialException as e:
            logger.error(f"SerialException opening port {self.port_name}: {e}")
            self.socketio.emit('log_message',
                               {'message': f"Грешка при отваряне на COM порт {self.port_name}: {e}", 'level': 'error'})
            return False
        except Exception as e:
            logger.error(f"Generic error opening port {self.port_name}: {e}")
            self.socketio.emit('log_message',
                               {'message': f"Неочаквана грешка при отваряне на COM порт {self.port_name}: {e}",
                                'level': 'error'})
            return False

    def start_reading_task(self):
        if self.is_running and self.serial_port and self.serial_port.is_open:
            logger.info("Starting the background task for reading from COM port.")
            self.socketio.start_background_task(target=self._read_from_port)
        else:
            logger.warning("Attempted to start reading task, but port is not open or ComPortManager not running.")

    def _read_from_port(self):
        logger.info(f"Background task started: Now reading from {self.port_name}...")
        buffer = ""
        while self.is_running:
            try:
                if self.serial_port and self.serial_port.is_open:
                    if self.serial_port.in_waiting > 0:
                        data_chunk = self.serial_port.read(self.serial_port.in_waiting).decode('utf-8', errors='ignore')
                        buffer += data_chunk
                        while '\n' in buffer or '\r' in buffer:
                            end_pos = -1
                            if '\n' in buffer: end_pos = buffer.find('\n')
                            if '\r' in buffer:
                                r_pos = buffer.find('\r')
                                if end_pos == -1 or r_pos < end_pos: end_pos = r_pos

                            line_to_process = buffer[:end_pos].strip()
                            buffer = buffer[end_pos + 1:]
                            if line_to_process:
                                self._process_barcode_data(line_to_process)
                else:  # Ако портът е затворен междувременно
                    self.is_running = False  # Спираме цикъла
                    logger.warning(f"Serial port {self.port_name} closed or not available while reading.")
                    break
                self.socketio.sleep(0.05)  # Важно за Socket.IO фонови задачи
            except Exception as e:
                logger.error(f"Unexpected error in _read_from_port: {e}", exc_info=True)
                self.is_running = False  # Спираме при сериозна грешка
                break
        logger.info(f"Background task for reading from {self.port_name} has stopped.")

    def _process_barcode_data(self, data):
        logger.info(f"Barcode scanned: '{data}'. Emitting 'barcode_scanned' to frontend.")
        self.socketio.emit('barcode_scanned', {'barcode': data})

    def close_port(self):
        self.is_running = False  # Сигнализираме на нишката да спре
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
                logger.info(f"Serial port {self.port_name} closed.")
            except Exception as e:
                logger.error(f"Error closing serial port {self.port_name}: {e}")
        self.serial_port = None