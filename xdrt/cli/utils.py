# coding=utf-8
# Copyright (c) Jonas Teuwen
import argparse
import logging
import pathlib
import sys

import SimpleITK as sitk

import xdrt
from xdrt import xdr_reader
from xdrt.utils import DATATYPES


def setup_logging(verbosity_level):
    levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    level = levels[min(len(levels) - 1, verbosity_level)]

    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")
    logging.warning("Beta software. In case you run into issues report at https://github.com/NKI-AI/xdrt/.")


def dir_path(path):
    path = pathlib.Path(path)
    if path.is_dir():
        return path
    raise argparse.ArgumentTypeError(f"{path} is not a valid directory.")


class BaseArgs(argparse.ArgumentParser):
    """
    Defines global default arguments.
    """

    def __init__(self, description=None, epilog=None, **overrides):
        """
        Parameters
        ----------
        epilog : str
        description : str
        overrides : (dict, optional)
            Keyword arguments used to override default argument values
        """
        super().__init__(
            description=description,
            epilog=epilog,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            add_help=False,
        )

        self.add_argument(
            "--no-compression",
            action="store_true",
            help="Do not compress output image. Otherwise, xdr2img will try to compress the image. "
            "Not all image formats support compression.",
        )
        self.add_argument(
            "--no-origin",
            action="store_true",
            help="If set, the origin will be set to 0. Can be convenient when the origin is erroneously parsed.",
        )
        self.add_argument(
            "--original-orientation",
            action="store_true",
            help="If set the orientation of the original underlying data format is not changed. "
            "Otherwise, it will be converted to LPS (recommended).",
        )
        self.add_argument(
            "--no-header",
            action="store_true",
            help="Do not write XDR header to output file.",
        )
        self.add_argument(
            "--temporal-average",
            type=str,
            help="Average along temporal dimension, "
            "either `weighted` to weight according to phase or `mean` for a normal average. "
            "Returns a float image.",
        )
        self.add_argument("--slope", type=float, help="Apply slope to the output image.")
        self.add_argument("--intercept", type=float, help="Apply intercept to the output image.")
        self.add_argument(
            "--cast",
            type=str,
            help=f"Cast the output. One of {', '.join(list(DATATYPES.keys()))}.",
        )
        self.add_argument("-v", "--verbose", action="count", help="Verbosity level", default=0)
        self.set_defaults(**overrides)


def read_xdr_as_simpleitk(input_xdr, temporal_average, slope, intercept, cast, no_header, original_orientation):
    try:
        xdr_image = xdr_reader.read(input_xdr, stop_before_data=False)
    except RuntimeError as e:
        sys.exit(f"error parsing {input_xdr}: {e}")
    except ValueError as e:
        sys.exit(f"error: {e}.")

    logging.info(f"{xdr_image.header.ndim}D image.")

    xdr_image = xdr_reader.postprocess_xdr_image(
        xdr_image,
        temporal_average=temporal_average,
        slope=slope,
        intercept=intercept,
        cast=cast,
    )

    sitk_image = xdrt.read_as_simpleitk(
        xdr_image,
        save_header=not no_header,
        lps_orientation=not original_orientation,
    )
    return sitk_image


def write_simpleitk_image(sitk_image, output_image, no_compression=False, extra_metadata=None):
    metadata = {k: sitk_image.GetMetaData(k) for k in sitk_image.GetMetaDataKeys()}
    for key, value in metadata.items():
        logging.info(f"{key}: {value}")

    try:
        writer = sitk.ImageFileWriter()
        writer.SetFileName(str(output_image))
        if not no_compression:
            logging.info("Writing with compression.")
            writer.UseCompressionOn()

        sitk_image.SetMetaData("Creator", f"xdrt {xdrt.__version__}")
        if extra_metadata:
            for k, v in extra_metadata.items():
                sitk_image.SetMetaData(k, str(v))

        writer.Execute(sitk_image)

    except RuntimeError as e:
        if "itk::ERROR: " in str(e):
            the_error = str(e).split("itk::ERROR: ")[-1]
            sys.exit(f"Error when writing {output_image}: {the_error}.")
        else:
            sys.exit(f"Unknown exception when writing {output_image}: {e}")
