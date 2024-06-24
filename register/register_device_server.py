import sys
import tango


def register_device(device):
    dev_info = tango.DbDevInfo()
    if device in reg_dict:
        for attr in reg_dict[device]:
            setattr(dev_info, attr, reg_dict[device][attr])
        db.add_device(dev_info)
        print(f'{device} is added')
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
            "basler": {'server': 'Basler/testsr', '_class': 'Basler', 'name': 'test/basler/1'},
            "basler_SF2": {'server': 'Basler/MA2', '_class': 'Basler', 'name': 'laser/basler/SF2'},
            "basler_MA2-Input": {'server': 'Basler/MA2', '_class': 'Basler', 'name': 'laser/basler/MA2-Input'},
            "basler_TA2-NearField": {'server': 'Basler/TA2-NearField', '_class': 'Basler', 'name': 'TA2/basler/TA2-NearField'},
            "basler_TA2-FarField": {'server': 'Basler/TA2-FarField', '_class': 'Basler', 'name': 'TA2/basler/TA2-FarField'},
            "camera": {'server': 'Camera/test', '_class': 'Camera', 'name': 'test/camera/1'},
            "gentec": {'server': 'GentecEO/testsr', '_class': 'GentecEO', 'name': 'test/gentec/1'},
            "gentec_MA1": {'server': 'GentecEO/MA1', '_class': 'GentecEO', 'name': 'laser/gentec/MA1'},
            "gentec_MA2": {'server': 'GentecEO/MA2', '_class': 'GentecEO', 'name': 'laser/gentec/MA2'},
            "gentec_MA3": {'server': 'GentecEO/MA3', '_class': 'GentecEO', 'name': 'laser/gentec/MA3'},
            "gentec_on_shot": {'server': 'GentecEO/Onshot', '_class': 'GentecEO', 'name': 'laser/gentec/Onshot'},
            "laser_warning_sign": {'server': 'LaserWarningSign/laser_warning_sign_sr', '_class': 'LaserWarningSign', 'name': 'facility/laser_warning_sign/1'},
            "waverunner_104mxi_1": {'server': 'LeCroy/old_scope', '_class': 'LeCroy', 'name': 'facility/lecroy/waverunner_104mxi_1'},
            "wavesurfer_3034z_1": {'server': 'LeCroy/wavesurfer_3034z_1', '_class': 'LeCroy', 'name': 'facility/lecroy/wavesurfer_3034z_1'},
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
