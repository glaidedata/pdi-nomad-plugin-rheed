from nomad.client import normalize_all
from nomad.datamodel import EntryArchive

from pdi_nomad_plugin_rheed.schema_packages.schema_package import (
    PointScan,
    RHEEDMeasurement,
    RHEEDPointScanResult,
)


def test_schema_instantiation():
    """
    Tests if the new RHEEDMeasurement schema can be instantiated and normalized.
    """
    # 1. Create a Point Scan Result
    scan_item = PointScan()
    scan_item.source_file = 'dummy_scan.csv'

    scan_result = RHEEDPointScanResult()
    scan_result.point_scans.append(scan_item)

    # 2. Create the Root Measurement and add the result
    entry = RHEEDMeasurement()
    entry.results.append(scan_result)

    # 3. Create Archive
    archive = EntryArchive(data=entry)

    # 4. Normalize
    normalize_all(archive)

    # 5. Verify structure
    assert isinstance(archive.data, RHEEDMeasurement)
    assert len(archive.data.results) == 1
    assert archive.data.results[0].point_scans[0].source_file == 'dummy_scan.csv'
