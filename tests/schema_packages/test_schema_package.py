import numpy as np
from nomad.client import normalize_all
from nomad.datamodel import EntryArchive

from pdi_nomad_plugin_rheed.schema_packages.schema_package import (
    ChamberGeometry,
    EGunSTAIB,
    InstrumentSettings,
    PointScan,
    RHEEDMeasurement,
    RHEEDMeasurementSettings,
    RHEEDPointScanResult,
    RHEEDSample,
    SubstrateHolder,
)


def test_schema_instantiation():
    """
    Tests if the new highly-structured RHEEDMeasurement schema can be
    instantiated, populated with the new hardware/sample classes, and normalized.
    """
    entry = RHEEDMeasurement()

    # 1. Test the renamed reference field
    entry.mbe_experiment_ref = 'm84123'

    # 2. Test new Instrument Settings
    entry.instrument_settings = InstrumentSettings(
        chamber_geometry=ChamberGeometry(distance_sample_to_screen_mm=150.0)
    )

    # 3. Test Substrate Holder
    entry.substrate_holder = SubstrateHolder(rotation_angle_alpha_deg=45.0)

    # 4. Test RHEEDSample (with numpy array for crystallographic direction)
    entry.sample = RHEEDSample(
        sample_id='PDI_Sample_001',
        sample_azimuth_uvw=np.array([1, 1, 0], dtype=np.int32),
    )

    # 5. Test nested Measurement Settings (Vendor-specific hardware)
    entry.measurement_settings = RHEEDMeasurementSettings(
        compensation_cage_on=True, egun_STAIB=EGunSTAIB(electron_energy_keV=15.0)
    )

    # 6. Create a Point Scan Result with the new sensor_definition_file
    scan_item = PointScan()
    scan_item.source_file = 'dummy_scan.csv'
    scan_item.sensor_definition_file = 'dummy_config.sn'

    scan_result = RHEEDPointScanResult()
    scan_result.point_scans.append(scan_item)

    # 7. Add result to the root measurement
    entry.results.append(scan_result)

    # 8. Create Archive & Normalize
    archive = EntryArchive(data=entry)
    normalize_all(archive)

    # 9. Verify structures and types
    assert isinstance(archive.data, RHEEDMeasurement)
    assert archive.data.mbe_experiment_ref == 'm84123'
    assert (
        archive.data.instrument_settings.chamber_geometry.distance_sample_to_screen_mm
        == 150.0  # noqa PLR2004
    )
    assert archive.data.substrate_holder.rotation_angle_alpha_deg == 45.0  # noqa PLR2004
    assert archive.data.sample.sample_id == 'PDI_Sample_001'
    assert list(archive.data.sample.sample_azimuth_uvw) == [1, 1, 0]
    assert archive.data.measurement_settings.egun_STAIB.electron_energy_keV == 15.0  # noqa PLR2004

    assert len(archive.data.results) == 1
    assert archive.data.results[0].point_scans[0].source_file == 'dummy_scan.csv'
    assert (
        archive.data.results[0].point_scans[0].sensor_definition_file
        == 'dummy_config.sn'
    )
