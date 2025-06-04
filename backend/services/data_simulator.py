# Файл: backend/services/data_simulator.py
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
        self._module_counter = 1
        self._turntable1_pos_tracker = 0
        self._turntable2_pos_tracker = 0

    def run(self):
        time.sleep(1)  # Изчакваме Flask да се инициализира напълно
        self.add_log_message("log.simulatorStarted", "info")
        logger.info("Data simulator thread actually started.")

        while self.running:
            self.socketio.sleep(5)
            if not self.running:
                break
            try:
                if "overall_status" in self.line_status_data:
                    self.line_status_data["overall_status"] = random.choice(
                        ["status.running", "status.warning", "status.maintenance", "status.idle"])

                if "robots" in self.line_status_data:
                    robot_statuses = ["status.working", "status.idle", "status.error"]
                    for i_str in self.line_status_data["robots"].keys():
                        if str(i_str) in self.line_status_data["robots"]:
                            self.line_status_data["robots"][str(i_str)]["status"] = random.choice(robot_statuses)

                if "turntable1" in self.line_status_data:
                    self._turntable1_pos_tracker = (self._turntable1_pos_tracker % 4) + 1
                    for i in range(1, 5):
                        pos_str = str(i)
                        if pos_str in self.line_status_data["turntable1"]:
                            self.line_status_data["turntable1"][pos_str]["status"] = random.choice(
                                ["status.idle", "status.working", "status.ok"])
                            if i == self._turntable1_pos_tracker:
                                self.line_status_data["turntable1"][pos_str][
                                    "moduleId"] = f"MOD-A{self._module_counter:03d}"
                                if i == 4: self._module_counter += 1
                            else:
                                self.line_status_data["turntable1"][pos_str]["moduleId"] = "--"

                if "turntable2" in self.line_status_data:
                    self._turntable2_pos_tracker = (self._turntable2_pos_tracker % 4) + 1
                    for i in range(1, 5):
                        pos_str = str(i)
                        if pos_str in self.line_status_data["turntable2"]:
                            self.line_status_data["turntable2"][pos_str]["status"] = random.choice(
                                ["status.idle", "status.working", "status.ok"])
                            if i == self._turntable2_pos_tracker:
                                self.line_status_data["turntable2"][pos_str]["moduleIds"] = [
                                    f"MOD-B{self._module_counter + j:03d}" for j in
                                    range(random.randint(0, 2))]  # По-малко модули
                                if i == 4: self._module_counter += 2  # Адаптираме брояча
                            else:
                                self.line_status_data["turntable2"][pos_str]["moduleIds"] = []

                if "trays" in self.line_status_data:
                    tray_statuses = ["status.okFull", "status.almostFull", "status.empty"]
                    if "in" in self.line_status_data["trays"]:
                        self.line_status_data["trays"]["in"]["status"] = random.choice(tray_statuses)
                    if "out" in self.line_status_data["trays"]:
                        self.line_status_data["trays"]["out"]["status"] = random.choice(tray_statuses)

                self.socketio.emit('update_status', self.line_status_data)
            except KeyError as ke:
                logger.error(
                    f"KeyError in data simulator loop: Key '{ke}' not found in line_status_data. Current keys: {list(self.line_status_data.keys())}",
                    exc_info=False)
            except Exception as e:
                logger.error(f"Error in data simulator loop: {e}", exc_info=True)

        logger.info("Data simulator thread loop finished.")

    def stop(self):
        self.running = False
        logger.info("Data simulator thread stopping command received.")