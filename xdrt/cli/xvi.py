# coding=utf-8
# Copyright (c) Jonas Teuwen
import argparse
import logging
import math
import pathlib
import string
import sys

from xdrt.cli.utils import BaseArgs, dir_path, read_xdr_as_simpleitk, setup_logging, write_simpleitk_image
from xdrt.xvi_reader import XVIFile

XVI_ACQN_TAGS = [
    "datetime",
    "version",
    "fraction_number",
    "image_number_in_fraction",
    "acqpars",
    "protocol",
    "airvaluemeasured",
    "watervaluemeasured",
    "tubema",
    "tubekv",
    "tubekvlength",
    "fov",
]


def build_path(formatting, fraction_number, num_fractions, image_number, num_images):
    length_of_fractions = int(math.log10(num_fractions)) + 1
    length_of_images = int(math.log10(num_images)) + 1

    path_dictionary = {
        "image": f"{str(image_number).zfill(length_of_images)}",
        "fraction": f"{str(fraction_number).zfill(length_of_fractions)}",
    }

    # Parse per part in string
    path_builder = formatting.split("/")
    prefix = "/" if formatting[0] == "/" else ""
    output_path = pathlib.Path(prefix)

    for part in path_builder:
        # Check the keys in part
        keys_in_part = [t[1] for t in string.Formatter().parse(part) if t[1] is not None]

        if [_ for _ in keys_in_part if _ not in ["image", "fraction"]]:
            raise ValueError(f"{formatting} is malformed. Only 'image' and 'fraction' are supported as keys.")
        part = part.format(**{k: v for k, v in path_dictionary.items() if k in keys_in_part})

        output_path = output_path / part
    if not output_path.suffixes:
        raise ValueError(f"{formatting} is malformed. Requires an extension.")
    return output_path


def main():
    """Console script for xdr2img."""
    base_parser = BaseArgs(
        "xvi2img reads .xvi files, connects these to the underlying .XDR files, and writes these to a directory "
        " in another medical imaging format."
    )
    parser = argparse.ArgumentParser(parents=[base_parser], add_help=True)
    parser.add_argument("INPUT_XVI", type=pathlib.Path, help="Path to XVI file.")
    parser.add_argument("FILES_ROOT", type=dir_path, help="Path to corresponding XDR files.")
    parser.add_argument("OUTPUT_DIRECTORY", type=dir_path, help="Directory to write output to.")
    parser.add_argument(
        "--format",
        type=str,
        help="Formatting of the output directory structure. "
        "Supported keywords are 'fraction' and 'image' "
        "which denote the respective fraction and number, starting from 0.",
        default="fraction_{fraction}/CBCT_{image}.nrrd",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)
    logging.info(f"Reading {args.INPUT_XVI}...")

    try:
        xvi_file = XVIFile(xvi_filename=args.INPUT_XVI, files_root=args.FILES_ROOT)
    except RuntimeError as e:
        logging.error(f"Loading XVI file failed: {e}")
        sys.exit()
    except FileNotFoundError as e:
        logging.error(f"Could not find file: {e}")
        sys.exit()

    num_fractions = xvi_file.num_fractions
    num_scans = xvi_file.num_scans
    logging.info(f"Found {num_fractions} fractions and a total of {num_scans} scans.")

    # TODO: Matching information to CT scans must be saved.
    for idx, scan in enumerate(xvi_file.scans):
        original_xdr = scan.reconstruction
        path_to_save = args.OUTPUT_DIRECTORY / build_path(
            args.format,
            scan.fraction_number,
            num_fractions,
            scan.image_number_in_fraction,
            num_fractions,
        )
        path_to_save.parent.mkdir(exist_ok=True, parents=True)
        extra_metadata = {}
        if not args.no_header:
            for k in XVI_ACQN_TAGS:
                if hasattr(scan, k):
                    extra_metadata["XVI_" + k] = getattr(scan, k)
                    logging.info(f"XVI_{k}: {getattr(scan, k)}")

        logging.info(f"Scan {idx + 1}/{num_scans}: {original_xdr} -> {path_to_save}.")

        # Read the XDR file
        sitk_image = read_xdr_as_simpleitk(
            original_xdr,
            temporal_average=args.temporal_average,
            slope=args.slope,
            intercept=args.intercept,
            cast=args.cast,
            no_header=args.no_header,
            original_orientation=args.original_orientation,
        )

        if args.no_origin:
            sitk_image.SetOrigin([0.0] * sitk_image.GetDimension())

        write_simpleitk_image(
            sitk_image,
            path_to_save,
            no_compression=args.no_compression,
            extra_metadata=extra_metadata,
        )

        logging.info(f"Wrote output to {path_to_save}.")

    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
