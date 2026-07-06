from common.GUI import GuiBase
from common.TaurusGUI_Argparse import TaurusArgparse
from common.config import device_name_table


# Keep field order aligned with PublishBoard server dynamic attributes.
FLOAT_ATTR_NAMES = [
    'datetime',
    'energy',
    'TITAN_QE95_energy',
    'GAIA_A_QE95_energy',
    'GAIA_B_QE95_energy',
    'TITAN_and_GAIA_A_QE95_energy',
    'TITAN_and_GAIA_B_QE95_energy',
    'GAIA_A_and_B_QE95_energy',
    'MA2_north_beam_QE95_energy',
    'MA2_full_power_QE95_energy',
]

LARGE_ATTR_FONT = {
    'datetime': {'font': 'Sans Serif', 'size': 18},
    'energy': {'font': 'Sans Serif', 'size': 18},
}


def create_app():
    if "combination" in args.device[0]:
        device_list = device_name_table[args.device[0]]
    elif isinstance(args.device, list):
        device_list = args.device
    else:
        device_list = [args.device]

    app = GuiBase(device_list, args.polling)

    for d in device_list:
        app.add_device(d)
        form_panel, form_layout = app.create_blank_panel("v")
        app.gui.createPanel(form_panel, f"{d}_form")
        app.create_form_panel(
            form_layout, d, FLOAT_ATTR_NAMES, set_attr_font=LARGE_ATTR_FONT)

    app.gui.removePanel("Manual")
    app.gui.show()
    app.app.exec_()


if __name__ == "__main__":
    parser = TaurusArgparse(
        description="GUI for PublishBoard",
        device_default="test/publishboard/1",
        polling_default=1000,
    )
    args = parser.parse_args()
    create_app()
