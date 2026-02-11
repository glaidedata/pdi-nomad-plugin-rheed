import logging
import os
from contextlib import contextmanager
from unittest.mock import MagicMock

from nomad.datamodel import EntryArchive

from pdi_nomad_plugin_rheed.parsers.parser import RHEEDParser
from pdi_nomad_plugin_rheed.schema_packages.schema_package import RawFileRHEEDData


# Helper to get the absolute path to the data folder
def get_test_file(filename):
    module_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(module_dir, '..', 'data', filename)


@contextmanager
def mock_update_entry_ctx(*args, **kwargs):
    # This acts as the dictionary that the parser writes the ELN data into
    holder = {}
    yield holder
    # We attach the result to the context so we can inspect it in the test
    kwargs.get('_test_capture', {})['data'] = holder.get('data')


def test_parse_scan():
    parser = RHEEDParser()
    archive = EntryArchive()

    # --- MOCKING THE SERVER CONTEXT ---
    archive.metadata = MagicMock()
    archive.metadata.upload_id = 'test_upload'

    archive.m_context = MagicMock()
    archive.m_context.raw_path_exists.return_value = False

    # We use a mutable dict to capture what the parser saves
    captured_eln = {}

    # Configure the mock to use our context manager
    def side_effect(*args, **kwargs):
        # Pass our capture dict to the context manager
        kwargs['_test_capture'] = captured_eln
        return mock_update_entry_ctx(*args, **kwargs)

    archive.m_context.update_entry.side_effect = side_effect

    # --- RUN PARSER ---
    test_file = get_test_file('export point scan.csv')
    parser.parse(test_file, archive, logging.getLogger())

    # --- VERIFY RAW ENTRY (Pointer) ---
    assert isinstance(archive.data, RawFileRHEEDData)
    assert archive.data.measurement is not None

    # --- VERIFY ELN CONTENT (The data passed to the mock) ---
    # The parser converted the ELN entry to a dict. Let's inspect it.
    eln_data = captured_eln.get('data', {})

    # Check that we parsed the point scan section
    assert 'point_scan' in eln_data
    scan = eln_data['point_scan']

    # Check sensors
    EXPECTED_SENSOR_COUNT = 3
    assert len(scan.get('sensors', [])) == EXPECTED_SENSOR_COUNT

    # Check plot
    assert 'plot' in scan
    assert len(scan['plot'].get('figures', [])) > 0
    assert scan['plot']['figures'][0]['label'] == 'Scan Intensity'


def test_parse_image():
    image_filename = 'image_2025-12-22___15-39-57.878.pgm'
    test_file = get_test_file(image_filename)

    if os.path.exists(test_file):
        parser = RHEEDParser()
        archive = EntryArchive()

        # --- MOCKING ---
        archive.metadata = MagicMock()
        archive.metadata.upload_id = 'test_upload'
        archive.m_context = MagicMock()
        archive.m_context.raw_path_exists.return_value = False

        captured_eln = {}

        def side_effect(*args, **kwargs):
            kwargs['_test_capture'] = captured_eln
            return mock_update_entry_ctx(*args, **kwargs)

        archive.m_context.update_entry.side_effect = side_effect

        # --- RUN ---
        parser.parse(test_file, archive, logging.getLogger())

        # --- VERIFY ---
        assert isinstance(archive.data, RawFileRHEEDData)

        eln_data = captured_eln.get('data', {})
        assert 'image' in eln_data
        img = eln_data['image']

        # Check Timestamp extraction
        assert img.get('timestamp') is not None

        # Check Plot
        assert 'plot' in img
        assert len(img['plot'].get('figures', [])) > 0
