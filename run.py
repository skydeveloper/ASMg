import os
import sys
import socket # Добавен за получаване на IP адрес
import webbrowser # Добавен за отваряне на браузъра
import threading # Добавен за отваряне на браузъра след стартиране на сървъра
import time # Добавен за забавяне преди отваряне на браузъра

project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print(f"DEBUG: [run.py] project_root is {project_root}")
# print(f"DEBUG: [run.py] sys.path is {sys.path}") # Може да се разкоментира при нужда

print("DEBUG: [run.py] Преди импортиране на backend.app")
try:
    # Импортираме инстанциите, които са създадени на модулно ниво в backend/app.py
    from backend.app import app, socketio, com_port_scanner, data_simulator
    from backend.config import Config
    print("DEBUG: [run.py] Успешно импортиране на backend.app, app и socketio, com_port_scanner, data_simulator, Config")
except ImportError as e:
    print(f"DEBUG: [run.py] Грешка при импорт (ImportError): {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e_gen:
    print(f"DEBUG: [run.py] Неочаквана грешка при импорт (Exception): {e_gen}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

def get_local_ip():
    """Опитва се да намери локалния IP адрес на машината."""
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1) # Намаляваме таймаута
        # Използваме DNS сървър на Google, който е вероятно да е достъпен
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1' # Fallback
    finally:
        if s:
            s.close()
    return ip

def open_browser(url, delay):
    """Отваря URL в браузъра след определено забавяне."""
    def _open():
        time.sleep(delay)
        print(f"DEBUG: [run.py] Опит за отваряне на браузъра с URL: {url}")
        webbrowser.open_new_tab(url)
    threading.Thread(target=_open, daemon=True).start()

if __name__ == '__main__':
    print(f"DEBUG: [run.py] Влизане в if __name__ == '__main__':")
    print(f"Стартиране на {getattr(Config, 'APP_NAME', 'ASMg')} приложението...")

    port = getattr(Config, 'PORT', 5000)
    debug_mode = getattr(Config, 'DEBUG', True)
    host_setting = getattr(Config, 'HOST', '0.0.0.0')

    local_ip = get_local_ip()
    app_url_local = f"http://localhost:{port}"
    app_url_network = f"http://{local_ip}:{port}"

    print("-" * 40)
    print(f" {getattr(Config, 'APP_NAME', 'ASMg')} Application Starting ")
    print("-" * 40)
    print(f"  * Debug mode: {'on' if debug_mode else 'off'}")
    print(f"  * Configured COM Port: {Config.BARCODE_SCANNER_PORT} at {Config.BARCODE_SCANNER_BAUDRATE} baud")
    print(f"  * Running on: http://{host_setting}:{port}")
    print(f"  * Достъпно на (локално): {app_url_local}")
    if host_setting == '0.0.0.0' and local_ip != '127.0.0.1':
        print(f"  * Достъпно в мрежата на: {app_url_network}")
    print("-" * 40)
    print("Натиснете CTRL+C за спиране на сървъра.")

    # Опитваме да отворим COM порта преди стартиране на сървъра
    if com_port_scanner:
        print("DEBUG: [run.py] Опит за отваряне на COM порт...")
        if not com_port_scanner.open_port():
            print(f"ПРЕДУПРЕЖДЕНИЕ: Неуспешно отваряне на COM порт {Config.BARCODE_SCANNER_PORT}. Баркод скенерът няма да работи.")
        else:
            print(f"DEBUG: [run.py] COM порт {Config.BARCODE_SCANNER_PORT} е отворен.")

    # Стартираме симулатора на данни, ако е в debug режим
    if Config.DEBUG and data_simulator:
        print("DEBUG: [run.py] Стартиране на DataSimulatorThread...")
        data_simulator.start()

    if debug_mode and not os.environ.get("WERKZEUG_RUN_MAIN"):
        open_browser(app_url_local, 2)

    try:
        socketio.run(app,
                     host=host_setting,
                     port=port,
                     debug=debug_mode,
                     use_reloader=False, # Оставяме го False, за да избегнем проблема с рестартирането
                     allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        print("DEBUG: [run.py] Сървърът е спрян ръчно (CTRL+C).")
    except Exception as e:
        print(f"DEBUG: [run.py] Грешка при стартиране или работа на socketio: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("DEBUG: [run.py] Изпълнява се finally блокът в run.py.")
        if com_port_scanner and com_port_scanner.is_running:
            print("DEBUG: [run.py] Затваряне на COM порт...")
            com_port_scanner.close_port()
        if data_simulator and data_simulator.is_alive():
            print("DEBUG: [run.py] Спиране на симулатора на данни...")
            data_simulator.stop()
            data_simulator.join(timeout=2) # Даваме малко повече време за приключване
        print("DEBUG: [run.py] Програмата приключи.")

    print("DEBUG: [run.py] socketio.run() завърши.")