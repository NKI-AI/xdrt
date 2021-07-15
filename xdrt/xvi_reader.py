# coding=utf-8
# Copyright (c) Jonas Teuwen
import configparser
import pathlib
from datetime import datetime
from typing import NamedTuple


class Patient(NamedTuple):
    patient_id: str
    first_name: str
    last_name: str
    date_of_birth: datetime


class _Reference(NamedTuple):
    date_time: datetime
    version: str
    level: int
    window: int


class Scan(NamedTuple):
    scan_uid: str
    date_time: datetime
    version: str
    level: float
    window: float
    filename: pathlib.Path


class XVIReconstruction:
    def __init__(self, path: pathlib.Path):
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
        self.path = pathlib.Path(path)
        self.patient: Patient
        self._reference: _Reference
        self.scan: Scan

        ini_files = self.path.glob("*.INI")
        xvi_files = self.path.glob("*.XVI")
        config = configparser.ConfigParser()
        for file in xvi_files:
            config.read(file)
        self._data_dict = config._sections  # type: ignore
        self.__parse_config()

        for file in ini_files:
            config.read(file)

        self.__parse_identification()

    def __parse_config(self):
        headers = ["RECONSTRUCTION", "REFERENCE"]
        if any(_ not in self._data_dict for _ in headers):
            raise RuntimeError(f"At least one XVI file in {self.path} should have a header in {headers}.")

        reconstruction = self._data_dict["RECONSTRUCTION"]
        datetime_str = reconstruction["reconstructiondate"] + " " + reconstruction["reconstructiontime"]
        date_time = datetime.strptime(datetime_str, "%Y%m%d %H:%M:%S")

        reference = self._data_dict["REFERENCE"]
        version = reference["avlversion"]
        level = int(reference["reference1.level"])
        window = int(reference["reference1.window"])

        self._reference = _Reference(date_time=date_time, version=version, level=level, window=window)

    def __parse_identification(self):
        if "IDENTIFICATION" not in self._data_dict:
            raise RuntimeError(f"At least one INI file in {self.path} should have an IDENTIFICATION header.")

        identification = self._data_dict["IDENTIFICATION"]

        patient_id = identification["patientid"]
        first_name = identification["firstname"]
        last_name = identification["lastname"]
        date_of_birth = datetime.strptime(identification["dob"], "%d.%m.%Y")
        self.patient = Patient(
            patient_id=patient_id, first_name=first_name, last_name=last_name, date_of_birth=date_of_birth
        )
        scan_uid = identification["scanuid"]
        scan_header = scan_uid + ".ALIGN"
        if scan_header not in self._data_dict:
            raise RuntimeError(f"Expected to find header {scan_header} in one of the configuration files.")

        reconstruction_filename = self.path / self._data_dict[scan_header]["reconstruction"]
        if not reconstruction_filename.is_file():
            raise RuntimeError(f"Expected reconstruction filename {reconstruction_filename} to exist.")

        self.scan = Scan(
            scan_uid=scan_uid,
            date_time=self._reference.date_time,
            version=self._reference.version,
            level=self._reference.level,
            window=self._reference.window,
            filename=reconstruction_filename,
        )

    def __repr__(self):
        return f"XVIReconstruction(path={self.path}, " f"patient={self.patient}, " f"scan={self.scan})"
