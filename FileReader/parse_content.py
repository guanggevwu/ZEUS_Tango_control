import numpy as np


def parse_tracklab_frame_data(text, width=None, index_offset=0):
	"""Parse the sparse TrackLab hit list into a 2D integer image.

	The detector file stores rows of the form:
	<flat_index> <timestamp> <channel> <intensity>
	followed by a footer line starting with "# Frame:". We keep only the flat
	pixel index and the intensity, then convert the index into a row-major 2D
	array with the usual zero-based mapping:
	index 0 -> [0, 0], index 1 -> [0, 1], ...
	"""
	if not text:
		return np.zeros((0, 0), dtype=np.uint16)

	records = []
	in_data_section = False

	for raw_line in text.splitlines():
		line = raw_line.strip()
		if not line:
			continue

		if line.startswith('# Frame:'):
			break

		if line.startswith('#') and '-' in line and line.count('-') > 20:
			in_data_section = True
			continue

		if not in_data_section or line.startswith('#'):
			continue

		parts = line.split()
		if not parts or not parts[0].strip():
			continue
		if len(parts) < 4:
			continue

		try:
			flat_index = int(parts[0])
			intensity = int(parts[3])
		except (TypeError, ValueError):
			continue

		records.append((flat_index, intensity))

	if not records:
		if width is None:
			width = 256
		return np.zeros((width, width), dtype=np.uint16)

	max_index = max(idx for idx, _ in records)
	if width is None:
		width = 256 if max_index < 256 * 256 else int(np.ceil(np.sqrt(max_index + 1)))

	image = np.zeros((width, width), dtype=np.int64)

	for idx, intensity in records:
		mapped_index = idx - index_offset
		if mapped_index < 0:
			continue
		row, col = divmod(mapped_index, width)
		if row >= width or col >= width:
			continue
		image[row, col] += intensity

	return image.astype(np.uint16, copy=False)
