import os

import tango
from taurus.external.qt import Qt
from taurus.qt.qtgui.panel import TaurusForm

from common.GUI import GuiBase
from common.TaurusGUI_Argparse import TaurusArgparse
from common.ui_config import device_name_table
from common.my_motor_widget import mymotor_read_only_item_factory

if __package__:
    from .grating_widget import PairMoveControl, PairMoveWidget
else:
    from grating_widget import PairMoveControl, PairMoveWidget


GRATING_DEVICES = (
    "laser/newmark/PW_grating_1",
    "laser/newmark/PW_grating_2",
)
GRATING_PANEL_NAME = "laser/newmark/PW_grating"
MINIMUM_ATTRIBUTES = ("user_defined_name", "ax1_position")


def resolve_devices(devices):
    """Opening either grating always opens the same ordered pair."""
    devices = [devices] if isinstance(devices, str) else list(devices)
    if devices and devices[0] in device_name_table:
        devices = list(device_name_table[devices[0]])
    pair_names = {name.lower() for name in GRATING_DEVICES}
    if any(name.lower() in pair_names for name in devices):
        devices = list(GRATING_DEVICES) + [
            name for name in devices if name.lower() not in pair_names
        ]
    return list(dict.fromkeys(devices))


def distance_model(device_names):
    """Signed separation in mm, evaluated by Taurus rather than either server."""
    first, second = device_names
    return (
        f'eval:({{tango:{first}/ax1_position}}-'
        f'{{tango:{second}/ax1_position}}).to("mm")'
    )


def configure_distance_row(row, control=None):
    row.setLabelConfig("MOVE (BOTH)")
    row.setWriteWidgetClass(None)
    if control is not None:
        class BoundPairMoveWidget(PairMoveWidget):
            def __init__(self, parent=None):
                super().__init__(control, parent)
        row.setWriteWidgetClass(BoundPairMoveWidget)
    row.setToolTip(
        "Readback: controller 1 - controller 2 (mm). "
        "Arrows move BOTH by the same signed step, preserving separation. "
        "Commands are sent back-to-back, not hardware-synchronized."
    )
    row.readWidget().setFormat("{0:.3f}")
    for widget in (row.labelWidget(), row.readWidget(), row.unitsWidget()):
        if widget is not None:
            widget.setFont(Qt.QFont("Sans Serif", 20))


def add_distance_row(layout, model, control=None):
    form = TaurusForm(withButtons=False)
    form.setModel([model])
    configure_distance_row(form[0], control)
    form.setSizePolicy(Qt.QSizePolicy.Preferred, Qt.QSizePolicy.Expanding)
    layout.addWidget(form, 1)
    return form


def add_minimum_form(layout, devices, control):
    # One form shares column widths and avoids a separate framed block per
    # controller/distance. No set-as, diagnostics, or saved-location rows.
    form = TaurusForm(withButtons=False)
    form.setItemFactories(include=[mymotor_read_only_item_factory, ".*"])
    models = [
        f"{device}/{attr}" for device in devices for attr in MINIMUM_ATTRIBUTES]
    form.setModel(models + [distance_model(devices)])
    for index, model in enumerate(models):
        if model.endswith("/ax1_position"):
            row = form[index]
            for widget in (row.labelWidget(), row.readWidget(), row.unitsWidget()):
                if widget is not None:
                    widget.setFont(Qt.QFont("Sans Serif", 20))
    configure_distance_row(form[len(models)], control)
    form.setSizePolicy(Qt.QSizePolicy.Preferred, Qt.QSizePolicy.Expanding)
    layout.addWidget(form, 1)
    return form


def build_gui(devices, polling):
    device_list = resolve_devices(devices)
    newmark_app = GuiBase(device_list, polling)

    grating_panels = {}
    if all(name in device_list for name in GRATING_DEVICES):
        grating_panels = {
            kind: newmark_app.create_blank_panel("v")
            for kind in ("more", "less", "minimum")
        }
        pair_control = PairMoveControl(GRATING_DEVICES, newmark_app.gui)
        pair_control.failed.connect(
            lambda message: Qt.QMessageBox.warning(
                newmark_app.gui, "MOVE (BOTH) failed", message)
        )

    for device_name in device_list:
        newmark_app.add_device(device_name)
        device_proxy = tango.DeviceProxy(device_name)
        if device_proxy.info().dev_class != "Newmark":
            continue

        less_list = [
            "user_defined_name",
            "error_message",
            "message",
            "current_location",
            "ax1_position",
            "set_ax1_as",
        ]
        more_list = [
            "host_computer",
            "saved_location_source",
            "user_defined_locations",
            "raw_command",
            "status",
            "state",
        ]

        location_file_path = os.path.join(
            os.path.dirname(__file__),
            f'{device_name.replace("/", "_")}_client_locations.txt',
        )
        if not os.path.isfile(location_file_path):
            with open(location_file_path, "w", newline="") as file:
                file.write("name positions\n")

        locations = []
        with open(location_file_path, "r") as file:
            next(file, None)
            for line in file:
                fields = [
                    item
                    for item in line.replace("\t", " ")
                    .strip()
                    .replace('"', "")
                    .split(" ")
                    if item
                ]
                if len(fields) == 2:
                    name, positions = fields
                    locations.append(f"{name}: ({positions})")

        if locations and device_proxy.saved_location_source == "client":
            device_proxy.user_defined_locations = locations
        else:
            device_proxy.load_server_side_list()

        dropdown = {
            "current_location": [
                (location, location.split(":", 1)[0])
                for location in newmark_app.attr_list[device_name][
                    "dp"
                ].user_defined_locations
            ],
            "saved_location_source": (("server", "server"), ("client", "client")),
        }

        is_grating = device_name in GRATING_DEVICES
        if is_grating:
            less_panel, less_layout = grating_panels["less"]
            more_panel, more_layout = grating_panels["more"]
            for layout in (less_layout, more_layout):
                layout.addWidget(Qt.QLabel(device_name))
        else:
            less_panel, less_layout = newmark_app.create_blank_panel("v")
            more_panel, more_layout = newmark_app.create_blank_panel("v")

        newmark_app.create_form_panel(
            less_layout,
            device_name,
            dropdown=dropdown,
            include=less_list,
            withButtons=False,
            set_attr_font={
                "ax1_position": {"font": '"Sans Serif"', "size": 20}
            },
        )
        newmark_app.add_command(
            less_layout, device_name, command_list=["Init", "stop"]
        )

        newmark_app.create_form_panel(
            more_layout,
            device_name,
            dropdown=dropdown,
            include=more_list,
            withButtons=False,
        )
        newmark_app.add_command(
            more_layout,
            device_name,
            command_list=[
                "move_to_negative_limit",
                "move_to_positive_limit",
                "set_as_zero",
            ],
            modified_cmd_name=[
                "ax1_move_to_negative_limit",
                "ax1_move_to_positive_limit",
                "ax1_set_as_zero",
            ],
            cmd_parameters=[[1], [1], [1]],
        )
        newmark_app.add_command(
            more_layout,
            device_name,
            command_list=["stop", "clear_controller_error"],
        )

        if not is_grating:
            newmark_app.gui.createPanel(more_panel, f"{device_name}_more")
            newmark_app.gui.createPanel(less_panel, f"{device_name}_less")

    for kind, (panel, layout) in grating_panels.items():
        if kind == "less":
            add_distance_row(layout, distance_model(
                GRATING_DEVICES), pair_control)
        elif kind == "minimum":
            add_minimum_form(layout, GRATING_DEVICES, pair_control)
            for index, device_name in enumerate(GRATING_DEVICES, 1):
                newmark_app.add_command(
                    layout, device_name, command_list=["Init", "stop"],
                    modified_cmd_name=[f"Init {index}", f"stop {index}"],
                )
        layout.setSpacing(4)
        layout.addStretch()
        newmark_app.gui.createPanel(panel, f"{GRATING_PANEL_NAME}_{kind}")

    newmark_app.gui.removePanel("Manual")
    return newmark_app


def create_app():
    newmark_app = build_gui(args.device, args.polling)
    newmark_app.gui.show()
    newmark_app.app.exec_()


if __name__ == "__main__":
    parser = TaurusArgparse(
        description="GUI for Newmark NSC-A1 device",
        device_default="test/newmark/nsc_a1",
        nargs_string="+",
        polling_default=1000,
    )
    args = parser.parse_args()
    create_app()
