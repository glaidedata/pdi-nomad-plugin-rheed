import logging
import os
from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest
from nomad.datamodel import EntryArchive, EntryMetadata

from pdi_nomad_plugin_rheed.parsers.parser import RHEEDParser
from pdi_nomad_plugin_rheed.schema_packages.schema_package import (
    RawFileRHEEDData,
    RHEEDMeasurement,
)


# --- Fixtures (Setup & Teardown) ---
@pytest.fixture
def data_folder():
    module_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(module_dir, '..', 'data')


@pytest.fixture
def trigger_filename():
    return 'test_trigger.rheed_metadata'


@pytest.fixture
def trigger_file(data_folder, trigger_filename):
    """Creates the dummy trigger file and cleans it up after the test."""
    trigger_path = os.path.join(data_folder, trigger_filename)
    with open(trigger_path, 'w') as f:
        f.write('Trigger')
    yield trigger_path
    # Cleanup
    if os.path.exists(trigger_path):
        os.remove(trigger_path)


# --- Test 1: The Parser (Pointer Creation) ---


def test_parser_creates_pointer(trigger_file, trigger_filename):
    """
    Verifies that the Parser correctly:
    1. Creates a RawFileRHEEDData entry (Pointer).
    2. Calls create_archive to spawn the ELN.
    3. Sets the correct 'data_file' reference in that ELN.
    """
    parser = RHEEDParser()
    archive = EntryArchive()
    archive.metadata = EntryMetadata()
    archive.metadata.upload_id = 'test_upload_id'
    archive.metadata.mainfile = trigger_filename

    # Mock server context
    archive.m_context = MagicMock()
    archive.m_context.raw_path_exists.return_value = False

    # Capture the data passed to create_archive
    captured_data = {}

    @contextmanager
    def mock_update_entry(*args, **kwargs):
        holder = {}
        yield holder
        captured_data.update(holder)

    archive.m_context.update_entry.side_effect = mock_update_entry

    # Run Parser
    parser.parse(trigger_file, archive, logging.getLogger())

    # VERIFY
    assert isinstance(archive.data, RawFileRHEEDData)
    assert archive.data.measurement is not None

    # Check if 'data_file' was correctly passed to the new ELN entry
    assert 'data' in captured_data
    assert captured_data['data']['data_file'] == trigger_filename


# --- Test 2: The Normalizer (File Scanning) ---
def test_measurement_normalization(trigger_file, trigger_filename):
    """
    Verifies that RHEEDMeasurement.normalize():
    1. Reads the 'data_file' field.
    2. Scans the directory.
    3. Populates the 'results' list with Images and Scans.
    """
    eln_entry = RHEEDMeasurement()
    eln_entry.data_file = trigger_filename  # The field set by the parser

    archive = EntryArchive()
    archive.data = eln_entry
    archive.metadata = EntryMetadata()

    # Set the entry name to prevent AttributeError in base class normalize
    archive.metadata.entry_name = 'Test Entry'

    # Mock 'raw_file' so normalize() can resolve the absolute path
    archive.m_context = MagicMock()

    @contextmanager
    def mock_raw_file(filename):
        # We return the path to our test trigger file
        class MockFile:
            name = trigger_file

        yield MockFile()

    archive.m_context.raw_file.side_effect = mock_raw_file

    # Run Normalization
    eln_entry.normalize(archive, logging.getLogger())

    # VERIFY
    results = eln_entry.results
    assert len(results) > 0, 'Normalize should have found files in the data directory'

    # Verify Images
    image_results = [r for r in results if r.result_type == 'image']
    assert len(image_results) > 0, 'Should have found images'
    assert image_results[0].plot is not None
    assert image_results[0].plot.figures[0].label == 'Intensity Map'

    # Verify Scans
    scan_results = [r for r in results if r.result_type == 'scan_point']
    if scan_results:
        scan_res = scan_results[0]
        assert len(scan_res.point_scans) > 0
        EXPECTED_SENSOR_COUNT = 3
        assert len(scan_res.point_scans[0].sensors) == EXPECTED_SENSOR_COUNT
        assert scan_res.point_scans[0].plot is not None
