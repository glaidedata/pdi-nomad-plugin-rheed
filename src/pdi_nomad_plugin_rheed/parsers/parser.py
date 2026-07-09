import os
import re
from datetime import datetime

import pandas as pd
from nomad.datamodel import EntryArchive
from nomad.parsing import MatchingParser

from pdi_nomad_plugin_rheed.schema_packages.schema_package import (
    Camera,
    ChamberGeometry,
    InstrumentSettings,
    RHEEDImageResult,
    RHEEDMeasurement,
    RHEEDMeasurementSettings,
    RHEEDPointScanResult,
    RHEEDVideoResult,
    Sample,
    SubstrateHolder,
)

# --- CONFIGURATION ---
CSV_TO_SCHEMA_MAP = {
    'azimuth': 'sample_azimuth_uvw',
    'substrate': 'sample_surface_compound',
    'substrate_orientation': 'sample_surface_hkl',
    'film': 'sample_surface_compound',
    'film_orientation': 'sample_surface_hkl',
    'mani_angle': 'rotation_angle_alpha_deg',
    'energy_kev': 'electron_energy_keV',
    'emission_uA': 'emission_current_uA',
    'filament_a': 'filament_current_A',
    'filament_v': 'filament_voltage_V',
    'grid_v': 'grid_voltage_V',
    'x_align': 'alignment_x',
    'y_align': 'alignment_y',
    'magnetic_lense': 'magnet_lens',
    'x_coarse': 'beam_deflection_x_coarse',
    'x_fine': 'beam_deflection_x_fine',
    'x_crossp': 'beam_deflection_x_crosspoint',
    'x_angle': 'beam_deflection_x_angle',
    'y_coarse': 'beam_deflection_y_coarse',
    'y_fine': 'beam_deflection_y_fine',
    'y_crossp': 'beam_deflection_y_crosspoint',
    'y_angle': 'beam_deflection_y_angle',
    'comments': 'notes',
}

INSTRUMENT_SETTINGS_COLUMN_MAP = {
    'electronicstype': (
        None,
        'electronics_type',
        lambda value: str(value).strip().upper(),
    ),
    'electronics': (None, 'electronics_type', lambda value: str(value).strip().upper()),
    'distancesampletoscreenmm': (
        'chamber_geometry',
        'distance_sample_to_screen_mm',
        float,
    ),
    'distancetoscreenmm': ('chamber_geometry', 'distance_sample_to_screen_mm', float),
    'resolutionxpx': ('camera', 'resolution_x_px', int),
    'resolutionypx': ('camera', 'resolution_y_px', int),
    'imagelengthcalibrationmmperpx': (
        'camera',
        'image_length_calibration_mm_per_px',
        float,
    ),
}


class RheedParser(MatchingParser):
    def parse(self, mainfile: str, archive: EntryArchive, logger):
        """
        Main entry point. Keeps the high-level workflow clean and easy to read.
        """
        logger.info('Starting RHEED parser.')

        # 1. Initialize ELN Copy
        measurement = RHEEDMeasurement()
        archive.data = measurement

        # 2. Get Workspace Context
        mainfile_dir = os.path.dirname(mainfile)
        all_files = os.listdir(mainfile_dir)

        # 3. Execute Helper Methods to Extract Data
        df_meta = self._parse_metadata_csv(mainfile, measurement, logger)
        df_rot = self._parse_rotation_log(mainfile_dir, logger)
        self._parse_instrument_settings(mainfile_dir, all_files, measurement, logger)

        # 4. Process and Match Files
        if df_meta is not None:
            self._process_data_files(all_files, df_meta, df_rot, measurement, logger)

        logger.info('Finished parsing RHEED metadata and linking files.')

    # ---------------------------------------------------------
    # HELPER METHODS (Keeps the main parse function clean)
    # ---------------------------------------------------------

    def _parse_metadata_csv(self, mainfile, measurement, logger):
        """Reads the master CSV and links the MBE ID."""
        try:
            df = pd.read_csv(mainfile)
            df.columns = df.columns.str.strip()

            if 'date' in df.columns and 'time' in df.columns:
                df['parsed_datetime'] = pd.to_datetime(
                    df['date'].astype(str) + ' ' + df['time'].astype(str),
                    errors='coerce',
                )

            # Extract MBE ID for reference linking
            if 'm8_id' in df.columns:
                valid_ids = df['m8_id'].dropna().astype(str)
                if not valid_ids.empty:
                    m8_id = valid_ids.iloc[0].split('_')[0]
                    measurement.measurement_id = f'RHD_{m8_id}'
            return df
        except Exception as e:
            logger.error(f'Failed to read metadata CSV: {e}')
            return None

    def _parse_rotation_log(self, mainfile_dir, logger):
        """Reads rotation.txt if it exists."""
        rot_path = os.path.join(mainfile_dir, 'rotation.txt')
        if os.path.exists(rot_path):
            try:
                return pd.read_csv(rot_path, sep=r'\s+|,', engine='python')
            except Exception as e:
                logger.warning(f'Could not parse rotation log: {e}')
        return None

    def _parse_instrument_settings(self, mainfile_dir, all_files, measurement, logger):
        """Extracts fixed instrument settings from the MBE Excel file."""
        excel_files = [f for f in all_files if f.endswith('.xlsx') and 'MBE' in f]
        if excel_files:
            try:
                excel_path = os.path.join(mainfile_dir, excel_files[0])
                df_excel = pd.read_excel(excel_path, sheet_name='RHEED settings')

                logger.info(
                    f'Loaded {len(df_excel)} rows from RHEED settings Excel file.'
                )

                instrument_settings = InstrumentSettings()

                def assign_setting(raw_key, raw_value):
                    if pd.isna(raw_key) or pd.isna(raw_value):
                        return
                    normalized_key = re.sub(r'[^a-z0-9]+', '', str(raw_key).lower())
                    mapping = INSTRUMENT_SETTINGS_COLUMN_MAP.get(normalized_key)
                    if mapping is None:
                        return

                    section_name, attr_name, caster = mapping
                    try:
                        value = caster(raw_value)
                    except (TypeError, ValueError):
                        return

                    target = instrument_settings
                    if section_name is not None:
                        target = getattr(instrument_settings, section_name, None)
                        if target is None:
                            if section_name == 'chamber_geometry':
                                target = ChamberGeometry()
                            elif section_name == 'camera':
                                target = Camera()
                            setattr(instrument_settings, section_name, target)

                    setattr(target, attr_name, value)

                for column in df_excel.columns:
                    non_null_values = df_excel[column].dropna()
                    if not non_null_values.empty:
                        assign_setting(column, non_null_values.iloc[0])

                if len(df_excel.columns) > 1:
                    key_column = df_excel.columns[0]
                    value_column = df_excel.columns[1]
                    for raw_key, raw_value in zip(
                        df_excel[key_column], df_excel[value_column]
                    ):
                        assign_setting(raw_key, raw_value)

                measurement.instrument_settings = instrument_settings
            except Exception as e:
                logger.warning(f'Could not parse Excel settings: {e}')

    def _process_data_files(self, all_files, df_meta, df_rot, measurement, logger):
        """Iterates through files and matches them to metadata."""
        assigned_files = set()
        time_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}___\d{2}-\d{2}-\d{2}\.\d{3})')

        # 1. Process files explicitly named in the CSV
        for _, row in df_meta.iterrows():
            fname = str(row.get('file_name', '')).strip()
            if fname in all_files:
                assigned_files.add(fname)
                result = self._create_result_instance(fname)
                if result:
                    self._populate_schema_from_row(result, row)
                    measurement.results.append(result)

        # 2. Process remaining unassigned files via Timestamp matching
        unassigned = [
            f
            for f in all_files
            if f not in assigned_files and f.endswith(('.tif', '.pgm', '.asc', '.csv'))
        ]
        for fname in unassigned:
            match = time_pattern.search(fname)
            if not match:
                continue

            try:
                file_dt = datetime.strptime(match.group(1), '%Y-%m-%d___%H-%M-%S.%f')
            except ValueError:
                continue

            result = self._create_result_instance(fname)
            if not result:
                continue
            result.datetime = file_dt.isoformat()

            if 'parsed_datetime' in df_meta.columns:
                past_meta = df_meta[df_meta['parsed_datetime'] <= file_dt]
                if not past_meta.empty:
                    best_row = past_meta.sort_values(
                        by='parsed_datetime', ascending=False
                    ).iloc[0]
                    self._populate_schema_from_row(result, best_row)

            # Set raw alpha angle from rotation log (Normalizer will do the math)
            if df_rot is not None and 'parsed_datetime' in df_rot.columns:
                past_rot = df_rot[df_rot['parsed_datetime'] <= file_dt]
                if not past_rot.empty:
                    best_rot = past_rot.sort_values(
                        by='parsed_datetime', ascending=False
                    ).iloc[0]
                    if result.substrate_holder is None:
                        result.substrate_holder = SubstrateHolder()
                    result.substrate_holder.rotation_angle_alpha_deg = float(
                        best_rot.iloc[-1]
                    )

            measurement.results.append(result)

    def _create_result_instance(self, fname):
        """Returns the correct schema class based on file extension."""
        if fname.endswith(('.tif', '.pgm')) and 'sensor' not in fname.lower():
            res = RHEEDImageResult()
            res.images = [fname]
            return res
        elif fname.endswith(('.asc', '.csv')) and 'sensor' not in fname.lower():
            res = RHEEDPointScanResult()
            res.point_scans = [fname]
            return res
        elif fname.endswith('.dst'):
            return RHEEDVideoResult()
        return None

    def _populate_schema_from_row(self, result_obj, row):
        """Maps a pandas row into the nested Schema objects."""
        sample = Sample()
        settings = RHEEDMeasurementSettings()

        # Handle Sample ID parsing
        m8_val = str(row.get('m8_id', ''))
        if '_' in m8_val:
            parts = m8_val.split('_')
            sample.sample_id = parts[0]
            result_obj.substrate_holder = SubstrateHolder(position_measured=parts[1])

        # Map dynamic CSV columns using our mapping dict
        for csv_col, schema_var in CSV_TO_SCHEMA_MAP.items():
            if csv_col in row and pd.notna(row[csv_col]):
                val = row[csv_col]
                if hasattr(sample, schema_var):
                    setattr(sample, schema_var, val)
                elif hasattr(settings, schema_var):
                    setattr(settings, schema_var, val)
                elif hasattr(result_obj, schema_var):
                    setattr(result_obj, schema_var, val)

        result_obj.sample = sample
        result_obj.measurement_settings = settings
