from datetime import datetime


def generate_basename(rep: str, look_up: dict) -> str:
    # default to '%s' if rep is not set.
    basename = '%s' if not rep else rep
    for c in look_up:
        if c in basename:
            basename = basename.replace(
                c, look_up[c])
    return basename
