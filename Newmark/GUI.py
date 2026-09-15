import os

import tango

from common.GUI import GuiBase
from common.TaurusGUI_Argparse import TaurusArgparse
from common.config import device_name_table


def create_app():
    if "combination" in args.device[0]:
        device_list = device_name_table[args.device[0]]
    elif isinstance(args.device, list):
        device_list = args.device
    else:
        device_list = [args.device]

    newmark_app = GuiBase(device_list, args.polling)

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
            "current_location": (
                (location, location.split(":", 1)[0])
                for location in newmark_app.attr_list[device_name][
                    "dp"
                ].user_defined_locations
            ),
            "saved_location_source": (("server", "server"), ("client", "client")),
        }

        less_panel, less_layout = newmark_app.create_blank_panel("v")
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

        more_panel, more_layout = newmark_app.create_blank_panel("v")
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

        newmark_app.gui.createPanel(more_panel, f"{device_name}_more")
        newmark_app.gui.createPanel(less_panel, f"{device_name}_less")

    newmark_app.gui.removePanel("Manual")
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
