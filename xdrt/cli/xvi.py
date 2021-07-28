# coding=utf-8
# Copyright (c) Jonas Teuwen
import argparse
import logging
import pathlib
import sys
from datetime import datetime

from xdrt.cli.utils import (
    BaseArgs,
    dir_path,
    read_xdr_as_simpleitk,
    setup_logging,
    write_dicom_image,
    write_simpleitk_image,
)
from xdrt.xvi_reader import XVIReconstruction


def read_xvi(input_folder) -> XVIReconstruction:
    try:
        xvi_reconstruction = XVIReconstruction(input_folder)
    except RuntimeError as e:
        logging.error(f"Loading XVI folder failed: {e}")
        sys.exit()

    return xvi_reconstruction


def write_to_dicom():
    """Console script for xdr2dcm."""
    base_parser = BaseArgs(
        "xvi2dcm reads folders, connects these to the underlying XDR files, and writes these to a directory "
        " in dicom."
    )

    parser = argparse.ArgumentParser(parents=[base_parser], add_help=True)
    parser.add_argument("INPUT_XVI", type=pathlib.Path, help="Path to XVI reconstruction folder.")
    parser.add_argument("OUTPUT_DIRECTORY", type=dir_path, help="Path to write output to.")

    args = parser.parse_args()
    setup_logging(args.verbose)
    logging.info(f"Reading {args.INPUT_XVI}...")
    xvi_reconstruction = read_xvi(args.INPUT_XVI)

    filename = xvi_reconstruction.scan.filename
    patient = xvi_reconstruction.patient

    # TODO: This is not a proper encoding for all names in different character sets
    patient_name = f"{patient.last_name.strip()}^{patient.first_name.strip()}"
    modification_time = xvi_reconstruction.scan.date_time.strftime("%H%M%S")
    modification_date = xvi_reconstruction.scan.date_time.strftime("%Y%m%d")

    dicom_dict = {
        "0010|0020": patient.patient_id,
        "0010|0010": patient_name,  # patient_name,
        "0010|0030": xvi_reconstruction.patient.date_of_birth.strftime("%Y%m%d"),  # Date of birth
        "0020|000d": xvi_reconstruction.scan.scan_uid,
        "0020|000e": "1.2.826.0.1.3680043.2.1126." + modification_date + ".1" + modification_time,
        "0020|0010": xvi_reconstruction.scan.scan_uid,
        "0008|0021": modification_date,  # Series date
        "0008|0031": modification_time,  # Series time
        "0008|0060": "CT",  # Modality
        "0008|0008": "DERIVED\\SECONDARY",
        "0008|1030": "XVI Reconstruct CBCT - XDRT conversion",  # Study Description
        "0008|103e": "XVI Reconstruct CBCT - XDRT conversion",  # Series Description
        "0028|1050": str(xvi_reconstruction.scan.level - 1024),  # window center
        "0028|1051": str(xvi_reconstruction.scan.window),  # window width
        "0028|1052": "-1024",  # Intercept
        "0028|1053": "1",  # Slope
    }

    # Read the XDR file
    sitk_image = read_xdr_as_simpleitk(
        filename,
        temporal_average=args.temporal_average,
        slope=args.slope,
        intercept=args.intercept,
        cast="uint16",
        no_header=args.no_header,
        original_orientation=args.original_orientation,
    )
    output_folder = args.OUTPUT_DIRECTORY / xvi_reconstruction.scan.scan_uid
    output_folder.mkdir(exist_ok=True)

    write_dicom_image(sitk_image, output_folder, metadata=dicom_dict)


def write_to_image():
    """Console script for xdr2img."""
    base_parser = BaseArgs(
        "xvi2img reads folders, connects these to the underlying XDR files, and writes these to a directory "
        " in another medical imaging format."
    )

    parser = argparse.ArgumentParser(parents=[base_parser], add_help=True)
    parser.add_argument("INPUT_XVI", type=pathlib.Path, help="Path to XVI reconstruction folder.")
    parser.add_argument("OUTPUT_FILE", type=pathlib.Path, help="Path to write output to.")

    args = parser.parse_args()
    setup_logging(args.verbose)
    logging.info(f"Reading {args.INPUT_XVI}...")
    extra_metadata = {}
    xvi_reconstruction = read_xvi(args.INPUT_XVI)

    reconstruction_dict = xvi_reconstruction.scan._asdict()
    filename = reconstruction_dict["filename"]

    # Read the XDR file
    sitk_image = read_xdr_as_simpleitk(
        filename,
        temporal_average=args.temporal_average,
        slope=args.slope,
        intercept=args.intercept,
        cast=args.cast,
        no_header=args.no_header,
        original_orientation=args.original_orientation,
    )

    if not args.no_header:
        _extra_metadata = {**xvi_reconstruction.patient._asdict(), **reconstruction_dict}
        for key, value in _extra_metadata.items():
            if isinstance(value, datetime):
                extra_metadata["XVI_" + key] = value.strftime("%d-%b-%Y (%H:%M:%S)")
            else:
                extra_metadata["XVI_" + key] = str(value)

    if args.no_origin:
        sitk_image.SetOrigin([0.0] * sitk_image.GetDimension())

    write_simpleitk_image(
        sitk_image,
        output_image=args.OUTPUT_FILE,
        no_compression=args.no_compression,
        extra_metadata=extra_metadata,
    )

    logging.info(f"Wrote output to {args.OUTPUT_FILE}.")

    return 0
