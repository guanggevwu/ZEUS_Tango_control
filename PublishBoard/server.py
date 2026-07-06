import tango
from tango import AttrWriteType, DevState
from tango.server import Device, attribute, command, device_property
import datetime
import logging
import csv
import os
from threading import Thread

import socket
import platform
from common.logger_adapter import LoggerAdapter
# -----------------------------

handlers = [logging.StreamHandler()]
logging.basicConfig(handlers=handlers,
                    format="%(asctime)s %(message)s", level=logging.INFO)

_energy_log_filename = 'energy_log.csv'
_datetime_alarm_threshold_seconds = 10

# (attr_name, label) — attr_name uses underscores (valid Tango/Python identifier)
#                      label preserves the original name (may include hyphens)
_float_attr_list = [
    ('TITAN_QE95_energy',      {
     'label': 'TITAN', 'unit': 'J', 'WriteType': AttrWriteType.READ_WRITE}),
    ('GAIA_A_QE95_energy',            {
     'label': 'GAIA-A', 'unit': 'J', 'WriteType': AttrWriteType.READ_WRITE}),
    ('GAIA_B_QE95_energy',            {
     'label': 'GAIA-B', 'unit': 'J', 'WriteType': AttrWriteType.READ_WRITE}),
    ('TITAN_and_GAIA_A_QE95_energy',  {
     'label': 'TITAN_and_GAIA-A', 'unit': 'J', 'WriteType': AttrWriteType.READ_WRITE}),
    ('TITAN_and_GAIA_B_QE95_energy',  {
     'label': 'TITAN_and_GAIA-B', 'unit': 'J', 'WriteType': AttrWriteType.READ_WRITE}),
    ('GAIA_A_and_B_QE95_energy', {
     'label': 'GAIA-A_and_B', 'unit': 'J', 'WriteType': AttrWriteType.READ_WRITE}),
    ('MA2_north_beam_QE95_energy',    {
     'label': 'MA2_north_beam', 'unit': 'J', 'WriteType': AttrWriteType.READ_WRITE}),
    ('MA2_full_power_QE95_energy',    {
     'label': 'MA2_full_power', 'unit': 'J', 'WriteType': AttrWriteType.READ_WRITE}),
]


class PublishBoard(Device):

    def init_device(self):
        Device.init_device(self)
        self.set_state(DevState.INIT)
        self._energy = 0.0
        self._datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.use_real_time = True
        try:
            self._host_computer = platform.node()
            self.init_float_attrs()
            self._energy_log_path = os.path.join(
                os.path.dirname(__file__), _energy_log_filename)
            self._ensure_energy_log_file()
            self.set_status("PublishBoard device is connected.")
            self.set_state(DevState.ON)
        except:
            print("Could NOT connect to PublishBoard")
            self.set_state(DevState.OFF)

    def _energy_attr_names(self):
        return [attr_name for attr_name, _ in _float_attr_list]

    def _ensure_energy_log_file(self):
        if os.path.exists(self._energy_log_path):
            return
        fieldnames = ['datetime'] + self._energy_attr_names()
        with open(self._energy_log_path, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

    def _append_energy_log(self):
        self._ensure_energy_log_file()
        fieldnames = ['datetime'] + self._energy_attr_names()
        row = {'datetime': self._datetime}
        for attr_name in self._energy_attr_names():
            row[attr_name] = getattr(self, f'_{attr_name}')
        with open(self._energy_log_path, 'a', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writerow(row)

    def _restore_energy_from_datetime(self, target_dt):
        self._ensure_energy_log_file()
        if os.path.getsize(self._energy_log_path) == 0:
            return None

        matched_row = None
        matched_dt = None
        with open(self._energy_log_path, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                try:
                    row_dt = datetime.datetime.strptime(
                        row.get('datetime', ''), "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    continue

                if row_dt <= target_dt and (matched_dt is None or row_dt >= matched_dt):
                    matched_row = row
                    matched_dt = row_dt

        if matched_row is None:
            return None

        for attr_name in self._energy_attr_names():
            try:
                value = float(matched_row.get(attr_name, 0.0))
            except (TypeError, ValueError):
                value = 0.0
            setattr(self, f'_{attr_name}', value)

        return matched_dt.strftime("%Y-%m-%d %H:%M:%S")

    def initialize_dynamic_attributes(self):
        prop = tango.UserDefaultAttrProp()
        prop.set_label('DateTime')
        prop.set_description(
            'Date and time writing format should be one of these: '
            '(1) YYYY-MM-DD HH:MM:SS, '
            '(2) YYYY-MM-DD (default to 12:00:00), '
            '(3) any other strings (default to the time of now)'
        )
        attr = tango.Attr('datetime', tango.DevString,
                          AttrWriteType.READ_WRITE)
        attr.set_default_properties(prop)
        self.add_attribute(attr, self.read_datetime,
                           self.write_datetime)

        for attr_name, properties in _float_attr_list:
            prop = tango.UserDefaultAttrProp()
            prop.set_label(properties.get('label', attr_name))
            prop.set_unit(properties.get('unit', ''))
            write_type = properties.get('WriteType', AttrWriteType.READ)
            attr = tango.Attr(attr_name, tango.DevDouble,
                              write_type)
            attr.set_default_properties(prop)
            if write_type == AttrWriteType.READ_WRITE:
                attr.set_memorized()
                # memorized but not hw_memorized
                attr.set_memorized_init(False)
                self.add_attribute(attr, self.read_float_attr,
                                   self.write_float_attr)
            else:
                self.add_attribute(attr, self.read_float_attr)

    def init_float_attrs(self):
        for attr_name, _ in _float_attr_list:
            setattr(self, f'_{attr_name}', 0.0)

    def read_float_attr(self, attr):
        attr.set_value(getattr(self, f'_{attr.get_name()}'))

    def write_float_attr(self, attr):
        setattr(self, f'_{attr.get_name()}', attr.get_write_value())
        self._append_energy_log()

    host_computer = attribute(
        label="host computer",
        dtype="str",
        access=AttrWriteType.READ,
    )

    def read_host_computer(self):
        return self._host_computer

    energy = attribute(
        label="Energy",
        dtype="float",
        unit="J",
        access=AttrWriteType.READ,
    )

    def read_energy(self):
        return self._energy

    def read_datetime(self, attr):
        if self.use_real_time:
            self._datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            dt = datetime.datetime.strptime(
                self._datetime, "%Y-%m-%d %H:%M:%S")
            deviation = abs((datetime.datetime.now() - dt).total_seconds())
            quality = tango.AttrQuality.ATTR_ALARM if deviation > _datetime_alarm_threshold_seconds else tango.AttrQuality.ATTR_VALID
        except ValueError:
            quality = tango.AttrQuality.ATTR_ALARM
        attr.set_value_date_quality(
            self._datetime, datetime.datetime.now().timestamp(),
            quality)

    def write_datetime(self, attr):
        value = attr.get_write_value()
        self.use_real_time = False
        try:
            # Try to parse the input as a datetime string
            dt = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                # If that fails, try to parse it as just a date
                dt = datetime.datetime.strptime(value, "%Y-%m-%d")
                # Set the time to 12:00:00 if only the date is provided
                dt = dt.replace(hour=12, minute=0, second=0)
            except ValueError:
                # If both parsing attempts fail, set to current time
                dt = datetime.datetime.now()
                self.use_real_time = True
        self._datetime = dt.strftime("%Y-%m-%d %H:%M:%S")
        restored_dt = self._restore_energy_from_datetime(dt)
        if restored_dt:
            logging.info(
                f"Restored energy values from log entry {restored_dt} "
                f"for requested datetime {self._datetime}")
        else:
            logging.info(
                f"No earlier log entry found for datetime {self._datetime}; values unchanged")


if __name__ == "__main__":
    PublishBoard.run_server()
