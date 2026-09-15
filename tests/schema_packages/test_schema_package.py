import csv
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import numpy as np
from nomad.datamodel import EntryArchive, EntryMetadata
from nomad.metainfo import File
from nomad.utils import get_logger
from openpyxl import Workbook
from PIL import Image

from pdi_nomad_plugin_rheed.schema_packages.schema_package import (
    PointScan,
    RHEEDImageResult,
    RHEEDMeasurement,
    RHEEDPointScanResult,
)


def _write_synthetic_inputs(tmp_path):
    metadata_path = tmp_path / 'nova_C_RHEED_meta_synthetic.csv'
    fieldnames = [
        'file_path',
        'file_name',
        'm8_id',
        'date',
        'time',
        'azimuth',
        'mani_angle',
        'x_align',
        'y_align',
        'magnetic_lense',
        'x_coarse',
        'x_fine',
        'x_crossp',
        'x_angle',
        'y_coarse',
        'y_fine',
        'y_crossp',
        'y_angle',
        'energy_kev',
        'comments',
    ]
    rows = [
        {
            'file_path': 'Z:\\Synthetic\\orbit_capture.dst',
            'file_name': 'nested/orbit_capture.dst',
            'm8_id': 'nova_C',
            'date': '2042-05-06',
            'time': '07-08-09.123',
            'azimuth': '1 0 1',
            'mani_angle': '17.25',
            'x_align': '1.1',
            'y_align': '2.2',
            'magnetic_lense': '3.3',
            'x_coarse': '4.4',
            'x_fine': '5.5',
            'x_crossp': '6.6',
            'x_angle': '7.7',
            'y_coarse': '8.8',
            'y_fine': '9.9',
            'y_crossp': '10.1',
            'y_angle': '11.2',
            'energy_kev': '21.75',
            'comments': 'frame_interval_s=0.25 number_of_frames=5 invented video',
        },
        {
            'file_path': 'Z:\\Synthetic\\crystal_image.tif',
            'file_name': 'nested\\crystal_image.tif',
            'm8_id': 'nova_D',
            'date': '2042-05-06',
            'time': '07-08-10.456',
            'azimuth': '0 1 1',
            'comments': 'invented image',
        },
        {
            'm8_id': 'scan_B',
            'date': '2042-05-06',
            'time': '07-08-09.500',
            'comments': 'invented scan metadata',
        },
    ]
    with metadata_path.open('w', encoding='utf-8', newline='') as metadata_file:
        writer = csv.DictWriter(metadata_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    (tmp_path / 'crystal_image.tif').write_bytes(b'synthetic image bytes')
    (tmp_path / 'sweep.asc').write_text(
        'Recorded at 2042-05-06   07:08:09.500\n'
        'Time [s] Sensor A Sensor B\n'
        '71001 71002\n\n'
        '-0.000 1.5 2.5\n'
        '1.000 3.5 4.5\n',
        encoding='utf-8',
    )
    (tmp_path / 'sensors_2042-05-06___07-08-08.000.sn').write_text(
        '[Sensor 0]\nType=Rect Area\n', encoding='utf-8'
    )
    (tmp_path / 'sensor_overview_2042-05-06___07-08-09.750.tif').write_bytes(
        b'synthetic sensor overview bytes'
    )
    (tmp_path / 'color_scale.col').write_text(
        '[Colors]\nGamma = 1.25\n', encoding='utf-8'
    )

    workbook = Workbook()
    settings_sheet = workbook.active
    settings_sheet.title = 'RHEED settings'
    settings_sheet.append(['meaning', 'created', 'created', 'electronics'])
    settings_sheet.append(['type', 'date', 'time', 'enum'])
    settings_sheet.append(['unit', '', '', 'FUG|STAIB'])
    settings_sheet.append(['format', 'date', 'time', 'string'])
    settings_sheet.append(['mode', 'invented', 'invented', 'invented'])
    settings_sheet.append(
        [
            'field',
            'date',
            'time',
            'electronics_type',
            'distance_sample_to_screen_mm',
            'image_length_calibration_mm_per_px',
            'resolution_x_px',
            'resolution_y_px',
            'sample_phi_holder_alpha_deg',
            'comment',
        ]
    )
    settings_sheet.append(
        [
            'value',
            datetime(2042, 5, 6),
            datetime(2042, 5, 6, 7, 8, 9).time(),
            'FUG',
            412.5,
            0.37,
            320,
            240,
            27.5,
            'invented workbook comment',
        ]
    )
    workbook.save(tmp_path / 'MBE42_config_w_RHEED.xlsx')

    (tmp_path / 'Rotation.txt').write_text(
        "'Synthetic Rotation Log File\n\n"
        "'Date,Rotation.steps,Rotation.deg\n"
        '06/05/2042 07:08:08.500 901 12.75\n'
        '06/05/2042 07:08:10.625 905 13.25\n',
        encoding='utf-8',
    )
    return metadata_path


def _normalize_synthetic_measurement(tmp_path, prepare_files=None):
    metadata_path = _write_synthetic_inputs(tmp_path)
    if prepare_files:
        prepare_files(tmp_path)
    archive = EntryArchive()
    archive.metadata = EntryMetadata(
        entry_name='synthetic_rheed_entry',
        upload_id='synthetic-upload',
        entry_id='synthetic-entry',
    )
    measurement = RHEEDMeasurement(data_file=str(metadata_path))
    archive.data = measurement
    archive.m_context = MagicMock()
    archive.m_context.upload_id = 'synthetic-upload'
    archive.m_context._get_ids.return_value = ('synthetic-upload', 'synthetic-entry')
    archive.m_context.normalize_reference.side_effect = lambda section, value: value

    @contextmanager
    def mock_raw_file(filename, mode):
        class MockFile:
            name = str(metadata_path)

        yield MockFile()

    archive.m_context.raw_file.side_effect = mock_raw_file
    measurement.normalize(archive, get_logger(__name__))
    return measurement


def test_schema_extraction_normalization(tmp_path):
    measurement = _normalize_synthetic_measurement(tmp_path)

    assert measurement.measurement_id == 'RHD_nova'
    assert len(measurement.results) == 4  # noqa: PLR2004
    results_by_name = {result.name: result for result in measurement.results}
    assert {name: result.result_type for name, result in results_by_name.items()} == {
        'orbit_capture.dst': 'video',
        'crystal_image.tif': 'image',
        'sweep.asc': 'scan_point',
        'sensor_overview_2042-05-06___07-08-09.750.tif': 'image',
    }

    video = results_by_name['orbit_capture.dst']
    image = results_by_name['crystal_image.tif']
    scan = results_by_name['sweep.asc']
    assert video.sample.sample_id == 'nova_C'
    assert video.substrate_holder.position_measured == 'C'
    assert image.sample.sample_id == 'nova_D'
    assert image.substrate_holder.position_measured == 'D'
    assert scan.sample.sample_id == 'scan_B'
    assert scan.substrate_holder.position_measured == 'B'
    assert image.images == 'crystal_image.tif'
    assert image.datetime == datetime(2042, 5, 6, 5, 8, 10, 456000, tzinfo=UTC)
    assert video.measurement_settings.e_gun_FUG.electron_energy_keV == 21.75  # noqa: PLR2004
    assert len(scan.point_scans) == 1
    point_scan = scan.point_scans[0]
    assert point_scan.source_file == 'sweep.asc'
    assert point_scan.start_time == datetime(2042, 5, 6, 5, 8, 9, 500000, tzinfo=UTC)
    assert point_scan.end_time == datetime(2042, 5, 6, 5, 8, 10, 500000, tzinfo=UTC)
    assert [sensor.sensor_name for sensor in point_scan.sensors] == [
        'Sensor A',
        'Sensor B',
    ]
    assert [sensor.sensor_id for sensor in point_scan.sensors] == [71001, 71002]
    assert list(point_scan.sensors[0].relative_time.magnitude) == [0.0, 1.0]
    assert list(point_scan.sensors[0].intensity) == [1.5, 3.5]
    assert list(point_scan.sensors[1].intensity) == [2.5, 4.5]
    assert point_scan.sensor_definition_file == 'sensors_2042-05-06___07-08-08.000.sn'
    assert (
        point_scan.sensor_position_overview_picture
        == 'sensor_overview_2042-05-06___07-08-09.750.tif'
    )
    assert measurement.color_table == 'color_scale.col'


def test_maps_all_fug_deflection_fields_and_preserves_missing_values(tmp_path):
    measurement = _normalize_synthetic_measurement(tmp_path)
    deflection = measurement.results[0].measurement_settings.deflection_unit_FUG

    assert deflection.alignment_x == 1.1  # noqa: PLR2004
    assert deflection.alignment_y == 2.2  # noqa: PLR2004
    assert deflection.magnet_lens == 3.3  # noqa: PLR2004
    assert deflection.beam_deflection_x_coarse == 4.4  # noqa: PLR2004
    assert deflection.beam_deflection_x_fine == 5.5  # noqa: PLR2004
    assert deflection.beam_deflection_x_crosspoint == 6.6  # noqa: PLR2004
    assert deflection.beam_deflection_x_angle == 7.7  # noqa: PLR2004
    assert deflection.beam_deflection_y_coarse == 8.8  # noqa: PLR2004
    assert deflection.beam_deflection_y_fine == 9.9  # noqa: PLR2004
    assert deflection.beam_deflection_y_crosspoint == 10.1  # noqa: PLR2004
    assert deflection.beam_deflection_y_angle == 11.2  # noqa: PLR2004

    missing = measurement.results[1].measurement_settings.deflection_unit_FUG
    assert missing.m_to_dict() == {}


def test_raw_file_quantities_use_nomad_file_references(tmp_path):
    measurement = _normalize_synthetic_measurement(tmp_path)
    results_by_name = {result.name: result for result in measurement.results}
    image = results_by_name['crystal_image.tif']
    point_scan = results_by_name['sweep.asc'].point_scans[0]

    assert (
        RHEEDMeasurement.m_def.all_quantities['data_file'].type.standard_type() == 'str'
    )
    assert not isinstance(RHEEDMeasurement.m_def.all_quantities['data_file'].type, File)
    assert isinstance(RHEEDImageResult.m_def.all_quantities['images'].type, File)
    assert isinstance(PointScan.m_def.all_quantities['source_file'].type, File)
    assert isinstance(
        PointScan.m_def.all_quantities['sensor_definition_file'].type, File
    )
    assert isinstance(
        PointScan.m_def.all_quantities['sensor_position_overview_picture'].type,
        File,
    )
    assert isinstance(RHEEDMeasurement.m_def.all_quantities['color_table'].type, File)

    assert image.m_to_dict()['images'] == 'crystal_image.tif'
    assert point_scan.m_to_dict()['source_file'] == 'sweep.asc'
    assert (
        point_scan.m_to_dict()['sensor_definition_file']
        == 'sensors_2042-05-06___07-08-08.000.sn'
    )
    assert (
        point_scan.m_to_dict()['sensor_position_overview_picture']
        == 'sensor_overview_2042-05-06___07-08-09.750.tif'
    )
    assert measurement.m_to_dict()['color_table'] == 'color_scale.col'


def test_interprets_csv_source_times_as_berlin_wall_clock_times(tmp_path):
    metadata_path = tmp_path / 'timestamps.csv'
    with metadata_path.open('w', encoding='utf-8', newline='') as metadata_file:
        writer = csv.DictWriter(metadata_file, fieldnames=['date', 'time'])
        writer.writeheader()
        writer.writerows(
            [
                {'date': '2042-01-15', 'time': '15-33-45.678'},
                {'date': '2042-07-15', 'time': '15-33-45.678'},
            ]
        )

    parsed = RHEEDMeasurement()._load_and_prep_csv(metadata_path)['parsed_datetime']
    berlin = ZoneInfo('Europe/Berlin')

    assert parsed.iloc[0] == datetime(2042, 1, 15, 15, 33, 45, 678000, tzinfo=berlin)
    assert parsed.iloc[0].astimezone(UTC) == datetime(
        2042, 1, 15, 14, 33, 45, 678000, tzinfo=UTC
    )
    assert parsed.iloc[1] == datetime(2042, 7, 15, 15, 33, 45, 678000, tzinfo=berlin)
    assert parsed.iloc[1].astimezone(UTC) == datetime(
        2042, 7, 15, 13, 33, 45, 678000, tzinfo=UTC
    )


def test_stores_tiff_and_pgm_plotly_previews_with_raw_references(
    tmp_path,
):
    tiff_values = np.array(
        [
            [[1, 2, 3], [4, 5, 6]],
            [[7, 8, 9], [10, 11, 12]],
        ],
        dtype=np.uint8,
    )
    pgm_name = 'snapshot_2042-05-06___07-08-13.500.pgm'

    def prepare_files(directory):
        Image.fromarray(tiff_values).save(directory / 'crystal_image.tif')
        (directory / pgm_name).write_text('P2\n2 2\n10\n1 12\n3 4\n', encoding='ascii')

    measurement = _normalize_synthetic_measurement(tmp_path, prepare_files)

    results_by_name = {result.name: result for result in measurement.results}
    tiff_result = results_by_name['crystal_image.tif']
    pgm_result = results_by_name[pgm_name]

    assert tiff_result.images == 'crystal_image.tif'
    assert pgm_result.images == pgm_name
    assert tiff_result.plot is not None
    assert pgm_result.plot is not None
    assert len(tiff_result.plot.figures) == 1
    assert len(pgm_result.plot.figures) == 1
    tiff_figure = tiff_result.plot.figures[0].figure
    pgm_figure = pgm_result.plot.figures[0].figure
    assert tiff_figure['data'][0]['type'] == 'image'
    assert np.array_equal(np.asarray(tiff_figure['data'][0]['z']), tiff_values)
    assert pgm_figure['data'][0]['type'] == 'heatmap'
    assert np.array_equal(
        np.asarray(pgm_figure['data'][0]['z']), np.array([[1, 12], [3, 4]])
    )


def test_parses_global_rheed_settings_from_excel(tmp_path):
    measurement = _normalize_synthetic_measurement(tmp_path)
    settings = measurement.instrument_settings

    assert settings.electronics_type == 'FUG'
    assert settings.chamber_geometry.distance_sample_to_screen_mm == 412.5  # noqa: PLR2004
    assert settings.camera.image_length_calibration_mm_per_px == 0.37  # noqa: PLR2004
    assert settings.camera.resolution_x_px == 320  # noqa: PLR2004
    assert settings.camera.resolution_y_px == 240  # noqa: PLR2004
    assert measurement.sample_phi_holder_alpha_deg == 27.5  # noqa: PLR2004


def test_parses_rotation_log_and_assigns_automatic_result(tmp_path):
    _write_synthetic_inputs(tmp_path)
    unindexed_name = 'unindexed_2042-05-06___07-08-12.500.tif'
    (tmp_path / unindexed_name).write_bytes(b'synthetic unindexed image bytes')
    measurement = RHEEDMeasurement()

    rotation = measurement._parse_rotation_log(tmp_path, get_logger(__name__))

    assert list(rotation['parsed_datetime']) == [
        datetime(2042, 5, 6, 7, 8, 8, 500000, tzinfo=ZoneInfo('Europe/Berlin')),
        datetime(2042, 5, 6, 7, 8, 10, 625000, tzinfo=ZoneInfo('Europe/Berlin')),
    ]
    assert list(rotation['steps']) == [901, 905]
    assert list(rotation['alpha']) == [12.75, 13.25]

    normalized = _normalize_synthetic_measurement(tmp_path)
    unindexed_result = next(
        result for result in normalized.results if result.name == unindexed_name
    )
    assert unindexed_result.substrate_holder.rotation_angle_alpha_deg == 13.25  # noqa: PLR2004


def test_parses_comma_separated_rotation_rows(tmp_path):
    (tmp_path / 'Rotation.txt').write_text(
        "'Synthetic Rotation Log File\n\n"
        "'Date,Rotation.steps,Rotation.deg\n"
        '15/01/2042,15:33:45.125,44,6.5\n'
        '15/01/2042 15:33:46.250,45,7.5\n',
        encoding='utf-8',
    )

    rotation = RHEEDMeasurement()._parse_rotation_log(tmp_path, get_logger(__name__))

    assert list(rotation['steps']) == [44, 45]
    assert list(rotation['alpha']) == [6.5, 7.5]
    assert rotation.iloc[0]['parsed_datetime'] == datetime(
        2042, 1, 15, 15, 33, 45, 125000, tzinfo=ZoneInfo('Europe/Berlin')
    )
    assert rotation.iloc[1]['parsed_datetime'] == datetime(
        2042, 1, 15, 15, 33, 46, 250000, tzinfo=ZoneInfo('Europe/Berlin')
    )


def test_assigns_rotation_alpha_with_explicit_precedence_and_calculates_phi(
    tmp_path,
):
    preceding_alpha = 12.75
    latest_alpha = 13.25
    large_explicit_alpha = 400
    holder_offset = 27.5

    def prepare_files(directory):
        metadata_path = directory / 'nova_C_RHEED_meta_synthetic.csv'
        with metadata_path.open(encoding='utf-8', newline='') as metadata_file:
            reader = csv.DictReader(metadata_file)
            fieldnames = reader.fieldnames
            rows = list(reader)

        rows[1]['mani_angle'] = '-1'

        def explicit_row(filename, timestamp, alpha, sample_id):
            row = {fieldname: '' for fieldname in fieldnames}
            row.update(
                {
                    'file_name': f'nested/{filename}',
                    'm8_id': sample_id,
                    'date': '2042-05-06',
                    'time': timestamp,
                    'mani_angle': alpha,
                    'comments': 'invented explicit rotation test',
                }
            )
            return row

        rows.extend(
            [
                explicit_row('zero_angle.pgm', '07-08-12.500', '0', 'zero_A'),
                explicit_row(
                    'large_angle.pgm',
                    '07-08-12.500',
                    str(large_explicit_alpha),
                    'large_B',
                ),
                explicit_row('exact_angle.pgm', '07-08-10.625', '-1', 'exact_C'),
            ]
        )
        with metadata_path.open('w', encoding='utf-8', newline='') as metadata_file:
            writer = csv.DictWriter(metadata_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        for filename in (
            'zero_angle.pgm',
            'large_angle.pgm',
            'exact_angle.pgm',
            'automatic_2042-05-06___07-08-12.500.pgm',
            'closer_future_2042-05-06___07-08-10.500.pgm',
            'no_preceding_2042-05-06___07-08-08.250.pgm',
        ):
            (directory / filename).write_text('P2\n1 1\n9\n7\n', encoding='ascii')

    measurement = _normalize_synthetic_measurement(tmp_path, prepare_files)
    results = {result.name: result for result in measurement.results}

    assert (
        results['crystal_image.tif'].substrate_holder.rotation_angle_alpha_deg
        == preceding_alpha
    )
    assert results['zero_angle.pgm'].substrate_holder.rotation_angle_alpha_deg == 0
    assert (
        results['large_angle.pgm'].substrate_holder.rotation_angle_alpha_deg
        == large_explicit_alpha
    )
    assert (
        results['exact_angle.pgm'].substrate_holder.rotation_angle_alpha_deg
        == latest_alpha
    )
    assert (
        results[
            'automatic_2042-05-06___07-08-12.500.pgm'
        ].substrate_holder.rotation_angle_alpha_deg
        == latest_alpha
    )
    assert (
        results[
            'closer_future_2042-05-06___07-08-10.500.pgm'
        ].substrate_holder.rotation_angle_alpha_deg
        == preceding_alpha
    )
    assert (
        getattr(
            results['no_preceding_2042-05-06___07-08-08.250.pgm'].substrate_holder,
            'rotation_angle_alpha_deg',
            None,
        )
        is None
    )
    assert (
        results['sweep.asc'].substrate_holder.rotation_angle_alpha_deg
        == preceding_alpha
    )

    assert results['zero_angle.pgm'].sample.sample_azimuth_phi_deg == holder_offset
    assert (
        results['large_angle.pgm'].sample.sample_azimuth_phi_deg
        == holder_offset + large_explicit_alpha
    )


def test_discovers_timestamped_tiff_and_pgm_files(tmp_path):
    _write_synthetic_inputs(tmp_path)
    tiff_name = 'unindexed_2042-05-06___07-08-12.500.tif'
    pgm_name = 'unindexed_2042-05-06___07-08-13.500.pgm'
    (tmp_path / tiff_name).write_bytes(b'synthetic unindexed tiff bytes')
    (tmp_path / pgm_name).write_text('P2\n1 1\n255\n7\n', encoding='ascii')

    normalized = _normalize_synthetic_measurement(tmp_path)
    discovered = {
        result.name: result
        for result in normalized.results
        if result.name in {tiff_name, pgm_name}
    }

    assert {name: result.result_type for name, result in discovered.items()} == {
        tiff_name: 'image',
        pgm_name: 'image',
    }
    assert discovered[tiff_name].datetime == datetime(
        2042, 5, 6, 5, 8, 12, 500000, tzinfo=UTC
    )
    assert discovered[tiff_name].sample.sample_id == 'nova_D'


def test_scan_metadata_priority(tmp_path):
    measurement = RHEEDMeasurement()

    def match_sample_id(rows, start_time, end_time):
        metadata_path = tmp_path / 'association.csv'
        with metadata_path.open('w', encoding='utf-8', newline='') as metadata_file:
            writer = csv.DictWriter(metadata_file, fieldnames=['m8_id', 'date', 'time'])
            writer.writeheader()
            writer.writerows(rows)

        result = RHEEDPointScanResult()
        measurement._match_scan_metadata(
            result,
            start_time,
            end_time,
            measurement._load_and_prep_csv(metadata_path),
        )
        return result.sample.sample_id

    scan_start = datetime(2042, 5, 6, 7, 8, 20, tzinfo=ZoneInfo('Europe/Berlin'))
    scan_end = datetime(2042, 5, 6, 7, 8, 25, tzinfo=ZoneInfo('Europe/Berlin'))
    assert (
        match_sample_id(
            [
                {'m8_id': 'before_A', 'date': '2042-05-06', 'time': '07-08-19.000'},
                {'m8_id': 'exact_B', 'date': '2042-05-06', 'time': '07-08-20.000'},
                {'m8_id': 'during_C', 'date': '2042-05-06', 'time': '07-08-21.000'},
            ],
            scan_start,
            scan_end,
        )
        == 'exact_B'
    )
    assert (
        match_sample_id(
            [
                {'m8_id': 'before_A', 'date': '2042-05-06', 'time': '07-08-19.000'},
                {'m8_id': 'during_B', 'date': '2042-05-06', 'time': '07-08-21.000'},
                {'m8_id': 'during_C', 'date': '2042-05-06', 'time': '07-08-22.000'},
            ],
            scan_start,
            scan_end,
        )
        == 'during_B'
    )
    assert (
        match_sample_id(
            [
                {'m8_id': 'before_A', 'date': '2042-05-06', 'time': '07-08-18.000'},
                {'m8_id': 'before_B', 'date': '2042-05-06', 'time': '07-08-19.000'},
                {'m8_id': 'after_C', 'date': '2042-05-06', 'time': '07-08-26.000'},
            ],
            scan_start,
            scan_end,
        )
        == 'before_B'
    )
    assert (
        match_sample_id(
            [
                {'m8_id': 'after_A', 'date': '2042-05-06', 'time': '07-08-26.000'},
                {'m8_id': 'after_B', 'date': '2042-05-06', 'time': '07-08-27.000'},
            ],
            scan_start,
            scan_end,
        )
        == 'after_A'
    )


def test_scan_auxiliary_priority(tmp_path):
    start_time = datetime(2042, 5, 6, 7, 8, 20, tzinfo=ZoneInfo('Europe/Berlin'))
    end_time = datetime(2042, 5, 6, 7, 8, 25, tzinfo=ZoneInfo('Europe/Berlin'))
    exact_name = 'sensors_2042-05-06___07-08-20.000.sn'
    during_name = 'sensors_2042-05-06___07-08-21.000.sn'
    after_name = 'sensor_overview_2042-05-06___07-08-26.000.tif'
    for filename in (exact_name, during_name, after_name):
        (tmp_path / filename).write_text('synthetic auxiliary', encoding='utf-8')

    measurement = RHEEDMeasurement()
    assert (
        measurement._select_scan_auxiliary(
            [exact_name, during_name], start_time, end_time
        )
        == exact_name
    )
    assert (
        measurement._select_scan_auxiliary([after_name], start_time, end_time)
        == after_name
    )
