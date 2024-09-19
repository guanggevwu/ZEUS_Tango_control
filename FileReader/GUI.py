from taurus_pyqtgraph import TaurusPlot
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

if True:
    from common.config import device_name_table, image_panel_config
    from common.TaurusGUI_Argparse import TaurusArgparse
    from Basler.GUI import BaslerGUI, create_app
parser = TaurusArgparse(
    description='GUI for Basler camera', device_default='test/basler/testcam', polling_default=1000)
parser.add_argument('-s', '--simple', action='store_true',
                    help="show image without shot number and command")
args = parser.parse_args()

if __name__ == "__main__":
    create_app()
