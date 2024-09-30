import tango
from tango.test_utils import DeviceTestContext
import unittest
import os


class TestBasler(unittest.TestCase):
    def setUp(self, device_name="test/basler/test"):
        '''
        On Windows PowerShell, use $env:dn="test/basler/test" to pass device_name
        '''
        if 'dn' in os.environ:
            self.device_name = os.environ["dn"]
        else:
            self.device_name = device_name
        self.dp = tango.DeviceProxy(device_name)

    def test_read_ud_flip(self):
        self.assertFalse(self.dp.ud_flip)

    def test_read_model(self):
        self.assertTrue(isinstance(self.dp.model, str))
