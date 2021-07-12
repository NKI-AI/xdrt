# coding=utf-8
# Copyright (c) Jonas Teuwen
import re
from datetime import datetime

import numpy as np

DATATYPES = {
    "int16": np.int16,
    "int32": np.int32,
    "int64": np.int64,
    "uint16": np.uint16,
    "uint32": np.uint32,
    "float32": np.float32,
    "float64": np.float64,
}


def camel_to_snake(name):
    # From: https://stackoverflow.com/a/1176023
    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()


def parse_xvi_datetime(datetime_str):
    if "; " in datetime_str:
        datetime_strp_str = "%Y%m%d; %H:%M:%S"
    else:
        datetime_strp_str = "%Y%m%d_%H:%M:%S"

    return datetime.strptime(datetime_str, datetime_strp_str) if datetime_str else None


def parse_xvi_url(url):
    url_parsed = {}
    for elem in url.split("\\"):
        name = elem.split(".")[-1]
        value = elem[: -len(name) - 1]
        if name == "patient":
            planning_part = "[DICOM planning]:"
            if planning_part not in url:
                raise NotImplementedError(
                    "Cannot handle patient ids not associated with DICOM planning scans. "
                    "If you want to handle such cases, "
                    "consider opening an issue on https://github.com/NKI-AI/xdrt/issues."
                )
            url_parsed[name] = value.split(":")[-1]
        else:
            url_parsed[name] = value

    return url_parsed


def make_integer(z):
    if z.is_integer():
        return int(z)
    return z
