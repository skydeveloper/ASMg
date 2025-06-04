# Файл: backend/services/device_communicator.py
import requests
import json
import logging

# Вземаме логера, който вече е конфигуриран в app.py
logger = logging.getLogger("ASMg_App")  # Уверете се, че името съвпада с това в app.py


class DeviceCommunicator:
    def __init__(self):
        # Може да добавите базови URL адреси или други настройки тук, ако е нужно
        logger.info("DeviceCommunicator initialized.")

    def _send_request(self, method, url, payload=None, headers=None):
        try:
            logger.debug(
                f"Sending {method} request to {url} with payload: {json.dumps(payload) if payload else 'None'}")

            if headers is None:
                headers = {'Content-Type': 'application/json'}

            if method.upper() == 'POST':
                response = requests.post(url, json=payload, headers=headers, timeout=15)
            elif method.upper() == 'GET':
                response = requests.get(url, params=payload, headers=headers, timeout=15)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None

            response.raise_for_status()  # Хвърля грешка за 4xx/5xx HTTP статуси

            logger.debug(
                f"Received response from {url}: {response.status_code} - {response.text[:200]}")  # Първите 200 символа
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            logger.error(
                f"HTTP error occurred: {http_err} - URL: {url} - Response: {http_err.response.text if http_err.response else 'N/A'}")
        except requests.exceptions.ConnectionError as conn_err:
            logger.error(f"Connection error occurred: {conn_err} - URL: {url}")
        except requests.exceptions.Timeout as timeout_err:
            logger.error(f"Timeout error occurred: {timeout_err} - URL: {url}")
        except requests.exceptions.RequestException as req_err:
            logger.error(f"An error occurred: {req_err} - URL: {url}")
        except json.JSONDecodeError as json_err:
            logger.error(
                f"JSON decode error for response from {url}: {json_err} - Response was: {response.text if 'response' in locals() else 'N/A'}")
        return None

    def start_test_on_device(self, device_ip, device_port, module_id, test_sequence_name):
        """
        Изпраща команда за стартиране на тест към конкретно устройство.
        """
        url = f"http://{device_ip}:{device_port}/api/start_test"  # Примерно URL
        payload = {
            "module_id": module_id,
            "test_sequence_name": test_sequence_name
        }
        return self._send_request('POST', url, payload)

    def start_programming_on_device(self, device_ip, device_port, module_id, firmware_details):
        """
        Изпраща команда за стартиране на програмиране към конкретно устройство.
        """
        url = f"http://{device_ip}:{device_port}/api/start_programming"  # Примерно URL
        payload = {
            "module_id": module_id,
            "firmware": firmware_details
            # firmware_details може да е обект с име на файл, версия и т.н.
        }
        return self._send_request('POST', url, payload)

    def get_device_status(self, device_ip, device_port):
        """
        Изпраща заявка за получаване на статуса на устройство.
        """
        url = f"http://{device_ip}:{device_port}/api/status"  # Примерно URL
        return self._send_request('GET', url)