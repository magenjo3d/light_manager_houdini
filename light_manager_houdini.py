"""
Light Manager +
Houdini 20 - PySide2 UI
Miguel Agenjo, 3D Generalist / Lighting TD
www.miguelagenjo.com
"""

import os
import json
import math
import random
import tempfile
from pathlib import Path
from datetime import datetime

# Prefer PySide6, but keep PySide2 fallback for Houdini environments.
try:
    from PySide6.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QComboBox, QListWidget,
        QMessageBox, QDoubleSpinBox, QSpinBox,
        QSlider, QCheckBox, QLineEdit, QScrollArea, QColorDialog,
        QFrame, QGroupBox, QDialogButtonBox, QStyle,
    )
    from PySide6.QtCore import Qt, Signal, QEvent, QSize, QLocale
    from PySide6.QtGui import QFont, QColor, QIcon, QBrush
except ImportError:
    from PySide2.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QComboBox, QListWidget,
        QMessageBox, QDoubleSpinBox, QSpinBox,
        QSlider, QCheckBox, QLineEdit, QScrollArea, QColorDialog,
        QFrame, QGroupBox, QDialogButtonBox, QStyle,
    )
    from PySide2.QtCore import Qt, Signal, QEvent, QSize, QLocale
    from PySide2.QtGui import QFont, QColor, QIcon, QBrush

try:
    import hou
    HOU_AVAILABLE = True
except ImportError:
    HOU_AVAILABLE = False

ROP_MANAGER_PATH = r"/users/miag/Public/miag_rop_manager_module.py"


# ==================== Stylesheet ====================

DARK_STYLESHEET = """
    QWidget {
        background-color: #333333;
        color: #CCCCCC;
    }
    QLabel {
        color: #CCCCCC;
    }
    QPushButton {
        background-color: #4D4D4D;
        color: #CCCCCC;
        border: 1px solid #1A1A1A;
        border-radius: 3px;
        padding: 3px;
    }
    QPushButton:hover {
        background-color: #5D5D5D;
    }
    QPushButton:pressed {
        background-color: #3D3D3D;
    }
    QListWidget {
        background-color: #2A2A2A;
        color: #CCCCCC;
        border: 1px solid #1A1A1A;
    }
    QListWidget::item:selected {
        background-color: #555555;
    }
    QComboBox {
        background-color: #4D4D4D;
        color: #CCCCCC;
        border: 1px solid #1A1A1A;
        padding: 2px;
    }
    QTextEdit {
        background-color: #2A2A2A;
        color: #CCCCCC;
        border: 1px solid #1A1A1A;
        padding: 5px;
    }
    QLineEdit {
        background-color: #2A2A2A;
        color: #CCCCCC;
        border: 1px solid #1A1A1A;
        padding: 3px;
    }
    QTabWidget::pane {
        border: 1px solid #1A1A1A;
    }
    QTabBar::tab {
        background-color: #282828;
        color: #CCCCCC;
        padding: 5px 15px;
        margin-right: 2px;
    }
    QTabBar::tab:selected {
        background-color: #333333;
    }
    QDoubleSpinBox, QSpinBox {
        background-color: #2A2A2A;
        color: #CCCCCC;
        border: 1px solid #0A0A0A;
        padding: 2px;
    }
    QSlider::groove:horizontal {
        background-color: #2D2D2D;
        height: 6px;
        border-radius: 3px;
    }
    QSlider::handle:horizontal {
        background-color: #AAAAAA;
        width: 14px;
        margin: -4px 0;
        border-radius: 7px;
    }
    QCheckBox {
        color: #CCCCCC;
    }
    QScrollArea {
        border: none;
    }
"""


# ==================== Qt Helper Widgets ====================

class FloatFieldSlider(QWidget):
    """Float field + horizontal slider combination"""
    valueChanged = Signal(float)
    SLIDER_RESOLUTION = 10000

    def __init__(self, label="", value=0.0, min_val=0.0, max_val=1.0, decimals=3, parent=None):
        super().__init__(parent)
        self._min = min_val
        self._max = max_val

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        if label:
            lbl = QLabel(label)
            lbl.setMinimumWidth(90)
            layout.addWidget(lbl)

        self.field = QDoubleSpinBox()
        self.field.setLocale(QLocale.c())
        self.field.setRange(-1e9, 1e9)
        self.field.setDecimals(decimals)
        self.field.setValue(value)
        self.field.setMinimumWidth(65)
        layout.addWidget(self.field, 2)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, self.SLIDER_RESOLUTION)
        self.slider.setValue(self._value_to_slider(value))
        layout.addWidget(self.slider, 3)

        self.field.valueChanged.connect(self._on_field_changed)
        self.slider.valueChanged.connect(self._on_slider_changed)

    def _value_to_slider(self, value):
        value = max(self._min, min(self._max, value))
        if self._max == self._min:
            return 0
        return int((value - self._min) / (self._max - self._min) * self.SLIDER_RESOLUTION)

    def _slider_to_value(self, pos):
        return self._min + (pos / self.SLIDER_RESOLUTION) * (self._max - self._min)

    def _on_field_changed(self, v):
        self.slider.blockSignals(True)
        self.slider.setValue(self._value_to_slider(v))
        self.slider.blockSignals(False)
        self.valueChanged.emit(v)

    def _on_slider_changed(self, pos):
        v = self._slider_to_value(pos)
        self.field.blockSignals(True)
        self.field.setValue(v)
        self.field.blockSignals(False)
        self.valueChanged.emit(v)

    def value(self):
        return self.field.value()

    def setValue(self, v):
        self.field.setValue(v)


class IntFieldSlider(QWidget):
    """Integer field + horizontal slider combination"""
    valueChanged = Signal(int)

    def __init__(self, label="", value=0, min_val=0, max_val=10, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        if label:
            lbl = QLabel(label)
            lbl.setMinimumWidth(90)
            layout.addWidget(lbl)

        self.field = QSpinBox()
        self.field.setRange(min_val, max_val * 10)
        self.field.setValue(value)
        self.field.setMinimumWidth(50)
        layout.addWidget(self.field, 2)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(min_val, max_val)
        self.slider.setValue(value)
        layout.addWidget(self.slider, 3)

        self.field.valueChanged.connect(self._on_field_changed)
        self.slider.valueChanged.connect(self._on_slider_changed)

    def _on_field_changed(self, v):
        sv = max(self.slider.minimum(), min(self.slider.maximum(), v))
        self.slider.blockSignals(True)
        self.slider.setValue(sv)
        self.slider.blockSignals(False)
        self.valueChanged.emit(v)

    def _on_slider_changed(self, v):
        self.field.blockSignals(True)
        self.field.setValue(v)
        self.field.blockSignals(False)
        self.valueChanged.emit(v)

    def value(self):
        return self.field.value()

    def setValue(self, v):
        self.field.setValue(v)


class ColorButton(QPushButton):
    """Color swatch button that opens a color picker dialog"""
    colorChanged = Signal(float, float, float)

    def __init__(self, r=1.0, g=1.0, b=1.0, parent=None):
        super().__init__(parent)
        self._color = (r, g, b)
        self.setMinimumSize(60, 25)
        self._update_style()
        self.clicked.connect(self._pick_color)

    def _update_style(self):
        r, g, b = self._color
        self.setStyleSheet(
            f"QPushButton {{ background-color: rgb({int(r*255)},{int(g*255)},{int(b*255)}); "
            f"border: 1px solid #1A1A1A; min-width: 30px; min-height: 15px; }}"
            f"QPushButton:hover {{ background-color: rgb({int(r*255)},{int(g*255)},{int(b*255)}); "
            f"border: 1px solid #5D5D5D; }}"
            f"QPushButton:pressed {{ background-color: rgb({int(r*255)},{int(g*255)},{int(b*255)}); "
            f"border: 1px solid #AAAAAA; }}"
        )

    def _pick_color(self):
        r, g, b = self._color
        initial = QColor(int(r * 255), int(g * 255), int(b * 255))
        dialog = QColorDialog(initial, self)
        dialog.setWindowTitle("Pick Light Color")
        dialog.setStyleSheet(
            "QPushButton {"
            "  background-color: #4D4D4D;"
            "  color: #CCCCCC;"
            "  border: 1px solid #1A1A1A;"
            "  border-radius: 3px;"
            "  padding: 4px 10px;"
            "}"
            "QPushButton:hover { background-color: #4D4D4D; border: 1px solid #5D5D5D; }"
            "QPushButton:pressed { background-color: #4D4D4D; border: 1px solid #AAAAAA; }"
        )

        fixed_btn_style = (
            "QPushButton {"
            "  background-color: #4D4D4D;"
            "  color: #CCCCCC;"
            "  border: 1px solid #1A1A1A;"
            "  border-radius: 3px;"
            "  padding: 4px 10px;"
            "}"
            "QPushButton:hover { background-color: #4D4D4D; border: 1px solid #1A1A1A; }"
            "QPushButton:pressed { background-color: #4D4D4D; border: 1px solid #1A1A1A; }"
        )
        for button_box in dialog.findChildren(QDialogButtonBox):
            for button in button_box.buttons():
                button.setStyleSheet(fixed_btn_style)

        if dialog.exec() == QColorDialog.Accepted:
            color = dialog.selectedColor()
            self._color = (color.redF(), color.greenF(), color.blueF())
            self._update_style()
            self.colorChanged.emit(*self._color)

    def color(self):
        return self._color

    def setColor(self, r, g, b):
        self._color = (r, g, b)
        self._update_style()


# ==================== Houdini / HtoA Constants ====================

# Node type names that are treated as lights
ARNOLD_LIGHT_TYPES = ("arnold_light", "hlight", "hlight::2.0")

# HtoA arnold_light  light_type  menu indices (HtoA 7.x / Houdini 20)
LIGHT_TYPE_MAP = {
    "Point":       0,
    "Distant":     1,
    "Spot":        2,
    "Area":        3,   # quad_light
    "Disk":        4,
    "Cylinder":    5,
    "Environment": 6,   # skydome_light
    "Mesh Light":  7,
    "Photometric": 8,
}

# Arnold light parameters available as custom attrs in the combo
ARNOLD_ATTRS = [
    "ar_cone_angle", "ar_penumbra_angle", "ar_spread", "ar_roundness", "ar_soft_edge", "ar_angle",
    "ar_normalize", "ar_cast_shadows", "ar_shadow_density",
    "ar_camera", "ar_diffuse", "ar_specular", "ar_sss", "ar_volume", "ar_indirect"
]

# Default reset values
DEFAULT_VALUES = {
    "ar_intensity": 1.0,
    "ar_exposure": 0.0,
    "ar_samples": 1,
    "ar_color": (1.0, 1.0, 1.0),
    "ar_temperature": 4500.0,
    "ar_use_color_temperature": 0,
    "ar_cone_angle": 30.0,
    "ar_penumbra_angle": 0.0,
    "ar_spread": 1.0,
    "ar_roundness": 0.0,
    "ar_soft_edge": 0.0,
    "ar_normalize": 1,
    "ar_cast_shadows": 1,
    "ar_shadow_density": 1.0,
    "ar_camera": 1.0,
    "ar_diffuse": 1.0,
    "ar_specular": 1.0,
    "ar_sss": 1.0,
    "ar_volume": 1.0,
    "ar_indirect": 1.0,
}


# ==================== Light Manager Tab ====================

class LightManagerTab(QWidget):
    """Light Manager tab - Houdini 20 / HtoA PySide2 implementation"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._syncing_ui_from_selection = False
        self._isolate_original_inputs = {}
        self._isolate_button = None
        self._lights_isolated = False
        self._isolate_light_states = {}
        self._disabled_light_original_colors = {}
        self._backup_temp_file = Path(tempfile.gettempdir()) / "light_manager_houdini_state.json"
        print("Light Manager temp config:", str(self._backup_temp_file))
        self._build_ui()
        self._refresh_light_list()

    @staticmethod
    def _make_separator():
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #555555;")
        return line

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(3)

        self._build_toolbar(main_layout)

        content_layout = QHBoxLayout()

        # -- Left: Light list --
        left_layout = QVBoxLayout()

        list_top_row = QHBoxLayout()
        list_top_row.setSpacing(3)

        # Refresh button
        list_top_row.addWidget(
            self._icon_btn("BUTTONS_reload.svg", "Refresh light list", self._refresh_light_list))
        
        #Sanity check button
        list_top_row.addWidget(
            self._icon_btn("SHELF_enableconstraints.svg", "Sanity Check", self._sanity_check))

        #Isolate lights button
        self.btn_isolate_lights = self._icon_btn(
            "CHANNELS_dope_deselect_all.svg",
            "Isolate selected lights",
            lambda: None,
        )
        self.btn_isolate_lights.setCheckable(True)
        self.btn_isolate_lights.setStyleSheet(
            "QPushButton { background-color: #4D4D4D; border: 1px solid #1A1A1A; border-radius: 3px; }"
            "QPushButton:hover { background-color: #5D5D5D; }"
            "QPushButton:pressed { background-color: #3D3D3D; }"
            "QPushButton:checked { background-color: #2E7D32; border: 1px solid #9CCC65; }"
        )
        self.btn_isolate_lights.toggled.connect(self._toggle_isolate_selected_lights)
        list_top_row.addWidget(self.btn_isolate_lights)

        # Lights count label
        self.lights_count_label = QLabel("Lights: 0")
        list_top_row.addWidget(self.lights_count_label)
        list_top_row.addStretch()
        left_layout.addLayout(list_top_row)

        self.light_list = QListWidget()
        self.light_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.light_list.setMinimumWidth(140)
        self.light_list.installEventFilter(self)
        self.light_list.itemSelectionChanged.connect(self._on_list_selection_changed)
        left_layout.addWidget(self.light_list)

        self._build_backup_row(left_layout)

        content_layout.addLayout(left_layout, 1)

        # -- Right: scrollable controls area --
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 5, 5, 5)
        right_layout.setSpacing(4)

        self._build_selection_row(right_layout)
        right_layout.addWidget(self._make_separator())
        self._build_light_populator(right_layout)
        right_layout.addWidget(self._make_separator())
        self._build_light_attributes(right_layout)

        right_scroll.setWidget(right_widget)
        content_layout.addWidget(right_scroll, 3)

        main_layout.addLayout(content_layout)

    # ---- Section builders ----

    def _build_backup_row(self, parent_layout):
        row = QHBoxLayout()
        state_icon = None
        if HOU_AVAILABLE:
            try:
                snap_icon = hou.qt.Icon("BUTTONS_capture.svg")
                load_icon = hou.qt.Icon("BUTTONS_auto_save.svg")
            except Exception:
                state_icon = None
        if state_icon is None:
            state_icon = self.style().standardIcon(QStyle.SP_BrowserReload)


        btn_save_state = QPushButton(" Snap")
        btn_save_state.setIcon(snap_icon)
        btn_save_state.clicked.connect(self._save_state)
        row.addWidget(btn_save_state)

        btn_load_state = QPushButton(" Load")
        btn_load_state.setIcon(load_icon)
        btn_load_state.clicked.connect(self._load_state)
        row.addWidget(btn_load_state)

        parent_layout.addLayout(row)

    @staticmethod
    def _make_group_box(title):
        group = QGroupBox(title)
        group.setStyleSheet(
            "QGroupBox { "
            "  border: 1px solid #555555; border-radius: 4px; "
            "  margin-top: 10px; padding: 8px 4px 4px 4px; "
            "  font-weight: bold; color: #AAAAAA; "
            "} "
            "QGroupBox::title { "
            "  subcontrol-origin: margin; left: 8px; "
            "  padding: 0 4px; "
            "}"
        )
        return group

    @staticmethod
    def _icon_btn(icon_name, tooltip, callback, size=32, fallback_std_icon=None):
        """Create a QPushButton with a Houdini icon name and optional Qt fallback."""
        btn = QPushButton()
        icon = None

        if icon_name and HOU_AVAILABLE:
            try:
                icon = hou.qt.Icon(icon_name)
            except Exception:
                icon = None

        if icon is None and fallback_std_icon is not None:
            icon = QApplication.style().standardIcon(fallback_std_icon)

        if icon is not None:
            btn.setIcon(icon)
            btn.setIconSize(QSize(size, size))
        else:
            # Fallback: use the tooltip text as a short label
            short = tooltip[:3] if tooltip else "?"
            btn.setText(short)
        btn.setToolTip(tooltip)
        btn.setFixedSize(size + 10, size + 10)
        btn.setStyleSheet(
            "QPushButton { background-color: #4D4D4D; border: 1px solid #1A1A1A; border-radius: 3px; }"
            "QPushButton:hover { background-color: #5D5D5D; }"
            "QPushButton:pressed { background-color: #3D3D3D; }"
        )
        btn.clicked.connect(callback)
        return btn

    def _build_toolbar(self, parent_layout):
        lbl = QLabel("Utils Shelf")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("background-color: #4A4A4A; padding: 3px;")
        parent_layout.addWidget(lbl)

        shelf_layout = QHBoxLayout()
        shelf_layout.setSpacing(6)

        # --- Group 1: Arnold Lights ---
        karma_group = self._make_group_box("Arnold Lights")
        karma_row = QHBoxLayout(karma_group)
        karma_row.setSpacing(3)

        karma_btns = [
            ("Area Light",    "OBJ_light_area",       self._create_area_light),
            ("Env Light",     "OBJ_light_environment",    self._create_env_light),
            ("Point Light",   "OBJ_light_point",       self._create_point_light),
            ("Spot Light",    "OBJ_light_spot",   self._create_spot_light),
            ("Distant Light", "OBJ_light_directional", self._create_distant_light),
            ("Photometric Light", "OBJ_hlight", self._create_photometric_light),
            ("Cylinder Light",  "OBJ_light_fluorescent",        self._create_cylinder_light),
            ("Disk Light",      "OBJ_light_disk",        self._create_disk_light),
            #("Mesh Light",      "OBJ_light_geo",        self._create_mesh_light),
        ]
        for label, icon_name, func in karma_btns:
            btn = QPushButton()
            btn.setToolTip(label)
            btn.setFixedSize(42, 42)
            btn.setStyleSheet(
                "QPushButton { background-color: #4D4D4D; border: 1px solid #1A1A1A; border-radius: 3px; }"
                "QPushButton:hover { background-color: #5D5D5D; }"
                "QPushButton:pressed { background-color: #3D3D3D; }"
            )
            icon = None
            if HOU_AVAILABLE:
                try:
                    icon = hou.qt.Icon(icon_name)
                except Exception:
                    pass
            if icon:
                btn.setIcon(icon)
                btn.setIconSize(QSize(26, 26))
            else:
                btn.setText(label[:4])
            btn.clicked.connect(func)
            karma_row.addWidget(btn)

        shelf_layout.addWidget(karma_group)

        # --- Group 2: Utils ---
        utils_group = self._make_group_box("Utils")
        utils_row = QHBoxLayout(utils_group)
        utils_row.setSpacing(3)

        utils_btns = [
            ("ROP Create",     "ROP_arnold",          self._create_arnold_rop),
            ("ROP manager", "BUTTONS_render",       self._open_render_settings),
            ("Isolate Texture", "BUTTONS_texture_only_show_groups.svg",       self._isolate_render_view)
        ]
        for label, icon_name, func in utils_btns:
            btn = QPushButton()
            if label == "Isolate Texture":
                btn.setCheckable(True)          # ON/OFF mode
                btn.setChecked(False)           # starts OFF
                self._isolate_button = btn
                
            btn.setToolTip(label)
            btn.setFixedSize(42, 42)
            btn.setStyleSheet(
                "QPushButton { background-color: #4D4D4D; border: 1px solid #1A1A1A; border-radius: 3px; }"
                "QPushButton:hover { background-color: #5D5D5D; }"
                "QPushButton:pressed { background-color: #3D3D3D; }"
                "QPushButton:checked {"
                "    background-color: #2E7D32;   /* active */"
                "    border: 1px solid #9CCC65;"
                "}"
            )
            icon = None
            if HOU_AVAILABLE:
                try:
                    icon = hou.qt.Icon(icon_name)
                except Exception:
                    pass
            if icon:
                btn.setIcon(icon)
                btn.setIconSize(QSize(26, 26))
            else:
                btn.setText(label[:4])
            if label == "Isolate Texture":
                btn.toggled.connect(func)
            else:
                btn.clicked.connect(func)
            utils_row.addWidget(btn)

        shelf_layout.addWidget(utils_group)

        parent_layout.addLayout(shelf_layout)

    def reset_isolate_button(self):
        """Clear isolate mode and restore pre-isolate enable states when needed."""
        if self._lights_isolated:
            try:
                for node in self._get_all_light_nodes():
                    if node.path() in self._isolate_light_states:
                        self._set_light_enabled(node, self._isolate_light_states[node.path()])
            except Exception:
                pass

        # Close-time safety: always restore texture isolate wiring explicitly.
        self._restore_isolated_material_inputs()

        self._lights_isolated = False
        self._isolate_light_states = {}

        if self._isolate_button and self._isolate_button.isChecked():
            self._isolate_button.blockSignals(True)
            self._isolate_button.setChecked(False)
            self._isolate_button.blockSignals(False)

        if hasattr(self, "btn_isolate_lights") and self.btn_isolate_lights is not None:
            self.btn_isolate_lights.blockSignals(True)
            self.btn_isolate_lights.setChecked(False)
            self.btn_isolate_lights.blockSignals(False)

    def on_window_closing(self):
        """Backward-compatible alias for close callback behavior."""
        self.reset_isolate_button()

    def _restore_isolated_material_inputs(self):
        """Restore all cached arnold_material input(0) connections for texture isolate mode."""
        if not HOU_AVAILABLE:
            self._isolate_original_inputs = {}
            return

        for material_path, original_path in list(self._isolate_original_inputs.items()):
            try:
                material_node = hou.node(material_path)
                if material_node is None:
                    continue
                original_node = hou.node(original_path) if original_path else None
                material_node.setInput(0, original_node)
            except Exception:
                pass

        self._isolate_original_inputs = {}

    def _build_selection_row(self, parent_layout):
        row = QHBoxLayout()

        btn_select_all = QPushButton("Select All Lights")
        btn_select_all.setMinimumHeight(30)
        btn_select_all.setStyleSheet("background-color: #006633;")
        btn_select_all.clicked.connect(self._select_all_lights)
        row.addWidget(btn_select_all)

        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Search by name...")
        self.search_field.returnPressed.connect(self._select_by_name)
        row.addWidget(self.search_field, 1)

        btn_search = QPushButton("Select by name")
        btn_search.clicked.connect(self._select_by_name)
        row.addWidget(btn_search)

        parent_layout.addLayout(row)

    def _build_light_populator(self, parent_layout):
        lbl = QLabel("Light Populator")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("background-color: #4A4A4A; padding: 3px;")
        lbl.setFixedHeight(20)
        parent_layout.addWidget(lbl)

        row = QHBoxLayout()

        row.addWidget(QLabel("Light Type:"))
        self.light_type_combo = QComboBox()
        self.light_type_combo.addItems(["Point", "Area", "Spot", "Photometric", "Mesh"])
        row.addWidget(self.light_type_combo)

        self.parent_check = QCheckBox("Parent to Object")
        row.addWidget(self.parent_check)

        self.locator_check = QCheckBox("Locator")
        self.locator_check.setChecked(True)
        row.addWidget(self.locator_check)

        btn_populate = QPushButton("Populate")
        btn_populate.clicked.connect(self._populate_lights)
        row.addWidget(btn_populate)

        parent_layout.addLayout(row)

    def _build_light_attributes(self, parent_layout):
        lbl = QLabel("Light Attributes")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("background-color: #4A4A4A; padding: 3px;")
        lbl.setFixedHeight(20)
        parent_layout.addWidget(lbl)

        # -- Color row --
        color_row = QHBoxLayout()
        color_row.addWidget(QLabel("Color"))

        self.color_btn = ColorButton()
        self.color_btn.colorChanged.connect(self._on_color_changed)
        color_row.addWidget(self.color_btn)

        btn_key_color = QPushButton("Key")
        btn_key_color.setStyleSheet("background-color: #4D1A1A;")
        btn_key_color.setMaximumWidth(26)
        btn_key_color.clicked.connect(lambda: self._key_parm("ar_color"))
        color_row.addWidget(btn_key_color)

        folder_icon = self.style().standardIcon(QStyle.SP_DirOpenIcon)
        btn_browse_file = QPushButton()
        btn_browse_file.setIcon(folder_icon)
        btn_browse_file.setToolTip("Browse File")
        btn_browse_file.setMaximumWidth(32)
        btn_browse_file.clicked.connect(self._browse_color_file)
        color_row.addWidget(btn_browse_file)

        btn_disconnect = QPushButton("Disconnect")
        btn_disconnect.clicked.connect(self._disconnect_files)
        color_row.addWidget(btn_disconnect)
        random_icon = None
        if HOU_AVAILABLE:
            try:
                random_icon = hou.qt.Icon("VOP_random.svg")
            except Exception:
                random_icon = None
        if random_icon is None:
            random_icon = self.style().standardIcon(QStyle.SP_BrowserReload)

        btn_random_color = QPushButton(" Random")
        btn_random_color.setIcon(random_icon)
        btn_random_color.clicked.connect(self._random_color)
        color_row.addWidget(btn_random_color)

        parent_layout.addLayout(color_row)

        # -- Temperature row --
        temp_row = QHBoxLayout()
        self.temp_slider = FloatFieldSlider("Temperature (K)", value=4500, min_val=1000, max_val=15000, decimals=0)
        self.temp_slider.valueChanged.connect(self._on_temperature_changed)
        temp_row.addWidget(self.temp_slider, 1)

        self.temp_check = QCheckBox("on/off")
        self.temp_check.setToolTip("When ON, Temperature updates ar_color. When OFF, only ar_temperature is updated.")
        self.temp_check.setChecked(False)
        temp_row.addWidget(self.temp_check)

        parent_layout.addLayout(temp_row)

        # -- Photometric file row --
        photo_row = QHBoxLayout()
        photo_row.addWidget(QLabel("Photometric File  "))
        btn_browse_photo = QPushButton(" Browse")
        btn_browse_photo.setIcon(folder_icon)
        btn_browse_photo.setToolTip("Browse File")
        btn_browse_photo.setMaximumWidth(320)
        btn_browse_photo.clicked.connect(self._browse_photometry_file)
        photo_row.addWidget(btn_browse_photo)
        photo_row.addStretch()
        parent_layout.addLayout(photo_row)

        # -- Intensity row --
        int_row = QHBoxLayout()
        self.intensity_slider = FloatFieldSlider("Intensity", value=1.0, min_val=0, max_val=25)
        self.intensity_slider.valueChanged.connect(
            lambda v: [self._set_parm(n, "ar_intensity", v) for n in self._get_selected_light_nodes()])
        int_row.addWidget(self.intensity_slider, 3)

        btn_key_int = QPushButton("Key")
        btn_key_int.setStyleSheet("background-color: #4D1A1A;")
        btn_key_int.setMaximumWidth(40)
        btn_key_int.clicked.connect(lambda: self._key_parm("ar_intensity"))
        int_row.addWidget(btn_key_int)

        int_row.addWidget(QLabel(" Range -> "))
        self.int_range_slider = FloatFieldSlider("", value=10, min_val=0, max_val=25)
        int_row.addWidget(self.int_range_slider, 2)

        btn_random_int = QPushButton() 

        btn_random_int.setIcon(random_icon)              
        btn_random_int.clicked.connect(self._randomize_intensity)
        int_row.addWidget(btn_random_int)

        parent_layout.addLayout(int_row)

        # -- Exposure row --
        exp_row = QHBoxLayout()
        self.exposure_slider = FloatFieldSlider("Exposure", value=0.0, min_val=-5, max_val=30)
        self.exposure_slider.valueChanged.connect(
            lambda v: [self._set_parm(n, "ar_exposure", v) for n in self._get_selected_light_nodes()])
        exp_row.addWidget(self.exposure_slider, 3)

        btn_key_exp = QPushButton("Key")
        btn_key_exp.setStyleSheet("background-color: #4D1A1A;")
        btn_key_exp.setMaximumWidth(40)
        btn_key_exp.clicked.connect(lambda: self._key_parm("ar_exposure"))
        exp_row.addWidget(btn_key_exp)

        exp_row.addWidget(QLabel(" Range -> "))
        self.exp_range_slider = FloatFieldSlider("", value=10, min_val=-5, max_val=30)
        exp_row.addWidget(self.exp_range_slider, 2)

        btn_random_exp = QPushButton()
        btn_random_exp.setIcon(random_icon)
        btn_random_exp.clicked.connect(self._randomize_exposure)
        exp_row.addWidget(btn_random_exp)

        parent_layout.addLayout(exp_row)

        # -- Samples row --
        sam_row = QHBoxLayout()
        self.samples_slider = IntFieldSlider("Samples", value=1, min_val=0, max_val=10)
        self.samples_slider.valueChanged.connect(
            lambda v: [self._set_parm(n, "ar_samples", v) for n in self._get_selected_light_nodes()])
        sam_row.addWidget(self.samples_slider, 1)

        btn_key_sam = QPushButton("Key")
        btn_key_sam.setStyleSheet("background-color: #4D1A1A;")
        btn_key_sam.setMaximumWidth(40)
        btn_key_sam.clicked.connect(lambda: self._key_parm("ar_samples"))
        sam_row.addWidget(btn_key_sam)

        parent_layout.addLayout(sam_row)

        # -- Custom attribute row --
        custom_row = QHBoxLayout()
        custom_row.addWidget(QLabel("Custom Attr"))

        self.custom_attr_combo = QComboBox()
        self.custom_attr_combo.addItems(ARNOLD_ATTRS)
        custom_row.addWidget(self.custom_attr_combo)

        self.custom_check = QCheckBox("on/off")
        self.custom_check.setChecked(True)
        self.custom_check.stateChanged.connect(self._on_custom_enable_changed)
        custom_row.addWidget(self.custom_check)

        self.custom_value_slider = FloatFieldSlider("", value=1, min_val=0, max_val=100)
        self.custom_value_slider.valueChanged.connect(self._on_custom_value_changed)
        custom_row.addWidget(self.custom_value_slider, 1)

        btn_key_custom = QPushButton("Key")
        btn_key_custom.setStyleSheet("background-color: #4D1A1A;")
        btn_key_custom.setMaximumWidth(40)
        btn_key_custom.clicked.connect(self._key_custom_attr)
        custom_row.addWidget(btn_key_custom)

        parent_layout.addLayout(custom_row)

        # -- Action buttons --
        parent_layout.addWidget(self._make_separator())

        action_row = QHBoxLayout()
        btn_default = QPushButton("Set Default Values")
        btn_default.clicked.connect(self._set_default_attributes)
        action_row.addWidget(btn_default)

        btn_del_keys = QPushButton("Delete All Keys")
        btn_del_keys.clicked.connect(self._delete_all_keys)
        action_row.addWidget(btn_del_keys)

        parent_layout.addLayout(action_row)

        parent_layout.addWidget(self._make_separator())
        btn_set_all = QPushButton("Set Current Values")
        btn_set_all.setMinimumHeight(30)
        btn_set_all.setStyleSheet("background-color: #2A3A3A; font-weight: bold;")
        btn_set_all.clicked.connect(self._set_all_attributes)
        parent_layout.addWidget(btn_set_all)

    # ---- Callback methods ----

    def _refresh_light_list(self):
        """Populate the light list. Connect to hou scene graph here."""
        self.light_list.clear()
        lights = self._get_scene_lights()
        for name in lights:
            self.light_list.addItem(name)

        # Disabled lights are shown greyed out in the list for quick visual feedback.
        for i in range(self.light_list.count()):
            item = self.light_list.item(i)
            node = hou.node(item.text()) if HOU_AVAILABLE else None
            is_enabled = self._is_light_enabled(node) if node is not None else True
            if node is not None:
                self._set_light_node_disabled_color(node, is_enabled)
            self._set_light_list_item_style(item, is_enabled)

        self.lights_count_label.setText(f"Lights: {len(lights)}")

    @staticmethod
    def _get_light_enable_parm(node):
        """Return the first existing light enable parm for an arnold/houdini light node."""
        if node is None:
            return None
        for parm_name in ("light_enable", "ar_enable", "enable", "enabled"):
            try:
                parm = node.parm(parm_name)
                if parm is not None:
                    return parm
            except Exception:
                pass
        return None

    def _is_light_enabled(self, node):
        parm = self._get_light_enable_parm(node)
        if parm is None:
            return True
        try:
            return bool(parm.eval())
        except Exception:
            return True

    def _set_light_enabled(self, node, enabled):
        parm = self._get_light_enable_parm(node)
        if parm is None:
            return
        try:
            parm.set(1 if enabled else 0)
            self._set_light_node_disabled_color(node, bool(enabled))
        except Exception:
            pass

    def _set_light_node_disabled_color(self, node, is_enabled):
        """Tint disabled nodes medium grey and restore original node color when enabled."""
        if node is None:
            return
        try:
            path = node.path()
            if is_enabled:
                original_rgb = self._disabled_light_original_colors.pop(path, None)
                if original_rgb is not None:
                    node.setColor(hou.Color(original_rgb))
            else:
                if path not in self._disabled_light_original_colors:
                    self._disabled_light_original_colors[path] = tuple(node.color().rgb())
                node.setColor(hou.Color((0.5, 0.5, 0.5)))
        except Exception:
            pass

    def _set_light_list_item_style(self, item, is_enabled):
        if is_enabled:
            item.setForeground(QBrush(QColor("#CCCCCC")))
        else:
            item.setForeground(QBrush(QColor("#7F7F7F")))

    def _toggle_isolate_selected_lights(self, is_on):
        """Disable all lights except selected ones; toggle OFF restores previous enable states."""
        all_lights = self._get_all_light_nodes()
        if not all_lights:
            self.btn_isolate_lights.blockSignals(True)
            self.btn_isolate_lights.setChecked(False)
            self.btn_isolate_lights.blockSignals(False)
            return

        selected_paths = {item.text() for item in self.light_list.selectedItems()}
        if not selected_paths:
            selected_paths = {n.path() for n in self._get_selected_light_nodes()}

        if is_on:
            if not selected_paths:
                QMessageBox.information(self, "Isolate Lights", "Select one or more lights to isolate.")
                self.btn_isolate_lights.blockSignals(True)
                self.btn_isolate_lights.setChecked(False)
                self.btn_isolate_lights.blockSignals(False)
                return

            self._isolate_light_states = {n.path(): self._is_light_enabled(n) for n in all_lights}
            for node in all_lights:
                self._set_light_enabled(node, node.path() in selected_paths)
            self._lights_isolated = True
        else:
            if self._lights_isolated:
                for node in all_lights:
                    original_state = self._isolate_light_states.get(node.path(), True)
                    self._set_light_enabled(node, original_state)
            self._lights_isolated = False
            self._isolate_light_states = {}

        self._refresh_light_list()

    # ==================== Scene Query Helpers ====================

    @staticmethod
    def _get_all_light_nodes():
        """Return all Arnold/Houdini light nodes anywhere in the scene (recursive)."""
        results = []
        def _recurse(node):
            for child in node.children():
                if child.type().name() in ARNOLD_LIGHT_TYPES:
                    results.append(child)
                # Recurse into subnets and any other container types"
                try:
                    if child.children() and "arnold_light" not in child.type().name():
                        _recurse(child)
                except Exception:
                    pass
        try:
            root = hou.node("/")
            if root is not None:
                _recurse(root)
        except Exception:
            pass
        return results

    @staticmethod
    def _get_selected_light_nodes():
        """Return currently selected light nodes in the Houdini scene."""
        try:
            return [n for n in hou.selectedNodes() if n.type().name() in ARNOLD_LIGHT_TYPES]
        except Exception:
            return []

    def _get_scene_lights(self):
        """Return sorted light node full paths from anywhere in the scene."""
        return sorted(n.path() for n in self._get_all_light_nodes())

    # ==================== Parm helpers ====================

    @staticmethod
    def _set_parm(node, name, value):
        """Safely set a scalar parameter on a node."""
        try:
            p = node.parm(name)
            if p is not None:
                p.set(value)
        except Exception:
            pass

    @staticmethod
    def _set_parm_tuple(node, name, value):
        """Safely set a tuple parameter (e.g. color) on a node."""
        try:
            pt = node.parmTuple(name)
            if pt is not None:
                pt.set(tuple(value))
        except Exception:
            pass

    @staticmethod
    def _eval_parm(node, name, default=None):
        """Safely evaluate a scalar parm; returns default on failure."""
        try:
            p = node.parm(name)
            return p.eval() if p is not None else default
        except Exception:
            return default

    @staticmethod
    def _eval_parm_tuple(node, name, default=None):
        """Safely evaluate a tuple parm; returns default on failure."""
        try:
            pt = node.parmTuple(name)
            return pt.eval() if pt is not None else default
        except Exception:
            return default

    @staticmethod
    def _kelvin_to_rgb(kelvin):
        """Approximate black-body color from Kelvin, normalized to [0, 1]."""
        k = max(1000.0, min(40000.0, float(kelvin))) / 100.0

        if k <= 66.0:
            red = 255.0
            green = 99.4708025861 * math.log(max(k, 1.0)) - 161.1195681661
            if k <= 19.0:
                blue = 0.0
            else:
                blue = 138.5177312231 * math.log(k - 10.0) - 305.0447927307
        else:
            red = 329.698727446 * ((k - 60.0) ** -0.1332047592)
            green = 288.1221695283 * ((k - 60.0) ** -0.0755148492)
            blue = 255.0

        red = max(0.0, min(255.0, red)) / 255.0
        green = max(0.0, min(255.0, green)) / 255.0
        blue = max(0.0, min(255.0, blue)) / 255.0
        return red, green, blue

    @classmethod
    def _rgb_to_kelvin(cls, rgb):
        """Approximate Kelvin from normalized RGB by nearest black-body match."""
        try:
            r, g, b = [max(0.0, min(1.0, float(c))) for c in rgb[:3]]
        except Exception:
            return None

        best_k = None
        best_err = None
        for k in range(1000, 15001, 50):
            kr, kg, kb = cls._kelvin_to_rgb(k)
            err = (kr - r) ** 2 + (kg - g) ** 2 + (kb - b) ** 2
            if best_err is None or err < best_err:
                best_err = err
                best_k = k
        return best_k

    # ==================== Arnold light creation ====================

    def _create_arnold_light(self, light_type_idx, name_prefix):
        """Create an arnold_light node. Tries the current network context first,
        falls back to /obj if the current context cannot host the node."""
        def _make_node(parent_net):
            node = parent_net.createNode("arnold_light")
            node.setName(name_prefix, unique_name=True)
            node.setColor(hou.Color((1, 1, 0)))  # yellow for visibility
            node.parm("ar_light_type").set(light_type_idx)
            node.moveToGoodPosition()
            return node

        node = None
        try:
            current_net = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor).pwd()
            node = _make_node(current_net)
        except Exception:
            try:
                obj_net = hou.node("/obj")
                node = _make_node(obj_net)
            except Exception as e:
                print(f"Light Manager: could not create arnold_light — {e}")
                return None

        self._refresh_light_list()
        return node

    def _on_list_selection_changed(self):
        items = self.light_list.selectedItems()
        names = [item.text() for item in items]
        if not names:
            return
        # Select the corresponding nodes in Houdini
        try:
            hou.clearAllSelected()
            for path in names:
                node = hou.node(path)
                if node is not None:
                    node.setSelected(True)
        except Exception:
            pass
        self._set_ui_from_selected_light(names[0])

    def _set_ui_from_selected_light(self, light_path):
        """Sync all UI controls to the current values of the given light node."""
        try:
            node = hou.node(light_path)
            if node is None:
                return
        except Exception:
            return

        widgets_to_block = [
            self.intensity_slider, self.exposure_slider, self.samples_slider,
            self.temp_slider, self.temp_check, self.custom_value_slider,
        ]
        self._syncing_ui_from_selection = True
        for w in widgets_to_block:
            w.blockSignals(True)
        try:
            # Color
            color = self._eval_parm_tuple(node, "ar_color", (1.0, 1.0, 1.0))
            if color:
                self.color_btn.setColor(*color[:3])

            # Intensity
            v = self._eval_parm(node, "ar_intensity", 1.0)
            if v is not None:
                self.intensity_slider.setValue(v)

            # Exposure
            v = self._eval_parm(node, "ar_exposure", 0.0)
            if v is not None:
                self.exposure_slider.setValue(v)

            # Samples
            v = self._eval_parm(node, "ar_samples", 1)
            if v is not None:
                self.samples_slider.setValue(int(v))

            # Color temperature value: use actual parm first, otherwise estimate from ar_color.
            temp_value = self._eval_parm(node, "ar_temperature", None)
            if temp_value is None:
                color_for_estimate = self._eval_parm_tuple(node, "ar_color", None)
                if color_for_estimate:
                    temp_value = self._rgb_to_kelvin(color_for_estimate)
            if temp_value is not None:
                self.temp_slider.setValue(float(temp_value))

            # Temperature on/off is a UI gate for ar_color updates only (manual state).

            # Custom attribute (current combo selection)
            attr_name = self.custom_attr_combo.currentText()
            if attr_name:
                v = self._eval_parm(node, attr_name)
                if v is not None:
                    self.custom_value_slider.setValue(float(v))
        except Exception:
            pass
        finally:
            for w in widgets_to_block:
                w.blockSignals(False)
            self._syncing_ui_from_selection = False

    def _select_by_name(self):
        text = self.search_field.text().strip()
        if not text:
            return
        try:
            hou.clearAllSelected()
            matched = [n for n in self._get_all_light_nodes() if text.lower() in n.path().lower()]
            for n in matched:
                n.setSelected(True)
            # Refresh list selection to reflect what was selected
            for i in range(self.light_list.count()):
                item = self.light_list.item(i)
                item.setSelected(any(n.path() == item.text() for n in matched))
        except Exception as e:
            print(f"Light Manager select by name error: {e}")

    def _on_color_changed(self, r, g, b):
        if self._syncing_ui_from_selection:
            return
        for node in self._get_selected_light_nodes():
            self._set_parm_tuple(node, "ar_color", (r, g, b))

    def _on_temperature_changed(self, value):
        if self._syncing_ui_from_selection:
            return

        rgb = self._kelvin_to_rgb(value)
        for node in self._get_selected_light_nodes():
            self._set_parm(node, "ar_temperature", value)
            if self.temp_check.isChecked():
                self._set_parm_tuple(node, "ar_color", rgb)

        if self._get_selected_light_nodes() and self.temp_check.isChecked():
            self.color_btn.setColor(*rgb)

    def _random_color(self):
        """Set random color on all selected lights"""
        for node in self._get_selected_light_nodes():
            try:
                r, g, b = random.uniform(0, 1), random.uniform(0, 1), random.uniform(0, 1)
                self._set_parm_tuple(node, "ar_color", (r, g, b))
            except:
                pass

    def _randomize_intensity(self):
        base = self.intensity_slider.value()
        range_val = self.int_range_slider.value()
        for node in self._get_selected_light_nodes():
            self._set_parm(node, "ar_intensity", random.uniform(base, range_val))

    def _randomize_exposure(self):
        base = self.exposure_slider.value()
        range_val = self.exp_range_slider.value()
        for node in self._get_selected_light_nodes():
            self._set_parm(node, "ar_exposure", random.uniform(base, range_val))

    def _on_custom_value_changed(self, value):
        if self._syncing_ui_from_selection:
            return
        attr_name = self.custom_attr_combo.currentText()
        for node in self._get_selected_light_nodes():
            self._set_parm(node, attr_name, value)

    def _on_custom_enable_changed(self, state):
        if self._syncing_ui_from_selection:
            return
        attr_name = self.custom_attr_combo.currentText()
        for node in self._get_selected_light_nodes():
            self._set_parm(node, attr_name, 1 if state else 0)

    def _key_custom_attr(self):
        attr_name = self.custom_attr_combo.currentText()
        self._key_parm(attr_name)

    def _delete_all_keys(self):
        attr_name = self.custom_attr_combo.currentText()
        for node in self._get_selected_light_nodes():
            for name in [attr_name, "ar_intensity", "ar_exposure", "ar_samples"]:
                try:
                    p = node.parm(name)
                    if p is not None:
                        p.deleteAllKeyframes()
                except Exception:
                    pass
            try:
                for comp in node.parmTuple("ar_color"):
                    comp.deleteAllKeyframes()
            except Exception:
                pass

    def _set_all_attributes(self):
        r, g, b = self.color_btn.color()
        for node in self._get_selected_light_nodes():
            self._set_parm(node, "ar_samples", self.samples_slider.value())
            self._set_parm(node, "ar_exposure", self.exposure_slider.value())
            self._set_parm(node, "ar_intensity", self.intensity_slider.value())
            self._set_parm_tuple(node, "ar_color", (r, g, b))

    def _populate_lights(self):
        parent = self.parent_check.isChecked()
        light_type = self.light_type_combo.currentText()
        locator = self.locator_check.isChecked()
        self._do_populate_lights(parent, light_type, locator)

    def _sanity_check(self):
        """Check for naming issues and duplicate light names."""
        try:
            lights = self._get_all_light_nodes()
            issues = []
            seen = set()
            for n in lights:
                if n.name() in seen:
                    issues.append(f"Duplicate name: {n.name()}")
                seen.add(n.name())
            if issues:
                msg = f"{len(issues)} issue(s) found:\n" + "\n".join(issues)
            else:
                msg = f"Sanity check passed — {len(lights)} light(s) found, no issues."
            QMessageBox.information(self, "Sanity Check", msg)
        except Exception as e:
            QMessageBox.warning(self, "Sanity Check", f"Error: {e}")
        self._refresh_light_list()

    def _delete_selected_lights(self):
        for node in self._get_selected_light_nodes():
            try:
                node.destroy()
            except Exception:
                pass
        self._refresh_light_list()

    def _save_state(self):
        """Snapshot the selected lights' parms to a JSON temp file."""
        selected = self._get_selected_light_nodes()
        if not selected:
            QMessageBox.warning(self, "Save State", "Select at least one light to save its state.")
            return

        payload = {"lights": []}
        for node in selected:
            light_data = {"name": node.name(), "parms": {}, "transform": {}}

            # Scalar parms
            for pname in [
                "light_type", "ar_intensity", "ar_exposure", "ar_samples", "ar_normalize",
                "ar_cast_shadows", "ar_shadow_density", "ar_camera", "ar_diffuse", "ar_specular",
                "ar_sss", "ar_volume", "ar_indirect", "ar_temperature", "ar_use_color_temperature",
                "ar_cone_angle", "ar_penumbra_angle", "ar_spread", "ar_roundness", "ar_soft_edge",
            ]:
                v = self._eval_parm(node, pname)
                if v is not None:
                    light_data["parms"][pname] = v

            # Color tuple parms
            for tname in ("ar_color", "ar_shadow_color"):
                v = self._eval_parm_tuple(node, tname)
                if v is not None:
                    light_data["parms"][tname] = list(v)

            # Photometric filename
            v = self._eval_parm(node, "ar_filename")
            if v is not None:
                light_data["parms"]["ar_filename"] = v

            # World transform (t/r/s)
            for tname in ("t", "r", "s"):
                v = self._eval_parm_tuple(node, tname)
                if v is not None:
                    light_data["transform"][tname] = list(v)

            payload["lights"].append(light_data)

        try:
            with self._backup_temp_file.open("w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2)
            QMessageBox.information(self, "Save State",
                                    f"Saved {len(selected)} light(s) to:\n{self._backup_temp_file}")
        except Exception as e:
            QMessageBox.warning(self, "Save State", f"Failed to save:\n{e}")

    def _load_state(self):
        """Restore previously snapped light parms to selected lights."""
        if not self._backup_temp_file.exists():
            QMessageBox.warning(self, "Load State", "No saved state found.")
            return

        selected = self._get_selected_light_nodes()
        if not selected:
            QMessageBox.warning(self, "Load State", "Select at least one light to load state into.")
            return

        try:
            with self._backup_temp_file.open("r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except Exception as e:
            QMessageBox.warning(self, "Load State", f"Failed to read saved state:\n{e}")
            return

        saved_lights = payload.get("lights", [])
        if not saved_lights:
            QMessageBox.warning(self, "Load State", "Saved state file contains no lights.")
            return

        def _apply(node, data):
            for pname, value in data.get("parms", {}).items():
                if isinstance(value, list):
                    self._set_parm_tuple(node, pname, value)
                else:
                    self._set_parm(node, pname, value)
            for tname, value in data.get("transform", {}).items():
                self._set_parm_tuple(node, tname, value)

        if len(saved_lights) == len(selected):
            for node, data in zip(selected, saved_lights):
                _apply(node, data)
            msg = "Restored state to all selected lights (matched order)."
        else:
            for node in selected:
                _apply(node, saved_lights[0])
            msg = (
                "Saved count differs from selection count.\n"
                "Applied first saved light state to all selected lights."
            )
        QMessageBox.information(self, "Load State", msg)

    def eventFilter(self, obj, event):
        if obj == self.light_list and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Delete:
                self._delete_selected_lights()
                return True
        return super().eventFilter(obj, event)

    # ==================== Full HtoA / Houdini Implementations ====================

    def _key_parm(self, parm_name):
        """Set a keyframe at the current frame on parm_name for all selected lights."""
        try:
            frame = hou.frame()
            for node in self._get_selected_light_nodes():
                if parm_name == "ar_color":
                    for comp in node.parmTuple("ar_color"):
                        kf = hou.Keyframe()
                        kf.setFrame(frame)
                        kf.setValue(comp.eval())
                        comp.setKeyframe(kf)
                else:
                    p = node.parm(parm_name)
                    if p is not None:
                        kf = hou.Keyframe()
                        kf.setFrame(frame)
                        kf.setValue(p.eval())
                        p.setKeyframe(kf)
        except Exception as e:
            print(f"Light Manager keyframe error: {e}")

    def _do_populate_lights(self, parent_to_object, light_type, use_locator):
        """
        Create Arnold lights at the transforms of the currently selected OBJ nodes
        (non-light geometry nodes).  Mirrors Maya Light Populator behaviour.
        """
        try:
            selected_objs = [
                n for n in hou.selectedNodes()
                if n.type().name() not in ARNOLD_LIGHT_TYPES
                and n.type().category().name() == "Object"
            ]
            if not selected_objs:
                QMessageBox.warning(self, "Light Populator",
                                    "Select at least one object node first.")
                return

            obj_net = hou.node("/obj")
            light_type_idx = 1
            active_light_type = str(self.light_type_combo.currentText())
            
            
            if "Area" in active_light_type:
                light_type_idx = 3
            elif "Spot" in active_light_type:
                light_type_idx = 2
            elif "Photometric" in active_light_type:
                light_type_idx = 8
            elif "Mesh" in active_light_type:
                light_type_idx = 7

            for obj in selected_objs:
                # Capture world transform from the source object
                try:
                    t = list(obj.parmTuple("t").eval())
                    r = list(obj.parmTuple("r").eval())
                except Exception:
                    t, r = [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]

                light_name_base = f"{obj.name()}_{light_type.replace(' ', '_')}_lgt"

                if use_locator:
                    # Create a null as the locator parent
                    null_node = obj_net.createNode("null", node_name=f"{obj.name()}_locator")
                    null_node.moveToGoodPosition()
                    self._set_parm_tuple(null_node, "t", t)
                    self._set_parm_tuple(null_node, "r", r)

                    light_node = obj_net.createNode("arnold_light")
                    light_node.setName(light_name_base, unique_name=True)
                    light_node.parm("ar_light_type").set(light_type_idx)
                    light_node.moveToGoodPosition()
                    # Match null position (parent parenting not available at OBJ level)
                    self._set_parm_tuple(light_node, "t", t)
                    self._set_parm_tuple(light_node, "r", r)
                    light_node.parm("keeppos").set(1)
                    light_node.setFirstInput(null_node)
                else:
                    light_node = obj_net.createNode("arnold_light")
                    light_node.setName(light_name_base, unique_name=True)
                    light_node.parm("light_type").set(light_type_idx)
                    light_node.moveToGoodPosition()
                    self._set_parm_tuple(light_node, "t", t)
                    self._set_parm_tuple(light_node, "r", r)
                    
                if light_type_idx == 7:
                    light_node.parm("ar_mesh").set(obj.path())

                if parent_to_object:
                    try:
                        null_node.setFirstInput(obj)
                    except Exception:
                        pass

            self._refresh_light_list()
        except Exception as e:
            print(f"Light Manager populate error: {e}")
            QMessageBox.warning(self, "Light Populator", f"Error: {e}")

    # ---- Toolbar action implementations ----

    def _select_all_lights(self):
        try:
            lights = self._get_all_light_nodes()
            hou.clearAllSelected()
            for n in lights:
                n.setSelected(True)
            # Also highlight in the UI list
            self.light_list.selectAll()
        except Exception as e:
            print(f"Light Manager select all error: {e}")

    def _create_area_light(self):
        self._create_arnold_light(LIGHT_TYPE_MAP["Area"], "area_lgt")

    def _create_env_light(self):
        self._create_arnold_light(LIGHT_TYPE_MAP["Environment"], "env_lgt")

    def _create_point_light(self):
        self._create_arnold_light(LIGHT_TYPE_MAP["Point"], "point_lgt")

    def _create_spot_light(self):
        self._create_arnold_light(LIGHT_TYPE_MAP["Spot"], "spot_lgt")

    def _create_distant_light(self):
        self._create_arnold_light(LIGHT_TYPE_MAP["Distant"], "distant_lgt")

    def _create_photometric_light(self):
        self._create_arnold_light(LIGHT_TYPE_MAP["Photometric"], "photometric_lgt")

    def _create_cylinder_light(self):
        self._create_arnold_light(LIGHT_TYPE_MAP["Cylinder"], "cylinder_lgt")

    def _create_disk_light(self):
        self._create_arnold_light(LIGHT_TYPE_MAP["Disk"], "disk_lgt")

    def _create_mesh_light(self):
        self._create_arnold_light(LIGHT_TYPE_MAP["Mesh Light"], "mesh_lgt")

    def _create_arnold_rop(self):
        """Open Arnold RenderView via HtoA Python API."""
        try:
            __import__('roptoolutils').createRenderNode('arnold')
        except Exception:
            pass


    def _isolate_render_view(self, is_on):
        """Toggle isolate connection on arnold_material input 0 and restore original on OFF."""
        try:
            current_node = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor).pwd()
            child_nodes = current_node.children()
            material_output = next((n for n in child_nodes if n.type().name() == "arnold_material"), None)
            if material_output is None:
                print("Light Manager isolate: arnold_material not found in current network.")
                return

            material_path = material_output.path()
            selected_node = hou.selectedNodes()[0] if hou.selectedNodes() else None

            # Cache original input only once (first time isolate is enabled for this material).
            if material_path not in self._isolate_original_inputs:
                original_input = material_output.input(0)
                self._isolate_original_inputs[material_path] = original_input.path() if original_input else None

            if is_on:
                if selected_node is None:
                    print("Light Manager isolate: select a node to isolate.")
                    return
                material_output.setInput(0, selected_node)
            else:
                original_path = self._isolate_original_inputs.pop(material_path, None)
                original_node = hou.node(original_path) if original_path else None
                material_output.setInput(0, original_node)
        except Exception as e:
            print(f"Light Manager isolate error: {e}")



    def _open_render_settings(self):
        """Open the Houdini Render Settings / Arnold ROP."""
        import runpy
        runpy.run_path(ROP_MANAGER_PATH)


    def _open_node_editor(self):
        """Focus the Houdini Network Editor."""
        try:
            pane = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
            if pane:
                pane.setIsCurrentTab()
        except Exception as e:
            print(f"Light Manager: could not focus network editor — {e}")


    def _browse_photometry_file(self):
        """Browse for an IES file and assign it to selected photometric lights."""
        try:
            file_path = hou.ui.selectFile(
                title="Select IES Photometric File",
                file_type=hou.fileType.Any,
                pattern="*.ies",
            )
            if not file_path:
                return
            for node in self._get_selected_light_nodes():
                self._set_parm(node, "ar_filename", file_path)
        except Exception as e:
            print(f"Light Manager browse photometry error: {e}")

    def _browse_color_file(self):
        """Browse for a texture and assign it to the light's color_texture parm."""
        try:
            file_path = hou.ui.selectFile(
                title="Select Color Texture",
                file_type=hou.fileType.Image,
            )
            if not file_path:
                return
            for node in self._get_selected_light_nodes():
                # HtoA uses 'color_texture' for texture-driven color on arnold_light
                node.parm("ar_light_color_type").set(2)  # Set to "Shader"
                image_node = hou.node(node.path() + "/shopnet/arnold_vopnet").createNode("arnold::image")
                light_output_node = hou.node(node.path() + "/shopnet/arnold_vopnet/OUT_light")
                if image_node and light_output_node:
                    image_node.setName("color_texture", unique_name=True)
                    image_node.parm("filename").set(file_path)
                    light_output_node.setInput(0, image_node)  # Connect to color input


        except Exception as e:
            print(f"Light Manager browse color file error: {e}")

    def _disconnect_files(self):
        """Clear texture parms on selected lights."""
        for node in self._get_selected_light_nodes():
            node.parm("ar_light_color_type").set(0)  # Set to "Shader"
            image_node = hou.node(node.path() + "/shopnet/arnold_vopnet/color_texture")
            if image_node:
                image_node.destroy()

    def _set_default_attributes(self):
        """Reset all light parms to their default values."""
        for node in self._get_selected_light_nodes():
            for pname, value in DEFAULT_VALUES.items():
                if isinstance(value, tuple):
                    self._set_parm_tuple(node, pname, value)
                else:
                    self._set_parm(node, pname, value)


# ==================== Main Window ====================

class LightManagerWindow(QWidget):
    """Light Manager + floating window - Houdini 20 / PySide2"""

    WINDOW_NAME = "LightManagerWindow"

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Tool)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle("Light Manager +")
        self.setGeometry(100, 100, 700, 650)
        self.setMinimumHeight(100)
        self.setMinimumWidth(250)
        self.setStyleSheet(DARK_STYLESHEET)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(3)

        title = QLabel("< Houdini ROP Light Manager + >")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("background-color: #1A1A1A; padding: 8px;")
        main_layout.addWidget(title)

        self.light_tab = LightManagerTab()
        main_layout.addWidget(self.light_tab)

        footer = QLabel("www.miguelagenjo.com")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("background-color: #1A1A1A; padding: 8px; font-size: 12px; color: #777777;")
        main_layout.addWidget(footer)

    def closeEvent(self, event):
        """Reset isolate state before closing the window."""
        if hasattr(self, "light_tab") and self.light_tab:
            self.light_tab.reset_isolate_button()
        super().closeEvent(event)


# ==================== Entry Point ====================

_current_window = None


def create_light_manager_window():
    """
    Launch Light Manager + as a floating window inside Houdini 20.

    Call from a Houdini shelf script or Python panel:
        import light_manager_houdini
        light_manager_houdini.create_light_manager_window()
    """
    global _current_window

    # Search all top-level widgets for an existing instance.
    # This works even when the module is re-executed and _current_window is reset.
    app = QApplication.instance()
    if app is not None:
        for widget in list(app.topLevelWidgets()):
            if widget.objectName() == LightManagerWindow.WINDOW_NAME:
                try:
                    if widget.isVisible():
                        # Window is open — refresh its list and bring it to front
                        widget.light_tab._refresh_light_list()
                        widget.raise_()
                        widget.activateWindow()
                        _current_window = widget
                        return widget
                    else:
                        # Window was closed but not yet destroyed — force close it
                        widget.close()
                except RuntimeError:
                    pass

    # Determine parent: use Houdini's main window when available
    parent = None
    if HOU_AVAILABLE:
        try:
            parent = hou.qt.mainWindow()
        except Exception:
            pass

    window = LightManagerWindow(parent=parent)
    window.setObjectName(LightManagerWindow.WINDOW_NAME)
    window.show()
    window.raise_()

    _current_window = window
    return window



create_light_manager_window()



