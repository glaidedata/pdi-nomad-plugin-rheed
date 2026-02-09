from nomad.client import normalize_all
from nomad.datamodel import EntryArchive

from pdi_nomad_plugin_rheed.schema_packages.schema_package import RHEEDPointScan


def test_schema_instantiation():
    """
    Tests if the RHEEDPointScan schema can be instantiated and normalized.
    """
    # 1. Create a dummy entry
    entry = RHEEDPointScan()
    entry.data_file = 'dummy.csv'

    # 2. Wrap it in an Archive
    archive = EntryArchive(data=entry)

    # 3. Normalize (triggers NOMAD's internal checks)
    normalize_all(archive)

    # 4. Verify
    assert archive.data.data_file == 'dummy.csv'
