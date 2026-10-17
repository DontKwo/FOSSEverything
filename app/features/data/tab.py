"""Data Studio workspace: format, minify, validate, and convert JSON/YAML/CSV/XML."""
from __future__ import annotations

import json
import os
import yaml
from typing import Any, Dict, Optional, Tuple

from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QFont, QGuiApplication
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QTextEdit,
    QPushButton, QLabel, QFileDialog, QMessageBox, QGroupBox,
    QSplitter, QLineEdit, QInputDialog
)

from app.core.customizable_toolbar import AppToolBar
from app.core.spinbox import NoScrollSpinBox
from app.features.data import ops as data_ops
from app.core.theme import resolved_palette
from app.core.tooltips import get_tooltip_for
from app.ui.ui_scaling import scaled_font_size


class DataTab(QWidget):
    """Interactive workspace for formatting and converting structured data."""

    def __init__(self, parent: Optional[QWidget] = None, settings: Optional[QSettings] = None) -> None:
        super().__init__(parent)
        self.settings = settings if settings is not None else QSettings("FOSSEverything", "FOSSEverything")
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel("Data Studio")
        title.setStyleSheet("font-weight: 700;")
        root.addWidget(title)
        root.addWidget(QLabel("Format, pretty-print, minify, validate, and convert JSON, YAML, CSV, and XML."))

        toolbar = AppToolBar(self.settings, "data_toolbar")
        self.toolbar = toolbar
        root.addWidget(toolbar)

        toolbar.add_action("Open File...", self._open_file, tooltip_key="Open Data File")
        toolbar.add_action("Save File...", self._save_file, tooltip_key="Save Data File")
        toolbar.add_action("Copy", self._copy_to_clipboard)
        toolbar.addSeparator()

        toolbar.addWidget(QLabel("Format:"))
        self.fmt_combo = QComboBox()
        self.fmt_combo.addItems(["JSON", "YAML", "XML", "CSV", "SQL", "JavaScript", "CSS"])
        self.fmt_combo.setToolTip(get_tooltip_for("Data Format"))
        self.fmt_combo.currentTextChanged.connect(self._validate_text)
        toolbar.addWidget(self.fmt_combo)

        toolbar.addWidget(QLabel(" Indent:"))
        self.indent_spin = NoScrollSpinBox()
        self.indent_spin.setRange(1, 8)
        self.indent_spin.setValue(2)
        self.indent_spin.setToolTip(get_tooltip_for("Indent"))
        toolbar.addWidget(self.indent_spin)

        toolbar.add_action("Pretty Print / Format", self._format_data)
        toolbar.add_action("Minify", self._minify_data)
        toolbar.add_action("Validate Syntax", self._validate_text)
        toolbar.addSeparator()

        toolbar.addWidget(QLabel(" Convert To:"))
        self.convert_combo = QComboBox()
        self.convert_combo.addItems(["JSON", "YAML", "CSV"])
        self.convert_combo.setToolTip(get_tooltip_for("Convert To"))
        toolbar.addWidget(self.convert_combo)
        toolbar.add_action("Convert", self._convert_format, tooltip_key="Convert Data")
        toolbar.addSeparator()

        toolbar.add_action("Infer Schema", self._infer_schema)
        toolbar.add_action("Unit Convert", self._convert_units)
        toolbar.add_action("Random", self._generate_random_value)
        toolbar.add_action(".ics", self._generate_ics)
        toolbar.add_action("Import .ics", self._import_ics, tooltip_key="Import .ics")
        toolbar.add_action("Preview Markdown", self._render_markdown_preview)
        toolbar.add_action("Diff", self._diff_documents)
        toolbar.add_action("Grammar Check", self._grammar_check)
        toolbar.add_action("Citation", self._generate_citation)
        toolbar.add_action("Cron", self._open_cron_dialog)

        toolbar.finalize()

        # JSONPath Query Bar
        query_bar = QHBoxLayout()
        query_bar.addWidget(QLabel("JSONPath Query:"))
        self.query_edit = QLineEdit()
        self.query_edit.setPlaceholderText("e.g. $.tools[*], store.book[0].title, $..version, [(@.local_first == true)]")
        self.query_edit.returnPressed.connect(self._run_jsonpath_query)
        query_bar.addWidget(self.query_edit, stretch=1)
        run_query_btn = QPushButton("Evaluate Query")
        run_query_btn.setToolTip(get_tooltip_for("Evaluate Query"))
        run_query_btn.setStyleSheet("font-weight: 600;")
        run_query_btn.clicked.connect(self._run_jsonpath_query)
        query_bar.addWidget(run_query_btn)
        root.addLayout(query_bar)

        # Editor
        self.editor = QTextEdit()
        font = QFont("Courier New" if os.name == "nt" else "Monospace", scaled_font_size(11))
        self.editor.setFont(font)
        self.editor.setPlaceholderText("Paste or open JSON, YAML, XML, or CSV data here...")
        self.editor.clear()
        self.editor.textChanged.connect(self._on_editor_changed)
        root.addWidget(self.editor, stretch=1)

        # Status & Validation Bar
        self.status_bar = QLabel("Ready")
        colors = self._status_colors()
        self.status_bar.setStyleSheet(f"background: {colors['success_bg']}; color: {colors['success_text']}; padding: 6px 12px; border-radius: 6px; font-weight: 600;")
        root.addWidget(self.status_bar)

    def _status_colors(self) -> Dict[str, str]:
        palette = resolved_palette(self.settings)
        return {
            "success_bg": palette["panel"],
            "success_text": palette["success"],
            "error_bg": palette["panel"],
            "error_text": palette["danger"],
        }

    def _on_editor_changed(self) -> None:
        self._validate_text()

    def _validate_text(self) -> None:
        text = self.editor.toPlainText()
        fmt = self.fmt_combo.currentText()
        is_valid, msg, line = data_ops.validate_syntax(text, fmt)
        colors = self._status_colors()

        if is_valid:
            self.status_bar.setText(f"[OK] {msg}")
            self.status_bar.setStyleSheet(f"background: {colors['success_bg']}; color: {colors['success_text']}; padding: 6px 12px; border-radius: 6px; font-weight: 600;")
        else:
            line_str = f" (Line {line})" if line else ""
            self.status_bar.setText(f"[!] {msg}{line_str}")
            self.status_bar.setStyleSheet(f"background: {colors['error_bg']}; color: {colors['error_text']}; padding: 6px 12px; border-radius: 6px; font-weight: 600;")

    def _format_data(self) -> None:
        text = self.editor.toPlainText()
        fmt = self.fmt_combo.currentText().lower()
        indent = self.indent_spin.value()
        try:
            if fmt == "json":
                formatted = data_ops.format_json(text, indent=indent)
            elif fmt == "yaml":
                formatted = data_ops.format_yaml(text, indent=indent)
            elif fmt == "xml":
                formatted = data_ops.format_xml(text, indent=indent)
            elif fmt == "sql":
                formatted = data_ops.format_sql(text)
            elif fmt == "javascript":
                formatted = data_ops.format_javascript(text)
            elif fmt == "css":
                formatted = data_ops.format_css(text)
            else:
                formatted = text
            self.editor.setPlainText(formatted)
        except Exception as exc:
            QMessageBox.critical(self, "Formatting Error", str(exc))

    def _minify_data(self) -> None:
        text = self.editor.toPlainText()
        fmt = self.fmt_combo.currentText().lower()
        try:
            if fmt == "json":
                minified = data_ops.minify_json(text)
            elif fmt == "xml":
                minified = data_ops.minify_xml(text)
            elif fmt == "sql":
                minified = data_ops.minify_sql(text)
            elif fmt == "javascript":
                minified = data_ops.minify_javascript(text)
            elif fmt == "css":
                minified = data_ops.minify_css(text)
            else:
                minified = text
            self.editor.setPlainText(minified)
        except Exception as exc:
            QMessageBox.critical(self, "Minification Error", str(exc))

    def _convert_format(self) -> None:
        text = self.editor.toPlainText()
        from_fmt = self.fmt_combo.currentText()
        to_fmt = self.convert_combo.currentText()
        try:
            converted = data_ops.convert_data_format(text, from_fmt, to_fmt)
            self.editor.setPlainText(converted)
            self.fmt_combo.setCurrentText(to_fmt)
        except Exception as exc:
            QMessageBox.critical(self, "Conversion Error", str(exc))

    def _copy_to_clipboard(self) -> None:
        text = self.editor.toPlainText()
        QGuiApplication.clipboard().setText(text)
        QMessageBox.information(self, "Copied", "Content copied to clipboard!")

    def _open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Data File", "", "All Data Files (*.json *.yaml *.yml *.xml *.csv *.txt);;JSON (*.json);;YAML (*.yaml *.yml);;XML (*.xml);;CSV (*.csv)"
        )
        if not path:
            return
        self.load_file(path)

    def load_file(self, path: str) -> None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.editor.setPlainText(content)
            ext = path.split(".")[-1].lower()
            if ext == "json":
                self.fmt_combo.setCurrentText("JSON")
            elif ext in ("yaml", "yml"):
                self.fmt_combo.setCurrentText("YAML")
            elif ext == "xml":
                self.fmt_combo.setCurrentText("XML")
            elif ext == "csv":
                self.fmt_combo.setCurrentText("CSV")
        except Exception as exc:
            QMessageBox.critical(self, "Open Error", str(exc))

    def _save_file(self) -> None:
        fmt = self.fmt_combo.currentText().lower()
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Data File", f"data.{fmt}", f"{fmt.upper()} Files (*.{fmt});;All Files (*.*)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.editor.toPlainText())
            QMessageBox.information(self, "Saved", f"File saved to {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", str(exc))

    def _run_jsonpath_query(self) -> None:
        query = self.query_edit.text().strip()
        if not query:
            return
        text = self.editor.toPlainText()
        fmt = self.fmt_combo.currentText().lower()
        try:
            if fmt == "yaml":
                data = yaml.safe_load(text)
            else:
                data = json.loads(text)
            result = data_ops.query_jsonpath(data, query)
            formatted = json.dumps(result, indent=2, ensure_ascii=False)
            self.editor.setPlainText(formatted)
            self.fmt_combo.setCurrentText("JSON")
            self.status_bar.setText(f"[OK] JSONPath query executed: {query}")
            colors = self._status_colors()
            self.status_bar.setStyleSheet(f"background: {colors['success_bg']}; color: {colors['success_text']}; padding: 6px 12px; border-radius: 6px; font-weight: 600;")
        except Exception as exc:
            QMessageBox.critical(self, "Query Evaluation Failed", f"Could not evaluate JSONPath: {exc}")

    def _infer_schema(self) -> None:
        text = self.editor.toPlainText()
        fmt = self.fmt_combo.currentText().lower()
        try:
            if fmt == "yaml":
                data = yaml.safe_load(text)
            else:
                data = json.loads(text)
            schema = data_ops.infer_json_schema(data)
            formatted = json.dumps(schema, indent=2, ensure_ascii=False)
            self.editor.setPlainText(formatted)
            self.fmt_combo.setCurrentText("JSON")
            self.status_bar.setText("[OK] Inferred standard JSON Schema (Draft-07)")
            colors = self._status_colors()
            self.status_bar.setStyleSheet(f"background: {colors['success_bg']}; color: {colors['success_text']}; padding: 6px 12px; border-radius: 6px; font-weight: 600;")
        except Exception as exc:
            QMessageBox.critical(self, "Schema Inference Failed", f"Could not infer schema: {exc}")

    def _convert_units(self) -> None:
        categories = ["Length", "Weight", "Temperature", "Time", "Area", "Volume", "Speed", "Pressure", "Angle", "Data"]
        category, ok = QInputDialog.getItem(self, "Unit Converter", "Category:", categories, 0, False)
        if not ok:
            return
        value, ok = QInputDialog.getDouble(self, "Unit Converter", "Value:", 1.0, -1_000_000_000, 1_000_000_000, 6)
        if not ok:
            return
        from_unit, ok = QInputDialog.getText(self, "Unit Converter", "Convert from unit:", text="m")
        if not ok:
            return
        to_unit, ok = QInputDialog.getText(self, "Unit Converter", "Convert to unit:", text="km")
        if not ok:
            return
        try:
            result = data_ops.convert_units(float(value), from_unit.strip(), to_unit.strip(), category)
            self.editor.setPlainText(f"{value} {from_unit.strip()} = {result} {to_unit.strip()}\n")
            self.status_bar.setText("[OK] Unit conversion complete")
        except Exception as exc:
            QMessageBox.critical(self, "Unit Conversion Failed", str(exc))

    def _generate_random_value(self) -> None:
        kind, ok = QInputDialog.getItem(self, "Random Generator", "Type:", ["String", "Password", "Number", "UUID", "Name", "Email"], 0, False)
        if not ok:
            return
        kind_lower = kind.lower()
        length = 12
        if kind_lower in {"string", "password"}:
            length, ok = QInputDialog.getInt(self, "Random Generator", "Length:", 12, 1, 256, 1)
            if not ok:
                return
        min_value = 0
        max_value = 100
        if kind_lower == "number":
            min_value, ok = QInputDialog.getInt(self, "Random Generator", "Minimum value:", 0, -10_000_000, 10_000_000, 1)
            if not ok:
                return
            max_value, ok = QInputDialog.getInt(self, "Random Generator", "Maximum value:", 100, min_value, 10_000_000, 1)
            if not ok:
                return
        try:
            if kind_lower == "number":
                value = data_ops.generate_random_value(kind_lower, length, min_value=min_value, max_value=max_value, count=1)
            else:
                value = data_ops.generate_random_value(kind_lower, length)
            if isinstance(value, list):
                text = "\n".join(str(v) for v in value)
            else:
                text = str(value)
            self.editor.setPlainText(text)
            self.status_bar.setText("[OK] Random value generated")
        except Exception as exc:
            QMessageBox.critical(self, "Random Generation Failed", str(exc))

    def _generate_ics(self) -> None:
        summary, ok = QInputDialog.getText(self, ".ics Export", "Event summary:", text="Project review")
        if not ok:
            return
        start, ok = QInputDialog.getText(self, ".ics Export", "Start (YYYY-MM-DD HH:MM or ISO):", text="2026-09-01 09:00")
        if not ok:
            return
        end, ok = QInputDialog.getText(self, ".ics Export", "End (YYYY-MM-DD HH:MM or ISO):", text="2026-09-01 10:00")
        if not ok:
            return
        location, _ = QInputDialog.getText(self, ".ics Export", "Location (optional):", text="")
        description, _ = QInputDialog.getText(self, ".ics Export", "Description (optional):", text="")
        payload = data_ops.generate_ics([
            {
                "summary": summary,
                "start": start,
                "end": end,
                "location": location,
                "description": description,
            }
        ])
        self.editor.setPlainText(payload)
        self.status_bar.setText("[OK] .ics event generated")

    def _import_ics(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import .ics Calendar", "", "Calendar Files (*.ics);;All Files (*.*)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            events = data_ops.parse_ics(text)
        except Exception as exc:
            QMessageBox.critical(self, "Import Failed", str(exc))
            return
        if not events:
            QMessageBox.information(self, "Import .ics", "No events were found in that file.")
            return
        self.fmt_combo.setCurrentText("JSON")
        self.editor.setPlainText(json.dumps(events, indent=2))
        self.status_bar.setText(f"[OK] Imported {len(events)} event(s) from {os.path.basename(path)}")

    def _render_markdown_preview(self) -> None:
        text = self.editor.toPlainText()
        palette = resolved_palette(self.settings)
        preview_html = data_ops.render_markdown_preview(
            text,
            text_color=palette["text"],
            panel_color=palette["panel"],
            code_color=palette["button"],
            accent_color=palette["accent"],
            border_color=palette["border"],
        )
        box = QMessageBox(self)
        box.setWindowTitle("Markdown Preview")
        box.setTextFormat(Qt.RichText)
        box.setText(preview_html)
        box.setStandardButtons(QMessageBox.StandardButton.Close)
        box.exec()

    def _diff_documents(self) -> None:
        current_text = self.editor.toPlainText()
        clipboard_text = QGuiApplication.clipboard().text()
        if not clipboard_text:
            QMessageBox.information(self, "Document Diff", "No text found in the clipboard to compare.")
            return
        diff = data_ops.diff_documents(current_text, clipboard_text)
        result = diff["diff"] if diff["diff"] else "No differences found."
        self.editor.setPlainText(result)
        self.status_bar.setText(f"[OK] Diff complete: {diff['summary']['added']} added, {diff['summary']['removed']} removed")

    def _grammar_check(self) -> None:
        text = self.editor.toPlainText()
        title = "Grammar Check"
        result = data_ops.grammar_check_text_advanced(text) if data_ops.languagetool_backend_available() else None
        if result is not None and result.get("available"):
            title = "Grammar Check (LanguageTool)"
        else:
            result = data_ops.grammar_check_text(text)
        if not result["issues"]:
            QMessageBox.information(self, title, f"{result['summary']} (Score: {result['score']}/100)")
            return
        lines = [f"Score: {result['score']}/100", result["summary"], ""]
        lines.extend(f"- [{issue['type']}] {issue['message']}" for issue in result["issues"])
        QMessageBox.warning(self, title, "\n".join(lines))

    def _generate_citation(self) -> None:
        style, ok = QInputDialog.getItem(self, "Citation Generator", "Style:", ["APA", "MLA", "Chicago", "BibTeX"], 0, False)
        if not ok:
            return
        authors, ok = QInputDialog.getText(self, "Citation Generator", "Author(s), comma-separated:", text="Jane Doe")
        if not ok:
            return
        title, ok = QInputDialog.getText(self, "Citation Generator", "Title:", text="Untitled Work")
        if not ok:
            return
        year, ok = QInputDialog.getText(self, "Citation Generator", "Year:", text="2026")
        if not ok:
            return
        publisher, ok = QInputDialog.getText(self, "Citation Generator", "Publisher / Journal (optional):", text="")
        if not ok:
            return
        entry = {
            "authors": [a.strip() for a in authors.split(",") if a.strip()],
            "title": title,
            "year": year,
            "publisher": publisher,
        }
        citation = data_ops.generate_citation(entry, style=style.lower())
        prefix = "\n" if self.editor.toPlainText().strip() else ""
        self.editor.insertPlainText(f"{prefix}{citation}\n")
        self.status_bar.setText(f"[OK] {style} citation generated")

    def _open_cron_dialog(self) -> None:
        expression, ok = QInputDialog.getText(self, "Cron Expression", "Cron expression (minute hour day-of-month month day-of-week):", text="0 9 * * 1-5")
        if not ok or not expression.strip():
            return
        try:
            description = data_ops.describe_cron(expression)
            runs = data_ops.next_cron_runs(expression, count=5)
            run_lines = "\n".join(run.strftime("%Y-%m-%d %H:%M") for run in runs)
            QMessageBox.information(self, "Cron Expression", f"{description}\n\nNext runs:\n{run_lines}")
        except Exception as exc:
            QMessageBox.critical(self, "Cron Parsing Failed", str(exc))

