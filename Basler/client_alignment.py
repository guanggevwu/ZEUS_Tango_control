import tango
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk
import tango
import scipy.ndimage as ndimage


class ImageOverlay:
    def __init__(self, root):
        self.dp = tango.DeviceProxy('test/basler/1')
        root.title("Image with overlay")
        frame1 = ttk.Frame(root, padding="3 3 12 12")
        frame1.grid(column=0, row=0)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        self.label = ttk.Label(root)
        self.label.grid(
            column=0, row=0, sticky='W')
        self.update()

    def update(self):
        if self.dp.is_new_image:
            self.tango_image = self.dp.image
            h, w = self.tango_image.shape
            cy, cx = [int(e) for e in ndimage.center_of_mass(self.tango_image)]
            print(np.mean(self.dp.image))
            # has to use add self. image is a local variable which gets garbage collected after the class is instantiated.

            # self.image = tk.PhotoImage(
            #     file=r'C:\Users\User\Downloads\Screenshot 2024-02-20 110546.png')
            # convert to RGB so that the overlay can have colors
            self.rgb_array = np.asarray(
                np.dstack((self.tango_image, self.tango_image, self.tango_image)), dtype=np.uint8)

            relative_x_height = self.relative_height(axis=0)
            relative_y_height = self.relative_height(axis=1)
            self.add_cross()
            for idx, p in enumerate(relative_x_height):
                self.rgb_array[h-p-1, idx, :] = [255, 0, 0]
            for idx, p in enumerate(relative_y_height):
                self.rgb_array[idx, p, :] = [255, 0, 0]
            self.rgb_array[cy-2:cy+3, cx-2:cx+3, :] = [255, 0, 0]
            img = Image.fromarray(self.rgb_array, 'RGB')
            self.image = ImageTk.PhotoImage(img)

            self.label['image'] = self.image
            # time.sleep(0.2)
        root.after(300, self.update)

    def relative_height(self, axis):
        profile = np.mean(self.tango_image, axis=axis)
        relative_height = ((profile-np.min(profile)) /
                           (np.max(profile)-np.min(profile))*len(profile)*0.3).astype(int)
        return relative_height

    def add_cross(self):
        self.rgb_array[int(self.rgb_array.shape[0]/2), :, :] = [0, 255, 0]
        self.rgb_array[:, int(self.rgb_array.shape[1]/2), :] = [0, 255, 0]


if __name__ == '__main__':
    root = tk.Tk()
    dummy = ImageOverlay(root)
    root.mainloop()
