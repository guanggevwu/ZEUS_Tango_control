import configparser
from tango import AttrWriteType, DevState
from tango.server import Device, attribute, command, device_property
import logging

# -----------------------------

handlers = [logging.StreamHandler()]
logging.basicConfig(handlers=handlers,
                    format="%(asctime)s %(message)s", level=logging.INFO)


class LaserWarningSign(Device):

    polling = 1000
    # is_memorized = True means the previous entered set value is remembered and is only for Read_WRITE access. For example in GUI, the previous set value,instead of 0, will be shown at the set value field.
    # hw_memorized=True, means the set value is written at the initialization step. Some of the properties are remembered in the camera's memory, so no need to remember them.
    is_memorized = True

    friendly_name = device_property(dtype=str, default_value='')

    # add to init
    source_path = attribute(
        label="Data source path",
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        memorized=is_memorized,
        doc='path of the data file'
    )

    def read_source_path(self):
        if not hasattr(self, '_source_path'):
            self._source_path = r"Z:\software\status\laser_warning_sign\status_get.ini"
        return self._source_path

    def write_source_path(self, value):
        self._source_path = value

    status_list = attribute(
        label="Strobe light",
        dtype=((str,),),
        max_dim_x=100,
        max_dim_y=100,
        polling_period=polling,
        access=AttrWriteType.READ,
    )

    def read_status_list(self):
        self.read_source_path()
        self._status_list = []
        self.config.read(self._source_path)
        for key, value in self.config['status'].items():
            self._status_list.append([key, value])
        return self._status_list

    strobe_light = attribute(
        label="Strobe light",
        dtype="str",
        access=AttrWriteType.READ,
    )

    def read_strobe_light(self):
        for i in self._status_list:
            if "strobe-light" in i[0] and i[1] == '1':
                return 'on'
            elif "strobe-light" in i[0] and i[1] == '0':
                return 'off'

    ta1 = attribute(
        label="Strobe light",
        dtype="str",
        access=AttrWriteType.READ,
    )

    def read_ta1(self):
        for i in self._status_list:
            if "ta1" in i[0] and i[1] == '1':
                for s in ['safe', 'caution', 'danger', 'radiation']:
                    if s in i[0]:
                        return s

    ta2 = attribute(
        label="Strobe light",
        dtype="str",
        access=AttrWriteType.READ,
    )

    def read_ta2(self):
        for i in self._status_list:
            if "ta2" in i[0] and i[1] == '1':
                for s in ['safe', 'caution', 'danger', 'radiation']:
                    if s in i[0]:
                        return s

    ta3 = attribute(
        label="Strobe light",
        dtype="str",
        access=AttrWriteType.READ,
    )

    def read_ta3(self):
        for i in self._status_list:
            if "ta3" in i[0] and i[1] == '1':
                for s in ['safe', 'caution', 'danger', 'radiation']:
                    if s in i[0]:
                        return s

    mezzanine = attribute(
        label="Strobe light",
        dtype="str",
        access=AttrWriteType.READ,
    )

    def read_mezzanine(self):
        for i in self._status_list:
            if "mezzanine" in i[0] and i[1] == '1':
                for s in ['safe', 'caution', 'danger', 'radiation']:
                    if s in i[0]:
                        return s

    clean_room = attribute(
        label="Strobe light",
        dtype="str",
        access=AttrWriteType.READ,
    )

    def read_clean_room(self):
        for i in self._status_list:
            if "clean-room" in i[0] and i[1] == '1':
                for s in ['safe', 'caution', 'danger', 'radiation']:
                    if s in i[0]:
                        return s

    def init_device(self):
        Device.init_device(self)
        self.config = configparser.ConfigParser()
        self.set_state(DevState.INIT)


if __name__ == "__main__":
    LaserWarningSign.run_server()
