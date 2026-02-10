from nomad.client import normalize_all
from nomad.datamodel import EntryArchive
from pdi_nomad_plugin_rheed.schema_packages.schema_package import ELNRHEEDMeasurement, RHEEDPointScan

def test_schema_instantiation():
    """
    Tests if the ELN schema can be instantiated and normalized.
    """
    # 1. Create the Scan section
    scan = RHEEDPointScan()
    scan.data_file = "dummy.csv"
    
    # 2. Wrap it in the main ELN Entry (since PointScan is now a subsection)
    entry = ELNRHEEDMeasurement()
    entry.point_scan = scan
    
    # 3. Create Archive
    archive = EntryArchive(data=entry)
    
    # 4. Normalize
    normalize_all(archive)
    
    # 5. Verify
    assert archive.data.point_scan.data_file == "dummy.csv"