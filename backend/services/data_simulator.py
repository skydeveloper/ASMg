import threading
import time
import random
import logging  # Добавяме logging

logger = logging.getLogger(__name__)  # Използваме логера от app.py


class DataSimulatorThread(threading.Thread):
    def __init__(self, socketio, line_status_data, add_log_message_func):  # Премахнат translations
        super().__init__(daemon=True)
        self.socketio = socketio
        self.line_status_data = line_status_data
        self.add_log_message = add_log_message_func
        self.running = True
        self._module_counter = 1
        self._turntable1_pos = 0
        self._turntable2_pos = 0
        self.add_log_message("log.simulatorInitialized", "debug")

    def run(self):
        self.add_log_message("log.simulatorStarted", "info")
        logger.info("Data simulator thread actually started.")  # Директно логване

        while self.running:
            time.sleep(5)
            if not self.running:
                break

            try:
                # Симулация на общ статус на линията
                overall_statuses = ["status.running", "status.running", "status.running", "status.warning",
                                    "status.maintenance"]
                self.line_status_data["overall_status"] = random.choice(overall_statuses)

                # Симулация на статус на роботи
                robot_statuses = ["status.working", "status.idle", "status.error"]
                for i in range(1, 4):
                    self.line_status_data["robots"][str(i)]["status"] = random.choice(robot_statuses)

                # Симулация на въртележка 1 (единични модули)
                self._turntable1_pos = (self._turntable1_pos % 4) + 1
                for i in range(1, 5):
                    pos_str = str(i)
                    if i == self._turntable1_pos:
                        self.line_status_data["turntable1"][pos_str]["status"] = "status.working"
                        self.line_status_data["turntable1"][pos_str]["moduleId"] = f"MOD-A{self._module_counter:03d}"
                        self.line_status_data["turntable1"][pos_str]["time"] = random.randint(1, 5)
                        if i == 4: self._module_counter += 1
                    elif i == (self._turntable1_pos - 1) or (self._turntable1_pos == 1 and i == 4):
                        self.line_status_data["turntable1"][pos_str]["status"] = "status.ok"
                        self.line_status_data["turntable1"][pos_str]["time"] = 5
                    else:
                        self.line_status_data["turntable1"][pos_str]["status"] = "status.idle"
                        self.line_status_data["turntable1"][pos_str]["moduleId"] = "--"
                        self.line_status_data["turntable1"][pos_str]["time"] = 0

                # Симулация на въртележка 2 (групи от модули)
                self._turntable2_pos = (self._turntable2_pos % 4) + 1
                for i in range(1, 5):
                    pos_str = str(i)
                    if i == self._turntable2_pos:
                        self.line_status_data["turntable2"][pos_str]["status"] = "status.working"
                        self.line_status_data["turntable2"][pos_str]["moduleIds"] = [
                            f"MOD-B{self._module_counter + j:03d}" for j in range(4)
                        ]
                        self.line_status_data["turntable2"][pos_str]["time"] = random.randint(10, 20)
                        self.line_status_data["turntable2"][pos_str]["progress"] = random.randint(10, 90)
                        if i == 4: self._module_counter += 4
                    elif i == (self._turntable2_pos - 1) or (self._turntable2_pos == 1 and i == 4):
                        self.line_status_data["turntable2"][pos_str]["status"] = "status.ok"
                        self.line_status_data["turntable2"][pos_str]["time"] = 20
                        self.line_status_data["turntable2"][pos_str]["progress"] = 100
                    else:
                        self.line_status_data["turntable2"][pos_str]["status"] = "status.idle"
                        self.line_status_data["turntable2"][pos_str]["moduleIds"] = []
                        self.line_status_data["turntable2"][pos_str]["time"] = 0
                        self.line_status_data["turntable2"][pos_str]["progress"] = 0

                # Симулация на статус на тави
                tray_statuses = ["status.okFull", "status.almostFull", "status.empty", "status.waitingForLoad",
                                 "status.waitingForUnload"]
                self.line_status_data["trays"]["in"]["status"] = random.choice(tray_statuses)
                self.line_status_data["trays"]["out"]["status"] = random.choice(tray_statuses)

                self.socketio.emit('update_status', self.line_status_data)
                # logger.debug(f"Simulated data update: {self.line_status_data}")
            except Exception as e:
                logger.error(f"Error in data simulator loop: {e}", exc_info=True)
                # Може да добавите self.add_log_message тук, но внимавайте да не предизвикате рекурсия или претоварване на логовете
        logger.info("Data simulator thread loop finished.")

    def stop(self):
        self.running = False
        self.add_log_message("log.simulatorStopping", "info")
        logger.info("Data simulator thread stopping command received.")