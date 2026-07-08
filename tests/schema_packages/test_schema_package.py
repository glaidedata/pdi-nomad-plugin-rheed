import datetime

from nomad.datamodel import EntryArchive, EntryMetadata
from nomad.utils import get_logger

from pdi_nomad_plugin_rheed.schema_packages.schema_package import (
    RHEEDImageResult,
    RHEEDMeasurement,
    Sample,
    SubstrateHolder,
)


def test_schema_normalization():
    # 1. Setup the archive and main measurement
    archive = EntryArchive()
    archive.metadata = EntryMetadata(entry_name='test_rheed_entry')
    measurement = RHEEDMeasurement()
    archive.data = measurement

    # Set the global offset angle
    measurement.sample_phi_holder_alpha_deg = 15.0

    # 2. Setup a mock Image Result
    result = RHEEDImageResult()
    result.datetime = datetime.datetime(2026, 3, 13, 16, 30, 0)

    # Add Sample and SubstrateHolder data to the result
    result.sample = Sample(sample_id='m84266')
    result.substrate_holder = SubstrateHolder(rotation_angle_alpha_deg=30.0)

    # Append to the polymorphic results list
    measurement.results.append(result)

    # 3. Run Normalization
    logger = get_logger(__name__)

    # NOMAD normalizes from the bottom up, so we normalize the result first
    result.normalize(archive, logger)
    measurement.normalize(archive, logger)

    # 4. Assertions to verify our schema logic

    # Check if the auto-ID generation works correctly
    assert measurement.measurement_id == 'RHD_m84266_2026-03-13_16-30-00', (
        f"Expected 'RHD_m84266_2026-03-13_16-30-00', got '{measurement.measurement_id}'"
    )

    # Check if the math for the sample azimuth phi degree works (15.0 + 30.0 = 45.0)
    assert result.sample.sample_azimuth_phi_deg == 45.0, (  # noqa: PLR2004
        f"Expected 45.0, got '{result.sample.sample_azimuth_phi_deg}'"
    )
