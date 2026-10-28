"""Windows interface for automated Binance spot trading."""

import json
from pathlib import Path
import queue
import shutil

# Local workers use a fixed executable and allowlisted actions, without a shell.
import subprocess  # nosec B404
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timezone, timedelta

import bot
import ai_review
import credential_store
from live_api import Binance
from live_engine import Engine, StateStore
from trader_text import TEXT

ROOT = bot.ROOT


def worker(action):
    import contextlib

    (ROOT / "logs").mkdir(exist_ok=True)
    with (ROOT / "logs" / (action + ".log")).open("a", encoding="utf-8") as output:
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            if action == "livebacktest":
                import backtest_live

                if (
                    not (ROOT / "data" / "BTCUSDT-1h.csv").exists()
                    or not (ROOT / "data" / "exchange_rules.json").exists()
                ):
                    sys.argv = ["bot", "fetch", "--days", "365"]
                    bot.main()
                backtest_live.main()
            else:
                sys.argv = ["bot", action]
                bot.main()
    return 0


class App:
    def __init__(self, root):
        self.root, self.frame, self.page = root, None, "dashboard"
        self.live_thread, self.engine, self.api, self.job = None, None, None, None
        self.stop_event = threading.Event()
        self.events = queue.Queue()
        self.notice, self.connection_record = None, None
        self.ai_record = None
        try:
            self.ai_record = ai_review.read_settings(ROOT)
        except Exception:
            self.notice = "ai_error"
        self.authorized = tk.BooleanVar(value=False)
        self.message = tk.StringVar()
        self.action_buttons = []
        try:
            self.language = json.loads((ROOT / "ui_settings.json").read_text()).get(
                "language", "en"
            )
        except (OSError, ValueError):
            self.language = "en"
        if self.language not in TEXT:
            self.language = "en"
        if (ROOT / ".private" / "connection.bin").exists():
            try:
                self.connection_record = credential_store.load(ROOT)
            except Exception:
                self.notice = "live_failed"
        width = min(1120, root.winfo_screenwidth() - 80)
        height = min(860, root.winfo_screenheight() - 100)
        root.geometry(f"{width}x{height}")
        root.minsize(900, 620)
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.bind(
            "<MouseWheel>", lambda event: self.canvas.yview_scroll(int(-event.delta / 120), "units")
        )
        root.report_callback_exception = lambda *args: messagebox.showerror(
            self.t("error_title"), self.t("error")
        )
        self.style()
        self.build()
        self.refresh()

    def t(self, key, **values):
        value = TEXT[self.language][key].format(**values)
        if self.language == "tr" and key == "history_live":
            value = value.translate(str.maketrans({",": ".", ".": ","}))
        return value

    def amount(self, value, places=4):
        text = f"{float(value):,.{places}f}"
        return (
            text.translate(str.maketrans({",": ".", ".": ","})) if self.language == "tr" else text
        )

    def style(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure(".", font=("Segoe UI", 10), background="#f5f6f8", foreground="#18212f")
        s.configure("TFrame", background="#f5f6f8")
        s.configure("Surface.TFrame", background="#ffffff")
        s.configure("Side.TFrame", background="#17202d")
        s.configure("Side.TLabel", background="#17202d", foreground="#d5dbe4")
        s.configure("TLabel", background="#f5f6f8")
        s.configure("Surface.TLabel", background="#ffffff")
        s.configure("Muted.TLabel", foreground="#566170")
        s.configure(
            "TButton",
            padding=(12, 8),
            background="#ffffff",
            foreground="#18212f",
            borderwidth=1,
            relief="flat",
        )
        s.map("TButton", background=[("active", "#e9edf3")])
        s.configure("Primary.TButton", background="#2454a6", foreground="white", borderwidth=0)
        s.map(
            "Primary.TButton",
            background=[("active", "#193e80"), ("disabled", "#a1adc1")],
            foreground=[("disabled", "#ffffff")],
        )
        s.configure(
            "Nav.TButton",
            background="#17202d",
            foreground="#e5e9f0",
            anchor="w",
            borderwidth=0,
            padding=(16, 12),
        )
        s.map("Nav.TButton", background=[("active", "#26354a")])
        s.configure("Selected.Nav.TButton", background="#2b3b51")
        s.configure("TCheckbutton", background="#f5f6f8")
        s.configure(
            "Treeview", background="#ffffff", fieldbackground="#ffffff", rowheight=31, borderwidth=0
        )
        s.configure(
            "Treeview.Heading", background="#e9edf3", foreground="#344155", padding=7, relief="flat"
        )
        s.map("Treeview.Heading", background=[("active", "#e9edf3")])
        s.configure("TEntry", padding=8, fieldbackground="#ffffff")

    def label(self, parent, text="", **kwargs):
        widget = ttk.Label(parent, text=text, **kwargs)
        self.wrapped.append(widget)
        return widget

    def build(self):
        if self.frame:
            self.frame.destroy()
        self.root.title(self.t("title"))
        self.wrapped, self.action_buttons = [], []
        self.frame = ttk.Frame(self.root)
        self.frame.pack(fill="both", expand=True)
        side = ttk.Frame(self.frame, style="Side.TFrame", width=180)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        ttk.Label(
            side, text="CRYPTO\nTRADER", style="Side.TLabel", font=("Segoe UI", 20, "bold")
        ).pack(anchor="w", padx=18, pady=(26, 5))
        ttk.Label(side, text="Binance.com", style="Side.TLabel").pack(
            anchor="w", padx=18, pady=(0, 30)
        )
        for page in ("dashboard", "connection", "ai_settings", "guide"):
            label_key = "ai_navigation" if page == "ai_settings" else page
            button = ttk.Button(
                side,
                text=self.t(label_key),
                style="Selected.Nav.TButton" if self.page == page else "Nav.TButton",
                command=lambda p=page: self.navigate(p),
            )
            button.pack(fill="x", padx=8, pady=2)
        ttk.Label(
            side, text="BTC / USDT\n10 USDT", style="Side.TLabel", font=("Segoe UI", 11)
        ).pack(side="bottom", anchor="w", padx=18, pady=24)
        main = ttk.Frame(self.frame, padding=(22, 20, 18, 16))
        main.pack(side="left", fill="both", expand=True)
        heading = ttk.Frame(main)
        heading.pack(fill="x")
        ttk.Label(heading, text=self.t(self.page), font=("Segoe UI", 22, "bold")).pack(side="left")
        choice = ttk.Combobox(heading, values=["English", "Türkçe"], state="readonly", width=10)
        choice.set("Türkçe" if self.language == "tr" else "English")
        choice.pack(side="right")
        choice.bind(
            "<<ComboboxSelected>>",
            lambda e: self.set_language("tr" if choice.get() == "Türkçe" else "en"),
        )
        ttk.Label(main, text=self.t("subtitle"), style="Muted.TLabel").pack(
            anchor="w", pady=(4, 15)
        )
        self.badge = tk.StringVar()
        ttk.Label(
            main, textvariable=self.badge, foreground="#8c2934", font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", pady=(0, 15))
        self.canvas = tk.Canvas(main, background="#f5f6f8", highlightthickness=0)
        bar = ttk.Scrollbar(main, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        self.canvas.pack(fill="both", expand=True)
        body = ttk.Frame(self.canvas)
        item = self.canvas.create_window(0, 0, window=body, anchor="nw")
        body.bind(
            "<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        def resize(event):
            self.canvas.itemconfigure(item, width=event.width)
            for widget in self.wrapped:
                widget.configure(wraplength=max(300, event.width - 32))

        self.canvas.bind("<Configure>", resize)
        self.canvas.bind(
            "<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-e.delta / 120), "units")
        )
        if self.page == "dashboard":
            self.dashboard(body)
        elif self.page == "connection":
            self.connection_page(body)
        elif self.page == "ai_settings":
            self.ai_page(body)
        else:
            self.label(body, self.t("help_live"), justify="left").pack(
                fill="x", anchor="w", pady=(0, 20)
            )
        self.render()

    def navigate(self, page):
        self.page = page
        self.build()

    def set_language(self, language):
        self.language = language
        (ROOT / "ui_settings.json").write_text(json.dumps({"language": language}))
        self.build()

    def dashboard(self, body):
        self.label(body, self.t("intro")).pack(fill="x", pady=(0, 16))
        cards = ttk.Frame(body)
        cards.pack(fill="x")
        self.cash_label, self.value_label = tk.StringVar(), tk.StringVar()
        for i, (label, value) in enumerate(
            [
                ("budget_card", None),
                ("cash_card", self.cash_label),
                ("value_card", self.value_label),
            ]
        ):
            cards.columnconfigure(i, weight=1, uniform="card")
            card = ttk.Frame(cards, style="Surface.TFrame", padding=14)
            card.grid(row=0, column=i, sticky="nsew", padx=(0, 8))
            ttk.Label(card, text=self.t(label), style="Surface.TLabel", font=("Segoe UI", 9)).pack(
                anchor="w"
            )
            if value is None:
                ttk.Label(
                    card, text="10 USDT", style="Surface.TLabel", font=("Segoe UI", 20, "bold")
                ).pack(anchor="w", pady=(8, 0))
            else:
                ttk.Label(
                    card, textvariable=value, style="Surface.TLabel", font=("Segoe UI", 20, "bold")
                ).pack(anchor="w", pady=(8, 0))
        self.label(body, self.t("position_note"), style="Muted.TLabel").pack(fill="x", pady=(9, 18))
        self.status, self.heartbeat = tk.StringVar(), tk.StringVar()
        self.label(body, textvariable=self.status, font=("Segoe UI", 12, "bold")).pack(
            fill="x", pady=(0, 4)
        )
        self.label(body, textvariable=self.heartbeat, style="Muted.TLabel").pack(
            fill="x", pady=(0, 15)
        )
        self.ai_summary = tk.StringVar()
        self.label(body, textvariable=self.ai_summary, style="Muted.TLabel").pack(
            fill="x", pady=(0, 12)
        )
        actions = ttk.Frame(body)
        actions.pack(fill="x")
        for key, action, style in [
            ("connect", lambda: self.navigate("connection"), "TButton"),
            ("start", self.start, "Primary.TButton"),
            ("stop", self.pause, "TButton"),
        ]:
            button = ttk.Button(actions, text=self.t(key), command=action, style=style)
            button.pack(side="left", padx=(0, 8))
            self.action_buttons.append(button)
        auth = ttk.Frame(body)
        auth.pack(fill="x", pady=(15, 8))
        ttk.Checkbutton(auth, variable=self.authorized).pack(side="left", anchor="n")
        self.label(auth, self.t("authorize")).pack(side="left", fill="x", expand=True)
        self.label(body, self.t("protection_note"), style="Muted.TLabel").pack(
            fill="x", pady=(0, 14)
        )
        self.label(body, textvariable=self.message, foreground="#8c2934").pack(
            fill="x", pady=(0, 12)
        )
        ttk.Label(body, text=self.t("position_heading"), font=("Segoe UI", 12, "bold")).pack(
            anchor="w", pady=(5, 10)
        )
        table_frame = ttk.Frame(body)
        table_frame.pack(fill="x")
        columns = ["time", "status", "buy", "stop", "target"]
        self.table = ttk.Treeview(table_frame, columns=columns, show="headings", height=4)
        for column, width in zip(columns, [145, 150, 120, 105, 105]):
            self.table.heading(column, text=self.t("table_" + column))
            self.table.column(column, width=width, minwidth=70, stretch=True)
        self.table.pack(fill="x")
        self.order_note = tk.StringVar()
        self.label(body, textvariable=self.order_note, style="Muted.TLabel").pack(
            fill="x", pady=(5, 16)
        )
        ttk.Label(body, text=self.t("limits_heading"), font=("Segoe UI", 12, "bold")).pack(
            anchor="w"
        )
        self.label(body, self.t("limits")).pack(fill="x", pady=(7, 18))
        actions = ttk.Frame(body)
        actions.pack(fill="x")
        ttk.Button(
            actions, text=self.t("research"), command=lambda: self.run_job("livebacktest")
        ).pack(side="left")
        ttk.Button(actions, text=self.t("fetch"), command=lambda: self.run_job("fetch")).pack(
            side="left", padx=8
        )
        self.history = tk.StringVar()
        self.label(body, textvariable=self.history, style="Muted.TLabel").pack(
            fill="x", pady=(10, 20)
        )

    def connection_page(self, body):
        self.label(body, self.t("connection_intro")).pack(fill="x", pady=(0, 15))
        self.label(body, self.t("connection_steps")).pack(fill="x", pady=(0, 20))
        if self.connection_record:
            self.label(body, self.t("saved")).pack(fill="x")
        else:
            ttk.Label(body, text=self.t("key")).pack(anchor="w")
            self.key_field = ttk.Entry(body, show="*", width=55)
            self.key_field.pack(fill="x", pady=(5, 14))
            ttk.Label(body, text=self.t("credential_label")).pack(anchor="w")
            self.secret_field = ttk.Entry(body, show="*", width=55)
            self.secret_field.pack(fill="x", pady=(5, 14))
            self.label(body, self.t("privacy_live"), style="Muted.TLabel").pack(
                fill="x", pady=(0, 18)
            )
            self.save_button = ttk.Button(
                body, text=self.t("save_connection"), style="Primary.TButton", command=self.setup
            )
            self.save_button.pack(anchor="w")
        self.label(body, textvariable=self.message, foreground="#8c2934").pack(fill="x", pady=20)

    def setup(self):
        key, secret = self.key_field.get().strip(), self.secret_field.get().strip()
        if not key or not secret:
            self.notice = "missing"
            return
        self.key_field.delete(0, "end")
        self.secret_field.delete(0, "end")
        self.save_button.configure(state="disabled")
        self.notice = "running_setup"

        def task():
            try:
                Binance(key, secret).preflight()
                record = credential_store.create(ROOT, key, secret)
                self.events.put(("saved", record))
            except Exception:
                self.events.put(("notice", "connection_failed"))

        threading.Thread(target=task, daemon=True).start()

    def ai_page(self, body):
        self.label(body, self.t("ai_intro")).pack(fill="x", pady=(0, 15))
        self.label(body, self.t("ai_privacy")).pack(fill="x", pady=(0, 15))
        self.label(body, self.t("ai_costs")).pack(fill="x", pady=(0, 20))
        if self.ai_record:
            self.label(body, self.t("ai_current", model=self.ai_record["model"])).pack(
                fill="x", pady=(0, 15)
            )
        ttk.Label(body, text=self.t("ai_key")).pack(anchor="w")
        self.ai_key_field = ttk.Entry(body, show="*", width=55)
        self.ai_key_field.pack(fill="x", pady=(5, 14))
        ttk.Label(body, text=self.t("ai_model")).pack(anchor="w")
        self.ai_model_field = ttk.Entry(body, width=55)
        self.ai_model_field.insert(
            0, self.ai_record["model"] if self.ai_record else ai_review.DEFAULT_MODEL
        )
        self.ai_model_field.pack(fill="x", pady=(5, 14))
        self.ai_consent = tk.BooleanVar(value=False)
        row = ttk.Frame(body)
        row.pack(fill="x", pady=(0, 15))
        ttk.Checkbutton(row, variable=self.ai_consent).pack(side="left", anchor="n")
        self.label(row, self.t("ai_consent")).pack(side="left", fill="x", expand=True)
        self.ai_save_button = ttk.Button(
            body, text=self.t("save_connection"), style="Primary.TButton", command=self.setup_ai
        )
        self.ai_save_button.pack(anchor="w")
        self.label(body, textvariable=self.message, foreground="#8c2934").pack(fill="x", pady=20)

    def setup_ai(self):
        key, model = self.ai_key_field.get().strip(), self.ai_model_field.get().strip()
        if not self.ai_consent.get():
            self.notice = "ai_consent_required"
            return
        self.ai_key_field.delete(0, "end")
        self.ai_save_button.configure(state="disabled")
        self.notice = "ai_checking"

        def task():
            try:
                ai_review.configure(ROOT, key, model)
                self.events.put(("ai_saved", ai_review.read_settings(ROOT)))
            except Exception:
                self.events.put(("notice", "ai_setup_failed"))

        threading.Thread(target=task, daemon=True).start()

    def start(self):
        if self.live_thread and self.live_thread.is_alive():
            return
        if not self.connection_record:
            self.notice = "need_connection"
            self.navigate("connection")
            return
        if not self.authorized.get():
            self.notice = "authority_needed"
            return
        if not self.ai_record and not self.read_state().get("active"):
            self.notice = "ai_unconfigured"
            self.navigate("ai_settings")
            return
        self.stop_event = threading.Event()
        self.api = Binance(
            self.connection_record["key"], self.connection_record["secret"], armed=True
        )
        self.engine = Engine(ROOT, self.api, self.connection_record, self.stop_event)
        self.notice = "connecting"

        def task():
            try:
                self.engine.run()
            except Exception:
                self.events.put(("notice", "live_failed"))

        self.live_thread = threading.Thread(target=task, daemon=True)
        self.live_thread.start()

    def pause(self):
        self.stop_event.set()
        if self.api:
            self.api.armed = False
        self.authorized.set(False)
        self.notice = "pausing" if self.live_thread and self.live_thread.is_alive() else "paused"

    def command(self, action):
        if action not in ("fetch", "livebacktest", "paper"):
            raise ValueError("Unknown local worker action")
        return (
            [sys.executable, "--worker", action]
            if getattr(sys, "frozen", False)
            else [sys.executable, str(Path(__file__).resolve()), "--worker", action]
        )

    def run_job(self, action):
        if self.job and self.job.poll() is None:
            self.notice = "job_busy"
            return
        # Allowlisted action, fixed current executable and no shell.
        self.job = subprocess.Popen(  # nosec B603
            self.command(action),
            cwd=ROOT,
            creationflags=subprocess.CREATE_NO_WINDOW,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.notice = "backtest_busy" if action == "livebacktest" else "fetch_busy"

    def read_state(self):
        if self.connection_record and (ROOT / "live_state.json").exists():
            try:
                return StateStore(ROOT, self.connection_record["secret"]).read()
            except Exception:
                self.notice = "live_failed"
        return {}

    def render(self):
        running = bool(
            self.live_thread and self.live_thread.is_alive() and not self.stop_event.is_set()
        )
        self.badge.set(self.t("badge_on" if running else "badge_off"))
        self.message.set(self.t(self.notice) if self.notice else "")
        if self.page != "dashboard":
            return
        state = self.read_state()
        ai_status = state.get("last_ai", {}).get(
            "status", "ai_ready" if self.ai_record else "ai_unconfigured"
        )
        self.ai_summary.set(
            self.t(
                "ai_summary",
                model=self.ai_record["model"] if self.ai_record else "OpenAI",
                status=self.t(ai_status)
                if ai_status in TEXT[self.language]
                else self.t("ai_error"),
            )
        )
        self.cash_label.set(self.amount(state["cash"]) if state else "—")
        self.value_label.set(
            self.amount(
                float(state["cash"]) + float(state["base"]) * float(state.get("last_bid", 0))
            )
            if state
            else "—"
        )
        code = state.get("status", "connecting") if running else "status_off"
        if running and state.get("halted"):
            code = state.get("halt_reason", "check_exchange")
        self.status.set(self.t(code) if code in TEXT[self.language] else self.t("check_exchange"))
        try:
            stamp = datetime.fromisoformat(state["heartbeat_utc"]).astimezone(
                timezone(timedelta(hours=3))
            )
            self.heartbeat.set(self.t("heartbeat_live", time=stamp.strftime("%d.%m.%Y %H:%M:%S")))
        except (KeyError, ValueError):
            self.heartbeat.set(self.t("no_live_check"))
        rows = list(state.get("cycles", []))[-5:]
        if state.get("active"):
            rows.append(state["active"])
        self.table.delete(*self.table.get_children())
        for cycle in reversed(rows):
            plan = cycle["plan"]
            stamp = datetime.fromtimestamp(cycle["created"], timezone(timedelta(hours=3))).strftime(
                "%d.%m %H:%M"
            )
            outcome = cycle.get("outcome", "")
            names = {
                "accepted": "protected_order"
                if cycle.get("protection") == "confirmed"
                else "submitted_order",
                "intent": "pending_order",
                "uncertain": "review_order",
                "rejected": "order_rejected",
                "closed": "closed_order",
                "not_filled": "not_filled",
            }
            label_key = names.get(outcome, "check_exchange")
            label = self.t(label_key)
            self.table.insert(
                "",
                "end",
                values=(
                    stamp,
                    label,
                    self.amount(plan["quantity"], 8),
                    self.amount(plan["stop"], 2),
                    self.amount(plan["target"], 2),
                ),
            )
        self.order_note.set("" if rows else self.t("no_orders"))
        try:
            result = json.loads((ROOT / "data" / "live_backtest.json").read_text())
            self.history.set(
                self.t(
                    "history_live",
                    count=result["candles"],
                    trades=result["closed_trades"],
                    final=result["final_equity"],
                    cash=result["cash"],
                    base=result["remaining_btc"],
                    change=result["return_pct"],
                )
            )
        except (OSError, ValueError, KeyError):
            self.history.set(self.t("history_none_live"))

    def refresh(self):
        try:
            while True:
                kind, data = self.events.get_nowait()
                if kind == "saved":
                    self.connection_record = data
                    self.notice = "connection_saved"
                    self.build()
                elif kind == "ai_saved":
                    self.ai_record = data
                    self.notice = "ai_saved"
                    self.build()
                else:
                    self.notice = data
                    if (
                        self.page == "connection"
                        and hasattr(self, "save_button")
                        and self.save_button.winfo_exists()
                    ):
                        self.save_button.configure(state="normal")
                    if (
                        self.page == "ai_settings"
                        and hasattr(self, "ai_save_button")
                        and self.ai_save_button.winfo_exists()
                    ):
                        self.ai_save_button.configure(state="normal")
        except queue.Empty:
            pass
        if self.job and self.job.poll() is not None:
            self.notice = "job_done" if self.job.returncode == 0 else "job_failed"
            self.job = None
        if self.notice == "connecting" and self.engine and self.engine.state:
            self.notice = None
        if self.notice == "pausing" and not (self.live_thread and self.live_thread.is_alive()):
            self.notice = "paused"
        self.render()
        self.root.after(1500, self.refresh)

    def close(self):
        self.pause()
        if self.job and self.job.poll() is None:
            import ctypes

            buffer = ctypes.create_unicode_buffer(32768)
            length = ctypes.windll.kernel32.GetSystemDirectoryW(buffer, len(buffer))
            if not 0 < length < len(buffer):
                raise RuntimeError("Windows system directory could not be resolved")
            tool = str(Path(buffer.value) / "taskkill.exe")
            # Absolute system tool; PID belongs to this app's worker.
            subprocess.run(  # nosec B603
                [tool, "/PID", str(self.job.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        deadline = time.time() + 25

        def finish():
            if self.live_thread and self.live_thread.is_alive() and time.time() < deadline:
                self.root.after(200, finish)
            else:
                self.root.destroy()

        finish()


def main():
    if getattr(sys, "frozen", False):
        seed = Path(sys._MEIPASS) / "seed_data"
        (ROOT / "data").mkdir(exist_ok=True)
        if seed.exists():
            for file in seed.iterdir():
                if file.is_file() and not (ROOT / "data" / file.name).exists():
                    shutil.copy2(file, ROOT / "data" / file.name)
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        if sys.argv[2] not in ("fetch", "livebacktest", "paper"):
            return 2
        try:
            return worker(sys.argv[2])
        except Exception:
            return 1
    import msvcrt

    lock = (ROOT / ".trader.lock").open("a+b")
    lock.seek(0)
    if not lock.read(1):
        lock.write(b"0")
        lock.flush()
    lock.seek(0)
    try:
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        return 1
    root = tk.Tk()
    app = App(root)
    if "--smoke-test" in sys.argv:

        def smoke():
            report = {"frozen": bool(getattr(sys, "frozen", False)), "folder": str(ROOT)}
            app.set_language("tr")
            root.update_idletasks()
            report["turkish_title"] = root.title()
            report["turkish_buttons_fit"] = all(
                b.winfo_width() >= b.winfo_reqwidth() for b in app.action_buttons
            )
            app.navigate("guide")
            root.update_idletasks()
            app.navigate("ai_settings")
            root.update_idletasks()
            report["ai_settings_rendered"] = True
            app.set_language("en")
            app.navigate("dashboard")
            root.update_idletasks()
            report["english_buttons_fit"] = all(
                b.winfo_width() >= b.winfo_reqwidth() for b in app.action_buttons
            )
            report["real_trading_off"] = not app.authorized.get() and app.live_thread is None
            # This smoke check only runs local historical computation, never
            # account authentication or any mutation endpoint.
            app.run_job("livebacktest")
            process = app.job
            deadline = time.time() + 35

            def finished():
                if process.poll() is None and time.time() < deadline:
                    root.after(500, finished)
                    return
                report["backtest_exit_code"] = process.poll()
                (ROOT / "launch-check.json").write_text(json.dumps(report, indent=2))
                app.close()

            root.after(500, finished)

        root.after(1000, smoke)
    root.mainloop()
    lock.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
