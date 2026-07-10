from contextlib import contextmanager
from unittest.mock import MagicMock

from nomad.datamodel import EntryArchive, EntryMetadata
from nomad.utils import get_logger

from pdi_nomad_plugin_rheed.schema_packages.schema_package import RHEEDMeasurement


def test_schema_extraction_normalization(tmp_path):
    """
    Tests the heavy-lifting extraction engine inside the normalizer.
    Verifies that it reads the CSV, parses the metadata, and populates the schema tree.
    """
    # 1. Create a dummy CSV file with mock data
    test_file = tmp_path / 'm84266_A_RHEED_meta_final.csv'
    csv_content = (
        'm8_id,date,time,file_name,azimuth,energy_kev,comments\n'
        'm84266_A,2026-03-13,16:33:40,dummy_image.tif,1 1 0,15.5,Test Comment\n'
    )
    test_file.write_text(csv_content)

    # 2. Setup the Archive and ELN entry
    archive = EntryArchive()
    archive.metadata = EntryMetadata(entry_name='test_rheed_entry')

    measurement = RHEEDMeasurement()
    measurement.data_file = str(test_file)  # Point the normalizer to our dummy file
    archive.data = measurement

    # 3. Mock the raw_file context manager so the normalizer can "open" the file
    archive.m_context = MagicMock()

    @contextmanager
    def mock_raw_file(filename, mode):
        class MockFile:
            name = str(test_file)

        yield MockFile()

    archive.m_context.raw_file.side_effect = mock_raw_file

    # 4. Run Normalization
    logger = get_logger(__name__)
    measurement.normalize(archive, logger)

    # 5. Assertions
    # Verify the global Measurement ID was pulled from m8_id
    assert measurement.measurement_id == 'RHD_m84266', (
        f"Expected 'RHD_m84266', got '{measurement.measurement_id}'"
    )

    # Verify the result was generated
    assert len(measurement.results) == 1, (
        'Normalizer did not create a result entry for the CSV row.'
    )

    res = measurement.results[0]

    # Verify specific data mapping
    assert res.sample.sample_id == 'm84266', 'Failed to parse sample_id from m8_id'
    assert res.sample.sample_azimuth_uvw == '1 1 0', 'Failed to map azimuth'
    assert res.notes == 'Test Comment', 'Failed to map comments to notes'

    # Verify deeply nested hardware mapping
    assert res.measurement_settings.e_gun_FUG.electron_energy_keV == 15.5, (  # noqa: PLR2004
        'Failed to map nested electron_energy_keV'
    )
