# Файл: backend/config.py
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_very_secret_key_123!' # Променете това!
    DEBUG = True  # Set to False in production
    PORT = 5000
    HOST = '0.0.0.0' # Позволява достъп от други машини в мрежата
    APP_NAME = "ASMg"

    # Barcode Scanner Configuration
    BARCODE_SCANNER_PORT = 'COM6' # Уверете се, че това е правилният порт
    BARCODE_SCANNER_BAUDRATE = 9600

    # OPC UA Server Configuration (примерни стойности)
    OPCUA_SERVER_URL = "opc.tcp://localhost:4840/freeopcua/server/"
    OPCUA_NAMESPACE = "http://example.com/RaspberryPi" 

    # Supported Languages: code: "Display Name"
    SUPPORTED_LANGUAGES = {
        'en': 'English',
        'bg': 'Български',
        'sr': 'Srpski'
    }
    DEFAULT_LANGUAGE = 'bg' # Език по подразбиране

    # Конфигурация за Traceability API
    TRACEABILITY_API_URL = os.environ.get('TRACEABILITY_API_URL', "http://oracleapi:3000")
    TRACEABILITY_API_KEY = os.environ.get('TRACEABILITY_API_KEY', "2512A449C4B001DBE0639F2B230AF06F")
    TRACEABILITY_WORKPLACE_ID = os.environ.get('TRACEABILITY_WORKPLACE_ID', "2400") # Използвахме "2400" в тестовете