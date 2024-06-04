import tango
import numpy as np
import scipy.ndimage as ndimage

from PIL import Image

# Maybe check/change the laser warning sign status before taking data
lws = tango.DeviceProxy('facility/laser_warning_sign/1')
if lws.clean_room != "danger":
    lws.clean_room = "danger"


bs = tango.DeviceProxy('test/basler/1')
bs.save_data = True
bs.trigger_selector = 'FrameStart'
bs.trigger_source = 'External'

# example for alignment
reference_image = np.array(Image.open("reference.tiff"))
while True:
    if bs.is_new_image:

        # corrx_map = ndimage.correlate(bs.image, reference_image)
        # displacement = find_peak(corrx_map) * resolution
        print(f"The current image is off-center for f{displacement}")
        move_translation_stage(displacement)
        break

# Other examples, e.g.
# We may also do an area scan and stitch them to get large-field-of-view and high-resolution image.
# We may do a delay timing scan to get the correct timing.
# We may do a distance scan to get the perfect focus distance.


# Example for save user data.
# The users may want  to save energy data along with their images.

energy_meter = tango.DeviceProxy('test/gentec/1')
while True:
    if bs.is_new_image:
        data = Image.fromarray(bs.image)
        energy = energy_meter.main_value
        data.save(f'xxxxx_{energy}.tiff')
        break
