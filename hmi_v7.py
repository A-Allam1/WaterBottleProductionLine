import tkinter as tk
from tkinter import ttk, messagebox
from production_lineV7 import ProductionLine


class WaterBottleHMI:
    def __init__(self, root):
        self.root = root
        self.root.title("Water Bottle Production Line - HMI V7")
        self.root.geometry("1600x900")
        self.root.configure(bg="#1a2332")

        self.line = ProductionLine()
        self.running = False
        self.current_stage_index = 0
        self.current_bottle = None

        self.stage_boxes = {}
        self.stage_positions = {}
        self.rework_arrows = {}

        self.stages = [
            "Bottle Creation", "Bottle QC", "Water Filling", "Fill QC",
            "Cap Installation", "Cap QC", "Label Application", "Label QC",
            "Final QC", "Packaging", "Shipped"
        ]

        self.default_colors = {
            "Bottle Creation": "#fff3cd",
            "Bottle QC": "#cce5ff",
            "Water Filling": "#fff3cd",
            "Fill QC": "#cce5ff",
            "Cap Installation": "#fff3cd",
            "Cap QC": "#cce5ff",
            "Label Application": "#fff3cd",
            "Label QC": "#cce5ff",
            "Final QC": "#cce5ff",
            "Packaging": "#d4edda",
            "Shipped": "#e8f5e9"
        }

        self.build_ui()
        self.update_display()
        self.update_runtime()

    def build_ui(self):
        title = tk.Label(
            self.root,
            text="WATER BOTTLE PRODUCTION LINE - HMI V7",
            font=("Courier New", 22, "bold"),
            bg="#0d1b2a",
            fg="#00b4d8",
            pady=15
        )
        title.pack(fill="x")

        control_frame = tk.Frame(self.root, bg="#1a2332", pady=12)
        control_frame.pack(fill="x")

        tk.Button(control_frame, text="▶ START", width=14, bg="#2dc653",
                  font=("Courier New", 11, "bold"), command=self.start).pack(side="left", padx=12)

        tk.Button(control_frame, text="■ STOP", width=14, bg="#e63946", fg="white",
                  font=("Courier New", 11, "bold"), command=self.stop).pack(side="left", padx=12)

        tk.Button(control_frame, text="↻ RESET", width=14, bg="#f4a261",
                  font=("Courier New", 11, "bold"), command=self.reset).pack(side="left", padx=12)

        tk.Button(control_frame, text="EXPORT CSV", width=14, bg="#00b4d8",
                  font=("Courier New", 11, "bold"), command=self.export_csv).pack(side="left", padx=12)

        self.state_label = tk.Label(
            control_frame,
            text="Machine State: STOPPED",
            font=("Courier New", 14, "bold"),
            bg="#1a2332",
            fg="#f4a261"
        )
        self.state_label.pack(side="right", padx=25)

        self.canvas = tk.Canvas(
            self.root,
            width=1500,
            height=260,
            bg="#243044",
            highlightthickness=0
        )
        self.canvas.pack(pady=8)

        self.draw_pipeline()

        self.status_banner = tk.Label(
            self.root,
            text="SYSTEM READY",
            font=("Courier New", 14, "bold"),
            bg="#243044",
            fg="#2dc653",
            pady=8
        )
        self.status_banner.pack(fill="x", padx=25, pady=5)

        self.build_statistics_panel()
        self.build_info_panel()
        self.build_tables()
        self.build_footer()

    def build_statistics_panel(self):
        stats_frame = tk.Frame(self.root, bg="#1a2332")
        stats_frame.pack(fill="x", padx=25, pady=8)

        self.stats_labels = {}

        stats = [
            "created", "filled", "capped", "labeled",
            "packaged", "shipped", "rejected", "reworked"
        ]

        for i, stat in enumerate(stats):
            box = tk.Frame(stats_frame, bg="#243044", padx=13, pady=8)
            box.grid(row=0, column=i, padx=5)

            tk.Label(
                box,
                text=stat.upper(),
                font=("Courier New", 8),
                bg="#243044",
                fg="#7a8fa8"
            ).pack()

            if stat == "rejected":
                color = "#e63946"
            elif stat == "reworked":
                color = "#f4a261"
            else:
                color = "#2dc653"

            value = tk.Label(
                box,
                text="0",
                font=("Courier New", 22, "bold"),
                bg="#243044",
                fg=color
            )
            value.pack()

            self.stats_labels[stat] = value

        kpi_frame = tk.Frame(self.root, bg="#1a2332")
        kpi_frame.pack(fill="x", padx=25, pady=5)

        self.kpi_labels = {}

        kpis = [
            ("efficiency", "EFFICIENCY %", "#2dc653"),
            ("rework_rate", "REWORK RATE %", "#f4a261"),
            ("reject_rate", "REJECT RATE %", "#e63946"),
            ("throughput", "BOTTLES / MIN", "#2dc653"),
            ("runtime", "RUNTIME", "#00b4d8")
        ]

        for i, (key, title, color) in enumerate(kpis):
            box = tk.Frame(kpi_frame, bg="#243044", padx=22, pady=8)
            box.grid(row=0, column=i, padx=8)

            tk.Label(
                box,
                text=title,
                font=("Courier New", 9),
                bg="#243044",
                fg="#7a8fa8"
            ).pack()

            value = tk.Label(
                box,
                text="0",
                font=("Courier New", 22, "bold"),
                bg="#243044",
                fg=color
            )
            value.pack()

            self.kpi_labels[key] = value

    def build_info_panel(self):
        info_frame = tk.Frame(self.root, bg="#1a2332", padx=25, pady=8)
        info_frame.pack(fill="x")

        self.current_label = tk.Label(
            info_frame,
            text="Current Bottle: None | Current Stage: None",
            font=("Courier New", 12, "bold"),
            bg="#1a2332",
            fg="#e0e8f0"
        )
        self.current_label.pack(anchor="w")

        self.event_label = tk.Label(
            info_frame,
            text="Last Event: None",
            font=("Courier New", 12, "bold"),
            bg="#1a2332",
            fg="#f4a261"
        )
        self.event_label.pack(anchor="w", pady=4)

    def build_tables(self):
        tables_frame = tk.Frame(self.root, bg="#1a2332", padx=25, pady=5)
        tables_frame.pack(fill="both", expand=True)

        left_frame = tk.Frame(tables_frame, bg="#1a2332")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        right_frame = tk.Frame(tables_frame, bg="#1a2332")
        right_frame.pack(side="right", fill="both", expand=True, padx=(10, 0))

        tk.Label(left_frame, text="QUALITY LOG", font=("Courier New", 11, "bold"),
                 bg="#1a2332", fg="#7a8fa8").pack(anchor="w")

        quality_columns = ("Type", "Bottle", "Stage", "Reason / Action")
        self.quality_tree = ttk.Treeview(left_frame, columns=quality_columns, show="headings", height=8)

        for col in quality_columns:
            self.quality_tree.heading(col, text=col)
            self.quality_tree.column(col, width=190)

        self.quality_tree.tag_configure("REWORK", foreground="#f4a261")
        self.quality_tree.tag_configure("REJECT", foreground="#e63946")
        self.quality_tree.pack(fill="both", expand=True, pady=5)

        tk.Label(right_frame, text="PRODUCTION HISTORY", font=("Courier New", 11, "bold"),
                 bg="#1a2332", fg="#7a8fa8").pack(anchor="w")

        history_columns = ("Time", "Bottle", "Result", "Stage")
        self.history_tree = ttk.Treeview(right_frame, columns=history_columns, show="headings", height=8)

        for col in history_columns:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=150)

        self.history_tree.tag_configure("SHIPPED", foreground="#2dc653")
        self.history_tree.tag_configure("REWORKED", foreground="#f4a261")
        self.history_tree.tag_configure("REJECTED", foreground="#e63946")
        self.history_tree.pack(fill="both", expand=True, pady=5)

    def build_footer(self):
        footer = tk.Label(
            self.root,
            text="SRH University | Advanced Programming | Water Bottle Production Line Simulation | Version 7 | Adam Hassan | InfluxDB + Grafana Telemetry",
            font=("Courier New", 9, "bold"),
            bg="#0d1b2a",
            fg="#7a8fa8",
            pady=8
        )
        footer.pack(fill="x", side="bottom")

    def draw_pipeline(self):
        start_x = 25
        y = 105
        box_width = 105
        box_height = 58
        spacing = 20

        for i, stage in enumerate(self.stages):
            x = start_x + i * (box_width + spacing)

            rect = self.canvas.create_rectangle(
                x, y, x + box_width, y + box_height,
                fill=self.default_colors[stage],
                outline="#111",
                width=2
            )

            self.canvas.create_text(
                x + box_width / 2,
                y + box_height / 2,
                text=stage,
                width=95,
                font=("Courier New", 7, "bold"),
                fill="#111"
            )

            self.stage_boxes[stage] = rect
            self.stage_positions[stage] = (x + box_width / 2, y - 25)

            if i < len(self.stages) - 1:
                self.canvas.create_line(
                    x + box_width,
                    y + box_height / 2,
                    x + box_width + spacing,
                    y + box_height / 2,
                    arrow=tk.LAST,
                    width=2,
                    fill="#cccccc"
                )

        self.rework_box = self.canvas.create_rectangle(
            640, 195, 860, 235,
            fill="#f4a261",
            outline="#111",
            width=2
        )

        self.canvas.create_text(
            750, 215,
            text="REWORK STATION",
            font=("Courier New", 9, "bold"),
            fill="#111"
        )

        qc_stages = ["Bottle QC", "Fill QC", "Cap QC", "Label QC"]

        for stage in qc_stages:
            x, _ = self.stage_positions[stage]

            arrow = self.canvas.create_line(
                x,
                y + box_height,
                750,
                195,
                fill="#3a4458",
                width=1,
                arrow=tk.LAST,
                dash=(2, 2)
            )

            self.rework_arrows[stage] = arrow


        self.bottle_dot = self.canvas.create_oval(
            0, 0, 22, 22,
            fill="#00b4d8",
            outline="white",
            width=2
        )

        self.bottle_text = self.canvas.create_text(
            0, 0,
            text="",
            fill="white",
            font=("Courier New", 9, "bold")
        )

        self.hide_bottle()

    def start(self):
        if self.running:
            return

        self.running = True
        self.line.start()

        self.status_banner.config(
            text="CONTINUOUS PRODUCTION WITH REWORK RUNNING",
            bg="#243044",
            fg="#2dc653"
        )

        self.start_new_bottle()

    def stop(self):
        self.running = False
        self.line.stop()

        self.status_banner.config(
            text="PRODUCTION STOPPED",
            bg="#243044",
            fg="#f4a261"
        )

        self.update_display()

    def reset(self):
        self.running = False
        self.line.reset()
        self.current_stage_index = 0
        self.current_bottle = None

        self.quality_tree.delete(*self.quality_tree.get_children())
        self.history_tree.delete(*self.history_tree.get_children())

        self.reset_stage_colors()
        self.hide_bottle()
        self.hide_rework_paths()

        self.status_banner.config(
            text="SYSTEM READY",
            bg="#243044",
            fg="#2dc653"
        )

        self.update_display()

    def start_new_bottle(self):
        if not self.running:
            return

        if self.line.machine_state != "RUNNING":
            return

        self.current_bottle = self.line.create_bottle()
        self.current_stage_index = 0
        self.process_current_stage()

    def process_current_stage(self):
        if not self.running:
            return

        if self.current_bottle is None:
            return

        stage = self.stages[self.current_stage_index]
        result = self.line.process_stage(self.current_bottle, stage)

        self.move_bottle(stage)
        self.update_display()

        if result == "REWORK":
            self.highlight_stage(stage, "REWORK")
            self.show_rework_path(stage)

            self.status_banner.config(
                text=f"Bottle #{self.current_bottle.id} reworked at {stage}: {self.current_bottle.defect_reason}",
                bg="#243044",
                fg="#f4a261"
            )

            self.root.after(900, self.hide_rework_paths)
            self.root.after(1100, self.process_current_stage)
            return

        if result == "REJECT":
            self.highlight_stage(stage, "REJECT")

            self.status_banner.config(
                text=f"Bottle #{self.current_bottle.id} rejected at Final QC: {self.current_bottle.defect_reason}",
                bg="#243044",
                fg="#e63946"
            )

            self.root.after(900, self.start_new_bottle)
            return

        self.highlight_stage(stage, "PASS")

        if stage == "Shipped":
            self.status_banner.config(
                text=f"Bottle #{self.current_bottle.id} shipped successfully",
                bg="#243044",
                fg="#2dc653"
            )

            self.root.after(700, self.start_new_bottle)
            return

        self.current_stage_index += 1
        self.root.after(600, self.process_current_stage)

    def move_bottle(self, stage):
        x, y = self.stage_positions[stage]

        self.canvas.coords(
            self.bottle_dot,
            x - 11,
            y - 11,
            x + 11,
            y + 11
        )

        self.canvas.coords(
            self.bottle_text,
            x,
            y - 24
        )

        if self.current_bottle:
            self.canvas.itemconfig(
                self.bottle_text,
                text=f"#{self.current_bottle.id}"
            )

    def hide_bottle(self):
        self.canvas.coords(self.bottle_dot, -50, -50, -30, -30)
        self.canvas.coords(self.bottle_text, -50, -50)
        self.canvas.itemconfig(self.bottle_text, text="")

    def show_rework_path(self, stage):
        self.hide_rework_paths()

        if stage in self.rework_arrows:
            self.canvas.itemconfig(
                self.rework_arrows[stage],
                fill="#ffb703",
                width=4,
                dash=()
            )

        self.canvas.itemconfig(
            self.rework_box,
            fill="#ffb703"
        )

    def hide_rework_paths(self):
        for arrow in self.rework_arrows.values():
            self.canvas.itemconfig(
                arrow,
                fill="#3a4458",
                width=1,
                dash=(2, 2)
            )

        self.canvas.itemconfig(
            self.rework_box,
            fill="#f4a261"
        )

    def highlight_stage(self, active_stage, result="PASS"):
        self.reset_stage_colors()

        if active_stage in self.stage_boxes:
            if result == "PASS":
                color = "#2dc653"
            elif result == "REWORK":
                color = "#f4a261"
            elif result == "REJECT":
                color = "#e63946"
            else:
                color = "#00b4d8"

            self.canvas.itemconfig(self.stage_boxes[active_stage], fill=color)

    def reset_stage_colors(self):
        for stage, color in self.default_colors.items():
            self.canvas.itemconfig(self.stage_boxes[stage], fill=color)

    def format_runtime(self, seconds):
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    def update_runtime(self):
        stats = self.line.get_stats()

        if "runtime" in self.kpi_labels:
            self.kpi_labels["runtime"].config(
                text=self.format_runtime(stats["runtime"])
            )

        if "throughput" in self.kpi_labels:
            self.kpi_labels["throughput"].config(
                text=str(stats["throughput"])
            )

        self.root.after(1000, self.update_runtime)

    def update_display(self):
        stats = self.line.get_stats()

        self.state_label.config(text=f"Machine State: {stats['machine_state']}")

        if stats["machine_state"] == "RUNNING":
            self.state_label.config(fg="#2dc653")
        else:
            self.state_label.config(fg="#f4a261")

        for key, label in self.stats_labels.items():
            label.config(text=str(stats[key]))

        self.kpi_labels["efficiency"].config(text=f"{stats['efficiency']}%")
        self.kpi_labels["rework_rate"].config(text=f"{stats['rework_rate']}%")
        self.kpi_labels["reject_rate"].config(text=f"{stats['reject_rate']}%")
        self.kpi_labels["throughput"].config(text=str(stats["throughput"]))
        self.kpi_labels["runtime"].config(text=self.format_runtime(stats["runtime"]))

        self.current_label.config(
            text=f"Current Bottle: {stats['current_bottle']} | Current Stage: {stats['current_stage']}"
        )

        logs = []

        for item in stats["rework_log"]:
            logs.append({
                "type": "REWORK",
                "bottle_id": item["bottle_id"],
                "stage": item["stage"],
                "reason": f"{item['reason']} → {item['action']}"
            })

        for item in stats["rejection_log"]:
            logs.append({
                "type": "REJECT",
                "bottle_id": item["bottle_id"],
                "stage": item["stage"],
                "reason": item["reason"]
            })

        if logs:
            last = logs[-1]
            self.event_label.config(
                text=f"Last Event: {last['type']} | Bottle #{last['bottle_id']} | {last['stage']} | {last['reason']}"
            )
        else:
            self.event_label.config(text="Last Event: None")

        self.quality_tree.delete(*self.quality_tree.get_children())

        for item in logs[-50:]:
            self.quality_tree.insert(
                "",
                "end",
                values=(
                    item["type"],
                    f"Bottle #{item['bottle_id']}",
                    item["stage"],
                    item["reason"]
                ),
                tags=(item["type"],)
            )

        self.history_tree.delete(*self.history_tree.get_children())

        for item in stats["production_history"][-50:]:
            self.history_tree.insert(
                "",
                "end",
                values=(
                    item["time"],
                    f"Bottle #{item['bottle_id']}",
                    item["result"],
                    item["stage"]
                ),
                tags=(item["result"],)
            )

    def export_csv(self):
        filename = self.line.export_csv()

        messagebox.showinfo(
            "Export Complete",
            f"Production report exported successfully:\n{filename}"
        )


if __name__ == "__main__":
    root = tk.Tk()
    app = WaterBottleHMI(root)
    root.mainloop()