# Файл: backend/services/com_port_manager.py
import serial
import time
import logging

# Премахваме 'import threading', вече не ни е нужен

logger = logging.getLogger("ASMg_App")

class ComPortManager:
    def __init__(self, port, baudrate, socketio):
        self.port_name = port
        self.baudrate = baudrate
        self.serial_port = None
        self.is_running = False
        self.socketio = socketio
        # Премахваме self.thread
        logger.info(f"ComPortManager initialized for port {self.port_name} at {self.baudrate} baud.")

    def open_port(self):
        """
        Вече само отваря порта физически, без да стартира нишка.
        """
        try:
            logger.debug(f"Attempting to open serial port: {self.port_name}")
            self.serial_port = serial.Serial(self.port_name, self.baudrate, timeout=1)
            self.is_running = True # Показваме, че сме готови за четене
            logger.info(f"Successfully opened serial port {self.port_name}")
            self.socketio.emit('log_message', {'message': f'COM порт {self.port_name} е успешно отворен.', 'level': 'success'})
            return True
        except Exception as e:
            logger.error(f"Error opening port {self.port_name}: {e}")
            self.socketio.emit('log_message', {'message': f'Грешка при отваряне на COM порт {self.port_name}: {e}', 'level': 'error'})
            return False

    def start_reading_task(self):
        """
        Нова функция, която стартира четенето като фонова задача на Socket.IO.
        """
        if self.is_running:
            logger.info("Starting the background task for reading from COM port.")
            self.socketio.start_background_task(target=self._read_from_port)
        else:
            logger.warning("Attempted to start reading task, but port is not running.")

    def _read_from_port(self):
        """
        Тази функция остава същата, но вече ще се изпълнява като задача на Socket.IO.
        """
        logger.info(f"Background task started: Now reading from {self.port_name}...")
        buffer = ""
        while self.is_running:
            if not self.serial_port or not self.serial_port.is_open:
                logger.warning(f"Serial port {self.port_name} is not open. Stopping reader task.")
                self.is_running = False
                break
            try:
                if self.serial_port.in_waiting > 0:
                    data_chunk = self.serial_port.read(self.serial_port.in_waiting).decode('utf-8', errors='ignore')
                    buffer += data_chunk
                    while '\n' in buffer or '\r' in buffer:
                        end_pos = buffer.find('\n') if '\n' in buffer else buffer.find('\r')
                        line_to_process = buffer[:end_pos].strip()
                        buffer = buffer[end_pos+1:]
                        if line_to_process:
                            self._process_barcode_data(line_to_process)
                # self.socketio.sleep() е много важно за фоновите задачи на Socket.IO
                self.socketio.sleep(0.05)
            except Exception as e:
                logger.error(f"Unexpected error in _read_from_port: {e}", exc_info=True)
                self.socketio.sleep(1)

    def _process_barcode_data(self, data):
        """Тази функция остава същата."""
        logger.info(f"Barcode scanned: '{data}'. Emitting 'barcode_scanned' to frontend.")
        self.socketio.emit('barcode_scanned', {'barcode': data})

    def close_port(self):
        """Тази функция остава същата."""
        self.is_running = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            logger.info(f"Serial port {self.port_name} closed.")
        self.serial_port = None