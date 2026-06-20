import csv
import json
import math
import os
import random
from datetime import datetime


TELEMETRY_FILE = "telemetry_state.json"


class Bottle:
    def __init__(self, bottle_id):
        self.id = bottle_id
        self.stage = "Created"
        self.defective = False
        self.defect_reason = None
        self.rework_reason = None


class ProductionLine:
    def __init__(self):
        self.created = 0
        self.filled = 0
        self.capped = 0
        self.labeled = 0
        self.packaged = 0
        self.shipped = 0
        self.rejected = 0
        self.reworked = 0

        self.current_bottle = None
        self.current_stage = "Idle"
        self.machine_state = "STOPPED"

        self.rejection_log = []
        self.rework_log = []
        self.production_history = []

        self.bottle_counter = 0
        self.start_time = None
        self.stop_time = None

    def start(self):
        self.machine_state = "RUNNING"
        if self.start_time is None:
            self.start_time = datetime.now()

    def stop(self):
        self.machine_state = "STOPPED"
        self.stop_time = datetime.now()

    def reset(self):
        self.__init__()
        self._write_telemetry_snapshot(self.get_stats(write_snapshot=False))

    def create_bottle(self):
        self.bottle_counter += 1
        bottle = Bottle(self.bottle_counter)
        self.created += 1
        self.current_bottle = bottle.id
        return bottle

    def check_defect(self, stage):
        defects = {
            "Bottle QC": ["Cracked Bottle", "Deformed Bottle"],
            "Fill QC": ["Underfilled Bottle", "Overfilled Bottle"],
            "Cap QC": ["Missing Cap", "Loose Cap"],
            "Label QC": ["Missing Label", "Crooked Label"],
            "Final QC": ["Contamination", "Overall Product Failure"]
        }

        if stage in defects and random.random() < 0.10:
            return random.choice(defects[stage])

        return None

    def rework_station(self, bottle, stage, reason):
        rework_actions = {
            "Bottle QC": "New bottle shell created",
            "Fill QC": "Bottle refilled",
            "Cap QC": "New cap installed",
            "Label QC": "New label applied"
        }

        action = rework_actions.get(stage, "Reworked")

        self.reworked += 1
        bottle.rework_reason = reason

        self.rework_log.append({
            "bottle_id": bottle.id,
            "stage": stage,
            "reason": reason,
            "action": action,
            "time": datetime.now().strftime("%H:%M:%S")
        })

        self.production_history.append({
            "bottle_id": bottle.id,
            "result": "REWORKED",
            "stage": stage,
            "reason": reason,
            "time": datetime.now().strftime("%H:%M:%S")
        })

        return action

    def process_stage(self, bottle, stage):
        self.current_stage = stage
        bottle.stage = stage
        bottle.defect_reason = None
        bottle.rework_reason = None

        if "QC" in stage:
            defect = self.check_defect(stage)

            if defect:
                bottle.defect_reason = defect

                if stage == "Final QC":
                    bottle.defective = True
                    self.rejected += 1

                    self.rejection_log.append({
                        "bottle_id": bottle.id,
                        "stage": stage,
                        "reason": defect,
                        "time": datetime.now().strftime("%H:%M:%S")
                    })

                    self.production_history.append({
                        "bottle_id": bottle.id,
                        "result": "REJECTED",
                        "stage": stage,
                        "reason": defect,
                        "time": datetime.now().strftime("%H:%M:%S")
                    })

                    return "REJECT"

                self.rework_station(bottle, stage, defect)
                return "REWORK"

        if stage == "Water Filling":
            self.filled += 1
        elif stage == "Cap Installation":
            self.capped += 1
        elif stage == "Label Application":
            self.labeled += 1
        elif stage == "Packaging":
            self.packaged += 1
        elif stage == "Shipped":
            self.shipped += 1

            self.production_history.append({
                "bottle_id": bottle.id,
                "result": "SHIPPED",
                "stage": "Shipped",
                "reason": "Success",
                "time": datetime.now().strftime("%H:%M:%S")
            })

        return "PASS"

    def get_runtime_seconds(self):
        if self.start_time is None:
            return 0

        if self.machine_state == "RUNNING":
            return int((datetime.now() - self.start_time).total_seconds())

        if self.stop_time:
            return int((self.stop_time - self.start_time).total_seconds())

        return 0

    def get_efficiency(self):
        if self.created == 0:
            return 0
        return round((self.shipped / self.created) * 100, 1)

    def get_rework_rate(self):
        if self.created == 0:
            return 0
        return round((self.reworked / self.created) * 100, 1)

    def get_reject_rate(self):
        if self.created == 0:
            return 0
        return round((self.rejected / self.created) * 100, 1)

    def get_throughput(self):
        runtime_seconds = self.get_runtime_seconds()

        if runtime_seconds <= 0:
            return 0

        runtime_minutes = runtime_seconds / 60
        return round(self.shipped / runtime_minutes, 1)

    def get_e10_state(self):
        if self.machine_state == "STOPPED":
            return "Standby"

        if self.machine_state == "RUNNING" and self.current_stage != "Idle":
            return "Productive"

        return "Standby"

    def get_sensor_values(self):
        runtime = self.get_runtime_seconds()

        if self.machine_state == "RUNNING":
            water_temperature = 22.5 + 2.5 * math.sin(runtime / 12) + random.uniform(-0.3, 0.3)
            conveyor_speed = 1.20 + random.uniform(-0.05, 0.05)
            motor_current = 4.8 + (self.reworked * 0.015) + random.uniform(-0.25, 0.25)
            tank_level = max(15.0, 100.0 - (self.filled % 85) + random.uniform(-1.5, 1.5))
        else:
            water_temperature = 21.5 + random.uniform(-0.2, 0.2)
            conveyor_speed = 0.0
            motor_current = 0.0
            tank_level = 100.0

        return {
            "water_temperature": round(water_temperature, 2),
            "conveyor_speed": round(conveyor_speed, 2),
            "motor_current": round(motor_current, 2),
            "tank_level": round(tank_level, 1)
        }

    def export_csv(self, filename="production_report_v7.csv"):
        with open(filename, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Time", "Bottle ID", "Result", "Stage", "Reason"])

            for item in self.production_history:
                writer.writerow([
                    item["time"],
                    item["bottle_id"],
                    item["result"],
                    item["stage"],
                    item["reason"]
                ])

        return filename

    def _write_telemetry_snapshot(self, stats):
        temp_file = TELEMETRY_FILE + ".tmp"
        try:
            with open(temp_file, "w", encoding="utf-8") as file:
                json.dump(stats, file, indent=2)
            os.replace(temp_file, TELEMETRY_FILE)
        except OSError:
            pass

    def get_stats(self, write_snapshot=True):
        sensors = self.get_sensor_values()
        now = datetime.now()

        stats = {
            "timestamp": now.isoformat(timespec="seconds"),
            "timestamp_epoch": now.timestamp(),
            "machine_state": self.machine_state,
            "e10_state": self.get_e10_state(),

            "created": self.created,
            "filled": self.filled,
            "capped": self.capped,
            "labeled": self.labeled,
            "packaged": self.packaged,
            "shipped": self.shipped,
            "rejected": self.rejected,
            "reworked": self.reworked,

            "efficiency": self.get_efficiency(),
            "rework_rate": self.get_rework_rate(),
            "reject_rate": self.get_reject_rate(),
            "throughput": self.get_throughput(),
            "runtime": self.get_runtime_seconds(),

            "current_bottle": self.current_bottle,
            "current_stage": self.current_stage,

            "water_temperature": sensors["water_temperature"],
            "conveyor_speed": sensors["conveyor_speed"],
            "motor_current": sensors["motor_current"],
            "tank_level": sensors["tank_level"],

            "rejection_log": self.rejection_log,
            "rework_log": self.rework_log,
            "production_history": self.production_history
        }

        if write_snapshot:
            self._write_telemetry_snapshot(stats)

        return stats
