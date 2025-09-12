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


def add_tango_device(server_class_name_property_input: dict):
    dev_info = tango.DbDevInfo()
    for attr in server_class_name_property_input:
        if attr in ['server', '_class', 'name']:
            setattr(dev_info, attr, server_class_name_property_input[attr])
    db.add_device(dev_info)
    print(f'{dev_info} is added')


def delete_server(server_instance):
    db.delete_server(server_instance)
    print(f'{server_instance} deleted')


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


if __name__ == "__main__":
    server_class_name_property_input = {
        'server': None, '_class': None, 'name': None}
    prompt_add_delete_show = "Add device (A/a), Delete device(D/d), or Quit (Q) ?\n"
    while True:
        user_input = input(prompt_add_delete_show)
        if user_input.lower() == 'a':
            info = {'Basler camera':
                    {'Please enter the camera name defined in Pylon Viewer.\n': 'friendly_name',
                     "Enter Y/y to use {tango_device_name} as the device name or manuallyenter the device name?\n": 'name'},
                    'Allied vision camera': {'Please enter the Tango device name in this format "**/vimba/**", for example "TA1/vimba/TA1_1".\n': 'full_name'}
                    }
            # prompt for device name
            prompt_device_type = "Enter number to choose device to add:\n" + \
                "\n".join(
                    [f"{idx}. {value}" for idx, value in enumerate(info.keys())]) + "\n"
            device_type_input = input(prompt_device_type)
            if not device_type_input.isdigit() or int(device_type_input) not in range(len(info)):
                print("Invalid device type. Please try again.")
                continue
            else:
                device_type = list(info.keys())[int(device_type_input)]
            if device_type == "Basler camera":
                server_class_name_property_input['property'] = {}
                # prompt for properties and device name
                for prompt, value in info[device_type].items():
                    if '{tango_device_name}' in prompt:
                        prompt = prompt.format(
                            tango_device_name=suggested_device_name)
                    user_input = input(prompt)
                    if value == 'friendly_name':
                        server_class_name_property_input['property'][value] = user_input
                        friendly_name = user_input
                        TA_search_patten = ['TA1', 'TA2',
                                            'TA3', 'laser', 'test', 'facility']
                        for ta in TA_search_patten:
                            if ta in user_input:
                                suggested_device_name = f'{ta}/basler/{user_input}'
                                break
                    elif (not user_input or user_input.lower() == 'y') and value == 'name':
                        server_class_name_property_input['name'] = suggested_device_name
                    elif user_input and value == 'name':
                        server_class_name_property_input['name'] = user_input
                server_class_name_property_input[
                    'server'] = f'Basler/{server_class_name_property_input["property"]["friendly_name"]}'
                server_class_name_property_input['_class'] = 'Basler'
                add_tango_device(server_class_name_property_input)
                if "property" in server_class_name_property_input:
                    db.put_device_property(
                        server_class_name_property_input['name'], server_class_name_property_input['property'])
                    print(
                        f'Property added. {server_class_name_property_input["property"]}')
            elif device_type == "Allied vision camera":
                # prompt for properties and device name
                for prompt, value in info[device_type].items():
                    user_input = input(prompt)
                    if user_input and value == 'full_name':
                        server_class_name_property_input['name'] = user_input
                server_class_name_property_input[
                    'server'] = f'Vimba/{user_input.split("/")[-1]}'
                server_class_name_property_input['_class'] = 'Vimba'
                add_tango_device(server_class_name_property_input)
            else:
                print("Currently only Basler camera is supported to add.")
                continue

        elif user_input.lower() == 'd':
            user_input = input("Show server/intance list? Y/N?")
            if user_input.lower() == 'y':
                servers = db.get_server_list()
                print("Current server/instance list:")
                for server in servers:
                    print(server)
            user_input = input("Enter server instance to delete: ")
            delete_server(user_input)
        # elif user_input.lower() == 'l':
        #     device_name = input("Enter device name to show info: ")
        #     get_properties(device_name)
        elif user_input.lower() == 'q':
            break
        else:
            print("Invalid input. Please try again.")

    # if len(sys.argv) == 1:
    #     print("not enough input arguments")
    # elif sys.argv[1] == "add":
    #     for i in sys.argv[2:]:
    #         register_device(i)
    # elif sys.argv[1] == "delete":
    #     for i in sys.argv[2:]:
    #         delete_server(i)
    # elif sys.argv[1] == "info":
    #     for i in sys.argv[2:]:
    #         get_properties(i)
