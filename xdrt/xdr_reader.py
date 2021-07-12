# coding=utf-8
# Copyright (c) Jonas Teuwen
import ctypes
import logging
import string
import sys
import warnings
from os import path
from pathlib import Path

import numpy as np
import SimpleITK as sitk

from xdrt.utils import DATATYPES, camel_to_snake, make_integer

nki_decompression_available = False
try:
    EXT = {"win32": "dll", "linux": "so", "darwin": "dylib"}
    nki_decompress_lib = f"libnkidecompress.{EXT[sys.platform]}"
    nki_compression = ctypes.cdll.LoadLibrary(
        Path(path.dirname(path.abspath(__file__))).parent / "lib" / nki_decompress_lib  # type: ignore
    )
    nki_decompression_available = True
except (ImportError, OSError) as e:
    warnings.warn(f"Decompression library not available. Will not be able to read compressed XDR: {e}.")

XDR_DTYPE_TO_PYTHON = {
    "xdr_real": "f4",
    "xdr_float": "f4",
    "xdr_double": "f8",
    "xdr_short": "i2",
    "xdr_integer": "i4",
    "byte": "uint8",
}

XDR_METADATA_KEYS = [
    "#$VERSION",
    "#$PATIENT_ID",
    "#$VOLUME_ID",
    "#$DATE",
    "#$TIME",
    "#$MODALITY",
    "#$XYZ_ORIENT",
    "#$LOCATION",
    "#$SLICE_AXIS",
    "#$VOL_FORMAT",
    "#$PAT_SYSTEM",
    "#$PAT_TO_WLD",
    "#$OWNER",
    "#$SOURCE",
    "#$COMMENT",
]

SIDDON_TO_DICOM = np.asarray([[1, 0, 0], [0, 0, -1], [0, 1, 0]])


class XDRImage:
    def __init__(self, header, data=None):
        """Placeholder for the XDR Image."""
        self.header = header
        self.data = data


class XDRHeader:
    def __init__(self, header_dict):
        self.__header_dict = header_dict
        self.__parse_header()

        self.min_ext = []
        self.max_ext = []

        self.phase = None

    def __parse_header(self):
        if "#$$url" in self.__header_dict:
            self.url = self.__header_dict["#$$url"].strip()

        required_keys = ["ndim", "field"]
        for required_key in required_keys:
            if required_key not in self.__header_dict:
                raise IOError(f"`{required_key}` is required in XDR header.")

        if self.__header_dict["field"] not in ["uniform", "rectilinear"]:
            raise NotImplementedError(f"field {self.__header_dict['field']} not supported.")

        if self.__header_dict["field"] == "rectilinear":
            warnings.warn(
                "field is `rectilinear`, this is only partly supported and currently handled as `uniform`. "
                "Likely this does not work. Create an issue at https://github.com/NKI-AI/xdrt/issues "
                "if your application requires this."
            )
        self.field = self.__header_dict["field"]

        self.ndim = int(self.__header_dict["ndim"])
        dim_names = [f"dim{idx + 1}" for idx in range(self.ndim)]

        shape = []
        for dim_name in dim_names:
            if dim_name not in self.__header_dict:
                raise IOError(f"`dimname` is required in XDR header when `ndim` is {self.ndim}.")
            shape.append(int(self.__header_dict[dim_name]))

        self.veclen = int(self.__header_dict["veclen"])

        self.__shape = tuple(shape)  # Internally the original order is needed, array itself needs to be flipped.
        self.shape = tuple(shape[::-1])
        self.size = np.prod(self.__shape)

        self.compression = int(self.__header_dict.get("nki_compression", 0))

        self.original_dtype = self.__header_dict["data"]
        self.dtype = XDR_DTYPE_TO_PYTHON[self.original_dtype]

        # Parse the array keys.
        self.parse_array_keys()

        for key in XDR_METADATA_KEYS:
            value = self.__header_dict.get(key, None)
            if not value:
                continue
            save_key = key[2:].lower()
            setattr(self, save_key, value)

        # Check if file is external
        self.external_data = False
        if "variable 1 file" in self.__header_dict:
            p = self.__header_dict["xdr_filename"]
            if p != "":
                p = f"{p}/"
            self.external_data = f"{p}{self.__header_dict['variable 1 file'].split(' ')[0]}"

    def parse_array_keys(self):
        array_keys = ["#$$ScanToSiddon", "#$$MatchToSiddon", "#$$PH"]
        for array_key in array_keys:
            array_str = self.__header_dict.get(array_key, None)
            if not array_str:
                continue

            # Remove double spaces
            array_str = " ".join(array_str.split())
            array_str = array_str.split(" ")

            array = np.array([float(_) for _ in array_str])
            if array_key == "#$$PH":
                if len(array) != self.shape[0]:
                    raise ValueError(
                        f"Phase was defined in XDR but array has different length from number of time points. "
                        f"Got {len(array)} and {len(self.shape[0])}."
                    )
                if self.ndim != 4:
                    raise ValueError(f"Phase was defined in XDR, but dimension is {self.ndim}.")

                phase_len = array.sum()
                # Due to round-off errors, sometimes the phase does not completely add up to 1.
                # Even with a respiratory cycle of 10s, this is a deviation of less than 1ms.
                if not (0.9999 <= phase_len <= 1.0001):
                    raise ValueError(
                        f"Phase was defined in XDR, but 0.9999 <= sum(phase) <= 1.0001 is required. Got {phase_len}."
                    )

                self.phase = array
            else:
                setattr(self, camel_to_snake(array_key[3:]), array.reshape((4, 4)))

    @property
    def spacing(self):
        # Spacing needs to be computed based on the image size and the matrix size.
        if not self.min_ext and self.max_ext:
            raise ValueError("min_ext and max_ext need to be set before spacing can be computed.")

        diff = np.asarray(self.max_ext) - np.asarray(self.min_ext)
        if self.field == "uniform":
            spacing = diff / (np.asarray(self.__shape) - 1)
        elif self.field == "rectilinear":
            if not len(diff) == self.ndim:
                raise NotImplementedError(
                    "Currently spacing is only implemented for \
                rectilinear fields which have uniform slice thicknesses."
                )
            spacing = diff / np.asarray(self.__shape) - 1
            warnings.warn(
                "Spacing for rectilinear fields are untested, and will output the same spacing as uniform fields."
            )

        return np.round(spacing, 3)  # micrometer resolution

    @property
    def affine(self):
        if hasattr(self, "scan_to_siddon"):
            if not self.min_ext:
                raise ValueError("min_ext required to compute affine.")

            affine = self.xdr_affine_to_affine(self.scan_to_siddon, self.min_ext)
            return affine
        return None

    @property
    def direction(self):
        if self.affine is not None:
            return self.affine[0:3, 0:3].flatten().tolist()

        # This happens when no ScanToSiddon is provided in the XDR header.
        default_siddon_affine = np.array([[0.0, 0.0, 1.0], [-1.0, 0.0, 0.0], [0.0, -1.0, 0.0]])
        # Convert to ITK coordinates
        default_affine = np.matmul(SIDDON_TO_DICOM, default_siddon_affine)

        return default_affine.flatten().tolist()

    @property
    def origin(self):
        if self.affine is not None:
            return self.affine[0:3, -1].flatten().tolist()[::-1]
        return [0.0, 0.0, 0.0]

    @staticmethod
    def xdr_affine_to_affine(affine_xdr, min_ext):
        affine_xdr = affine_xdr.transpose()
        affine = affine_xdr.copy()
        direction = affine[0:3, 0:3]

        direction = np.matmul(SIDDON_TO_DICOM, direction)
        b = affine[:-1, -1]
        min_ext = min_ext.copy()
        min_ext[0] *= -1

        # TODO: Below [0:3] in min_ext is required to support 4D images. This needs more proper investigation.
        b = min_ext[0:3] + np.matmul(SIDDON_TO_DICOM, b)[::-1] * 10.0  # To mm

        new_affine = np.hstack([direction, b.reshape(-1, 1)])
        new_affine = np.vstack([new_affine, [0.0, 0.0, 0.0, 1.0]])

        return new_affine

    def __repr__(self):
        out_str = "XDRHeader("
        for k, v in self.__dict__.items():
            if k == "_spacing":
                k = "spacing"
                v = self.spacing

            if k.startswith("_XDRHeader"):
                continue
            if isinstance(v, np.ndarray):
                v = f"np.ndarray(shape={v.shape}, dtype={v.dtype})"

            out_str += f"{k}={v}, "
        out_str = out_str[:-2]
        out_str += ")"
        return out_str


def read(xdr_filename, stop_before_data=False):
    """Read XDR file.

    Arguments
    ---------
    xdr_filename : PathLike
        Path to XDR file.
    stop_before_data : bool
        Only read header, stop before loading and (optional) decompressing the data.

    Returns
    -------
    XDRImage
    """
    file_handler = open(xdr_filename, "rb")

    text_header = []
    form_feed = False

    initial_header = []
    header_counter = 0

    while True:
        # Read character by character, until a form feed is encountered
        next_character = file_handler.read(1)

        # Read until EOF
        if next_character == "" or (ord(next_character) == 12 and form_feed):
            break

        text_header.append(next_character)
        form_feed = ord(next_character) == 12

        if header_counter <= 4:
            initial_header.append(next_character.decode("utf-8"))
        elif header_counter == 5:
            first_header_chars = "".join(initial_header)
            if first_header_chars != "# AVS":
                file_handler.close()
                raise RuntimeError(f"Header of XDR file should start with `# AVS`. Got {first_header_chars}.")

        header_counter += 1

    # Decode text header:
    decoded_header = []
    for character in text_header:
        try:
            decoded_header.append(character.decode("utf-8"))
        except UnicodeDecodeError:
            decoded_header.append("__#ERR#__")

    # Join characters to string and remove white space characters
    header_lines = [_ for _ in ("".join(decoded_header)).splitlines() if _ not in string.whitespace]

    # Split header lines around =
    header_dict = {"xdr_filename": xdr_filename}
    for line in header_lines:
        if line.startswith("# "):
            continue

        splitted = line.split("=")
        if len(splitted) == 1:
            header_dict[splitted[0]] = ""
        else:
            if "__#ERR#__" in splitted[1]:
                header_dict[splitted[0]] = "#DECODING_ERROR#"
            else:
                header_dict[splitted[0]] = splitted[1]

    header = XDRHeader(header_dict)
    if stop_before_data:
        return XDRImage(header, data=None)

    # TODO: No veclen in compression yet
    if header.compression > 0:
        if not nki_decompression_available:
            raise ValueError("Decompression library not compiled.")

        # Must calculate how many bytes of compressed data there are.
        image_data_offset = file_handler.tell()
        extent_data_offset = path.getsize(xdr_filename) - header.ndim * 2 * 4
        comp_size = extent_data_offset - image_data_offset

        source_data = np.fromfile(file_handler, dtype="uint8", count=comp_size)
        destination_data = np.zeros(header.size, dtype="<i2")

        nki_compression.nki_private_decompress(
            destination_data.ctypes.data_as(ctypes.POINTER(ctypes.c_short)),
            source_data.ctypes.data_as(ctypes.POINTER(ctypes.c_char)),
            len(source_data),
        )
        raw_data = np.asarray(destination_data, order="F", dtype="<i2")

        if not file_handler.tell() == extent_data_offset:
            file_handler.close()
            raise IOError(f"Error in reading binary date from {xdr_filename}.")

    else:
        if header.external_data:
            file_handler.close()
            file_handler = open(header.external_data, "rb")

        dtype = XDR_DTYPE_TO_PYTHON.get(header_dict["data"], False)
        if not dtype:
            raise NotImplementedError(f"dtype {dtype} not supported.")

        if dtype == "uint8":
            raw_data = np.fromfile(file_handler, dtype="uint8")
        else:
            raw_data = np.asarray(
                np.fromfile(file_handler, dtype=f">{dtype}", count=header.size * header.veclen),
                order="F",
                dtype=f"<{dtype}",
            )

    # AVSField standard defines the min_ext and max_ext based on final bytes.
    for _ in range(header.ndim):
        header.min_ext.append(np.fromfile(file_handler, dtype=">f4", count=1)[0] * 10.0)  # * 10. to convert to mm.
        header.max_ext.append(np.fromfile(file_handler, dtype=">f4", count=1)[0] * 10.0)  # * 10. to convert to mm.
    if file_handler.tell() != path.getsize(xdr_filename):
        file_handler.close()
        raise IOError("Unexpected extra bytes.")

    file_handler.close()

    if not header.ndim == len(header.min_ext) == len(header.max_ext):
        raise IOError(
            f"Dimension {header.ndim} must match length of min_ext and max_ext."
            f" Got {header.ndim}, {header.min_ext} and {header.max_ext}"
        )

    shape = header.shape

    if header.veclen != 1:
        warnings.warn(
            f"Data with {header.veclen} components is not properly tested, and likely does not work. "
            f"Create a GitHub issue if your application requires this."
        )
        shape = shape + (header.veclen,)

    data = raw_data.reshape(shape)
    return XDRImage(header, data=data)


def postprocess_xdr_image(
    xdr_image: XDRImage,
    temporal_average: str,
    slope: float,
    intercept: float,
    cast: str,
) -> XDRImage:
    if temporal_average:
        logging.info(f"Computing temporal average: {temporal_average}.")

        if temporal_average not in ["mean", "weighted"]:
            sys.exit("xdr2img: error: --temporal-average must be either `mean` or `weighted`.")

        if xdr_image.header.ndim != 4:
            sys.exit("xdr2img: error: --temporal-average can only be used with 4D images.")

        weights = 1.0
        if temporal_average == "weighted":
            if not hasattr(xdr_image.header, "phase"):
                logging.warning("Phase is not available. Temporal average will be mean.")
            else:
                weights = np.asarray(xdr_image.header.phase)

        xdr_image.data = (weights * xdr_image.data.T).T.sum(axis=0)
        xdr_image.header.ndim = 3  # Data is now 3D

    if slope:
        logging.info(f"Slope set: {slope}.")
        xdr_image.data = xdr_image.data * make_integer(slope)

    if intercept:
        logging.info(f"Intercept set: {intercept}.")
        xdr_image.data = xdr_image.data + make_integer(intercept)

    if cast:
        logging.info(f"Casting to: {cast}.")
        if cast not in list(DATATYPES.keys()):
            sys.exit(f"xdr2img: error: Expected casting type to be one of {list(DATATYPES.keys())}. Got {cast}.")
        xdr_image.data = xdr_image.data.astype(DATATYPES[cast])

    return xdr_image


def read_as_simpleitk(xdr_image, lps_orientation=True, save_header=False):
    """Read XDR file as an SimpleITK image.

    Arguments
    ---------
    xdr_filename : XDRImage
        The XDRImage.
    lps_orientation : bool
        The orientation of the underlying data array will be rotated to ensure the orientation matrix is as
        close to a unit matrix as possible.
    save_header : bool
        If set the header will be added as metadata to the image. Beware that subsequent ITK filters will drop this
        metadata.

    Returns
    -------
    sitk.Image or list of sitk.Image
    """

    data = xdr_image.data

    header = xdr_image.header
    images = []

    if header.ndim == 3:
        images.append(_create_simpleitk_image(data, header))

    elif header.ndim == 4:  # Time-axis is 0-th axis.
        for curr_data in data:
            images.append(_create_simpleitk_image(curr_data, header))
    else:
        raise NotImplementedError("Currently on 3D and 4D XDR is implemented.")

    if lps_orientation:
        images = [_change_orientation(curr_image) for curr_image in images]

    if len(images) == 1:
        sitk_image = images[0]
    else:
        # Now the image is 4D
        sitk_image = sitk.JoinSeries(images)

    if header.phase is not None:
        sitk_image.SetMetaData("phase", " ".join([str(_) for _ in header.phase]))
    if save_header:
        for key in XDR_METADATA_KEYS:
            key = key[2:].lower()
            value = header.__dict__.get(key, None)
            if not value:
                continue
            sitk_image.SetMetaData("XDR_" + str(key), str(value))

    return sitk_image


def _create_simpleitk_image(data, header):
    sitk_image = sitk.GetImageFromArray(data, isVector=header.veclen > 1)
    sitk_image.SetSpacing(header.spacing)
    if header.origin:
        sitk_image.SetOrigin(header.origin)
    if header.direction:
        sitk_image.SetDirection(header.direction)

    return sitk_image


def _change_orientation(sitk_image):
    """
    Changes the underlying data array to LPS orientation.

    """
    curr_filter = sitk.DICOMOrientImageFilter()
    sitk_image = curr_filter.Execute(sitk_image)
    return sitk_image
