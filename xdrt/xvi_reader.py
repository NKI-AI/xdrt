# coding=utf-8
# Copyright (c) Jonas Teuwen
import configparser
import logging
import pathlib
from typing import Dict, List, Optional

from xdrt.utils import parse_xvi_datetime, parse_xvi_url

RELEVANT_RECONSTRUCTION_TAGS = [
    "acqpars",
    "message",
    "protocol",
    "spr",
    "averagebreathingperiod",
    "fourd_sortingmode",
    "reconstructionvoxelsize",
    "airvaluemeasured",
    "watervaluemeasured",
    "phasehistogram",
    "tubema",
    "tubekv",
    "tubekvlength",
    "fov",
]


class XVIFile:
    def __init__(self, xvi_filename: pathlib.Path, files_root: Optional[pathlib.Path] = None):
        """
        Object holding an XVI file.

        Parameters
        ----------
        xvi_filename : pathlib.Path
            Path to XVI file.
        files_root : pathlib.Path
            Path to the root directory where the files can be found. This will be prepended to the reconstruction
            filename as derived from xvi_filename. If set, there will be a check if the reconstruction files exist.
        """
        if not pathlib.Path(xvi_filename).exists():
            raise FileNotFoundError(f"XVI file {xvi_filename} does not exist.")
        config = configparser.ConfigParser()
        self.xvi_filename = xvi_filename
        config.read(xvi_filename)
        self._xvi_dict = config._sections  # type: ignore
        self.files_root = files_root

        self.num_scans = 0
        self.num_fractions = 0
        self.is_sbrt = False

        self.__parse_xvi_key()
        self.__parse_exports()

    def __parse_xvi_key(self):
        if "XVI" not in self._xvi_dict:
            raise RuntimeError(f"{self.xvi_filename} misses an [XVI] header.")

        xvi_dict = self._xvi_dict["XVI"]
        urls = ["patient", "scan", "plan", "beam", "dose", "delineation"]
        for url in urls:
            data = xvi_dict[url + "url"]
            setattr(self, f"{url}", parse_xvi_url(data) if data.strip() != "" else None)

        self.version = xvi_dict["version"]

        fourd_dvf_url = xvi_dict.get("fourd_dvf_url", None)
        if xvi_dict and xvi_dict != "":
            self.dvf_url = fourd_dvf_url

        self.is_sbrt = False
        self.num_fractions = None

    def __parse_exports(self):
        xvi_conf = self._xvi_dict

        exports = {_.replace(".EXPORT", ""): xvi_conf[_] for _ in xvi_conf if _.endswith(".EXPORT")}
        reconstructions = {_.split(" ")[0]: xvi_conf[_] for _ in xvi_conf if _.endswith(".RECON")}

        # Now get the reconstructions which actually have an export
        # It is possible that there are no .RECON keys, in this case, we drop the extra metadata.
        if not reconstructions:
            reconstructions = {k: {} for k in exports}
            logging.warning(
                f"{self.xvi_filename} has no *.RECON keys. "
                f"Resulting XVIScan objects will hold no acquisition metadata."
            )
        else:
            reconstructions = {k: reconstructions[k] for k in exports}

        scans = []
        for k in reconstructions:
            scans.append(XVIScan(reconstructions[k], exports[k], files_root=self.files_root))

        # Sort on export time
        scans.sort(key=lambda x: x.datetime)

        prev_datetime = None
        curr_fraction = []
        fractions = []
        image_number_in_fraction = 0
        curr_fraction_num = 0
        for scan in scans:
            curr_datetime = scan.datetime
            if not prev_datetime:
                prev_datetime = curr_datetime

            time_diff = curr_datetime - prev_datetime
            prev_datetime = curr_datetime

            # less then 6 hours between scans belongs to the same fraction
            if time_diff.total_seconds() > 6 * 60 * 60:
                fractions.append(XVIFraction(curr_fraction_num, curr_fraction))
                curr_fraction = []
                curr_fraction_num += 1
                image_number_in_fraction = 0
            scan.fraction_number = curr_fraction_num
            scan.image_number_in_fraction = image_number_in_fraction
            image_number_in_fraction += 1
            curr_fraction.append(scan)

        # Add last fraction if there were previous scans.
        if curr_fraction_num > 0:
            fractions.append(XVIFraction(curr_fraction_num, curr_fraction))

        # Check if this is an SBRT treatment.
        # This will happen when all fractions have more than one scan.
        scans_per_fraction = [fraction.num_scans for fraction in fractions]
        has_multiple_scans = [x > 1 for x in scans_per_fraction]
        if all(has_multiple_scans) and has_multiple_scans:
            self.is_sbrt = True

        if len(set(has_multiple_scans)) > 1:
            raise RuntimeError(
                "Any treatment has to be either completely SBRT (multiple scans per fraction) or not at all."
            )

        self.fractions = fractions
        self.scans = scans
        self.num_fractions = len(fractions)
        self.num_scans = len(scans)

    def __repr__(self):
        return (
            f"XVIFile(xvi_filename={self.xvi_filename}, "
            f"num_fractions={self.num_fractions}, "
            f"num_scans={self.num_scans}, "
            f"is_sbrt={self.is_sbrt})"
        )


class XVIScan:
    def __init__(
        self,
        reconstruction: Dict,
        export: Dict,
        files_root: Optional[pathlib.Path] = None,
    ):
        """
        Object holding an XVI scan object

        Parameters
        ----------
        reconstruction : dict
            .RECON dict belonging to this scan from the XVI file.
        export : dict
            .EXPORT dict belonging to this scan, obtained from the XVI file.
        files_root : pathlib.Path
            Path to the root directory where the files can be found. This will be prepended to the reconstruction
            filename as derived from xvi_filename. If set, there will be a check if the reconstruction files exist.
        """
        # Both reconstruction and export contain useful information.
        self.datetime = parse_xvi_datetime(export.get("datetime", None))
        self.patientid = export.get("patientid", None)
        self.version = export["version"]

        reconstruction_path = pathlib.Path(export["reconstruction"])
        if files_root:
            reconstruction_path = files_root / reconstruction_path
            if not reconstruction_path.exists():
                raise FileNotFoundError(f"Scan {reconstruction_path} does not exist.")

        self.fraction_number = None
        self.image_number_in_fraction = None
        self.reconstruction = pathlib.Path(reconstruction_path)
        self.exported_scan_id = export["exportedscanid"]

        for tag in RELEVANT_RECONSTRUCTION_TAGS:
            if tag in reconstruction:
                setattr(self, tag, reconstruction[tag])

    def __repr__(self):
        return (
            f"XVIScan(patientid={self.patientid}, "
            f"datetime={self.datetime}, "
            f"protocol={self.protocol}, "
            f"reconstruction={self.reconstruction}, "
            f"fraction_number={self.fraction_number})"
        )


class XVIFraction:
    def __init__(self, fraction, scans):
        """
        Object holding an XVI fraction.

        Parameters
        ----------
        fraction : XVIFraction
        scans : List[XVIScan]
        """
        self.scans = scans
        self.fraction = fraction
        self.num_scans = len(scans)

    def __repr__(self):
        return f"XVIFraction(fraction={self.fraction}, num_scans={self.num_scans})"
