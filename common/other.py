from datetime import datetime


def generate_basename(rep: str, look_up: dict) -> str:
    '''
    if interpretation is not needed, i.e., without {}, use the passed arguments directly. Otherwise, get the attribute name first and replace attribute name in the argument with its value.
    '''
    basename = rep
    for c in look_up:
        if c in basename:

            if '{' not in look_up[c]:
                basename = basename.replace(
                    c, look_up[c])
            else:
                attr_name = look_up[c][look_up[c].find(
                    "{")+1:look_up[c].find("}")].split(':')[0]
                basename = basename.replace(
                    c,  look_up[c].replace(attr_name, '').format(getattr(look_up['device_proxy'], attr_name)))
    return basename
