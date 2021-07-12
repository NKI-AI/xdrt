# coding=utf-8
# Copyright (c) Jonas Teuwen
import argparse
import logging
import pathlib
import sys

from xdrt.cli.utils import BaseArgs, read_xdr_as_simpleitk, setup_logging, write_simpleitk_image


def main():
    """Console script for xdr2img."""
    base_parser = BaseArgs("xdr2img converts XDR images to other medical imaging formats.")
    parser = argparse.ArgumentParser(parents=[base_parser], add_help=True)
    parser.add_argument("INPUT_XDR", type=pathlib.Path, help="Path to XDR file.")
    parser.add_argument(
        "OUTPUT_IMAGE",
        type=pathlib.Path,
        help="Path to output image including extension.",
    )
    args = parser.parse_args()
    setup_logging(args.verbose)

    logging.info(f"Reading {args.INPUT_XDR}...")

    sitk_image = read_xdr_as_simpleitk(
        args.INPUT_XDR,
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
        args.OUTPUT_IMAGE,
        no_compression=args.no_compression,
        extra_metadata=None,
    )

    logging.info(f"Wrote output to {args.OUTPUT_IMAGE}.")

    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
