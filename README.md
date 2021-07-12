# XDRT (XDR Tools)

[![pypi](https://img.shields.io/pypi/v/xdrt.svg)](https://pypi.python.org/pypi/xdrt)

XDRT is a python toolkit to work with the XDR file format used e.g. by Elekta to store cone-beam CT images and as reconstructed by XVI.
The reading of `.xvi` files is also supported, allowing to find the map the XDR file to the moment of acquistion
(which fraction, what type of scan).


* Free software: Apache Software License 2.0. Decompression library is public domain, but has a different
[license](xdrt/lib/nki_decompression/LICENSE).
* Documentation: https://docs.aiforoncology.nl/xdrt/.


## Features
* Utilities to read (compressed) 3D and 4D XDR files in python.
* Ability to read XVI files and link planning scans with cone-beam CT scans.
* `xdr2img` command line utility to convert xdr images to ITK supported formats.
* `xvi2img` command line utility converts all fractions to ITK supported formats.

## How to use
The package needs to compile the decompression library, which can be done with:
`python setup.py install` or with `pip install git+https://github.com/NKI-AI/xdrt.git`
or from PyPi using `pip install xdrt`.

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
* Protocol is not detected from the XVI file (e.g. 4D-CBCT + SBRT). Images in fraction are output consecutively.

Create an [issue](https://github.com/NKI-AI/xdrt/issues) if this is an urgent issue for you.
