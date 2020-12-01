# XDRT (XDR Tools)

[![pypi](https://img.shields.io/pypi/v/xdrt.svg)](https://pypi.python.org/pypi/xdrt)
[![rtd](https://readthedocs.org/projects/xdrt/badge/?version=latest)](https://xdrt.readthedocs.io/en/latest/?badge=latest)

XDRT is a python toolkit to work with the XDR file format used e.g. by Elekta to store cone-beam CT images.


* Free software: Apache Software License 2.0. Decompression library is public domain, but has a different
[license](xdrt/lib/nki_decompression/LICENSE).
* Documentation: https://xdrt.readthedocs.io.


## Features
* Utilities to read (compressed) 3D and 4D XDR files in python.
* `xdr2img` command line utility to convert xdr images to ITK supported formats.

## How to use
The package needs to compile the decompression library, which can be done with:
`python setup.py install` or with `pip install git+https://github.com/NKI-AI/xdrt.git`.

The command line program `xdr2img image.xdr image.nrrd` converts images from XDR
to any ITK supported format. For more details check `xdr2img --help`.


### Work in progress
This package is work in progress, if you have an image which is not properly parsed
by `xdrt`, create an issue with the image and expected output.

The following is not yet supported:
.
* Origin is not yet always properly parsed.
* Only `uniform` grids are currently supported.

Create an issue if this is an urgent for you.
