import tango
import numpy as np
import scipy.ndimage as ndimage
import os
import csv
from PIL import Image


run, shot = 1, 1
bs = tango.DeviceProxy('test/basler/1')
bs.trigger_selector = 'FrameStart'
bs.trigger_source = 'Software'
bs.is_polling_periodically = False
save_path = r'C:\Users\User\Desktop\tmp\tango_save_path'
em = tango.DeviceProxy('test/gentec/1')

while True:
    if bs.is_new_image:
        # save image
        if bs.format_pixel.lower() == 'mono8':
            current_image = bs.image.astype('uint8')
        data = Image.fromarray(current_image)
        data.save(os.path.join(save_path, f'run{run}shot{shot}_image.tiff'))
        # save energy meter reading
        with open(os.path.join(save_path, f'run{run}shot{shot}_energy.csv'), 'w+', newline='') as csvfile:
            fieldnames = ['read_time', 'main_value']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            row_dict = {}
            for key in fieldnames:
                row_dict[key] = getattr(em, f'{key}')
            writer.writerow(row_dict)
        shot += 1
