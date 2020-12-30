==================
XDR Toolkit (XDRT)
==================

XDRT is a python toolkit to work with the XDR file format used e.g. by Elekta to store cone-beam CT images and as reconstructed by XVI.
The reading of `.xvi` files is also supported, allowing to find the map the XDR file to the moment of acquistion
(which fraction, what type of scan).

XDRT is free software governed by the Apache Software License 2.0. The used decompression library is public domain,
but has a different `license`_.

.. _license: https://github.com/NKI-AI/xdrt/blob/main/xdrt/lib/nki_decompression/LICENSE


Features
========
* Utilities to read (compressed) 3D and 4D XDR files in python.
* Ability to read XVI files and link planning scans with cone-beam CT scans.
* The command line program :code:`xdr2img image.xdr image.nrrd` converts images from XDR to any ITK supported format. For more details check :code:`xdr2img --help`.
* The command line program :code:`xvi2img` reads XVI files and combined with the XDR files, writes to a new directory and image format. For more details check :code:`xvi2img --help`.

Work in progress
================
This package is work in progress, if you have an image which is not properly parsed
by :code:`xdrt`, create an issue with the image and expected output.

The following is not yet supported:

* Origin is not yet always properly parsed.
* Only `uniform` grids are currently supported.
* Protocol is not detected from the XVI file (e.g. 4D-CBCT + SBRT). Images in fraction are output consecutively.

Create an `issue`_, if this is an urgent issue for you.

.. _issue: https://github.com/NKI-AI/xdrt/issues
