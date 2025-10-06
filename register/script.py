import sys
import tango


def register_device(device):
    dev_info = tango.DbDevInfo()
    if device in reg_dict:
        for attr in reg_dict[device]:
            if attr in ['server', '_class', 'name']:
                setattr(dev_info, attr, reg_dict[device][attr])
        db.add_device(dev_info)
        print(f'{device} is added')
        if "property" in reg_dict[device]:
            db.put_device_property(
                reg_dict[device]['name'], reg_dict[device]['property'])
            print(f'Property added. {reg_dict[device]["property"]}')
    else:
        print("wrong device name")


def delete_server(device):
    if device in reg_dict:
        db.delete_server(reg_dict[device]['server'])
        print(f'{device} deleted')


def get_properties(device):
    prop = db.get_device_property_list(reg_dict[device]['name'], '*')
    print(db.get_device_property(
        reg_dict[device]['name'], list(prop.value_string)))
    # db.get_device_property(device_name,[property_name]) : return {property_name : value}


def delete_properties(device, *args):
    if not len(args):
        prop = db.get_device_property_list(reg_dict[device]['name'], '*')
        db.delete_device_property(
            reg_dict[device]['name'], list(prop.value_string))
        print(f'{list(prop.value_string)} is deleted')
    elif len(args) == 1:
        db.delete_device_property(reg_dict[device]['name'], args[0])
        print(f'{args[0]} is deleted')


db = tango.Database()

# 'server', ServerName/Instance _class, class name in the code? 'name', domain/family/member?
reg_dict = {"power_supply": {'server': 'PowerSupply/testsr', '_class': 'PowerSupply', 'name': 'test/power_supply/1'},
            "power_supply_1": {'server': 'PowerSupply/testsr', '_class': 'PowerSupply', 'name': 'test/power_supply/2'},
            "basler_test": {'server': 'Basler/test', '_class': 'Basler', 'name': 'test/basler/test', 'property': {'friendly_name': 'test'}},
            "basler_SF2": {'server': 'Basler/MA2', '_class': 'Basler', 'name': 'laser/basler/SF2'},
            "basler_MA2-Input": {'server': 'Basler/MA2', '_class': 'Basler', 'name': 'laser/basler/MA2-Input'},
            "basler_3PW_Grating-4_NF": {'server': 'Basler/3PW_Grating-4_NF', '_class': 'Basler', 'name': 'laser/basler/3PW_Grating-4_NF'},
            "basler_3PW_Grating-4_FF": {'server': 'Basler/3PW_Grating-4_FF', '_class': 'Basler', 'name': 'laser/basler/3PW_Grating-4_FF'},
            "basler_3PW_Screen": {'server': 'Basler/3PW_Screen', '_class': 'Basler', 'name': 'laser/basler/3PW_Screen'},
            "basler_TA2-NearField": {'server': 'Basler/TA2-NearField', '_class': 'Basler', 'name': 'TA2/basler/TA2-NearField'},
            "basler_TA2-FarField": {'server': 'Basler/TA2-FarField', '_class': 'Basler', 'name': 'TA2/basler/TA2-FarField'},
            "basler_TA2-Alignment": {'server': 'Basler/TA2-Alignment', '_class': 'Basler', 'name': 'TA2/basler/TA2-Alignment'},
            "basler_TA2-GOSSIP": {'server': 'Basler/TA2-GOSSIP', '_class': 'Basler', 'name': 'TA2/basler/TA2-GOSSIP'},
            "basler_TA2-Screen-1w": {'server': 'Basler/TA2-Screen-1w', '_class': 'Basler', 'name': 'TA2/basler/TA2-Screen-1w', 'property': {'friendly_name': 'TA2-Screen-1w'}},
            "basler_TA2-Screen-2w": {'server': 'Basler/TA2-Screen-2w', '_class': 'Basler', 'name': 'TA2/basler/TA2-Screen-2w', 'property': {'friendly_name': 'TA2-Screen-2w'}},
            "basler_TA3-NearField": {'server': 'Basler/TA3-NearField', '_class': 'Basler', 'name': 'TA3/basler/TA3-NearField', 'property': {'friendly_name': 'TA3-NearField'}},
            "basler_TA3-Eprofile": {'server': 'Basler/TA3-Eprofile', '_class': 'Basler', 'name': 'TA3/basler/TA3-Eprofile', 'property': {'friendly_name': 'TA3-Eprofile'}},

            "basler_TA1-Ebeam": {'server': 'Basler/TA1-Ebeam', '_class': 'Basler', 'name': 'TA1/basler/TA1-Ebeam'},
            "basler_TA1-EspecH": {'server': 'Basler/TA1-EspecH', '_class': 'Basler', 'name': 'TA1/basler/TA1-EspecH'},
            "basler_TA1-EspecL": {'server': 'Basler/TA1-EspecL', '_class': 'Basler', 'name': 'TA1/basler/TA1-EspecL'},
            "basler_TA1-Shadowgraphy": {'server': 'Basler/TA1-Shadowgraphy', '_class': 'Basler', 'name': 'TA1/basler/TA1-Shadowgraphy'},
            "basler_TA1-MagnetScreen": {'server': 'Basler/TA1-MagnetScreen', '_class': 'Basler', 'name': 'TA1/basler/TA1-MagnetScreen'},
            "basler_TA1-SideView": {'server': 'Basler/TA1-SideView', '_class': 'Basler', 'name': 'TA1/basler/TA1-SideView'},
            "basler_TA1-TopView": {'server': 'Basler/TA1-TopView', '_class': 'Basler', 'name': 'TA1/basler/TA1-TopView'},
            "basler_TA1-Tape-Reflect": {'server': 'Basler/TA1-Tape-Reflect', '_class': 'Basler', 'name': 'TA1/basler/TA1-Tape-Reflect'},
            "basler_TA1-WedgeReflect": {'server': 'Basler/TA1-WedgeReflect', '_class': 'Basler', 'name': 'TA1/basler/TA1-WedgeReflect'},
            "basler_TA1-LYSO": {'server': 'Basler/TA1-LYSO', '_class': 'Basler', 'name': 'TA1/basler/TA1-LYSO'},
            "basler_TA1-LYSO-spec": {'server': 'Basler/TA1-LYSO-spec', '_class': 'Basler', 'name': 'TA1/basler/TA1-LYSO-spec'},
            "basler_TA1-DumpScreen": {'server': 'Basler/TA1-DumpScreen', '_class': 'Basler', 'name': 'TA1/basler/TA1-DumpScreen'},
            "basler_TA1_Gas_Cell_ft": {'server': 'Basler/TA1_Gas_Cell_ft', '_class': 'Basler', 'name': 'TA1/basler/TA1_Gas_Cell_ft'},
            "basler_TA1-Input_Ref.": {'server': 'Basler/TA1-Input_Ref.', '_class': 'Basler', 'name': 'TA1/basler/TA1-Input_Ref.'},
            "basler_TA1-Output_Ref.": {'server': 'Basler/TA1-Output_Ref.', '_class': 'Basler', 'name': 'TA1/basler/TA1-Output_Ref.'},
            "basler_TA1-Vac_gauge": {'server': 'Basler/TA1-Vac_gauge', '_class': 'Basler', 'name': 'TA1/basler/TA1-Vac_gauge'},
            "camera": {'server': 'Camera/test', '_class': 'Camera', 'name': 'test/camera/1'},
            "gentec": {'server': 'GentecEO/testsr', '_class': 'GentecEO', 'name': 'test/gentec/1'},
            "gentec_MA1": {'server': 'GentecEO/MA1', '_class': 'GentecEO', 'name': 'laser/gentec/MA1'},
            "gentec_MA2": {'server': 'GentecEO/MA2', '_class': 'GentecEO', 'name': 'laser/gentec/MA2'},
            "gentec_MA3_QE12": {'server': 'GentecEO/MA3_QE12', '_class': 'GentecEO', 'name': 'laser/gentec/MA3_QE12'},
            "gentec_MA3_QE195": {'server': 'GentecEO/MA3_QE195', '_class': 'GentecEO', 'name': 'laser/gentec/MA3_QE195'},
            "gentec_on_shot": {'server': 'GentecEO/Onshot', '_class': 'GentecEO', 'name': 'laser/gentec/Onshot'},
            "laser_warning_sign": {'server': 'LaserWarningSign/laser_warning_sign_sr', '_class': 'LaserWarningSign', 'name': 'facility/laser_warning_sign/1'},
            "waverunner_104mxi_1": {'server': 'LeCroy/old_scope', '_class': 'LeCroy', 'name': 'facility/lecroy/waverunner_104mxi_1'},
            "wavesurfer_3034z_1": {'server': 'LeCroy/wavesurfer_3034z_1', '_class': 'LeCroy', 'name': 'facility/lecroy/wavesurfer_3034z_1'},
            "dg535_test": {'server': 'DG535/testsr', '_class': 'DG535', 'name': 'test/dg535/1'},
            "esp300_test": {'server': 'ESP301/test', '_class': 'ESP301', 'name': 'test/esp300/esp300_test'},
            "esp300_turning_box3": {'server': 'ESP301/esp300_turning_box3', '_class': 'ESP301', 'name': 'test/esp300/esp300_turning_box3'},
            "file_reader_1": {'server': 'FileReader/file_reader_1', '_class': 'FileReader', 'name': 'facility/file_reader/file_reader_1'},
            "file_reader_2": {'server': 'FileReader/image_reader_2', '_class': 'FileReader', 'name': 'facility/file_reader/image_reader_2', 'property': {'file_type': 'image'}},
            "file_reader_3": {'server': 'FileReader/xy_reader', '_class': 'FileReader', 'name': 'facility/file_reader/xy_reader', 'property': {'file_type': 'xy'}},
            "file_reader_4": {'server': 'FileReader/TA1-wr9254', '_class': 'FileReader', 'name': 'facility/file_reader/TA1-wr9254', 'property': {'file_type': 'xy'}},
            "file_reader_5": {'server': 'FileReader/WinXP_cam', '_class': 'FileReader', 'name': 'facility/file_reader/WinXP_cam', 'property': {'file_type': 'image'}},
            "file_reader_6": {'server': 'FileReader/laser_axis', '_class': 'FileReader', 'name': 'facility/file_reader/laser_axis', 'property': {'file_type': 'image'}},
            "file_reader_7": {'server': 'FileReader/transverse', '_class': 'FileReader', 'name': 'facility/file_reader/transverse', 'property': {'file_type': 'image'}},
            "file_reader_8": {'server': 'FileReader/spectrometer', '_class': 'FileReader', 'name': 'facility/file_reader/spectrometer', 'property': {'file_type': 'xy'}},
            "file_reader_9": {'server': 'FileReader/TA3-Xray', '_class': 'FileReader', 'name': 'TA3/file_reader/TA3-Xray', 'property': {'file_type': 'image'}},

            "asyncio_device_1": {'server': 'AsyncioDevice/asyncio_device_1', '_class': 'AsyncioDevice', 'name': 'test/asyncio_device/asyncio_device_1'},
            "TA1_regulator_1": {'server': 'GXRegulator/TA1_regulator_1', '_class': 'GXRegulator', 'name': 'TA1/gx_regulator/TA1_regulator_1', 'property': {'high_voltage_channel': '0', 'low_voltage_channel': '1'}},
            "TA1_regulator_2": {'server': 'GXRegulator/TA1_regulator_2', '_class': 'GXRegulator', 'name': 'TA1/gx_regulator/TA1_regulator_2', 'property': {'high_voltage_channel': '2', 'low_voltage_channel': '3'}},
            "TA3_regulator_1": {'server': 'GXRegulator/TA3_regulator_1', '_class': 'GXRegulator', 'name': 'TA3/gx_regulator/TA3_regulator_1', 'property': {'high_voltage_channel': '0', 'low_voltage_channel': '1'}},
            "TA3_regulator_2": {'server': 'GXRegulator/TA3_regulator_2', '_class': 'GXRegulator', 'name': 'TA3/gx_regulator/TA3_regulator_2', 'property': {'high_voltage_channel': '2', 'low_voltage_channel': '3'}},
            "labview": {'server': 'LabviewPrograme/labview', '_class': 'LabviewPrograme', 'name': 'laser/labview/labview_programe', 'property': {'port': '61557'}},
            "taurus_test": {'server': 'TaurusTest/taurustest', '_class': 'TaurusTest', 'name': 'sys/taurustest/1'},
            "Vimba_TA2_1": {'server': 'Vimba/TA2-1', '_class': 'Vimba', 'name': 'TA2/vimba/TA2-1'},

            }


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("not enough input arguments")
    elif sys.argv[1] == "add":
        for i in sys.argv[2:]:
            register_device(i)
    elif sys.argv[1] == "delete":
        for i in sys.argv[2:]:
            delete_server(i)
    elif sys.argv[1] == "info":
        for i in sys.argv[2:]:
            get_properties(i)
