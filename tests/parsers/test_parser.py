import logging
import os

from nomad.datamodel import EntryArchive

from pdi_nomad_plugin_rheed.parsers.parser import RHEEDParser
from pdi_nomad_plugin_rheed.schema_packages.schema_package import (
    RHEEDImage,
    RHEEDPointScan,
)


# Helper to get the absolute path to the data folder
def get_test_file(filename):
    module_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(module_dir, '..', 'data', filename)


def test_parse_scan():
    """
    Tests if the parser correctly reads a .csv point scan.
    """
    parser = RHEEDParser()
    archive = EntryArchive()

    test_file = get_test_file('export point scan.csv')

    parser.parse(test_file, archive, logging.getLogger())

    assert isinstance(archive.data, RHEEDPointScan)
    EXPECTED_SENSOR_COUNT = 3
    assert len(archive.data.sensors) == EXPECTED_SENSOR_COUNT
    assert archive.data.sensors[0].name == 'Sensor 1'
    assert len(archive.data.figures) > 0
    assert archive.data.figures[0].label == 'Scan Intensity'


def test_parse_image():
    """
    Tests if the parser correctly reads a .pgm image.
    """
    image_filename = 'image_2025-12-22___15-39-57.878.pgm'
    test_file = get_test_file(image_filename)

    if os.path.exists(test_file):
        parser = RHEEDParser()
        archive = EntryArchive()

        parser.parse(test_file, archive, logging.getLogger())

        assert isinstance(archive.data, RHEEDImage)
        assert archive.data.image_file == image_filename
        assert archive.data.timestamp is not None
        assert len(archive.data.figures) > 0
