import threading
import time
import random
import logging

logger = logging.getLogger("ASMg_App")


class DataSimulatorThread(threading.Thread):
    def __init__(self, socketio, line_status_data, add_log_message_func):
        super().__init__(daemon=True)
        self.socketio = socketio
        self.line_status_data = line_status_data
        self.add_log_message = add_log_message_func
        self.running = True

    def run(self):
        logger.info("--- SIMULATOR V2 --- НОВАТА ВЕРСИЯ НА СИМУЛАТОРА Е СТАРТИРАНА ---")
        self.add_log_message("log.simulatorStarted", "info")

        cycle_count = 0
        while self.running:
            self.socketio.sleep(5)
            cycle_count += 1
            logger.debug(f"Simulator loop, cycle: {cycle_count}")

            try:
                # В тази версия не правим нищо друго, освен да логваме.
                # Това е за тест, за да видим дали този код изобщо се изпълнява.
                pass

            except Exception as e:
                logger.error(f"Error in data simulator loop: {e}", exc_info=True)

        logger.info("Data simulator thread loop finished.")

    def stop(self):
        self.running = False
        logger.info("Data simulator thread stopping command received.")