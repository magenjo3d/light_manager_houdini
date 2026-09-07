try:
    from PySide6.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QComboBox, QListWidget,
        QMessageBox, QDoubleSpinBox, QSpinBox,
        QSlider, QCheckBox, QLineEdit, QScrollArea, QColorDialog,
        QFrame, QGroupBox, QDialogButtonBox, QStyle, QDialog, QButtonGroup,
        QTableWidget, QTableWidgetItem, QHeaderView, QGridLayout, QMenu,
    )
    from PySide6.QtCore import Qt, Signal, QEvent, QSize, QLocale, QTimer
    from PySide6.QtGui import QFont, QColor, QIcon
except ImportError:
    from PySide2.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QComboBox, QListWidget,
        QMessageBox, QDoubleSpinBox, QSpinBox,
        QSlider, QCheckBox, QLineEdit, QScrollArea, QColorDialog,
        QFrame, QGroupBox, QDialogButtonBox, QStyle, QDialog, QButtonGroup,
        QTableWidget, QTableWidgetItem, QHeaderView, QGridLayout, QMenu,
    )
    from PySide2.QtCore import Qt, Signal, QEvent, QSize, QLocale, QTimer
    from PySide2.QtGui import QFont, QColor, QIcon

import hou


class ROPManager(QWidget):
    WINDOW_NAME = "ROPManagerWindow"
    UNUSED_COLOR = (0.50, 0.50, 0.50)
    USED_LINK_COLORS = {
        "force": (0.20, 0.85, 0.20),
        "phantom": (0.90, 0.20, 0.20),
        "matte": (0.0, 0.0, 0.0),
        "exclude": (0.55, 0.35, 0.18),
        "candidate": (0.58, 0.36, 0.82),
    }

    def __init__(self, parent=None):
        super(ROPManager, self).__init__(parent, Qt.Tool)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle("ROP Manager")
        self._original_node_colors = {}
        self._current_rop_node = None
        self._row_property_parms = {}
        
        self.initUI()

    def initUI(self):
        self.main_layout = QHBoxLayout(self)

        self.content_widget = QWidget(self)
        content_layout = QVBoxLayout(self.content_widget)

        # ROP Type Selection
        rop_type_layout = QHBoxLayout()
        rop_type_label = QLabel("ROP Type:")
        self.rop_type_combo = QComboBox()
        self.rop_type_combo.addItems(["Arnold", "Mantra", "Karma"])
        rop_type_layout.addWidget(rop_type_label)
        rop_type_layout.addWidget(self.rop_type_combo)
        content_layout.addLayout(rop_type_layout)

        # ROP List
        self.rop_list = QListWidget()
        self.rop_list_hint = QLabel("Tip: Double-click on the ROP to jump inside")
        self.rop_list_hint.setStyleSheet("color: #9A9A9A;")
        content_layout.addWidget(self.rop_list_hint)
        content_layout.addWidget(self.rop_list)



        # Buttons
        button_layout = QHBoxLayout()
        add_button = QPushButton("Add ROP")
        remove_button = QPushButton("Remove ROP")
        update_button = QPushButton("Update List")
        button_layout.addWidget(add_button)
        button_layout.addWidget(remove_button)
        button_layout.addWidget(update_button)
        content_layout.addLayout(button_layout)

        self.main_layout.addWidget(self.content_widget, 2)

        self.details_toggle_button = QPushButton("◀")
        self.details_toggle_button.setToolTip("Show ROP details")
        self.details_toggle_button.setFixedWidth(24)
        self.details_toggle_button.clicked.connect(self.toggle_details_panel)
        self.main_layout.addWidget(self.details_toggle_button)

        self.details_panel = QFrame(self)
        self.details_panel.setFrameShape(QFrame.StyledPanel)
        self.details_panel.setMinimumWidth(320)
        self.details_panel.setMaximumWidth(16777215)
        self.details_panel.setVisible(False)

        details_layout = QGridLayout(self.details_panel)
        details_layout.setContentsMargins(6, 6, 6, 6)
        details_layout.addWidget(QLabel("Selected ROP Details"), 0, 0)

        self.rop_details_hint = QLabel("Tip: Right-click a Property or Value cell to quickly add or remove nodes")
        self.rop_details_hint.setStyleSheet("color: #9A9A9A;")
        details_layout.addWidget(self.rop_details_hint, 1, 0)

        self.rop_details_table = QTableWidget(0, 3, self.details_panel)
        self.rop_details_table.setHorizontalHeaderLabels(["Category", "Property", "Value"])
        self.rop_details_table.verticalHeader().setVisible(False)
        self.rop_details_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.rop_details_table.setSelectionMode(QTableWidget.NoSelection)
        self.rop_details_table.setWordWrap(True)
        self.rop_details_table.setAlternatingRowColors(True)
        self.rop_details_table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.rop_details_table.setStyleSheet(
            "QTableWidget { alternate-background-color: rgb(58, 58, 58); }"
        )
        self.rop_details_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.rop_details_table.customContextMenuRequested.connect(self._show_property_context_menu)
        self.rop_details_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.rop_details_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.rop_details_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.rop_details_table.horizontalHeader().setStretchLastSection(True)
        details_layout.addWidget(self.rop_details_table, 2, 0)
        details_layout.addWidget(self._build_color_legend_widget(), 3, 0)
        details_layout.setRowStretch(2, 1)
        details_layout.setColumnStretch(0, 1)

        self.main_layout.addWidget(self.details_panel, 3)


        # Connect signals
        add_button.clicked.connect(self.add_rop)
        remove_button.clicked.connect(self.remove_rop)
        update_button.clicked.connect(self.update_rop_list)
        self.show_existing_rops(hou.node("/"))
        self.rop_list.itemDoubleClicked.connect(self.select_rop)
        self.rop_list.currentItemChanged.connect(self.on_current_rop_changed)

        self.update_selected_rop_details(None)
        self.main_layout.setStretch(0, 1)
        self.main_layout.setStretch(2, 0)

    def toggle_details_panel(self):
        is_open = self.details_panel.isVisible()
        self.details_panel.setVisible(not is_open)
        self.details_toggle_button.setText("▶" if is_open else "◀")
        self.details_toggle_button.setToolTip("Show ROP details" if is_open else "Hide ROP details")
        if not is_open:
            self.main_layout.setStretch(0, 1)
            self.main_layout.setStretch(2, 2)
            self.resize(max(self.width(), 980), max(self.height(), 560))
            # Recompute sizes after layout settles to avoid oversized first render rows.
            QTimer.singleShot(0, self._auto_resize_details_table)
        else:
            self.main_layout.setStretch(0, 1)
            self.main_layout.setStretch(2, 0)

    def _build_color_legend_widget(self):
        legend_widget = QWidget(self.details_panel)
        legend_layout = QHBoxLayout(legend_widget)
        legend_layout.setContentsMargins(0, 2, 0, 0)
        legend_layout.setSpacing(8)

        def add_entry(label, rgb):
            entry = QWidget(legend_widget)
            entry_layout = QHBoxLayout(entry)
            entry_layout.setContentsMargins(0, 0, 0, 0)
            entry_layout.setSpacing(4)

            swatch = QLabel()
            swatch.setFixedSize(10, 10)
            swatch.setStyleSheet(
                "background-color: rgb({},{},{}); border: 1px solid #666;".format(
                    int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255)
                )
            )

            txt = QLabel(label)
            entry_layout.addWidget(swatch)
            entry_layout.addWidget(txt)
            legend_layout.addWidget(entry)

        add_entry("Forced", self.USED_LINK_COLORS["force"])
        add_entry("Phantom", self.USED_LINK_COLORS["phantom"])
        add_entry("Matte", self.USED_LINK_COLORS["matte"])
        add_entry("Exclude", self.USED_LINK_COLORS["exclude"])
        add_entry("Candidate", self.USED_LINK_COLORS["candidate"])
        add_entry("Unused", self.UNUSED_COLOR)
        legend_layout.addStretch()
        return legend_widget

    def _add_detail_row(self, category, prop, value, parm_names=None):
        row = self.rop_details_table.rowCount()
        self.rop_details_table.insertRow(row)

        category_item = QTableWidgetItem(str(category))
        prop_item = QTableWidgetItem(str(prop))
        value_item = QTableWidgetItem(str(value))

        base_color = self.rop_details_table.palette().base().color()
        row_shade = base_color.lighter(130) if (row % 2 == 0) else base_color.darker(78)

        category_item.setFlags(category_item.flags() & ~Qt.ItemIsEditable)
        prop_item.setFlags(prop_item.flags() & ~Qt.ItemIsEditable)
        value_item.setFlags(value_item.flags() & ~Qt.ItemIsEditable)
        category_item.setData(Qt.BackgroundRole, row_shade)
        prop_item.setData(Qt.BackgroundRole, row_shade)
        value_item.setData(Qt.BackgroundRole, row_shade)
        category_item.setBackground(row_shade)
        prop_item.setBackground(row_shade)
        value_item.setBackground(row_shade)

        self.rop_details_table.setItem(row, 0, category_item)
        self.rop_details_table.setItem(row, 1, prop_item)
        self.rop_details_table.setItem(row, 2, value_item)

        if parm_names:
            prop_item.setToolTip("Right-click this Property to add or remove selected Houdini nodes")
            self._row_property_parms[row] = list(parm_names)

    def _show_property_context_menu(self, pos):
        index = self.rop_details_table.indexAt(pos)
        if not index.isValid() or index.column() not in (1, 2):
            return

        parm_names = self._row_property_parms.get(index.row())
        if not parm_names:
            return

        menu = QMenu(self.rop_details_table)
        add_action = menu.addAction("Add Selected Nodes")
        remove_action = menu.addAction("Remove Selected Nodes")
        clear_action = menu.addAction("Clear All")

        global_pos = self.rop_details_table.viewport().mapToGlobal(pos)
        highlight_items = []
        original_look = []
        highlight_bg = QColor(255, 214, 64)
        highlight_fg = QColor(255, 215, 96)

        for col in (0, 1, 2):
            cell_item = self.rop_details_table.item(index.row(), col)
            if cell_item is None:
                continue
            highlight_items.append(cell_item)
            original_look.append((cell_item.background(), cell_item.foreground()))
            cell_item.setBackground(highlight_bg)
            cell_item.setForeground(highlight_fg)

        # Force paint so the highlight is visible before the context menu blocks UI updates.
        self.rop_details_table.viewport().update()
        QApplication.processEvents()

        try:
            chosen = menu.exec(global_pos)
        except AttributeError:
            chosen = menu.exec_(global_pos)
        finally:
            for cell_item, (bg, fg) in zip(highlight_items, original_look):
                cell_item.setBackground(bg)
                cell_item.setForeground(fg)
            self.rop_details_table.viewport().update()

        if chosen == add_action:
            self._add_selected_nodes_to_property(parm_names)
        elif chosen == remove_action:
            self._remove_selected_nodes_from_property(parm_names)
        elif chosen == clear_action:
            self._clear_property_nodes(parm_names)

    def _add_selected_nodes_to_property(self, parm_names):
        rop_node = self._current_rop_node
        if not rop_node:
            return

        selected_paths = [node.path() for node in hou.selectedNodes()]
        if not selected_paths:
            QMessageBox.information(self, "No Selection", "Select one or more Houdini nodes first.")
            return

        parm = self._first_existing_parm(rop_node, parm_names)
        if not parm:
            QMessageBox.warning(self, "Parameter Missing", "This ROP does not expose the selected property parameter.")
            return

        tokens = self._split_node_paths(self._read_parm_as_string(parm))
        merged = list(tokens)
        for path in selected_paths:
            if path not in merged:
                merged.append(path)

        parm.set(" ".join(merged))
        self.update_selected_rop_details(rop_node)

    def _remove_selected_nodes_from_property(self, parm_names):
        rop_node = self._current_rop_node
        if not rop_node:
            return

        selected_paths = {node.path() for node in hou.selectedNodes()}
        if not selected_paths:
            QMessageBox.information(self, "No Selection", "Select one or more Houdini nodes first.")
            return

        parm = self._first_existing_parm(rop_node, parm_names)
        if not parm:
            QMessageBox.warning(self, "Parameter Missing", "This ROP does not expose the selected property parameter.")
            return

        tokens = self._split_node_paths(self._read_parm_as_string(parm))
        kept_tokens = [token for token in tokens if token not in selected_paths]

        parm.set(" ".join(kept_tokens))
        self.update_selected_rop_details(rop_node)

    def _clear_property_nodes(self, parm_names):
        rop_node = self._current_rop_node
        if not rop_node:
            return

        parm = self._first_existing_parm(rop_node, parm_names)
        if not parm:
            QMessageBox.warning(self, "Parameter Missing", "This ROP does not expose the selected property parameter.")
            return

        parm.set("")
        self.update_selected_rop_details(rop_node)

    def _first_existing_parm_value(self, node, parm_names):
        for parm_name in parm_names:
            parm = node.parm(parm_name)
            if not parm:
                continue
            try:
                val = parm.eval()
            except Exception:
                val = parm.unexpandedString()
            if val not in (None, ""):
                return parm_name, val
        return None, ""

    def _first_existing_parm(self, node, parm_names):
        for parm_name in parm_names:
            parm = node.parm(parm_name)
            if parm:
                return parm
        return None

    def _read_parm_as_string(self, parm):
        try:
            return parm.evalAsString()
        except Exception:
            try:
                return str(parm.eval())
            except Exception:
                return parm.unexpandedString()

    def _split_node_paths(self, raw_value):
        if raw_value in (None, "", "-"):
            return []
        return [token for token in str(raw_value).split() if token]

    def _expand_token_to_nodes(self, token):
        if not token or token.startswith("^"):
            return []

        direct = hou.node(token)
        if direct:
            return [direct]

        resolved = []
        for root_path in ("/", "/obj", "/stage"):
            root = hou.node(root_path)
            if not root:
                continue
            try:
                matches = root.glob(token)
            except Exception:
                matches = ()
            for node in matches:
                if node is not None:
                    resolved.append(node)
            if resolved:
                break

        return resolved

    def _save_node_original_color(self, node):
        node_path = node.path()
        if node_path not in self._original_node_colors:
            self._original_node_colors[node_path] = node.color().rgb()

    def _restore_original_node_colors(self):
        for node_path, rgb in list(self._original_node_colors.items()):
            node = hou.node(node_path)
            if node:
                node.setColor(hou.Color(rgb))
        self._original_node_colors.clear()

    def _extract_linked_nodes(self, rop_node, parm_names):
        parm = self._first_existing_parm(rop_node, parm_names)
        if not parm:
            return []

        nodes = []
        seen = set()
        for token in self._split_node_paths(self._read_parm_as_string(parm)):
            for linked_node in self._expand_token_to_nodes(token):
                node_path = linked_node.path()
                if node_path in seen:
                    continue
                seen.add(node_path)
                nodes.append(linked_node)
        return nodes

    def _apply_selection_color_scheme(self, rop_node):
        if not rop_node:
            self._restore_original_node_colors()
            return

        selected_rop_path = rop_node.path()

        force_nodes = []
        force_nodes += self._extract_linked_nodes(rop_node, ["objects", "forceobject", "forceobjects", "forcedobjects", "forced_objects", "ar_force_objects"])
        force_nodes += self._extract_linked_nodes(rop_node, ["forcelights", "forcedlights", "forced_lights", "ar_force_lights"])

        phantom_nodes = []
        phantom_nodes += self._extract_linked_nodes(rop_node, ["phantom_objects", "phantom", "phantomobjects", "forcedphantom", "forced_phantom", "ar_force_phantom"])
        phantom_nodes += self._extract_linked_nodes(rop_node, ["phantomlights", "forcedphantomlights", "forced_phantom_lights", "ar_force_phantom_lights"])

        matte_nodes = []
        matte_nodes += self._extract_linked_nodes(rop_node, ["matte", "matte_objects", "forcematte", "forcematteobjects", "forcedmatte", "forced_matte", "ar_force_matte"])
        matte_nodes += self._extract_linked_nodes(rop_node, ["forcemattelights", "forcedmattelights", "forced_matte_lights", "ar_force_matte_lights"])

        exclude_nodes = []
        exclude_nodes += self._extract_linked_nodes(rop_node, ["excludeobject", "excludeobjects", "exclude_objects", "ar_exclude_objects"])
        exclude_nodes += self._extract_linked_nodes(rop_node, ["excludelights", "exclude_lights", "ar_exclude_lights"])

        candidate_nodes = []
        candidate_nodes += self._extract_linked_nodes(rop_node, ["candobjects", "candobject", "vobject", "candidateobjects", "candidate_objects", "ar_objects"])
        candidate_nodes += self._extract_linked_nodes(rop_node, ["alights", "candlights", "candidatelights", "candidate_lights", "ar_lights"])

        all_nodes = list(hou.node("/").allSubChildren())
        for node in all_nodes:
            self._save_node_original_color(node)
            node.setColor(hou.Color(self.UNUSED_COLOR))

        # Resolve overlaps with explicit priority: exclude > matte > phantom > force > candidate.
        color_priority = {
            "candidate": 1,
            "force": 2,
            "phantom": 3,
            "matte": 4,
            "exclude": 5,
        }

        node_best_color = {}
        node_best_priority = {}

        def register_nodes(nodes, color_key):
            priority = color_priority[color_key]
            for node in nodes:
                node_path = node.path()
                current_priority = node_best_priority.get(node_path, -1)
                if priority > current_priority:
                    node_best_priority[node_path] = priority
                    node_best_color[node_path] = self.USED_LINK_COLORS[color_key]

        register_nodes(candidate_nodes, "candidate")
        register_nodes(force_nodes, "force")
        register_nodes(phantom_nodes, "phantom")
        register_nodes(matte_nodes, "matte")
        register_nodes(exclude_nodes, "exclude")

        for node_path, rgb in node_best_color.items():
            linked_node = hou.node(node_path)
            if linked_node:
                linked_node.setColor(hou.Color(rgb))

        # Keep selected ROP readable and stable while the rest is colorized.
        selected_rgb = self._original_node_colors.get(selected_rop_path)
        if selected_rgb is not None:
            current_rop = hou.node(selected_rop_path)
            if current_rop:
                current_rop.setColor(hou.Color(selected_rgb))

    def _resolve_link_list_value(self, node, parm_names):
        parm_name, value = self._first_existing_parm_value(node, parm_names)
        if parm_name:
            return value
        return "-"

    def _add_linked_rows(self, rop_node, category, mapping):
        for label, parm_names in mapping:
            value = self._resolve_link_list_value(rop_node, parm_names)
            self._add_detail_row(category, label, value, parm_names=parm_names)

    def _auto_resize_details_table(self):
        self.rop_details_table.resizeColumnsToContents()
        self.rop_details_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

        # If the panel is hidden or not laid out yet, avoid wrap-based row overestimation.
        if not self.details_panel.isVisible() or self.rop_details_table.viewport().width() < 80:
            compact_height = max(22, self.rop_details_table.fontMetrics().height() + 8)
            for row in range(self.rop_details_table.rowCount()):
                self.rop_details_table.setRowHeight(row, compact_height)
            return

        self.rop_details_table.resizeRowsToContents()

    def update_selected_rop_details(self, rop_node):
        self._current_rop_node = rop_node
        self._row_property_parms.clear()
        self.rop_details_table.setRowCount(0)

        if rop_node is None:
            self._add_detail_row("Output", "Status", "No ROP selected")
            self._auto_resize_details_table()
            self._apply_selection_color_scheme(None)
            return

        for parm_name, label in (("f1", "Start"), ("f2", "End"), ("f3", "Step")):
            parm = rop_node.parm(parm_name)
            if parm:
                try:
                    self._add_detail_row("Frame Range", label, parm.eval())
                except Exception:
                    self._add_detail_row("Frame Range", label, parm.unexpandedString())

        out_parm, out_val = self._first_existing_parm_value(
            rop_node,
            ["ar_picture", "vm_picture", "picture", "sopoutput", "lopoutput"],
        )
        if out_parm:
            self._add_detail_row("Output", out_parm, out_val)

        object_links = [
            ("Candidate Objects", ["candobjects", "vobject", "candidateobjects", "candidate_objects", "ar_objects"]),
            ("Forced Objects", ["objects", "forceobject", "forceobjects", "forcedobjects", "forced_objects", "ar_force_objects"]),
            ("Forced Matte", ["matte", "matte_objects", "forcematte", "forcematteobjects", "forcedmatte", "forced_matte", "ar_force_matte"]),
            ("Forced Phantom", ["phantom_objects", "phantom", "phantomobjects", "forcedphantom", "forced_phantom", "ar_force_phantom"]),
            ("Exclude Objects", ["excludeobject", "excludeobjects", "exclude_objects", "ar_exclude_objects"]),
        ]
        self._add_linked_rows(rop_node, "Objects", object_links)

        light_links = [
            ("Solo Lights", ["sololight", "sololights", "sololight"]),
            ("Candidate Lights", ["alights", "candlights", "candidate_lights", "ar_lights"]),
            ("Forced Lights", ["forcelights", "forcedlights", "forced_lights", "ar_force_lights"]),
            ("Exclude Lights", ["excludelights", "exclude_lights", "ar_exclude_lights"]),
        ]
        self._add_linked_rows(rop_node, "Lights", light_links)
        self._auto_resize_details_table()
        self._apply_selection_color_scheme(rop_node)

    def on_current_rop_changed(self, current, _previous):
        if not current:
            self.update_selected_rop_details(None)
            return

        self.update_selected_rop_details(hou.node(current.text()))

    def select_rop(self, item):
        rop_name = item.text()
        rop_node = hou.node(rop_name)
        if rop_node:
            hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor).setCurrentNode(rop_node)
            self.update_selected_rop_details(rop_node)
        else:
            QMessageBox.warning(self, "ROP Not Found", f"Could not find ROP node: {rop_name}")
            self.update_selected_rop_details(None)

    def show_existing_rops(self, context):
        root = context.children()
        
        for child in root:
            self.show_existing_rops(child)
            if child.type().name() in ["ifd", "karma", "arnold"]:
                self.rop_list.addItem(child.path())
        
    def update_rop_list(self):
        self.rop_list.clear()
        self.show_existing_rops(hou.node("/"))
        self.update_selected_rop_details(None)

    def _ask_name_and_suffix(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("New ROP")

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Enter a name for the new ROP:"))

        name_field = QLineEdit(dialog)
        layout.addWidget(name_field)

        suffix_row = QHBoxLayout()
        suffix_row.addWidget(QLabel("Suffix:"))
        bty_check = QCheckBox("bty")
        shd_check = QCheckBox("shd")
        tech_check = QCheckBox("tech")
        bty_check.setChecked(True)

        suffix_group = QButtonGroup(dialog)
        suffix_group.setExclusive(True)
        suffix_group.addButton(bty_check)
        suffix_group.addButton(shd_check)
        suffix_group.addButton(tech_check)

        suffix_row.addWidget(bty_check)
        suffix_row.addWidget(shd_check)
        suffix_row.addWidget(tech_check)
        suffix_row.addStretch()
        layout.addLayout(suffix_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=dialog)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.Accepted:
            return None, None

        name = name_field.text().strip()
        if tech_check.isChecked():
            suffix = "tech"
        elif shd_check.isChecked():
            suffix = "shd"
        else:
            suffix = "bty"
        return name, suffix

    def add_rop(self):
        rop_type = self.rop_type_combo.currentText()
        text, suffix = self._ask_name_and_suffix()

        if text is None:
            return

        if text:
            rop_name = f"{text}_{suffix}"
        else:
            rop_name = f"{rop_type.lower()}"
        
        renderers = {
            "Arnold": "arnold",
            "Mantra": "ifd",
            "Karma": "karma"
        }
        
        rop_node = hou.node("/out").createNode(renderers[rop_type], rop_name)
        self.rop_list.addItem(rop_node.path())
        self.rop_list.setCurrentRow(self.rop_list.count() - 1)
        self.update_selected_rop_details(rop_node)
        hou.node("/out").layoutChildren()

    def remove_rop(self):
        selected_items = self.rop_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a ROP to remove.")
            return
        for item in selected_items:
            self.rop_list.takeItem(self.rop_list.row(item))
            rop_node = hou.node(item.text())
            if rop_node:
                rop_node.destroy()
                hou.node("/out").layoutChildren()

        current_item = self.rop_list.currentItem()
        self.on_current_rop_changed(current_item, None)

    def closeEvent(self, event):
        self._restore_original_node_colors()
        super(ROPManager, self).closeEvent(event)

_rop_manager_window = None


def create_rop_manager_window():
    global _rop_manager_window

    app = QApplication.instance()
    if app is not None:
        for widget in list(app.topLevelWidgets()):
            if widget.objectName() == ROPManager.WINDOW_NAME:
                try:
                    if widget.isVisible():
                        widget.raise_()
                        widget.activateWindow()
                        _rop_manager_window = widget
                        return widget
                    widget.close()
                except RuntimeError:
                    pass

    try:
        parent = hou.qt.mainWindow()
    except Exception:
        parent = None

    window = ROPManager(parent=parent)
    window.setObjectName(ROPManager.WINDOW_NAME)
    window.show()
    window.raise_()
    window.activateWindow()

    _rop_manager_window = window
    return window


create_rop_manager_window()