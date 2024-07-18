import argparse


class TaurusArgparse(argparse.ArgumentParser):
    def __init__(self, description, device_default, polling_default=500):
        super().__init__()
        self.description = description
        self.add_argument('device', default=device_default, nargs='?',
                          help="device full name")
        self.add_argument('--polling', type=int, default=polling_default,
                          help="polling period")
        self.add_argument('-c', '--compact', action='store_true',
                          help="Use compact mode for Taurus form")
