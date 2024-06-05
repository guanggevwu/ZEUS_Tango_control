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
        with open(os.path.join(save_path, f'run{run}_energy.csv'), 'a+', newline='') as csvfile:
            fieldnames = ['shot', 'run_shot', 'read_time', 'main_value']
            reader = csv.DictReader(csvfile)
            row = None
            for row in reader:
                pass
            if row is not None:
                previous_value = row['main_value']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not csvfile.tell():
                writer.writeheader()
            row_dict = {}
            for key in fieldnames:
                if key == 'run_shot':
                    row_dict[key] = f'run{run}_shot{shot}'
                else:
                    row_dict[key] = getattr(em, f'{key}')
                # validate
                if row is not None and previous_value == row_dict['main_value']:
                    print("Miss Fire!")
            writer.writerow(row_dict)
        shot += 1
