import re


def get_axis_order(device, attributes):
    """Resolve Newport GUI ordering without changing controller axis mappings."""
    properties = device.get_property(['axis_property', 'axis_order'])
    axis_text = ','.join(properties.get('axis_property', [])).strip()
    order_text = ','.join(properties.get('axis_order', [])).strip()
    try:
        if axis_text:
            axes = [int(value.strip()) for value in axis_text.split(',')]
        else:
            axes = [int(match.group(1)) for name in attributes
                    if (match := re.fullmatch(r'ax(\d+)_position', name))]
        order = [int(value.strip()) for value in order_text.split(',')] if order_text else sorted(axes)
    except ValueError as exc:
        raise ValueError('axis_property and axis_order must be comma-separated axis numbers') from exc
    if len(order) != len(set(order)) or set(order) != set(axes):
        raise ValueError('axis_order must contain every configured axis exactly once')
    return order