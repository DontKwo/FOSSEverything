"""File & Text Checksum workspace: compute and verify SHA-256, MD5, directory manifests."""
from __future__ import annotations

import json
import os
from typing import Optional, Tuple
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QObject, QSettings
from PyQt6.QtGui import QGuiApplication, QFont, QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QLineEdit,
    QTextEdit, QPushButton, QLabel, QFileDialog, QMessageBox, QGroupBox,
    QTabWidget, QCheckBox, QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QInputDialog
)
from app.core.customizable_toolbar import AppToolBar
from app.features.hash import ops as hash_ops
from app.core.theme import resolved_palette
from app.core.tooltips import get_tooltip_for
from app.ui.ui_scaling import scaled_font_pt, scaled_font_size


class _HashWorker(QObject):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, path: str, algorithms: list[str]) -> None:
        super().__init__()
        self.path = path
        self.algorithms = algorithms

    def run(self) -> None:
        try:
            results = hash_ops.multi_hash_file(self.path, self.algorithms)
            self.finished.emit(results)
        except Exception as exc:
            self.error.emit(str(exc))


class _DirHashWorker(QObject):
    progress = pyqtSignal(int, int, int, int)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, dir_path: str, algorithm: str) -> None:
        super().__init__()
        self.dir_path = dir_path
        self.algorithm = algorithm

    def run(self) -> None:
        try:
            res = hash_ops.hash_directory_tree(
                self.dir_path,
                algorithm=self.algorithm,
                progress_cb=lambda done, total, b_done, b_tot: self.progress.emit(done, total, b_done, b_tot)
            )
            self.finished.emit(res)
        except Exception as exc:
            self.error.emit(str(exc))


class HashTab(QWidget):
    """Interactive checksum and integrity verification workspace."""

    def __init__(self, parent: Optional[QWidget] = None, settings: Optional[QSettings] = None) -> None:
        super().__init__(parent)
        self.settings = settings if settings is not None else QSettings("FOSSEverything", "FOSSEverything")
        self.current_dir_hash_res: Optional[dict] = None
        self._build_ui()

    def _status_colors(self) -> Tuple[str, str]:
        palette = resolved_palette(self.settings)
        return palette["success"], palette["danger"]

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        title = QLabel("Hash & Checksum")
        title.setStyleSheet("font-weight: 700;")
        root.addWidget(title)
        root.addWidget(QLabel("Compute SHA-256, MD5, file hashes, and directory manifests locally. Zero cloud involvement."))

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_file_tab(), "File Hash")
        self.tabs.addTab(self._build_dir_tab(), "Directory Manifest")
        self.tabs.addTab(self._build_text_tab(), "Text Hash")
        self.tabs.addTab(self._build_compare_tab(), "Compare Files")
        self.tabs.addTab(self._build_verify_tab(), "Verify Hash")
        self.tabs.addTab(self._build_manifest_diff_tab(), "Manifest Diff")
        self.tabs.addTab(self._build_sign_policy_tab(), "Sign && Policy")
        root.addWidget(self.tabs, stretch=1)

    def load_file(self, file_path: str) -> None:
        """Route file directly to File Hash tab."""
        self.tabs.setCurrentIndex(0)
        self.file_path_edit.setText(file_path)
        size = os.path.getsize(file_path)
        self.file_size_label.setText(f"File size: {size:,} bytes ({size / (1024*1024):.2f} MB)")
        self._compute_file_hash()

    # ─── File Hash tab ───────────────────────────────────────────────────────
    def _build_file_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(12)

        file_box = QGroupBox("Select File")
        file_layout = QHBoxLayout(file_box)
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Select or drop a file...")
        browse_btn = QPushButton("Browse...")
        browse_btn.setToolTip(get_tooltip_for("Browse"))
        browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(self.file_path_edit, stretch=1)
        file_layout.addWidget(browse_btn)
        layout.addWidget(file_box)

        self.file_size_label = QLabel("")
        self.file_size_label.setStyleSheet(f"font-size: {scaled_font_pt(11)};")
        layout.addWidget(self.file_size_label)

        algo_box = QGroupBox("Algorithms to Compute")
        algo_layout = QHBoxLayout(algo_box)
        self.algo_checks = {}
        for algo in ["sha256", "md5", "sha1", "sha512", "blake2b"]:
            cb = QCheckBox(algo.upper())
            cb.setToolTip(get_tooltip_for(f"Include {algo.upper()} Checksum"))
            cb.setChecked(algo in ("sha256", "md5", "sha1"))
            self.algo_checks[algo] = cb
            algo_layout.addWidget(cb)
        layout.addWidget(algo_box)

        self.hash_btn = QPushButton("Compute Hashes")
        self.hash_btn.setToolTip(get_tooltip_for("Compute Hashes"))
        self.hash_btn.setStyleSheet("font-weight: 700; padding: 8px 16px;")
        self.hash_btn.clicked.connect(self._compute_file_hash)
        layout.addWidget(self.hash_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        res_box = QGroupBox("Checksum Results")
        res_form = QFormLayout(res_box)
        self.hash_results = {}
        for algo in ["sha256", "md5", "sha1", "sha512", "blake2b"]:
            row = QHBoxLayout()
            le = QLineEdit()
            le.setFont(QFont("Courier New", scaled_font_size(9)))
            le.setReadOnly(True)
            copy_btn = QPushButton("Copy")
            copy_btn.setToolTip(get_tooltip_for("Copy"))
            copy_btn.setFixedWidth(55)
            copy_btn.clicked.connect(lambda _, l=le: self._copy_value(l.text()))
            row.addWidget(le, stretch=1)
            row.addWidget(copy_btn)
            res_form.addRow(f"{algo.upper()}:", row)
            self.hash_results[algo] = le
        layout.addWidget(res_box, stretch=1)
        return w

    # ─── Directory Manifest Tab ──────────────────────────────────────────────
    def _build_dir_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(12)

        top_row = QHBoxLayout()
        self.dir_path_edit = QLineEdit()
        self.dir_path_edit.setPlaceholderText("Select a folder to hash recursively...")
        browse_dir_btn = QPushButton("Browse Folder...")
        browse_dir_btn.setToolTip(get_tooltip_for("Browse Folder"))
        browse_dir_btn.clicked.connect(self._browse_dir)
        top_row.addWidget(self.dir_path_edit, stretch=1)
        top_row.addWidget(browse_dir_btn)

        self.dir_algo_combo = QComboBox()
        self.dir_algo_combo.setToolTip(get_tooltip_for("Directory Hash Algorithm"))
        self.dir_algo_combo.addItems([a.upper() for a in hash_ops.SUPPORTED_ALGORITHMS])
        self.dir_algo_combo.setCurrentText("SHA256")
        top_row.addWidget(QLabel("Algorithm:"))
        top_row.addWidget(self.dir_algo_combo)

        hash_dir_btn = QPushButton("Hash Directory")
        hash_dir_btn.setToolTip(get_tooltip_for("Hash Directory"))
        hash_dir_btn.setStyleSheet("font-weight: 700; padding: 6px 14px;")
        hash_dir_btn.clicked.connect(self._run_hash_directory)
        top_row.addWidget(hash_dir_btn)

        verify_man_btn = QPushButton("Verify Manifest...")
        verify_man_btn.setToolTip(get_tooltip_for("Verify Manifest"))
        verify_man_btn.clicked.connect(self._verify_manifest_file)
        top_row.addWidget(verify_man_btn)

        layout.addLayout(top_row)

        self.dir_progress = QProgressBar()
        self.dir_progress.setVisible(False)
        layout.addWidget(self.dir_progress)

        self.dir_status_label = QLabel("No directory hashed yet.")
        self.dir_status_label.setStyleSheet("font-weight: 500;")
        layout.addWidget(self.dir_status_label)

        # Table of files
        self.dir_table = QTableWidget(0, 4)
        self.dir_table.setHorizontalHeaderLabels(["Status", "File Path", "Checksum Digest", "Size"])
        self.dir_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.dir_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.dir_table, stretch=1)

        bottom_toolbar = AppToolBar(self.settings, "hash_dir_results_toolbar")
        bottom_toolbar.add_action("Export Checksum Manifest (.sha256 / .txt)...", self._export_dir_manifest, tooltip_key="Export Checksum Manifest")
        bottom_toolbar.add_action("Copy All Hashes", self._copy_all_dir_hashes, tooltip_key="Copy All Hashes")
        bottom_toolbar.finalize()
        layout.addWidget(bottom_toolbar)

        return w

    # ─── Text Hash tab ───────────────────────────────────────────────────────
    def _build_text_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(12)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Algorithm:"))
        self.text_algo_combo = QComboBox()
        self.text_algo_combo.setToolTip(get_tooltip_for("Text Hash Algorithm"))
        self.text_algo_combo.addItems([a.upper() for a in hash_ops.SUPPORTED_ALGORITHMS])
        self.text_algo_combo.currentIndexChanged.connect(self._hash_text_live)
        top_row.addWidget(self.text_algo_combo)
        key_label = QLabel("HMAC key:")
        self.text_key_input = QLineEdit()
        self.text_key_input.setPlaceholderText("optional key for keyed hashing")
        self.text_key_input.textChanged.connect(self._hash_text_live)
        top_row.addWidget(key_label)
        top_row.addWidget(self.text_key_input, stretch=1)
        top_row.addStretch()
        layout.addLayout(top_row)

        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Type or paste text here to hash in real-time...")
        self.text_input.textChanged.connect(self._hash_text_live)
        layout.addWidget(self.text_input, stretch=1)

        res_box = QGroupBox("Digest")
        res_layout = QHBoxLayout(res_box)
        self.text_hash_result = QLineEdit()
        self.text_hash_result.setFont(QFont("Courier New", scaled_font_size(10)))
        self.text_hash_result.setReadOnly(True)
        copy_btn = QPushButton("Copy")
        copy_btn.setToolTip(get_tooltip_for("Copy"))
        copy_btn.clicked.connect(lambda: self._copy_value(self.text_hash_result.text()))
        res_layout.addWidget(self.text_hash_result, stretch=1)
        res_layout.addWidget(copy_btn)
        layout.addWidget(res_box)
        return w

    def _build_compare_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(12)

        form = QFormLayout()
        file_a_row = QHBoxLayout()
        self.compare_file_a = QLineEdit()
        self.compare_file_a.setPlaceholderText("Choose first file...")
        browse_a = QPushButton("Browse...")
        browse_a.setToolTip(get_tooltip_for("Browse File A"))
        browse_a.clicked.connect(lambda: self._browse_compare_file(0))
        file_a_row.addWidget(self.compare_file_a, stretch=1)
        file_a_row.addWidget(browse_a)
        form.addRow("File A:", file_a_row)

        file_b_row = QHBoxLayout()
        self.compare_file_b = QLineEdit()
        self.compare_file_b.setPlaceholderText("Choose second file...")
        browse_b = QPushButton("Browse...")
        browse_b.setToolTip(get_tooltip_for("Browse File B"))
        browse_b.clicked.connect(lambda: self._browse_compare_file(1))
        file_b_row.addWidget(self.compare_file_b, stretch=1)
        file_b_row.addWidget(browse_b)
        form.addRow("File B:", file_b_row)

        self.compare_algo = QComboBox()
        self.compare_algo.setToolTip(get_tooltip_for("Compare Algorithm"))
        self.compare_algo.addItems([a.upper() for a in hash_ops.SUPPORTED_ALGORITHMS])
        self.compare_algo.setCurrentText("SHA256")
        form.addRow("Algorithm:", self.compare_algo)
        layout.addLayout(form)

        compare_btn = QPushButton("Compare Files")
        compare_btn.setToolTip(get_tooltip_for("Compare Files"))
        compare_btn.clicked.connect(self._compare_files)
        compare_btn.setStyleSheet("font-weight: 700; padding: 8px 16px;")
        layout.addWidget(compare_btn)

        self.compare_results = QLabel("Waiting for two files to compare.")
        self.compare_results.setStyleSheet(f"font-size: {scaled_font_pt(16)}; font-weight: 700; padding: 10px;")
        self.compare_results.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.compare_results, stretch=1)
        return w

    # ─── Verify Hash tab ─────────────────────────────────────────────────────
    def _build_verify_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(14)

        verify_form = QFormLayout()
        verify_file_row = QHBoxLayout()
        self.verify_file = QLineEdit()
        self.verify_file.setPlaceholderText("Select file to verify...")
        browse_verify_btn = QPushButton("Browse...")
        browse_verify_btn.setToolTip(get_tooltip_for("Browse"))
        browse_verify_btn.clicked.connect(self._browse_verify_file)
        verify_file_row.addWidget(self.verify_file, stretch=1)
        verify_file_row.addWidget(browse_verify_btn)
        verify_form.addRow("File:", verify_file_row)

        self.verify_algo_combo = QComboBox()
        self.verify_algo_combo.setToolTip(get_tooltip_for("Verify Algorithm"))
        self.verify_algo_combo.addItems([a.upper() for a in hash_ops.SUPPORTED_ALGORITHMS])
        self.verify_algo_combo.setCurrentText("SHA256")
        verify_form.addRow("Algorithm:", self.verify_algo_combo)

        self.verify_expected = QLineEdit()
        self.verify_expected.setFont(QFont("Courier New", scaled_font_size(10)))
        self.verify_expected.setPlaceholderText("Paste the expected hash here...")
        verify_form.addRow("Expected hash:", self.verify_expected)
        layout.addLayout(verify_form)

        self.verify_btn = QPushButton("Verify Integrity")
        self.verify_btn.setToolTip(get_tooltip_for("Verify Manifest"))
        self.verify_btn.setStyleSheet("font-weight: 700; padding: 8px 16px;")
        self.verify_btn.clicked.connect(self._verify_hash)
        layout.addWidget(self.verify_btn)

        self.verify_result_label = QLabel("")
        self.verify_result_label.setStyleSheet(f"font-size: {scaled_font_pt(16)}; font-weight: 700; padding: 10px;")
        self.verify_result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.verify_result_label, stretch=1)
        return w

    # ─── Manifest Diff tab ───────────────────────────────────────────────────
    def _build_manifest_diff_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(12)

        form = QFormLayout()
        row_a = QHBoxLayout()
        self.diff_manifest_a = QLineEdit()
        self.diff_manifest_a.setPlaceholderText("Choose older/original manifest...")
        browse_a = QPushButton("Browse...")
        browse_a.clicked.connect(lambda: self._browse_diff_manifest(0))
        row_a.addWidget(self.diff_manifest_a, stretch=1)
        row_a.addWidget(browse_a)
        form.addRow("Manifest A (old):", row_a)

        row_b = QHBoxLayout()
        self.diff_manifest_b = QLineEdit()
        self.diff_manifest_b.setPlaceholderText("Choose newer/updated manifest...")
        browse_b = QPushButton("Browse...")
        browse_b.clicked.connect(lambda: self._browse_diff_manifest(1))
        row_b.addWidget(self.diff_manifest_b, stretch=1)
        row_b.addWidget(browse_b)
        form.addRow("Manifest B (new):", row_b)
        layout.addLayout(form)

        diff_btn = QPushButton("Compare Manifests")
        diff_btn.setToolTip(get_tooltip_for("Compare Manifests"))
        diff_btn.setStyleSheet("font-weight: 700; padding: 8px 16px;")
        diff_btn.clicked.connect(self._run_manifest_diff)
        layout.addWidget(diff_btn)

        self.diff_summary_label = QLabel("Choose two manifests to compare.")
        layout.addWidget(self.diff_summary_label)

        self.diff_table = QTableWidget(0, 3)
        self.diff_table.setHorizontalHeaderLabels(["Change", "File", "Detail"])
        self.diff_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.diff_table, stretch=1)
        return w

    # ─── Sign & Policy tab ───────────────────────────────────────────────────
    def _build_sign_policy_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(14)

        keys_box = QGroupBox("Signing Keypair (Ed25519)")
        keys_layout = QHBoxLayout(keys_box)
        gen_keys_btn = QPushButton("Generate Keypair...")
        gen_keys_btn.setToolTip(get_tooltip_for("Generate Keypair"))
        gen_keys_btn.clicked.connect(self._generate_keypair)
        keys_layout.addWidget(gen_keys_btn)
        self.keys_status_label = QLabel("No keypair generated yet.")
        keys_layout.addWidget(self.keys_status_label, stretch=1)
        layout.addWidget(keys_box)

        sign_box = QGroupBox("Sign a File")
        sign_form = QFormLayout(sign_box)
        sign_file_row = QHBoxLayout()
        self.sign_file_edit = QLineEdit()
        sign_browse = QPushButton("Browse...")
        sign_browse.setToolTip(get_tooltip_for("Browse File to Sign"))
        sign_browse.clicked.connect(self._browse_sign_file)
        sign_file_row.addWidget(self.sign_file_edit, stretch=1)
        sign_file_row.addWidget(sign_browse)
        sign_form.addRow("File to sign:", sign_file_row)

        priv_key_row = QHBoxLayout()
        self.sign_private_key_edit = QLineEdit()
        priv_browse = QPushButton("Browse...")
        priv_browse.setToolTip(get_tooltip_for("Browse Private Key"))
        priv_browse.clicked.connect(self._browse_private_key)
        priv_key_row.addWidget(self.sign_private_key_edit, stretch=1)
        priv_key_row.addWidget(priv_browse)
        sign_form.addRow("Private key (.pem):", priv_key_row)

        self.sign_signer_name_edit = QLineEdit()
        self.sign_signer_name_edit.setToolTip(get_tooltip_for("Signer Name"))
        sign_form.addRow("Signer name (optional):", self.sign_signer_name_edit)

        self.sign_timestamp_check = QCheckBox("Include local timestamp (multi-party bundle)")
        self.sign_timestamp_check.setToolTip(get_tooltip_for("Include Local Timestamp"))
        sign_form.addRow("", self.sign_timestamp_check)

        sign_btn = QPushButton("Sign File...")
        sign_btn.setToolTip(get_tooltip_for("Sign File"))
        sign_btn.clicked.connect(self._sign_file)
        sign_form.addRow("", sign_btn)
        layout.addWidget(sign_box)

        trusted_box = QGroupBox("Trusted Keys (local keyring)")
        trusted_layout = QVBoxLayout(trusted_box)
        trusted_combo_row = QHBoxLayout()
        self.trusted_key_combo = QComboBox()
        self.trusted_key_combo.setToolTip(get_tooltip_for("Trusted Key"))
        trusted_combo_row.addWidget(self.trusted_key_combo, stretch=1)
        add_trusted_btn = QPushButton("Add Trusted Key...")
        add_trusted_btn.setToolTip(get_tooltip_for("Add Trusted Key"))
        add_trusted_btn.clicked.connect(self._add_trusted_key)
        trusted_combo_row.addWidget(add_trusted_btn)
        remove_trusted_btn = QPushButton("Remove Selected")
        remove_trusted_btn.setToolTip(get_tooltip_for("Remove Trusted Key"))
        remove_trusted_btn.clicked.connect(self._remove_trusted_key)
        trusted_combo_row.addWidget(remove_trusted_btn)
        trusted_layout.addLayout(trusted_combo_row)
        trusted_layout.addWidget(QLabel("Select a trusted key above to use it for verification below instead of browsing a .pem file."))
        layout.addWidget(trusted_box)
        self._refresh_trusted_key_combo()

        verify_box = QGroupBox("Verify a Signature")
        verify_form = QFormLayout(verify_box)
        verify_file_row = QHBoxLayout()
        self.sig_verify_file_edit = QLineEdit()
        verify_file_browse = QPushButton("Browse...")
        verify_file_browse.setToolTip(get_tooltip_for("Browse File to Verify Signature"))
        verify_file_browse.clicked.connect(self._browse_sig_verify_file)
        verify_file_row.addWidget(self.sig_verify_file_edit, stretch=1)
        verify_file_row.addWidget(verify_file_browse)
        verify_form.addRow("File:", verify_file_row)

        sig_row = QHBoxLayout()
        self.sig_verify_sig_edit = QLineEdit()
        sig_browse = QPushButton("Browse...")
        sig_browse.setToolTip(get_tooltip_for("Browse Signature File"))
        sig_browse.clicked.connect(self._browse_signature_file)
        sig_row.addWidget(self.sig_verify_sig_edit, stretch=1)
        sig_row.addWidget(sig_browse)
        verify_form.addRow("Signature (.sig/.sigjson):", sig_row)

        self.verify_timestamped_check = QCheckBox("This is a timestamped bundle (.sigjson)")
        self.verify_timestamped_check.setToolTip(get_tooltip_for("Timestamped Bundle"))
        verify_form.addRow("", self.verify_timestamped_check)

        pub_key_row = QHBoxLayout()
        self.sig_verify_pubkey_edit = QLineEdit()
        pub_browse = QPushButton("Browse...")
        pub_browse.setToolTip(get_tooltip_for("Browse Public Key"))
        pub_browse.clicked.connect(self._browse_public_key)
        pub_key_row.addWidget(self.sig_verify_pubkey_edit, stretch=1)
        pub_key_row.addWidget(pub_browse)
        verify_form.addRow("Public key (.pem):", pub_key_row)
        verify_form.addRow("", QLabel("Leave the public key path blank to use the trusted key selected above instead."))

        verify_sig_btn = QPushButton("Verify Signature")
        verify_sig_btn.setToolTip(get_tooltip_for("Verify Signature"))
        verify_sig_btn.clicked.connect(self._verify_signature_action)
        verify_form.addRow("", verify_sig_btn)
        layout.addWidget(verify_box)

        policy_box = QGroupBox("Policy-Based Manifest Verification")
        policy_form = QFormLayout(policy_box)
        self.policy_combo = QComboBox()
        self.policy_combo.setToolTip(get_tooltip_for("Verification Policy"))
        for name, cfg in hash_ops.verification_policy_presets().items():
            self.policy_combo.addItem(f"{name} - {cfg['description']}", name)
        policy_form.addRow("Policy:", self.policy_combo)

        policy_manifest_row = QHBoxLayout()
        self.policy_manifest_edit = QLineEdit()
        policy_manifest_browse = QPushButton("Browse...")
        policy_manifest_browse.setToolTip(get_tooltip_for("Browse Policy Manifest"))
        policy_manifest_browse.clicked.connect(self._browse_policy_manifest)
        policy_manifest_row.addWidget(self.policy_manifest_edit, stretch=1)
        policy_manifest_row.addWidget(policy_manifest_browse)
        policy_form.addRow("Manifest:", policy_manifest_row)

        policy_sig_row = QHBoxLayout()
        self.policy_sig_edit = QLineEdit()
        policy_sig_browse = QPushButton("Browse...")
        policy_sig_browse.setToolTip(get_tooltip_for("Browse Policy Signature"))
        policy_sig_browse.clicked.connect(self._browse_policy_signature)
        policy_sig_row.addWidget(self.policy_sig_edit, stretch=1)
        policy_sig_row.addWidget(policy_sig_browse)
        policy_form.addRow("Signature (if required):", policy_sig_row)

        policy_pub_row = QHBoxLayout()
        self.policy_pubkey_edit = QLineEdit()
        policy_pub_browse = QPushButton("Browse...")
        policy_pub_browse.setToolTip(get_tooltip_for("Browse Policy Public Key"))
        policy_pub_browse.clicked.connect(self._browse_policy_pubkey)
        policy_pub_row.addWidget(self.policy_pubkey_edit, stretch=1)
        policy_pub_row.addWidget(policy_pub_browse)
        policy_form.addRow("Public key (if required):", policy_pub_row)

        apply_policy_btn = QPushButton("Verify Against Policy")
        apply_policy_btn.setToolTip(get_tooltip_for("Verify Against Policy"))
        apply_policy_btn.setStyleSheet("font-weight: 700; padding: 8px 16px;")
        apply_policy_btn.clicked.connect(self._apply_policy_verification)
        policy_form.addRow("", apply_policy_btn)
        layout.addWidget(policy_box)

        self.policy_result_label = QLabel("")
        layout.addWidget(self.policy_result_label, stretch=1)
        return w

    # ─── File Handlers ───────────────────────────────────────────────────────
    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select File to Hash", "", "All Files (*.*)")
        if path:
            self.file_path_edit.setText(path)
            size = os.path.getsize(path)
            self.file_size_label.setText(f"File size: {size:,} bytes ({size / (1024*1024):.2f} MB)")
            for le in self.hash_results.values():
                le.setText("")

    def _browse_verify_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select File to Verify", "", "All Files (*.*)")
        if path:
            self.verify_file.setText(path)

    def _compute_file_hash(self) -> None:
        path = self.file_path_edit.text()
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "No File", "Please select a valid file first.")
            return
        algos = [algo for algo, cb in self.algo_checks.items() if cb.isChecked()]
        if not algos:
            QMessageBox.warning(self, "No Algorithm", "Select at least one hash algorithm.")
            return

        self.hash_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        self._thread = QThread()
        self._worker = _HashWorker(path, algos)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_hash_finished)
        self._worker.error.connect(self._on_hash_error)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def _on_hash_finished(self, results: dict) -> None:
        self.hash_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        for algo, le in self.hash_results.items():
            le.setText(results.get(algo, ""))

    def _on_hash_error(self, msg: str) -> None:
        self.hash_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Hash Error", msg)

    # ─── Directory Manifest Handlers ─────────────────────────────────────────
    def _browse_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Folder to Hash Recursively")
        if path:
            self.dir_path_edit.setText(path)

    def _run_hash_directory(self) -> None:
        path = self.dir_path_edit.text().strip()
        if not path or not os.path.isdir(path):
            QMessageBox.warning(self, "Invalid Directory", "Please select a valid folder to hash.")
            return

        algo = self.dir_algo_combo.currentText().lower()
        self.dir_progress.setVisible(True)
        self.dir_progress.setValue(0)
        self.dir_status_label.setText(f"Scanning & hashing files in {os.path.basename(path)} with {algo.upper()}...")

        self._d_thread = QThread()
        self._d_worker = _DirHashWorker(path, algo)
        self._d_worker.moveToThread(self._d_thread)
        self._d_thread.started.connect(self._d_worker.run)
        self._d_worker.progress.connect(self._on_dir_progress)
        self._d_worker.finished.connect(self._on_dir_finished)
        self._d_worker.error.connect(self._on_dir_error)
        self._d_worker.finished.connect(self._d_thread.quit)
        self._d_thread.start()

    def _on_dir_progress(self, done: int, total: int, b_done: int, b_tot: int) -> None:
        if total > 0:
            self.dir_progress.setMaximum(total)
            self.dir_progress.setValue(done)
            mb_done = b_done / (1024 * 1024)
            self.dir_status_label.setText(f"Processed {done}/{total} files ({mb_done:.1f} MB)...")

    def _on_dir_finished(self, res: dict) -> None:
        self.current_dir_hash_res = res
        self.dir_progress.setVisible(False)
        tot_mb = res['total_bytes'] / (1024 * 1024)
        self.dir_status_label.setText(f"[OK] Completed: {res['total_files']} files hashed ({tot_mb:.2f} MB) using {res['algorithm'].upper()}")

        self.dir_table.setRowCount(len(res["files"]))
        for r, item in enumerate(res["files"]):
            success, danger = self._status_colors()
            status_item = QTableWidgetItem(item["status"])
            status_item.setForeground(QColor(success) if item["status"] == "OK" else QColor(danger))
            self.dir_table.setItem(r, 0, status_item)
            self.dir_table.setItem(r, 1, QTableWidgetItem(item["rel_path"]))
            hash_item = QTableWidgetItem(item["hash"])
            hash_item.setFont(QFont("Courier New", scaled_font_size(9)))
            self.dir_table.setItem(r, 2, hash_item)
            self.dir_table.setItem(r, 3, QTableWidgetItem(f"{item['size']:,} B"))

    def _on_dir_error(self, msg: str) -> None:
        self.dir_progress.setVisible(False)
        QMessageBox.critical(self, "Directory Hash Error", msg)

    def _export_dir_manifest(self) -> None:
        if not self.current_dir_hash_res or not self.current_dir_hash_res["files"]:
            QMessageBox.warning(self, "No Hashes", "Please hash a directory first.")
            return

        algo = self.current_dir_hash_res["algorithm"]
        default_name = f"manifest.{algo}"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Checksum Manifest", default_name,
            f"Checksum Manifest (*.{algo} *.txt);;All Files (*.*)"
        )
        if path:
            try:
                lines = [f"# Checksum manifest generated by FOSSEverything ({algo.upper()})"]
                for item in self.current_dir_hash_res["files"]:
                    if item["status"] == "OK":
                        lines.append(f"{item['hash']}  {item['rel_path']}")
                with open(path, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n")
                QMessageBox.information(self, "Manifest Saved", f"Saved manifest file to {path}")
            except Exception as exc:
                QMessageBox.critical(self, "Save Failed", str(exc))

    def _copy_all_dir_hashes(self) -> None:
        if not self.current_dir_hash_res or not self.current_dir_hash_res["files"]:
            return
        lines = [f"{item['hash']}  {item['rel_path']}" for item in self.current_dir_hash_res["files"] if item["status"] == "OK"]
        QGuiApplication.clipboard().setText("\n".join(lines))
        QMessageBox.information(self, "Copied", f"Copied {len(lines)} checksum lines to clipboard!")

    def _verify_manifest_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Checksum Manifest File", "",
            "Manifest Files (*.sha256 *.md5 *.sha1 *.sha512 *.txt);;All Files (*.*)"
        )
        if not path:
            return

        base_dir = os.path.dirname(path)
        reply = QMessageBox.question(
            self, "Base Directory",
            f"Verify files relative to the manifest directory\n{base_dir}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.No:
            chosen = QFileDialog.getExistingDirectory(self, "Select Base Directory of Files to Verify")
            if chosen:
                base_dir = chosen

        try:
            rep = hash_ops.verify_checksum_manifest(path, base_dir=base_dir)
            self.dir_table.setRowCount(len(rep["results"]))
            for r, item in enumerate(rep["results"]):
                status = item["status"]
                status_item = QTableWidgetItem(status)
                success, danger = self._status_colors()
                if status == "PASS":
                    status_item.setForeground(QColor(success))
                else:
                    status_item.setForeground(QColor(danger))
                self.dir_table.setItem(r, 0, status_item)
                self.dir_table.setItem(r, 1, QTableWidgetItem(item["rel_path"]))
                hash_item = QTableWidgetItem(item["actual"] or f"Expected: {item['expected']}")
                hash_item.setFont(QFont("Courier New", scaled_font_size(9)))
                self.dir_table.setItem(r, 2, hash_item)
                self.dir_table.setItem(r, 3, QTableWidgetItem(""))

            msg = (f"Manifest Verification Results:\n- Total: {rep['total']}\n"
                   f"- Passed: {rep['passed']}\n- Failed: {rep['failed']}\n"
                   f"- Missing: {rep['missing']}")
            if rep["failed"] == 0 and rep["missing"] == 0:
                self.dir_status_label.setText(
                    f"[OK] All {rep['passed']} files match the manifest checksums!")
                QMessageBox.information(self, "Verification Passed", msg)
            else:
                self.dir_status_label.setText(
                    f"[ERROR] Manifest errors: {rep['failed']} failed, {rep['missing']} missing.")
                QMessageBox.warning(self, "Verification Issues", msg)
        except Exception as exc:
            QMessageBox.critical(self, "Verification Error", str(exc))

    # ─── Text & Single Verify Handlers ───────────────────────────────────────
    def _hash_text_live(self) -> None:
        text = self.text_input.toPlainText()
        algo = self.text_algo_combo.currentText().lower()
        if not text:
            self.text_hash_result.setText("")
            return
        try:
            key = self.text_key_input.text().strip()
            if key:
                result = hash_ops.hmac_digest(text, key, algo)
            else:
                result = hash_ops.hash_text(text, algo)
            self.text_hash_result.setText(result)
        except Exception as exc:
            self.text_hash_result.setText(f"Error: {exc}")

    def _browse_compare_file(self, which: int) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select a file to compare", "", "All Files (*.*)")
        if not path:
            return
        if which == 0:
            self.compare_file_a.setText(path)
        else:
            self.compare_file_b.setText(path)

    def _compare_files(self) -> None:
        file_a = self.compare_file_a.text().strip()
        file_b = self.compare_file_b.text().strip()
        if not file_a or not file_b:
            QMessageBox.warning(self, "Missing files", "Select two files to compare.")
            return
        if not os.path.exists(file_a) or not os.path.exists(file_b):
            QMessageBox.warning(self, "Missing files", "Both files must exist on disk before comparing.")
            return
        try:
            same = hash_ops.compare_files(
                file_a, file_b, self.compare_algo.currentText().lower())
            success_color, danger_color = self._status_colors()
            if same:
                self.compare_results.setText(
                    "[MATCH] The files are identical for the selected algorithm.")
                style = (f"font-size: {scaled_font_pt(16)}; font-weight: 700; "
                         f"color: {success_color}; padding: 10px;")
                self.compare_results.setStyleSheet(style)
            else:
                self.compare_results.setText(
                    "[DIFFERENT] The files do not match for the selected algorithm.")
                style = (f"font-size: {scaled_font_pt(16)}; font-weight: 700; "
                         f"color: {danger_color}; padding: 10px;")
                self.compare_results.setStyleSheet(style)
        except Exception as exc:
            QMessageBox.critical(self, "Comparison Error", str(exc))

    def _verify_hash(self) -> None:
        path = self.verify_file.text()
        expected = self.verify_expected.text().strip()
        algo = self.verify_algo_combo.currentText().lower()
        if not path or not expected:
            QMessageBox.warning(self, "Missing Info", "Please provide both a file and an expected hash.")
            return
        try:
            match = hash_ops.verify_hash(path, expected, algo)
            success_color, danger_color = self._status_colors()
            if match:
                self.verify_result_label.setText(
                    "[OK] File is intact and matches the expected checksum.")
                style = (f"font-size: {scaled_font_pt(15)}; font-weight: 700; "
                         f"color: {success_color}; padding: 12px;")
                self.verify_result_label.setStyleSheet(style)
            else:
                self.verify_result_label.setText(
                    "[MISMATCH] File has been modified or the checksum is wrong.")
                style = (f"font-size: {scaled_font_pt(15)}; font-weight: 700; "
                         f"color: {danger_color}; padding: 12px;")
                self.verify_result_label.setStyleSheet(style)
        except Exception as exc:
            QMessageBox.critical(self, "Verification Error", str(exc))

    def _copy_value(self, text: str) -> None:
        if text:
            QGuiApplication.clipboard().setText(text)

    # ─── Manifest Diff Handlers ──────────────────────────────────────────────
    def _browse_diff_manifest(self, which: int) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Manifest File", "", "Manifest Files (*.sha256 *.md5 *.sha1 *.sha512 *.txt);;All Files (*.*)"
        )
        if not path:
            return
        if which == 0:
            self.diff_manifest_a.setText(path)
        else:
            self.diff_manifest_b.setText(path)

    def _run_manifest_diff(self) -> None:
        path_a = self.diff_manifest_a.text().strip()
        path_b = self.diff_manifest_b.text().strip()
        if not path_a or not path_b:
            QMessageBox.warning(self, "Missing Manifests", "Select both manifest files to compare.")
            return
        try:
            diff = hash_ops.diff_manifests(path_a, path_b)
        except Exception as exc:
            QMessageBox.critical(self, "Diff Failed", str(exc))
            return

        self.diff_summary_label.setText(
            f"Added: {len(diff['added'])}  |  Removed: {len(diff['removed'])}  |  "
            f"Changed: {len(diff['changed'])}  |  Unchanged: {diff['unchanged_count']}"
        )

        rows = []
        success, danger = self._status_colors()
        for rel in diff["added"]:
            rows.append(("ADDED", rel, "", success))
        for rel in diff["removed"]:
            rows.append(("REMOVED", rel, "", danger))
        for item in diff["changed"]:
            rows.append(("CHANGED", item["rel_path"], f"{item['old_hash']} -> {item['new_hash']}", danger))

        self.diff_table.setRowCount(len(rows))
        for r, (change, rel, detail, color) in enumerate(rows):
            change_item = QTableWidgetItem(change)
            change_item.setForeground(QColor(color))
            self.diff_table.setItem(r, 0, change_item)
            self.diff_table.setItem(r, 1, QTableWidgetItem(rel))
            self.diff_table.setItem(r, 2, QTableWidgetItem(detail))

    # ─── Content Signing Handlers ────────────────────────────────────────────
    def _generate_keypair(self) -> None:
        priv_path, _ = QFileDialog.getSaveFileName(self, "Save Private Key", "signing_key.pem", "PEM Key (*.pem)")
        if not priv_path:
            return
        pub_path, _ = QFileDialog.getSaveFileName(self, "Save Public Key", "signing_key.pub.pem", "PEM Key (*.pem)")
        if not pub_path:
            return
        try:
            hash_ops.save_signing_keypair(priv_path, pub_path)
            self.keys_status_label.setText(f"Keypair saved:\n{priv_path}\n{pub_path}")
            QMessageBox.information(self, "Keypair Generated", "Keep the private key secret; share only the public key.")
        except Exception as exc:
            QMessageBox.critical(self, "Key Generation Failed", str(exc))

    def _browse_sign_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select File to Sign", "", "All Files (*.*)")
        if path:
            self.sign_file_edit.setText(path)

    def _browse_private_key(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Private Key", "", "PEM Key (*.pem);;All Files (*.*)")
        if path:
            self.sign_private_key_edit.setText(path)

    def _sign_file(self) -> None:
        target = self.sign_file_edit.text().strip()
        key_path = self.sign_private_key_edit.text().strip()
        if not target or not key_path:
            QMessageBox.warning(self, "Missing Info", "Select a file and a private key.")
            return
        try:
            with open(key_path, "rb") as f:
                private_pem = f.read()
            if self.sign_timestamp_check.isChecked():
                signer_name = self.sign_signer_name_edit.text().strip() or None
                bundle = hash_ops.sign_file_with_timestamp(target, private_pem, signer_name=signer_name)
                out_path, _ = QFileDialog.getSaveFileName(self, "Save Timestamped Signature", target + ".sigjson", "Timestamped Signature (*.sigjson)")
                if out_path:
                    with open(out_path, "w", encoding="utf-8") as f:
                        json.dump(bundle, f, indent=2)
                    QMessageBox.information(self, "Signed", f"Timestamped signature saved to {out_path}\n(local attestation, not a third-party RFC 3161 timestamp)")
            else:
                signature = hash_ops.sign_file(target, private_pem)
                out_path, _ = QFileDialog.getSaveFileName(self, "Save Signature", target + ".sig", "Signature File (*.sig)")
                if out_path:
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(signature)
                    QMessageBox.information(self, "Signed", f"Signature saved to {out_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Signing Failed", str(exc))

    def _browse_sig_verify_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select File to Verify", "", "All Files (*.*)")
        if path:
            self.sig_verify_file_edit.setText(path)

    def _browse_signature_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Signature File", "", "Signature File (*.sig);;All Files (*.*)")
        if path:
            self.sig_verify_sig_edit.setText(path)

    def _browse_public_key(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Public Key", "", "PEM Key (*.pem);;All Files (*.*)")
        if path:
            self.sig_verify_pubkey_edit.setText(path)

    def _resolve_public_key_pem(self, pub_path: str) -> Optional[bytes]:
        """Return public key PEM bytes from an explicit path, or from the selected trusted key."""
        if pub_path:
            with open(pub_path, "rb") as f:
                return f.read()
        trusted_pem = self.trusted_key_combo.currentData()
        if trusted_pem:
            return trusted_pem.encode("utf-8")
        return None

    def _verify_signature_action(self) -> None:
        target = self.sig_verify_file_edit.text().strip()
        sig_path = self.sig_verify_sig_edit.text().strip()
        pub_path = self.sig_verify_pubkey_edit.text().strip()
        if not target or not sig_path:
            QMessageBox.warning(self, "Missing Info", "Select a file and its signature.")
            return
        try:
            public_pem = self._resolve_public_key_pem(pub_path)
            if not public_pem:
                QMessageBox.warning(self, "Missing Info", "Select a public key file or a trusted key.")
                return
            if self.verify_timestamped_check.isChecked():
                with open(sig_path, "r", encoding="utf-8") as f:
                    bundle = json.load(f)
                result = hash_ops.verify_timestamped_signature(bundle, public_pem, target)
                lines = [
                    f"Signature valid: {result['signature_valid']}",
                    f"File unchanged since signing: {result['hash_matches']}",
                    f"Timestamp: {result['timestamp']}",
                    f"Signer: {result['signer_name'] or '(unspecified)'}",
                ]
                if result["signature_valid"] and result["hash_matches"]:
                    QMessageBox.information(self, "Timestamped Signature Verified", "\n".join(lines))
                else:
                    QMessageBox.warning(self, "Timestamped Signature Problem", "\n".join(lines))
            else:
                with open(sig_path, "r", encoding="utf-8") as f:
                    signature_b64 = f.read().strip()
                valid = hash_ops.verify_signature(target, signature_b64, public_pem)
                if valid:
                    QMessageBox.information(self, "Signature Valid", "The signature matches this file and public key.")
                else:
                    QMessageBox.warning(self, "Signature Invalid", "The signature does not match this file and public key.")
        except Exception as exc:
            QMessageBox.critical(self, "Verification Failed", str(exc))

    # ─── Trusted-Key Handlers ────────────────────────────────────────────────
    def _refresh_trusted_key_combo(self) -> None:
        self.trusted_key_combo.clear()
        self.trusted_key_combo.addItem("(none selected)", "")
        for name, pem in sorted(hash_ops.list_trusted_keys().items()):
            self.trusted_key_combo.addItem(name, pem)

    def _add_trusted_key(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Public Key to Trust", "", "PEM Key (*.pem);;All Files (*.*)")
        if not path:
            return
        name, ok = QInputDialog.getText(self, "Name This Key", "Label for this trusted key (e.g. a signer's name):")
        if not ok or not name.strip():
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                public_pem = f.read()
            hash_ops.add_trusted_key(name.strip(), public_pem)
            self._refresh_trusted_key_combo()
        except Exception as exc:
            QMessageBox.critical(self, "Add Trusted Key Failed", str(exc))

    def _remove_trusted_key(self) -> None:
        name = self.trusted_key_combo.currentText()
        if not name or self.trusted_key_combo.currentData() == "":
            return
        hash_ops.remove_trusted_key(name)
        self._refresh_trusted_key_combo()

    # ─── Policy Verification Handlers ────────────────────────────────────────
    def _browse_policy_manifest(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Manifest File", "", "Manifest Files (*.sha256 *.md5 *.sha1 *.sha512 *.txt);;All Files (*.*)"
        )
        if path:
            self.policy_manifest_edit.setText(path)

    def _browse_policy_signature(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Signature File", "", "Signature File (*.sig);;All Files (*.*)")
        if path:
            self.policy_sig_edit.setText(path)

    def _browse_policy_pubkey(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Public Key", "", "PEM Key (*.pem);;All Files (*.*)")
        if path:
            self.policy_pubkey_edit.setText(path)

    def _apply_policy_verification(self) -> None:
        policy_name = self.policy_combo.currentData()
        manifest_path = self.policy_manifest_edit.text().strip()
        if not manifest_path:
            QMessageBox.warning(self, "Missing Manifest", "Select a manifest to verify.")
            return
        try:
            result = hash_ops.apply_verification_policy(
                policy_name,
                manifest_path,
                signature_path=self.policy_sig_edit.text().strip() or None,
                public_key_path=self.policy_pubkey_edit.text().strip() or None,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Policy Verification Failed", str(exc))
            return

        success, danger = self._status_colors()
        lines = [
            f"Policy: {policy_name}",
            f"Manifest: {result['passed']}/{result['total']} passed, {result['failed']} failed, {result['missing']} missing",
        ]
        overall_ok = result["failed"] == 0 and result["missing"] == 0
        if result["signature_required"]:
            lines.append(f"Signature: {'VALID' if result['signature_verified'] else 'INVALID/MISSING'}")
            overall_ok = overall_ok and bool(result["signature_verified"])
        color = success if overall_ok else danger
        self.policy_result_label.setText("\n".join(lines))
        self.policy_result_label.setStyleSheet(f"font-weight: 700; color: {color}; padding: 10px;")
