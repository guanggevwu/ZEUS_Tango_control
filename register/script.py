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
            "basler_TA2-Screen-1w": {'server': 'Basler/TA2-Screen-1w', '_class': 'Basler', 'name': 'TA2/basler/TA2-Screen-1w', 'property': {'friendly_name': 'TA2-Screen-1w'}},
            "basler_TA2-Screen-2w": {'server': 'Basler/TA2-Screen-2w', '_class': 'Basler', 'name': 'TA2/basler/TA2-Screen-2w', 'property': {'friendly_name': 'TA2-Screen-2w'}},
            "basler_TA3-NearField": {'server': 'Basler/TA3-NearField', '_class': 'Basler', 'name': 'TA3/basler/TA3-NearField', 'property': {'friendly_name': 'TA3-NearField'}},
            "basler_TA3-Eprofile": {'server': 'Basler/TA3-Eprofile', '_class': 'Basler', 'name': 'TA3/basler/TA3-Eprofile', 'property': {'friendly_name': 'TA3-Eprofile'}},
            "basler_test": {'server': 'Basler/basler_test', '_class': 'Basler', 'name': 'test/basler/basler_test', 'property': {'friendly_name': 'test'}},


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
            "esp302_test": {'server': 'ESP301/esp302_test', '_class': 'ESP301', 'name': 'test/esp301/esp302_test', 'property': {'ip': '192.168.131.75'}},
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
            "owis_test": {'server': 'OwisPS/test', '_class': 'OwisPS', 'name': 'test/owisps/test', 'property': {'axis': '1,2', 'part_number': 'S41.N29.08BH.V6'}},
            "owis_TA1_1": {'server': 'OwisPS/TA1-owis1', '_class': 'OwisPS', 'name': 'TA!/owisps/TA1-owis1', 'property': {'axis': '1,2,3,4,5,6,7,8,9', 'part_number': 'S41.N29.08BH.V6,S41.N29.08BH.V6,S41.N29.08BH.V6,S41.N29.08BH.V6,S41.N29.08BH.V6,S41.N29.08BH.V6,S41.N29.08BH.V6,S41.N29.08BH.V6,S41.N29.08BH.V6'}},
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
