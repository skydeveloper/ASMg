import requests
import json
import urllib3
import logging  # Добавяме logging

# Потискане на предупрежденията за InsecureRequestWarning при verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class TraceabilityAPI:
    def __init__(self, base_url, api_key, logger_func=None):  # Добавяме logger_func
        self.base_url = base_url
        self.headers = {
            "IMI-API-KEY": api_key,
            "Content-Type": "application/json"
        }
        self.logger = logger_func if logger_func else logging.getLogger(__name__)
        self.logger.info(f"TraceabilityAPI initialized with URL: {self.base_url}")

    def _log(self, level, message):
        """Помощна функция за логване."""
        if level == "info":
            self.logger.info(message)
        elif level == "error":
            self.logger.error(message)
        elif level == "warning":
            self.logger.warning(message)
        elif level == "debug":
            self.logger.debug(message)
        else:
            self.logger.info(message)
    '''
    def send_request(self, procedure, params):
        """Изпраща заявка към Traceability API."""
        payload = {
            "OWNER": "TRANS",
            "PACKAGE": "AUTOMATION_FTPCK",  # или "SENSITECH", ако е глобално за всички процедури
            "PROCEDURE": procedure,
            "PARAMS": params
        }
        self._log('debug',
                  f"Traceability API Request: URL={self.base_url}/executeProcedure, Payload={json.dumps(payload)}")

        try:
            response = requests.post(f"{self.base_url}/executeProcedure",
                                     headers=self.headers,
                                     data=json.dumps(payload),
                                     verify=False,
                                     timeout=10)
            self._log('debug',
                      f"Traceability API Response: Status={response.status_code}, Body={response.text[:500]}")  # Логваме първите 500 символа от отговора
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            self._log('error',
                      f"Traceability API - HTTP error for {procedure}: {http_err} - Response: {response.text if 'response' in locals() else 'N/A'}")
        except requests.exceptions.ConnectionError as conn_err:
            self._log('error', f"Traceability API - Connection error for {procedure}: {conn_err}")
        except requests.exceptions.Timeout as timeout_err:
            self._log('error', f"Traceability API - Timeout error for {procedure}: {timeout_err}")
        except requests.exceptions.RequestException as req_err:
            self._log('error', f"Traceability API - General request error for {procedure}: {req_err}")
        except json.JSONDecodeError as json_err:
            self._log('error',
                      f"Traceability API - Error decoding JSON response for {procedure}: {json_err} - Response was: {response.text if 'response' in locals() else 'N/A'}")
        return None
    '''
    def send_request(self, procedure, params, package=""):
        """Изпраща заявка към Traceability API."""
        payload = {
            "OWNER": "TRANS",
            "PACKAGE": package,  # Вече е параметър с default стойност ""
            "PROCEDURE": procedure,
            "PARAMS": params
        }
        self._log('debug',
                  f"Traceability API Request: URL={self.base_url}/executeProcedure, Payload={json.dumps(payload)}")

        try:
            response = requests.post(f"{self.base_url}/executeProcedure",
                                     headers=self.headers,
                                     data=json.dumps(payload),
                                     verify=False,
                                     timeout=10)
            self._log('debug',
                      f"Traceability API Response: Status={response.status_code}, Body={response.text[:500]}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            self._log('error',
                      f"Traceability API - HTTP error for {procedure}: {http_err} - Response: {response.text if 'response' in locals() else 'N/A'}")
        except requests.exceptions.ConnectionError as conn_err:
            self._log('error', f"Traceability API - Connection error for {procedure}: {conn_err}")
        except requests.exceptions.Timeout as timeout_err:
            self._log('error', f"Traceability API - Timeout error for {procedure}: {timeout_err}")
        except requests.exceptions.RequestException as req_err:
            self._log('error', f"Traceability API - General request error for {procedure}: {req_err}")
        except json.JSONDecodeError as json_err:
            self._log('error',
                      f"Traceability API - Error decoding JSON response for {procedure}: {json_err} - Response was: {response.text if 'response' in locals() else 'N/A'}")
        return None

    # STEP1: Validate Operator Badge
    def validate_operator_badge(self, reader_id):
        self._log('info', f"Validating operator badge: {reader_id}")
        params = {"P_READER": reader_id}
        return self.send_request("GET_VALID_EMNOEXT", params)

    '''
    # STEP2: Register operation and operator
    def ftpck_new_order(self, workplace_id, route_map, employee_id):
        self._log('info',
                  f"Registering new order: Workplace={workplace_id}, RouteMap={route_map}, Employee={employee_id}")
        params = {
            "P_RDNO": workplace_id,
            "P_ROUTE_MAP": route_map,
            "P_EMNO": employee_id
        }
        return self.send_request("FTPCK_NEW_ORDER", params)
    '''
    # STEP2: Register operation and operator
    def ftpck_new_order(self, workplace_id, route_map, employee_id):
        self._log('info',
                  f"Registering new order: Workplace={workplace_id}, RouteMap={route_map}, Employee={employee_id}")
        params = {
            "P_RDNO": workplace_id,
            "P_ROUTE_MAP": route_map,
            "P_EMNO": employee_id
        }
        # Променете извикването на send_request, за да подадете PACKAGE
        return self.send_request("FTPCK_NEW_ORDER", params, package="AUTOMATION_FTPCK")

    # STEP3: Register  Package
    def pck_new_pack(self, workplace_id, pack_barcode):
        self._log('info', f"Registering new pack: Workplace={workplace_id}, PackBarcode={pack_barcode}")
        params = {
            "P_RDNO": workplace_id,
            "P_PCKB": pack_barcode
        }
        return self.send_request("PCK_NEW_PACK", params)

    # STEP4: Extracting Module ID from Barcode
    def get_mdno_from_string_ext(self, module_barcode, product_id):
        self._log('info', f"Extracting module ID: Barcode={module_barcode}, ProductID={product_id}")
        params = {
            "P_MDSTR": module_barcode,
            "P_MITM": product_id
        }
        return self.send_request("GETMDNOFROMSTRINGEXT", params)

    # STEP5: Validate Module
    def ftpck_module_in(self, workplace_id, module_id):
        self._log('info', f"Validating module IN: Workplace={workplace_id}, ModuleID={module_id}")
        params = {
            "P_RDNO": workplace_id,
            "P_MDNO": module_id,
            "P_RTFL": "0"
        }
        return self.send_request("FTPCK_MODULE_IN", params)

    # STEP6: Save Test Result
    def ftpck_module_out(self, workplace_id, employee_id, module_id, test_status="1", test_data="TEST DATA",
                         fail_info=""):
        self._log('info',
                  f"Saving module OUT (test result): Workplace={workplace_id}, Employee={employee_id}, ModuleID={module_id}, Status={test_status}")
        params = {
            "P_RDNO": workplace_id,
            "P_EMNO": employee_id,
            "P_MDNO": module_id,
            "P_RTFL": "0",
            "P_TSFL": str(test_status),
            "P_DATA": test_data,
            "P_ERRI": fail_info if str(test_status) == "0" else ""
        }
        return self.send_request("FTPCK_MODULE_OUT", params)

    # STEP7: Generate CAB Label
    def get_cab_label(self, workplace_id, module_id, product_id):
        self._log('info', f"Getting CAB label: Workplace={workplace_id}, ModuleID={module_id}, ProductID={product_id}")
        params = {
            "P_RDNO": workplace_id,
            "P_MDNO": module_id,
            "P_MITM": product_id
        }
        return self.send_request("GET_CAB_LABEL", params)

    # STEP8: Register Module to Package
    def pck_module_in(self, workplace_id, package_id, item_id, module_id, label_content, employee_id):
        self._log('info',
                  f"Registering module to package: Workplace={workplace_id}, PackageID={package_id}, ModuleID={module_id}")
        params = {
            "P_RDNO": workplace_id,
            "P_PCID": package_id,
            "P_ITEM": item_id,
            "P_MDNO": module_id,
            "P_CVAL": label_content,
            "P_EMNO": employee_id
        }
        return self.send_request("PCK_MODULE_IN", params)


if __name__ == "__main__":
    # Конфигурация на логера за самостоятелно тестване
    test_logger = logging.getLogger("TraceabilityAPITest")
    test_logger.setLevel(logging.DEBUG)
    test_handler = logging.StreamHandler()
    test_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    test_handler.setFormatter(test_formatter)
    test_logger.addHandler(test_handler)
    test_logger.info("--- Самостоятелно тестване на TraceabilityAPI ---")

    BASE_URL_TEST = "http://oracleapi:3000"
    API_KEY_TEST = "2512A449C4B001DBE0639F2B230AF06F"

    api_client = TraceabilityAPI(BASE_URL_TEST, API_KEY_TEST, logger_func=test_logger)

    test_logger.info("🔄 Стартиране на тестове за Traceability API...\n")
    WORKPLACE_ID = "2400"

    test_logger.info("--- Тест за валидация на оператор ---")
    test_badge = "2HC7912"
    response = api_client.validate_operator_badge(test_badge)
    if response and response.get("OUT_DATA") and isinstance(response["OUT_DATA"], list) and len(
            response["OUT_DATA"]) > 0:
        operator_data = response["OUT_DATA"][0]
        if operator_data.get("P_EXID") == "0":
            test_logger.info(
                f"✅ Валиден оператор: {test_badge} -> Име: {operator_data.get('P_NAME')}, ID: {operator_data.get('P_EMNO')}")
        elif operator_data.get("P_EXID") == "1":
            test_logger.warning(f"❌ Невалиден оператор (P_EXID=1): {test_badge} - {operator_data.get('P_ERR_MSG')}")
        else:
            test_logger.warning(f"❓ Неизвестен отговор за оператор: {test_badge} -> {operator_data}")
    elif response and response.get("ERROR_STACK"):
        test_logger.error(f"❌ Грешка от API при валидация на оператор {test_badge}: {response.get('ERROR_STACK')}")
    else:
        test_logger.error(f"❌ Няма отговор или неочакван формат за оператор: {test_badge}")
    test_logger.info("-" * 20)

    # Можете да добавите още тестове тук по същия начин
    # ... (останалите тестове от вашия файл, ако желаете) ...

    test_logger.info("✅ Всички тестове завършени!")



