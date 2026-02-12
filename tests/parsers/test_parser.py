import logging
import os

from nomad.datamodel import EntryArchive

from pdi_nomad_plugin_rheed.parsers.parser import RHEEDParser
from pdi_nomad_plugin_rheed.schema_packages.schema_package import RHEEDMeasurement


# Helper to get the absolute path to the data folder
def get_data_folder():
    module_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(module_dir, '..', 'data')


def test_parse_full_collection():
    """
    Tests if the parser correctly aggregates images and scans from the folder
    when triggered by the dummy metadata file.
    """
    data_folder = get_data_folder()

    # 1. Create the dummy trigger file inside tests/data
    trigger_file = os.path.join(data_folder, 'test_trigger.rheed_metadata')
    with open(trigger_file, 'w') as f:
        f.write('Trigger')

    try:
        # 2. Setup the parser
        parser = RHEEDParser()
        archive = EntryArchive()

        # 3. Run the parser on the trigger file
        parser.parse(trigger_file, archive, logging.getLogger())

        # 4. Verify the Root Entry
        assert isinstance(archive.data, RHEEDMeasurement)
        assert archive.data.name == 'RHEED Measurement Collection'

        # 5. Verify Results were found and added
        results = archive.data.results
        assert len(results) > 0, 'Parser should have found files in the data directory'

        # --- Verify Images ---
        # Look for the .pgm result
        image_results = [r for r in results if r.result_type == 'image']
        assert len(image_results) > 0, 'Should have found the .pgm image'

        # Check that the plot was generated
        pgm_res = image_results[0]
        assert pgm_res.plot is not None
        assert len(pgm_res.plot.figures) > 0
        assert pgm_res.plot.figures[0].label == 'Intensity Map'
        assert pgm_res.timestamp is not None  # Check timestamp extraction

        # --- Verify Scans ---
        # Look for the scan result
        scan_results = [r for r in results if r.result_type == 'scan_point']
        if scan_results:
            scan_res = scan_results[0]
            assert len(scan_res.point_scans) > 0

            # Check the first scan content
            first_scan = scan_res.point_scans[0]
            EXPECTED_SENSOR_COUNT = 3
            assert len(first_scan.sensors) == EXPECTED_SENSOR_COUNT

            # Check scan plot
            assert first_scan.plot is not None
            assert len(first_scan.plot.figures) > 0
            assert first_scan.plot.figures[0].label == 'Scan Intensity'

    finally:
        # 6. Cleanup: Remove the dummy trigger file
        if os.path.exists(trigger_file):
            os.remove(trigger_file)
