import os
from nomad.datamodel import EntryArchive
from nomad.utils import get_logger

from pdi_nomad_plugin_rheed.parsers.parser import RheedParser
from pdi_nomad_plugin_rheed.schema_packages.schema_package import RHEEDMeasurement

def test_parse_file():
    parser = RheedParser()
    archive = EntryArchive()
    logger = get_logger(__name__)
    
    # Define the path to your test CSV
    test_file = 'tests/data/test_rheed_meta.csv'
    
    # Failsafe: Create a dummy CSV dynamically if you haven't put one in the folder yet
    if not os.path.exists(test_file):
        with open(test_file, 'w') as f:
            f.write("m8_id,date,time,file_name\n")
            f.write("m84266_A,2026-03-13,16:33:40,dummy_image.tif\n")
            
    # Run the parser
    parser.parse(test_file, archive, logger)
    
    # Basic structural assertions
    assert archive.data is not None, "Parser did not assign data to the archive."
    assert isinstance(archive.data, RHEEDMeasurement), "Archive data is not a RHEEDMeasurement."
    
    # Verify the MBE ID was extracted and prepended to the measurement_id correctly
    assert archive.data.measurement_id == "RHD_m84266", \
        f"Expected Measurement ID to be 'RHD_m84266', got '{archive.data.measurement_id}'"
    
    # Clean up the dummy file if we generated it
    if os.path.exists(test_file) and "dummy_image" in open(test_file).read():
        os.remove(test_file)