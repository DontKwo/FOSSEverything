"""Network Monitor workspace: live outbound connections, history, stats, per-app summary."""
from __future__ import annotations

import sqlite3
from typing import Optional

from PyQt6.QtCore import QDate, QPoint, Qt, QSettings, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDateEdit,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from app.features.network_monitor import db
from app.features.network_monitor.monitor import ConnectionMonitor, LiveConnection
from app.core.tooltips import get_tooltip_for

DEFAULT_POLL_INTERVAL_MS = 3000
DEFAULT_RETENTION_DAYS = 30
NEW_DESTINATION_COLOR = QColor(255, 235, 156)

LIVE_COLUMNS = [
    "Process", "PID", "Local Port", "Remote IP", "Remote Domain",
    "Remote Port", "Protocol", "Sent (process)", "Recv (process)", "First Seen",
]
HISTORY_COLUMNS = ["Timestamp", "Process", "PID", "Remote Domain", "Remote IP", "Remote Port", "Protocol", "New?"]
PER_APP_COLUMNS = ["Process", "Total Connections", "Unique Domains", "Last Seen"]
STATS_TABLE_COLUMNS = ["Name", "Connections"]


def _format_bytes(count: int) -> str:
    value = float(count)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


class _PollWorker(QThread):
    result_ready = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, monitor: ConnectionMonitor, parent: QThread | None = None) -> None:
        super().__init__(parent)
        self.monitor = monitor

    def run(self) -> None:
        try:
            connections: list[LiveConnection] = self.monitor.poll()
            self.result_ready.emit(connections)
        except Exception as exc:
            self.error.emit(str(exc))


class _LiveView(QWidget):
    def __init__(self, conn: sqlite3.Connection, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.conn = conn
        self._connections: list[LiveConnection] = []

        self.status_label = QLabel("Waiting for first poll...")

        self.table = QTableWidget(0, len(LIVE_COLUMNS))
        self.table.setHorizontalHeaderLabels(LIVE_COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        self.unknown_list = QListWidget()
        self.unknown_list.setMaximumWidth(260)
        mark_known_button = QPushButton("Mark selected as known")
        mark_known_button.setToolTip(get_tooltip_for("Mark destination as known"))
        mark_known_button.clicked.connect(self._mark_selected_known)

        side_panel = QWidget()
        side_layout = QVBoxLayout(side_panel)
        side_layout.addWidget(QLabel("New / unknown destinations"))
        side_layout.addWidget(self.unknown_list)
        side_layout.addWidget(mark_known_button)

        splitter = QSplitter()
        splitter.addWidget(self.table)
        splitter.addWidget(side_panel)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)

        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addWidget(splitter)

        self.refresh_unknown_list()

    def update_connections(self, connections: list[LiveConnection]) -> None:
        self._connections = connections
        self.table.setRowCount(len(connections))
        for row, item in enumerate(connections):
            values = [
                item.process_name,
                str(item.pid) if item.pid is not None else "",
                str(item.local_port) if item.local_port is not None else "",
                item.remote_ip,
                item.remote_domain or "",
                str(item.remote_port) if item.remote_port is not None else "",
                item.protocol,
                _format_bytes(item.bytes_sent),
                _format_bytes(item.bytes_recv),
                item.first_seen,
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if item.is_new_destination:
                    cell.setBackground(NEW_DESTINATION_COLOR)
                self.table.setItem(row, col, cell)

        new_count = sum(1 for c in connections if c.is_new_destination)
        self.status_label.setText(
            f"{len(connections)} active connection(s) - {new_count} to unknown destination(s)"
        )
        self.refresh_unknown_list()

    def refresh_unknown_list(self) -> None:
        self.unknown_list.clear()
        for row in db.unknown_destinations(self.conn):
            label = row["domain"] or row["ip"]
            list_item = QListWidgetItem(f"{label}  ({row['ip']})")
            list_item.setData(Qt.ItemDataRole.UserRole, row["ip"])
            self.unknown_list.addItem(list_item)

    def _mark_selected_known(self) -> None:
        known_ips = set()
        for list_item in self.unknown_list.selectedItems():
            ip = list_item.data(Qt.ItemDataRole.UserRole)
            db.mark_destination_known(self.conn, ip)
            known_ips.add(ip)
        for connection in self._connections:
            if connection.remote_ip in known_ips:
                connection.is_new_destination = False
        self.refresh_unknown_list()
        self.update_connections(self._connections)

    def _show_context_menu(self, position: QPoint) -> None:
        row = self.table.rowAt(position.y())
        if row < 0 or row >= len(self._connections):
            return
        connection = self._connections[row]
        menu = QMenu(self)
        action = menu.addAction(f"Mark {connection.remote_ip} as known")
        chosen = menu.exec(self.table.viewport().mapToGlobal(position))
        if chosen == action:
            db.mark_destination_known(self.conn, connection.remote_ip)
            connection.is_new_destination = False
            self.refresh_unknown_list()
            self.update_connections(self._connections)


class _HistoryView(QWidget):
    def __init__(self, conn: sqlite3.Connection, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.conn = conn

        self.process_input = QLineEdit()
        self.process_input.setPlaceholderText("Process name contains...")
        self.domain_input = QLineEdit()
        self.domain_input.setPlaceholderText("Domain or IP contains...")

        self.start_date = QDateEdit(calendarPopup=True)
        self.start_date.setDate(QDate.currentDate().addDays(-7))
        self.end_date = QDateEdit(calendarPopup=True)
        self.end_date.setDate(QDate.currentDate())

        search_button = QPushButton("Search")
        search_button.setToolTip(get_tooltip_for("Search connection history"))
        search_button.clicked.connect(self.run_search)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Process:"))
        filter_row.addWidget(self.process_input)
        filter_row.addWidget(QLabel("Domain/IP:"))
        filter_row.addWidget(self.domain_input)
        filter_row.addWidget(QLabel("From:"))
        filter_row.addWidget(self.start_date)
        filter_row.addWidget(QLabel("To:"))
        filter_row.addWidget(self.end_date)
        filter_row.addWidget(search_button)

        self.result_count_label = QLabel("")

        self.table = QTableWidget(0, len(HISTORY_COLUMNS))
        self.table.setHorizontalHeaderLabels(HISTORY_COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        layout = QVBoxLayout(self)
        layout.addLayout(filter_row)
        layout.addWidget(self.result_count_label)
        layout.addWidget(self.table)

        self.run_search()

    def run_search(self) -> None:
        start = self.start_date.date().toString("yyyy-MM-dd") + "T00:00:00"
        end = self.end_date.date().toString("yyyy-MM-dd") + "T23:59:59"
        rows = db.search_history(
            self.conn,
            process_name=self.process_input.text().strip(),
            domain=self.domain_input.text().strip(),
            start_date=start,
            end_date=end,
        )
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                row["timestamp"],
                row["process_name"] or "",
                str(row["pid"]) if row["pid"] is not None else "",
                row["remote_domain"] or "",
                row["remote_ip"] or "",
                str(row["remote_port"]) if row["remote_port"] is not None else "",
                row["protocol"] or "",
                "Yes" if row["is_new_destination"] else "",
            ]
            for col, value in enumerate(values):
                self.table.setItem(row_index, col, QTableWidgetItem(value))
        self.result_count_label.setText(f"{len(rows)} result(s)")


def _build_stats_table() -> QTableWidget:
    table = QTableWidget(0, len(STATS_TABLE_COLUMNS))
    table.setHorizontalHeaderLabels(STATS_TABLE_COLUMNS)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    return table


def _fill_stats_table(table: QTableWidget, rows: list, name_key: str, count_key: str) -> None:
    table.setRowCount(len(rows))
    for row_index, row in enumerate(rows):
        table.setItem(row_index, 0, QTableWidgetItem(str(row[name_key] or "")))
        table.setItem(row_index, 1, QTableWidgetItem(str(row[count_key])))


class _StatsView(QWidget):
    def __init__(self, conn: sqlite3.Connection, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.conn = conn

        self.top_processes_table = _build_stats_table()
        self.top_domains_table = _build_stats_table()

        tables_row = QHBoxLayout()
        processes_column = QVBoxLayout()
        processes_column.addWidget(QLabel("Top processes by connection count"))
        processes_column.addWidget(self.top_processes_table)
        domains_column = QVBoxLayout()
        domains_column.addWidget(QLabel("Top domains contacted"))
        domains_column.addWidget(self.top_domains_table)
        tables_row.addLayout(processes_column)
        tables_row.addLayout(domains_column)

        self.figure = Figure(figsize=(5, 2.5))
        self.canvas = FigureCanvasQTAgg(self.figure)

        refresh_button = QPushButton("Refresh stats")
        refresh_button.setToolTip(get_tooltip_for("Refresh network stats"))
        refresh_button.clicked.connect(self.refresh)

        layout = QVBoxLayout(self)
        layout.addLayout(tables_row)
        layout.addWidget(QLabel("Connections over time (last 30 days)"))
        layout.addWidget(self.canvas)
        layout.addWidget(refresh_button)

        self.refresh()

    def refresh(self) -> None:
        _fill_stats_table(self.top_processes_table, db.top_processes(self.conn), "process_name", "connection_count")
        _fill_stats_table(self.top_domains_table, db.top_domains(self.conn), "destination", "connection_count")

        rows = db.connections_over_time(self.conn, days=30)
        days = [row["day"] for row in rows]
        counts = [row["connection_count"] for row in rows]

        self.figure.clear()
        axes = self.figure.add_subplot(111)
        axes.plot(days, counts, marker="o")
        axes.set_ylabel("Connections")
        axes.tick_params(axis="x", labelrotation=45, labelsize=7)
        self.figure.tight_layout()
        self.canvas.draw()


class _PerAppView(QWidget):
    def __init__(self, conn: sqlite3.Connection, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.conn = conn

        self.table = QTableWidget(0, len(PER_APP_COLUMNS))
        self.table.setHorizontalHeaderLabels(PER_APP_COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        refresh_button = QPushButton("Refresh")
        refresh_button.setToolTip(get_tooltip_for("Refresh per-app summary"))
        refresh_button.clicked.connect(self.refresh)

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addWidget(refresh_button)

        self.refresh()

    def refresh(self) -> None:
        rows = db.per_app_summary(self.conn)
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                row["process_name"] or "",
                str(row["total_connections"]),
                str(row["unique_domains"]),
                row["last_seen"] or "",
            ]
            for col, value in enumerate(values):
                self.table.setItem(row_index, col, QTableWidgetItem(value))


class NetworkMonitorTab(QWidget):
    """Workspace tab: polls outbound connections and tracks history/stats per app."""

    def __init__(self, settings: Optional[QSettings] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.settings = settings if settings is not None else QSettings("FOSSEverything", "FOSSEverything")

        self.monitor = ConnectionMonitor()
        self.conn = db.connect()

        retention_days = int(self.settings.value("network_monitor/retention_days", DEFAULT_RETENTION_DAYS))
        pruned = db.prune_older_than(self.conn, retention_days)

        self.status_label = QLabel()
        visibility = "full" if self.monitor.has_admin_visibility() else "limited to your user account"
        status_text = f"Process visibility: {visibility}."
        if pruned:
            status_text += f" Pruned {pruned} record(s) older than {retention_days} days."
        self.status_label.setText(status_text)

        self.live_view = _LiveView(self.conn)
        self.history_view = _HistoryView(self.conn)
        self.stats_view = _StatsView(self.conn)
        self.per_app_view = _PerAppView(self.conn)

        self.inner_tabs = QTabWidget()
        self.inner_tabs.addTab(self.live_view, "Live Connections")
        self.inner_tabs.addTab(self.history_view, "History")
        self.inner_tabs.addTab(self.stats_view, "Stats")
        self.inner_tabs.addTab(self.per_app_view, "Per-App Summary")
        self.inner_tabs.currentChanged.connect(self._on_tab_changed)

        wipe_button = QPushButton("Wipe all history...")
        wipe_button.setToolTip(get_tooltip_for("Wipe network history"))
        wipe_button.clicked.connect(self._wipe_history)

        retention_button = QPushButton("Set retention period...")
        retention_button.setToolTip(get_tooltip_for("Set network retention period"))
        retention_button.clicked.connect(self._set_retention)

        toolbar_row = QHBoxLayout()
        toolbar_row.addWidget(wipe_button)
        toolbar_row.addWidget(retention_button)
        toolbar_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(toolbar_row)
        layout.addWidget(self.status_label)
        layout.addWidget(self.inner_tabs)

        self.poll_worker: _PollWorker | None = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._start_poll)
        self.timer.start(DEFAULT_POLL_INTERVAL_MS)
        self._start_poll()

    def _on_tab_changed(self, index: int) -> None:
        widget = self.inner_tabs.widget(index)
        if widget is self.history_view:
            self.history_view.run_search()
        elif widget is self.stats_view:
            self.stats_view.refresh()
        elif widget is self.per_app_view:
            self.per_app_view.refresh()

    def _start_poll(self) -> None:
        if self.poll_worker is not None and self.poll_worker.isRunning():
            return
        self.poll_worker = _PollWorker(self.monitor, parent=self)
        self.poll_worker.result_ready.connect(self._on_poll_result)
        self.poll_worker.error.connect(self._on_poll_error)
        self.poll_worker.start()

    def _on_poll_result(self, connections: list[LiveConnection]) -> None:
        self.live_view.update_connections(connections)

    def _on_poll_error(self, message: str) -> None:
        self.status_label.setText(f"Poll failed: {message}")

    def _wipe_history(self) -> None:
        choice = QMessageBox.question(
            self,
            "Wipe all history",
            "This permanently deletes all logged connections and known destinations.\n"
            f"Database file: {db.db_path()}\n\nContinue?",
        )
        if choice == QMessageBox.StandardButton.Yes:
            db.wipe_all(self.conn)
            self.history_view.run_search()
            self.stats_view.refresh()
            self.per_app_view.refresh()
            self.live_view.refresh_unknown_list()

    def _set_retention(self) -> None:
        current = int(self.settings.value("network_monitor/retention_days", DEFAULT_RETENTION_DAYS))
        days, ok = QInputDialog.getInt(
            self, "Retention period", "Keep history for this many days:", current, 1, 3650
        )
        if ok:
            self.settings.setValue("network_monitor/retention_days", days)
            pruned = db.prune_older_than(self.conn, days)
            self.status_label.setText(f"Retention set to {days} days. Pruned {pruned} record(s).")
