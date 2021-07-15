# XDRT (XDR Tools)

[![pypi](https://img.shields.io/pypi/v/xdrt.svg)](https://pypi.python.org/pypi/xdrt)
[![Pylint](https://github.com/NKI-AI/xdrt/actions/workflows/pylint.yml/badge.svg)](https://github.com/NKI-AI/xdrt/actions/workflows/pylint.yml)
[![mypy](https://github.com/NKI-AI/xdrt/actions/workflows/mypy.yml/badge.svg)](https://github.com/NKI-AI/xdrt/actions/workflows/mypy.yml)
[![Black](https://github.com/NKI-AI/xdrt/actions/workflows/black.yml/badge.svg)](https://github.com/NKI-AI/xdrt/actions/workflows/black.yml)

XDRT is a python toolkit to work with the XDR file format used e.g. by Elekta to store cone-beam CT images and as reconstructed by XVI.
The reading of complete XVI reconstruction folders is also supported, exporting to either an ITK supported format or DICOM, recovering metadata from the XVI files.


* Free software: Apache Software License 2.0. Decompression library is public domain, but has a different
[license](xdrt/lib/nki_decompression/LICENSE).
* Documentation: https://docs.aiforoncology.nl/xdrt/.
* Installation instructions: https://docs.aiforoncology.nl/xdrt/installation.html.


## Features
* Utilities to read (compressed) 3D and 4D XDR files in python.
* Ability to read XVI files and link planning scans with cone-beam CT scans.
* `xdr2img` command line utility to convert xdr images to ITK supported formats.
* `xvi2img` command line utility converts a fraction (reconstruction) to ITK supported formats.
* `xvi2dcm` command line utility converts a fraction (reconstruction) to dicom.

## How to use
The package needs to compile the decompression library, which can be done with:
`python setup.py install` or with `pip install git+https://github.com/NKI-AI/xdrt.git`
or from PyPi using `pip install xdrt`. Detailed installation instructions are available in
the [documentation](https://docs.aiforoncology.nl/xdrt/installation.html).

* The command line program `xdr2img image.xdr image.nrrd` converts images from XDR
to any ITK supported format. For more details check `xdr2img --help`.
* The command line program `xvi2img` reads XVI files and combined with the XDR files, writes
to a new directory and image format. For more details check `xvi2img --help`.


### Work in progress
This package is work in progress, if you have an image which is not properly parsed
by `xdrt`, create an issue with the image and expected output.

The following is not yet supported:

* Origin is not yet always properly parsed.
* Only `uniform` grids are currently supported.


Create an [issue](https://github.com/NKI-AI/xdrt/issues) if this is an urgent issue for you.
