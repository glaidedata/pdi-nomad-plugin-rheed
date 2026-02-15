import logging
import os
from unittest.mock import MagicMock

from nomad.datamodel import EntryArchive, EntryMetadata

from pdi_nomad_plugin_rheed.parsers.parser import RHEEDParser
from pdi_nomad_plugin_rheed.schema_packages.schema_package import RHEEDMeasurement


# Helper to get the absolute path to the data folder
def get_data_folder():
    module_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(module_dir, '..', 'data')


def test_parse_full_collection():
    """
    Tests if the parser creates the entry and normalize() populates it
    with images and scans from the folder.
    """
    data_folder = get_data_folder()
    trigger_filename = 'test_trigger.rheed_metadata'

    # 1. Create the dummy trigger file inside tests/data
    trigger_path = os.path.join(data_folder, trigger_filename)
    with open(trigger_path, 'w') as f:
        f.write('Trigger')

    try:
        # 2. Setup the parser and archive
        parser = RHEEDParser()
        archive = EntryArchive()

        archive.metadata = EntryMetadata()
        archive.metadata.mainfile = trigger_filename

        # --- CRITICAL: Mock the Server Context ---
        # normalize() function needs to know where the files are.
        # We fake the 'raw_path' to point to our local test data folder.
        archive.m_context = MagicMock()
        archive.m_context.raw_path.return_value = data_folder

        # 3. Run the parser
        # (This now only creates the empty RHEEDMeasurement entry)
        parser.parse(trigger_path, archive, logging.getLogger())

        # 4. Verify the Entry exists but is likely empty of results
        assert isinstance(archive.data, RHEEDMeasurement)

        # 5. Run Normalization MANUALLY
        archive.data.normalize(archive, logging.getLogger())

        # 6. Verify Results were found and added
        results = archive.data.results
        assert len(results) > 0, (
            'Normalize should have found files in the data directory'
        )

        # --- Verify Images ---
        # Look for the .pgm result
        image_results = [r for r in results if r.result_type == 'image']
        assert len(image_results) > 0, 'Should have found the .pgm image'

        # Check that the plot was generated
        pgm_res = image_results[0]
        assert pgm_res.plot is not None
        assert len(pgm_res.plot.figures) > 0
        assert pgm_res.plot.figures[0].label == 'Intensity Map'
        assert pgm_res.timestamp is not None

        # --- Verify Scans ---
        # Look for the scan result
        scan_results = [r for r in results if r.result_type == 'scan_point']
        if scan_results:
            scan_res = scan_results[0]
            assert len(scan_res.point_scans) > 0

            # Check the first scan content
            first_scan = scan_res.point_scans[0]
            # Check the timestamp fix we implemented earlier
            assert first_scan.start_time is not None
            EXPECTED_SENSOR_COUNT = 3
            assert len(first_scan.sensors) == EXPECTED_SENSOR_COUNT

            # Check scan plot
            assert first_scan.plot is not None
            assert len(first_scan.plot.figures) > 0

    finally:
        # 7. Cleanup: Remove the dummy trigger file
        if os.path.exists(trigger_path):
            os.remove(trigger_path)
