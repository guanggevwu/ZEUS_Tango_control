from common.GUI import GuiBase
from common.TaurusGUI_Argparse import TaurusArgparse
from common.config import device_name_table
import tango
import os


LESS_LIST = [
    "user_defined_name",
    "current_location",
]

MORE_LIST = [
    "host_computer",
    "saved_location_source",
    "user_defined_locations",
    "status",
    "state",
]


def _dynamic_position_attrs(device_proxy):
    return sorted(
        attr_name
        for attr_name in device_proxy.get_attribute_list()
        if attr_name.startswith("sn_") and attr_name.endswith("_position")
    )


def _dynamic_home_identify_commands(device_proxy):
    command_names = device_proxy.get_command_list()
    dynamic_home = sorted(
        cmd_name
        for cmd_name in command_names
        if cmd_name.startswith("sn_") and cmd_name.endswith("_home")
    )
    dynamic_identify = sorted(
        cmd_name
        for cmd_name in command_names
        if cmd_name.startswith("sn_") and cmd_name.endswith("_identify")
    )
    return dynamic_home + dynamic_identify


def _load_client_locations(device_name):
    location_file_path = os.path.join(
        os.path.dirname(
            __file__), f"{device_name.replace('/', '_')}_client_locations.txt"
    )
    if not os.path.isfile(location_file_path):
        with open(location_file_path, "w", newline="") as file_obj:
            file_obj.write("name positions\n")

    loaded_locations = []
    with open(location_file_path, "r") as file_obj:
        next(file_obj)
        for line in file_obj:
            if line.strip():
                name, positions = [
                    entry
                    for entry in line.replace("\t", " ").strip().replace('"', "").split(" ")
                    if entry
                ]
                loaded_locations.append(f"{name}: ({positions})")
    return loaded_locations


def create_app():
    if "combination" in args.device[0]:
        device_list = device_name_table[args.device[0]]
    elif isinstance(args.device, list):
        device_list = args.device
    else:
        device_list = [args.device]

    xa_app = GuiBase(device_list, args.polling, is_form_compact=args.compact)
    created_panels = 0

    for device_name in device_list:
        xa_app.add_device(device_name)
        dev_class = tango.DeviceProxy(device_name).info().dev_class
        client_locations = _load_client_locations(device_name)
        device_proxy = tango.DeviceProxy(device_name)
        dynamic_position_attrs = _dynamic_position_attrs(device_proxy)
        dynamic_home_identify = _dynamic_home_identify_commands(device_proxy)
        if client_locations and device_proxy.saved_location_source == "client":
            device_proxy.user_defined_locations = client_locations
        else:
            device_proxy.load_server_side_list()

        dropdown = {
            "current_location": (
                (location, location.split(":")[0])
                for location in xa_app.attr_list[device_name]["dp"].user_defined_locations
            ),
            "saved_location_source": (("server", "server"), ("client", "client")),
        }

        less_panel, less_layout = xa_app.create_blank_panel("v")
        xa_app.create_form_panel(
            less_layout,
            device_name,
            dropdown=dropdown,
            include=LESS_LIST + dynamic_position_attrs,
            withButtons=False,
            set_attr_font={
                key: {"font": '"Sans Serif"', "size": 20}
                for key in dynamic_position_attrs
            },
        )
        xa_app.add_command(
            less_layout,
            device_name,
            command_list=dynamic_home_identify + ["stop"],
        )

        more_panel, more_layout = xa_app.create_blank_panel("v")
        xa_app.create_form_panel(
            more_layout,
            device_name,
            dropdown=dropdown,
            include=MORE_LIST,
            withButtons=False,
        )
        xa_app.add_command(
            more_layout,
            device_name,
            command_list=[
                "move_to_negative_limit",
                "move_to_positive_limit",
                *dynamic_home_identify,
                "stop",
            ],
        )

        xa_app.gui.createPanel(more_panel, f"{device_name}_more")
        xa_app.gui.createPanel(less_panel, f"{device_name}_less")
        created_panels += 2

    if created_panels > 0:
        xa_app.gui.removePanel("Manual")
    xa_app.gui.show()
    xa_app.app.exec_()


if __name__ == "__main__":
    parser = TaurusArgparse(
        description="GUI for Thorlabs XA KDC101 device",
        device_default="test/thorlabsxa/kdc101_test",
        nargs_string="+",
        polling_default=1000,
    )
    args = parser.parse_args()
    create_app()
