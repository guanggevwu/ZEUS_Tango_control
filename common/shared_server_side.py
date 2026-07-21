import numpy as np
from skimage.morphology import erosion, reconstruction
from skimage.morphology.footprints import square
from tango import AttrWriteType
from tango.server import attribute


def add_center_of_mass_functions(cls):
    """Add center-of-mass attributes and helper methods to an image Tango device class.

    The decorated class should call ``self.initialize_center_of_mass_attributes()``
    from ``initialize_dynamic_attributes()`` when the center-of-mass attributes
    should be exposed. It should also call ``self.calculate_center_of_mass()`` after updating
    ``self._image``.
    """
    cls.initialize_center_of_mass_attributes = initialize_center_of_mass_attributes
    cls.read_center_of_mass_x = read_center_of_mass_x
    cls.read_center_of_mass_y = read_center_of_mass_y
    cls.read_CoM_filter_low = read_CoM_filter_low
    cls.write_CoM_filter_low = write_CoM_filter_low
    cls.read_CoM_filter_percentile_low = read_CoM_filter_percentile_low
    cls.write_CoM_filter_percentile_low = write_CoM_filter_percentile_low
    cls.read_CoM_filter_high = read_CoM_filter_high
    cls.write_CoM_filter_high = write_CoM_filter_high
    cls.read_CoM_filter_percentile_high = read_CoM_filter_percentile_high
    cls.write_CoM_filter_percentile_high = write_CoM_filter_percentile_high
    cls.read_remove_small_objects = read_remove_small_objects
    cls.write_remove_small_objects = write_remove_small_objects
    cls.calculate_center_of_mass = calculate_center_of_mass
    return cls


def initialize_center_of_mass_attributes(self):
    center_of_mass_x = attribute(
        name='center_of_mass_x',
        label="center of mass x",
        dtype=float,
        access=AttrWriteType.READ,
        doc='x coordinate of the center of mass. Top left of the image is defined as (0, 0)',
    )

    center_of_mass_y = attribute(
        name='center_of_mass_y',
        label="center of mass y",
        dtype=float,
        access=AttrWriteType.READ,
        doc='y coordinate of the center of mass. Top left of the image is defined as (0, 0)',
    )

    CoM_filter_low = attribute(
        name='CoM_filter_low',
        label="CoM filter low",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        format='8.1f',
        memorized=True,
        hw_memorized=True,
        doc='Pixels that have intensity lower than this value will be set as 0 when calculating the center of mass. CoM_filter_low and CoM_filter_percentile_low are interdependent.',
    )

    CoM_filter_percentile_low = attribute(
        name='CoM_filter_percentile_low',
        label="CoM filter percentile low",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        format='8.6f',
        memorized=True,
        hw_memorized=True,
        doc='Pixels that have intensity below this percentile will be set as 0 when calculating the center of mass. Default value is 0.999 (99.9th percentile). CoM_filter_low and CoM_filter_percentile_low are interdependent.',
    )

    CoM_filter_high = attribute(
        name='CoM_filter_high',
        label="CoM filter high",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        format='8.1f',
        memorized=True,
        hw_memorized=True,
        doc='Pixels that have intensity higher than this value will be set as 0 when calculating the center of mass. CoM_filter_high and CoM_filter_percentile_high are interdependent.',
    )

    CoM_filter_percentile_high = attribute(
        name='CoM_filter_percentile_high',
        label="CoM filter percentile high",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        format='8.6f',
        memorized=True,
        hw_memorized=True,
        doc='Pixels that have intensity above this percentile will be set as 0 when calculating the center of mass. Default value is 1.0 (100th percentile). CoM_filter_high and CoM_filter_percentile_high are interdependent.',
    )

    remove_small_objects = attribute(
        name='remove_small_objects',
        label="remove small objects",
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
        memorized=True,
        hw_memorized=True,
        doc='Use erosion and reconstruction to remove small bright objects before calculating the center of mass.',
    )

    self._center_of_mass_x = 0
    self._center_of_mass_y = 0
    self._CoM_filter_low = 0.0
    self._CoM_filter_percentile_low = 0.999
    self._CoM_filter_low_source = 'percentile'
    self._CoM_filter_high = 999999.0
    self._CoM_filter_percentile_high = 1.0
    self._CoM_filter_high_source = 'value'
    self._remove_small_objects = False
    self.add_attribute(center_of_mass_x)
    self.add_attribute(center_of_mass_y)
    self.add_attribute(CoM_filter_low)
    self.add_attribute(CoM_filter_percentile_low)
    self.add_attribute(CoM_filter_high)
    self.add_attribute(CoM_filter_percentile_high)
    self.add_attribute(remove_small_objects)


def read_center_of_mass_x(self, attr=None):
    return self._center_of_mass_x


def read_center_of_mass_y(self, attr=None):
    return self._center_of_mass_y


def read_CoM_filter_low(self, attr=None):
    return self._CoM_filter_low


def write_CoM_filter_low(self, attr):
    value = attr.get_write_value() if hasattr(attr, 'get_write_value') else attr
    self._CoM_filter_low = float(value)
    self._CoM_filter_low_source = 'value'
    self.calculate_center_of_mass()


def read_CoM_filter_percentile_low(self, attr=None):
    return self._CoM_filter_percentile_low


def write_CoM_filter_percentile_low(self, attr):
    value = attr.get_write_value() if hasattr(attr, 'get_write_value') else attr
    value = float(value)
    if not 0.0 <= value <= 1.0:
        raise ValueError('CoM_filter_percentile_low must be within [0, 1].')
    self._CoM_filter_percentile_low = value
    self._CoM_filter_low_source = 'percentile'
    self.calculate_center_of_mass()


def read_CoM_filter_high(self, attr=None):
    return self._CoM_filter_high


def write_CoM_filter_high(self, attr):
    value = attr.get_write_value() if hasattr(attr, 'get_write_value') else attr
    self._CoM_filter_high = float(value)
    self._CoM_filter_high_source = 'value'
    self.calculate_center_of_mass()


def read_CoM_filter_percentile_high(self, attr=None):
    return self._CoM_filter_percentile_high


def write_CoM_filter_percentile_high(self, attr):
    value = attr.get_write_value() if hasattr(attr, 'get_write_value') else attr
    value = float(value)
    if not 0.0 <= value <= 1.0:
        raise ValueError('CoM_filter_percentile_high must be within [0, 1].')
    self._CoM_filter_percentile_high = value
    self._CoM_filter_high_source = 'percentile'
    self.calculate_center_of_mass()


def read_remove_small_objects(self, attr=None):
    return self._remove_small_objects


def write_remove_small_objects(self, attr):
    value = attr.get_write_value() if hasattr(attr, 'get_write_value') else attr
    self._remove_small_objects = bool(value)
    self.calculate_center_of_mass()


def update_CoM_filter_low_from_percentile(self, image):
    self._CoM_filter_low = float(np.percentile(
        image, self._CoM_filter_percentile_low * 100.0))


def update_CoM_filter_percentile_low_from_filter(self, image):
    self._CoM_filter_percentile_low = float(
        np.count_nonzero(image <= self._CoM_filter_low) / image.size)


def update_CoM_filter_high_from_percentile(self, image):
    self._CoM_filter_high = float(np.percentile(
        image, self._CoM_filter_percentile_high * 100.0))


def update_CoM_filter_percentile_high_from_filter(self, image):
    self._CoM_filter_percentile_high = float(
        np.count_nonzero(image <= self._CoM_filter_high) / image.size)


def calculate_center_of_mass(self):
    if hasattr(self, '_center_of_mass_x') and hasattr(self, '_image'):
        image = np.squeeze(np.asarray(self._image))
        if image.ndim != 2 or image.size == 0:
            self._center_of_mass_x = 0
            self._center_of_mass_y = 0
            self._CoM_filter_low = 0.0
            self._CoM_filter_high = 999999.0
            return

        image = image.astype(np.float64, copy=False)
        if not np.isfinite(image).all():
            self._center_of_mass_x = 0
            self._center_of_mass_y = 0
            self._CoM_filter_low = 0.0
            self._CoM_filter_high = 999999.0
            return

        if getattr(self, '_CoM_filter_low_source', 'percentile') == 'value':
            update_CoM_filter_percentile_low_from_filter(self, image)
        else:
            update_CoM_filter_low_from_percentile(self, image)
        if getattr(self, '_CoM_filter_high_source', 'value') == 'value':
            update_CoM_filter_percentile_high_from_filter(self, image)
        else:
            update_CoM_filter_high_from_percentile(self, image)
        mask = (image >= self._CoM_filter_low) & (
            image <= self._CoM_filter_high)
        if not np.any(mask):
            max_index = np.unravel_index(np.argmax(image), image.shape)
            self._center_of_mass_x = float(max_index[1])
            self._center_of_mass_y = float(max_index[0])
            return

        masked_image = image * mask
        if self._remove_small_objects:
            seed = erosion(masked_image, square(3))
            masked_image = reconstruction(seed, masked_image)
        total_intensity = np.sum(masked_image)
        if total_intensity <= 0:
            max_index = np.unravel_index(np.argmax(image), image.shape)
            self._center_of_mass_x = float(max_index[1])
            self._center_of_mass_y = float(max_index[0])
            return

        yy, xx = np.indices(image.shape)
        self._center_of_mass_x = np.sum(xx * masked_image) / total_intensity
        self._center_of_mass_y = np.sum(yy * masked_image) / total_intensity
        self.push_change_event(
            "center_of_mass_x", self.read_center_of_mass_x())
        self.push_change_event(
            "center_of_mass_y", self.read_center_of_mass_y())
        self.push_change_event("CoM_filter_low",
                               self.read_CoM_filter_low())
        self.push_change_event("CoM_filter_percentile_low",
                               self.read_CoM_filter_percentile_low())
        self.push_change_event("CoM_filter_high",
                               self.read_CoM_filter_high())
        self.push_change_event("CoM_filter_percentile_high",
                               self.read_CoM_filter_percentile_high())
