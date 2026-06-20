import json
import os
import time
from datetime import datetime, timezone

try:
    from influxdb_client import InfluxDBClient, Point
    from influxdb_client.client.write_api import SYNCHRONOUS
except ImportError:
    print("Missing package: influxdb-client")
    print("Install it with: pip install influxdb-client")
    raise

from production_lineV7 import ProductionLine, TELEMETRY_FILE


URL = os.getenv("INFLUX_URL", "http://localhost:8086")
TOKEN = os.getenv("INFLUX_TOKEN", "my-super-secret-token")
ORG = os.getenv("INFLUX_ORG", "lecture")
BUCKET = os.getenv("INFLUX_BUCKET", "factory")
LINE_NAME = os.getenv("LINE_NAME", "WaterBottleLine-A")

STAGES = [
    "Bottle Creation", "Bottle QC", "Water Filling", "Fill QC",
    "Cap Installation", "Cap QC", "Label Application", "Label QC",
    "Final QC", "Packaging", "Shipped"
]

STATE_CODES = {
    "STOPPED": 0,
    "RUNNING": 1,
    "Standby": 2,
    "Productive": 3,
    "Unscheduled Downtime": 4
}


class DemoSimulation:
    def __init__(self):
        self.line = ProductionLine()
        self.line.start()
        self.current_bottle = None
        self.stage_index = 0

    def step(self):
        if self.current_bottle is None:
            self.current_bottle = self.line.create_bottle()
            self.stage_index = 0

        stage = STAGES[self.stage_index]
        result = self.line.process_stage(self.current_bottle, stage)

        if result == "REWORK":
            pass
        elif result == "REJECT":
            self.current_bottle = None
            self.stage_index = 0
        elif stage == "Shipped":
            self.current_bottle = None
            self.stage_index = 0
        else:
            self.stage_index += 1

        return self.line.get_stats(write_snapshot=False)


def read_hmi_stats(max_age_seconds=6):
    if not os.path.exists(TELEMETRY_FILE):
        return None

    try:
        with open(TELEMETRY_FILE, "r", encoding="utf-8") as file:
            stats = json.load(file)
    except (json.JSONDecodeError, OSError):
        return None

    timestamp_epoch = stats.get("timestamp_epoch", 0)
    if time.time() - timestamp_epoch > max_age_seconds:
        return None

    return stats


def number(value, default=0):
    if value is None:
        return default
    return value


def write_stats(write_api, stats, source):
    now = datetime.now(timezone.utc)

    machine_state = str(stats.get("machine_state", "UNKNOWN"))
    e10_state = str(stats.get("e10_state", "UNKNOWN"))
    current_stage = str(stats.get("current_stage", "Unknown"))

    production_point = (
        Point("water_bottle_production")
        .tag("line", LINE_NAME)
        .tag("source", source)
        .tag("machine_state", machine_state)
        .tag("e10_state", e10_state)
        .tag("current_stage", current_stage)
        .field("created", int(number(stats.get("created"))))
        .field("filled", int(number(stats.get("filled"))))
        .field("capped", int(number(stats.get("capped"))))
        .field("labeled", int(number(stats.get("labeled"))))
        .field("packaged", int(number(stats.get("packaged"))))
        .field("shipped", int(number(stats.get("shipped"))))
        .field("rejected", int(number(stats.get("rejected"))))
        .field("reworked", int(number(stats.get("reworked"))))
        .field("current_bottle", int(number(stats.get("current_bottle"))))
        .field("runtime", int(number(stats.get("runtime"))))
        .field("efficiency", float(number(stats.get("efficiency"))))
        .field("rework_rate", float(number(stats.get("rework_rate"))))
        .field("reject_rate", float(number(stats.get("reject_rate"))))
        .field("throughput", float(number(stats.get("throughput"))))
        .time(now)
    )

    sensor_point = (
        Point("water_bottle_sensors")
        .tag("line", LINE_NAME)
        .tag("source", source)
        .tag("machine_state", machine_state)
        .field("water_temperature", float(number(stats.get("water_temperature"))))
        .field("conveyor_speed", float(number(stats.get("conveyor_speed"))))
        .field("motor_current", float(number(stats.get("motor_current"))))
        .field("tank_level", float(number(stats.get("tank_level"))))
        .time(now)
    )

    state_point = (
        Point("water_bottle_state")
        .tag("line", LINE_NAME)
        .tag("source", source)
        .tag("machine_state", machine_state)
        .tag("e10_state", e10_state)
        .tag("current_stage", current_stage)
        .field("state_code", int(STATE_CODES.get(machine_state, STATE_CODES.get(e10_state, 0))))
        .field("current_stage_text", current_stage)
        .field("machine_status_text", machine_state)
        .field("e10_state_text", e10_state)
        .time(now)
    )

    write_api.write(
        bucket=BUCKET,
        org=ORG,
        record=[production_point, sensor_point, state_point]
    )


def main():
    client = InfluxDBClient(url=URL, token=TOKEN, org=ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)
    demo = DemoSimulation()

    print("Sending water bottle production telemetry to InfluxDB.")
    print(f"InfluxDB URL: {URL}")
    print(f"Organization: {ORG}")
    print(f"Bucket: {BUCKET}")
    print("Run hmi_v7.py for live HMI telemetry, or leave it closed for demo telemetry.")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            stats = read_hmi_stats()
            source = "hmi"

            if stats is None:
                stats = demo.step()
                source = "producer_demo"

            write_stats(write_api, stats, source)

            print(
                f"{datetime.now().strftime('%H:%M:%S')} | "
                f"source={source:<13} "
                f"state={stats.get('machine_state'):<8} "
                f"stage={str(stats.get('current_stage')):<18} "
                f"created={stats.get('created'):<4} "
                f"shipped={stats.get('shipped'):<4} "
                f"rejected={stats.get('rejected'):<3} "
                f"reworked={stats.get('reworked'):<3} "
                f"eff={stats.get('efficiency')}%"
            )

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nTelemetry producer stopped.")
    finally:
        client.close()


if __name__ == "__main__":
    main()