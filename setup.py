#!/usr/bin/env python
# coding=utf-8

"""The setup script."""
import ast

with open("xdrt/__init__.py") as f:
    for line in f:
        if line.startswith("__version__"):
            version = ast.parse(line).body[0].value.s  # type: ignore
            break

import os
import platform
import re
import subprocess
import sys
from distutils.version import LooseVersion

from setuptools import Extension, find_packages, setup
from setuptools.command.build_ext import build_ext

with open("README.md") as readme_file:
    readme = readme_file.read()


class CMakeExtension(Extension):
    # This is from: https://www.benjack.io/2017/06/12/python-cpp-tests.html
    def __init__(self, name, sourcedir=""):
        Extension.__init__(self, name, sources=[])
        self.sourcedir = os.path.abspath(sourcedir)


class CMakeBuild(build_ext):
    # This is from: https://www.benjack.io/2017/06/12/python-cpp-tests.html
    def run(self):
        try:
            out = subprocess.check_output(["cmake", "--version"])
        except OSError:
            raise RuntimeError(
                "CMake must be installed to build the following extensions: "
                + ", ".join(e.name for e in self.extensions)
            )

        if platform.system() == "Windows":
            cmake_version = LooseVersion(re.search(r"version\s*([\d.]+)", out.decode()).group(1))
            if cmake_version < "3.1.0":
                raise RuntimeError("CMake >= 3.1.0 is required on Windows")

        for ext in self.extensions:
            self.build_extension(ext)

    def build_extension(self, ext):
        extdir = os.path.abspath(os.path.dirname(self.get_ext_fullpath(ext.name)))

        cmake_args = [
            "-DCMAKE_LIBRARY_OUTPUT_DIRECTORY=" + extdir,
            "-DPYTHON_EXECUTABLE=" + sys.executable,
        ]

        cfg = "Debug" if self.debug else "Release"
        build_args = ["--config", cfg]

        if platform.system() == "Windows":
            cmake_args += ["-DCMAKE_LIBRARY_OUTPUT_DIRECTORY_{}={}".format(cfg.upper(), extdir)]
            if sys.maxsize > 2 ** 32:
                cmake_args += ["-A", "x64"]
            build_args += ["--", "/m"]
        else:
            cmake_args += ["-DCMAKE_BUILD_TYPE=" + cfg]
            build_args += ["--", "-j2"]

        env = os.environ.copy()
        env["CXXFLAGS"] = '{} -DVERSION_INFO=\\"{}\\"'.format(env.get("CXXFLAGS", ""), self.distribution.get_version())
        if not os.path.exists(self.build_temp):
            os.makedirs(self.build_temp)
        subprocess.check_call(["cmake", ext.sourcedir] + cmake_args, cwd=self.build_temp, env=env)
        subprocess.check_call(["cmake", "--build", "."] + build_args, cwd=self.build_temp)
        print()  # Add an empty line for cleaner output


setup(
    author="Jonas Teuwen",
    author_email="j.teuwen@nki.nl",
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    entry_points={
        "console_scripts": [
            "xdr2img=xdrt.cli.xdr:main",
            "xvi2img=xdrt.cli.xvi:main",
        ],
    },
    description="XDRT (XDR Toolkit) is a python toolkit to work with the Elekta XDR and XVI file formats.",
    install_requires=["numpy>=0.19", "SimpleITK>=2.0"],
    license="Apache Software License 2.0 for the python code, and custom license for the external decoding library.",
    long_description=readme,
    long_description_content_type="text/markdown",
    include_package_data=True,
    keywords="xdrt",
    name="xdrt",
    packages=find_packages(include=["xdrt", "xdrt.*"]),
    test_suite="tests",
    extras_require={
        "dev": [
            "pytest",
            "pytest-mock",
            "sphinx_copybutton",
            "numpydoc",
            "myst_parser",
            "sphinx-book-theme",
            "pylint",
            "pydantic",
        ],
    },
    url="https://github.com/NKI-AI/xdrt",
    version=version,
    zip_safe=False,
    ext_modules=[CMakeExtension("lib/nki_decompression")],
    cmdclass=dict(build_ext=CMakeBuild),
)
