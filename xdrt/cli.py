# coding=utf-8
import argparse
import sys
import pathlib
import xdrt
import SimpleITK as sitk
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


def main():
    """Console script for xdr2img."""
    parser = argparse.ArgumentParser(
        description="xdr2img converts XDR images to other medical imaging formats."
    )
    parser.add_argument("INPUT_XDR", type=pathlib.Path, help="Path to XDR file.")
    parser.add_argument(
        "OUTPUT_IMAGE",
        type=pathlib.Path,
        help="Path to output image including extension.",
    )
    parser.add_argument(
        "--no-compression",
        action="store_true",
        help="Do not compress output image. Otherwise, xdr2img will try to compress the image. "
        "Not all image formats support compression.",
    )
    parser.add_argument(
        "--no-origin",
        action="store_true",
        help="If set, the origin will be set to 0. Can be convenient when the origin is erroneously parsed.",
    )
    parser.add_argument(
        "--original-orientation",
        action="store_true",
        help="If set the orientation of the original underlying data format is not changed. "
        "Otherwise, it will be converted to LPS (recommended).",
    )
    parser.add_argument(
        "--no-header",
        action="store_true",
        help="Do not write XDR header to output file.",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose mode.")
    parser.add_argument(
        "--temporal-average",
        type=str,
        help="Average along temporal dimension, "
        "either `weighted` to weight according to phase or `mean` for a normal average. "
        "Returns a float image.",
    )
    parser.add_argument("--slope", type=float, help="Apply slope to the output image.")
    parser.add_argument(
        "--intercept", type=float, help="Apply intercept to the output image."
    )
    parser.add_argument(
        "--cast",
        type=str,
        help=f"Cast the output. One of {', '.join(list(DATATYPES.keys()))}.",
    )

    args = parser.parse_args()
    global verbose
    verbose = args.verbose

    print_verbose(f"Reading {args.INPUT_XDR}...")

    try:
        sitk_image = xdrt.read_as_simpleitk(
            args.INPUT_XDR,
            save_header=not args.no_header,
            lps_orientation=not args.original_orientation,
        )
    except RuntimeError as e:
        sys.exit(f"xdr2img: error parsing {args.INPUT_XDR}: {e}")
    except ValueError as e:
        sys.exit(f"xdr2img: error: {e}.")

    # Filters remove metadata
    metadata = {k: sitk_image.GetMetaData(k) for k in sitk_image.GetMetaDataKeys()}
    for key, value in metadata.items():
        print_verbose(f"{key}: {value}")

    print_verbose(f"{sitk_image.GetDimension()}D image.")

    if args.temporal_average:
        print_verbose(f"Computing temporal average: {args.temporal_average}.")

        if args.temporal_average not in ["mean", "weighted"]:
            sys.exit(
                f"xdr2img: error: --temporal-average must be either `mean` or `weighted`."
            )

        if sitk_image.GetDimension() != 4:
            sys.exit(
                f"xdr2img: error: --temporal-average can only be used with 4D images."
            )

        weights = 1.0
        if args.temporal_average == "weighted":
            if "phase" not in sitk_image.GetMetaDataKeys():
                print("Phase is not available. Temporal average will be mean.")
            else:
                weights = np.asarray(
                    [float(_) for _ in sitk_image.GetMetaData("phase").split(" ")]
                )

        sitk_image = apply_numpy_to_sitk(
            sitk_image, lambda x: (weights * x.T).T.sum(axis=0)[np.newaxis, ...]
        )[:, :, :, 0]

    if args.no_origin:
        sitk_image.SetOrigin([0.0] * sitk_image.GetDimension())

    if args.slope:
        print_verbose(f"Slope set: {args.slope}.")
        sitk_image = apply_numpy_to_sitk(
            sitk_image, lambda x: x * make_integer(args.slope)
        )

    if args.intercept:
        print_verbose(f"Intercept set: {args.intercept}.")
        sitk_image = apply_numpy_to_sitk(
            sitk_image, lambda x: x + make_integer(args.intercept)
        )

    if args.cast:
        print_verbose(f"Casting to: {args.cast}.")
        if args.cast not in list(DATATYPES.keys()):
            sys.exit(
                f"xdr2img: error: Expected casting type to be one of {list(DATATYPES.keys())}. Got {args.cast}."
            )
        sitk_image = apply_numpy_to_sitk(
            sitk_image, lambda x: x.astype(DATATYPES[args.cast])
        )

    try:
        writer = sitk.ImageFileWriter()
        writer.SetFileName(str(args.OUTPUT_IMAGE))
        if not args.no_compression:
            print_verbose("Writing with compression.")
            writer.UseCompressionOn()

        for k, v in metadata.items():
            sitk_image.SetMetaData(k, v)

        writer.Execute(sitk_image)

    except RuntimeError as e:
        if "itk::ERROR: " in str(e):
            the_error = str(e).split("itk::ERROR: ")[-1]
            sys.exit(f"xdr2img: error when writing {args.OUTPUT_IMAGE}: {the_error}.")
        else:
            sys.exit(
                f"xdr2img: unknown exception when writing {args.OUTPUT_IMAGE}: {e}"
            )

    print_verbose(f"Wrote output to {args.OUTPUT_IMAGE}.")

    return 0


# This is easier with ITK
def apply_numpy_to_sitk(sitk_image, numpy_func):
    """Apply a simple function to the underlying numpy array"""
    data = sitk.GetArrayFromImage(sitk_image)

    origin = sitk_image.GetOrigin()
    direction = sitk_image.GetDirection()
    spacing = sitk_image.GetSpacing()

    metadata = {k: sitk_image.GetMetaData(k) for k in sitk_image.GetMetaDataKeys()}

    data_out = numpy_func(data)
    assert (
        data_out.ndim == data.ndim
    ), "can only use this function when spatial shapes do not change."

    # TODO: There are also RLE types at the end of the range
    sitk_image = sitk.GetImageFromArray(
        data_out, isVector=sitk_image.GetPixelIDValue() > 9
    )
    sitk_image.SetOrigin(origin)
    sitk_image.SetDirection(direction)
    sitk_image.SetSpacing(spacing)

    for k, v in metadata.items():
        sitk_image.SetMetaData(k, v)

    return sitk_image


def make_integer(z):
    if z.is_integer():
        return int(z)
    return z


def print_verbose(string):
    if verbose:
        print(f"INFO: {string}")


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
