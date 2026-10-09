from tango import AttrWriteType, DevState
from tango.server import Device, attribute
import datetime
import logging
import socket
from common.logger_adapter import LoggerAdapter
# -----------------------------


class Clock(Device):
    def init_device(self):
        super().init_device()  # this loads the device properties
        logger = logging.getLogger(self.__class__.__name__)
        self.logger = LoggerAdapter(self.__class__.__name__, logger)
        handlers = [logging.StreamHandler()]
        logging.basicConfig(handlers=handlers,
                            format="%(asctime)s %(message)s", level=logging.INFO)
        self._host_computer = socket.gethostname()
        self.set_status("Clock device is connected.")
        self.set_state(DevState.ON)

    time = attribute(
        label="time",
        dtype=str,
        access=AttrWriteType.READ,
        polling_period=100,
    )

    def read_time(self):
        self._time = datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S.%f')
        return self._time

    host_computer = attribute(
        label="host computer",
        dtype="str",
        access=AttrWriteType.READ,
    )

    def read_host_computer(self):
        return self._host_computer


if __name__ == "__main__":
    Clock.run_server()
