import numpy as np
from tango import AttrWriteType
from tango.server import attribute


def add_centroid_functions(cls):
	"""Add centroid attributes and helper methods to an image Tango device class.

	The decorated class should call ``self.initialize_centroid_attributes()``
	from ``initialize_dynamic_attributes()`` when the centroid attributes should
	be exposed. It should also call ``self.calculate_centroid()`` after updating
	``self._image``.
	"""
	cls.initialize_centroid_attributes = initialize_centroid_attributes
	cls.read_centroid_x = read_centroid_x
	cls.read_centroid_y = read_centroid_y
	cls.read_centroid_threshold = read_centroid_threshold
	cls.read_threshold_percentile = read_threshold_percentile
	cls.write_threshold_percentile = write_threshold_percentile
	cls.calculate_centroid = calculate_centroid
	return cls


def initialize_centroid_attributes(self):
	centroid_x = attribute(
		name='centroid_x',
		label="centroid x",
		dtype=float,
		access=AttrWriteType.READ,
		doc='x coordinate of the centroid. Top left of the image is defined as (0, 0)',
	)

	centroid_y = attribute(
		name='centroid_y',
		label="centroid y",
		dtype=float,
		access=AttrWriteType.READ,
		doc='y coordinate of the centroid. Top left of the image is defined as (0, 0)',
	)

	centroid_threshold = attribute(
		name='centroid_threshold',
		label="centroid threshold",
		dtype=float,
		access=AttrWriteType.READ,
		doc='threshold intensity for the centroid calculation',
	)

	threshold_percentile = attribute(
		name='threshold_percentile',
		label="threshold percentile",
		dtype=float,
		access=AttrWriteType.READ_WRITE,
		format='8.4f',
		memorized=True,
		hw_memorized=True,
		doc='Threshold percentile as a fraction in [0, 1]. Default value is 0.999 (99.9th percentile).',
	)

	self._centroid_x = 0
	self._centroid_y = 0
	self._centroid_threshold = 0.0
	self._threshold_percentile = 0.999
	self.add_attribute(centroid_x)
	self.add_attribute(centroid_y)
	self.add_attribute(centroid_threshold)
	self.add_attribute(threshold_percentile)


def read_centroid_x(self, attr=None):
	return self._centroid_x


def read_centroid_y(self, attr=None):
	return self._centroid_y


def read_centroid_threshold(self, attr=None):
	return self._centroid_threshold


def read_threshold_percentile(self, attr=None):
	return self._threshold_percentile


def write_threshold_percentile(self, attr):
	value = attr.get_write_value() if hasattr(attr, 'get_write_value') else attr
	value = float(value)
	if not 0.0 <= value <= 1.0:
		raise ValueError('threshold_percentile must be within [0, 1].')
	self._threshold_percentile = value
	self.calculate_centroid()


def calculate_centroid(self):
	if hasattr(self, '_centroid_x') and hasattr(self, '_image'):
		image = np.squeeze(np.asarray(self._image))
		if image.ndim != 2 or image.size == 0:
			self._centroid_x = 0
			self._centroid_y = 0
			self._centroid_threshold = 0.0
			return self._centroid_x, self._centroid_y, self._centroid_threshold

		image = image.astype(np.float64, copy=False)
		if not np.isfinite(image).all():
			self._centroid_x = 0
			self._centroid_y = 0
			self._centroid_threshold = 0.0
			return self._centroid_x, self._centroid_y, self._centroid_threshold

		self._centroid_threshold = float(np.percentile(
			image, self._threshold_percentile * 100.0))
		mask = image >= self._centroid_threshold
		if not np.any(mask):
			max_index = np.unravel_index(np.argmax(image), image.shape)
			self._centroid_x = float(max_index[1])
			self._centroid_y = float(max_index[0])
			return self._centroid_x, self._centroid_y, self._centroid_threshold

		masked_image = image * mask
		total_intensity = np.sum(masked_image)
		if total_intensity <= 0:
			max_index = np.unravel_index(np.argmax(image), image.shape)
			self._centroid_x = float(max_index[1])
			self._centroid_y = float(max_index[0])
			return self._centroid_x, self._centroid_y, self._centroid_threshold

		yy, xx = np.indices(image.shape)
		self._centroid_x = np.sum(xx * masked_image) / total_intensity
		self._centroid_y = np.sum(yy * masked_image) / total_intensity
		self.push_change_event("centroid_x", self.read_centroid_x())
		self.push_change_event("centroid_y", self.read_centroid_y())
		self.push_change_event("centroid_threshold",
							   self.read_centroid_threshold())
		return self._centroid_x, self._centroid_y, self._centroid_threshold
