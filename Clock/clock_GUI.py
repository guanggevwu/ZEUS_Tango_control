"""Taurus GUI displaying the time reported by a Clock device."""

from common.TaurusGUI_Argparse import TaurusArgparse


def create_app(args):
    # Parse CLI options before loading Qt and plotting dependencies.
    from common.GUI import GuiBase

    device_list = args.device if isinstance(
        args.device, list) else [args.device]
    clock_app = GuiBase(device_list, args.polling,
                        is_form_compact=args.compact)
    clock_app.gui.setWindowTitle('Clock')

    for device_name in device_list:
        clock_app.add_device(device_name)
        panel, layout = clock_app.create_blank_panel('v')
        clock_app.gui.createPanel(panel, f'{device_name}_clock')
        clock_app.create_form_panel(
            layout, device_name,
            include=['time', 'host_computer', 'state', 'status'],
            withButtons=False,
            set_attr_font={'time': {'font': 'Monospace', 'size': 24}},
        )

    clock_app.gui.removePanel('Manual')
    clock_app.gui.show()
    return clock_app.app.exec_()


def main(argv=None):
    parser = TaurusArgparse(
        description='GUI for Clock',
        device_default='facility/Clock/clock',
        nargs_string='*',
        polling_default=100,
    )
    return create_app(parser.parse_args(argv))


if __name__ == '__main__':
    raise SystemExit(main())
