import os
import re
import pandas as pd
from datetime import datetime

import numpy as np
from nomad.metainfo import SchemaPackage, Quantity, SubSection, Section, Datetime, MEnum
from nomad.datamodel.data import ArchiveSection, EntryData
from nomad.datamodel.metainfo.basesections import Measurement, MeasurementResult
from nomad.datamodel.metainfo.annotations import ELNAnnotation, ELNComponentEnum

m_package = SchemaPackage()


# ---------------------------------------------------------
# 1. Global Instrument Sections
# ---------------------------------------------------------
class ChamberGeometry(ArchiveSection):
    distance_sample_to_screen_mm = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )


class Camera(ArchiveSection):
    resolution_x_px = Quantity(type=int, a_eln=dict(component='NumberEditQuantity'))
    resolution_y_px = Quantity(type=int, a_eln=dict(component='NumberEditQuantity'))
    image_length_calibration_mm_per_px = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )


class InstrumentSettings(ArchiveSection):
    electronics_type = Quantity(
        type=MEnum('FUG', 'STAIB'), a_eln=dict(component='EnumEditQuantity')
    )
    chamber_geometry = SubSection(section_def=ChamberGeometry)
    camera = SubSection(section_def=Camera)


# ---------------------------------------------------------
# 2. Hardware Settings (Dynamic)
# ---------------------------------------------------------
class EGunSTAIB(ArchiveSection):
    electron_energy_keV = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )
    emission_current_uA = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )
    filament_current_A = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )


class EGunFUG(ArchiveSection):
    electron_energy_keV = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )
    emission_current_uA = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )
    filament_current_A = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )
    filament_voltage_V = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )
    grid_voltage_V = Quantity(type=float, a_eln=dict(component='NumberEditQuantity'))
    topaz_voltage_V = Quantity(type=float, a_eln=dict(component='NumberEditQuantity'))


class DeflectionUnitSTAIB(ArchiveSection):
    grid = Quantity(type=float, a_eln=dict(component='NumberEditQuantity'))
    focus = Quantity(type=float, a_eln=dict(component='NumberEditQuantity'))
    beam_deflection_x = Quantity(type=float, a_eln=dict(component='NumberEditQuantity'))
    beam_deflection_y = Quantity(type=float, a_eln=dict(component='NumberEditQuantity'))
    beam_rocking = Quantity(type=float, a_eln=dict(component='NumberEditQuantity'))


class DeflectionUnitFUG(ArchiveSection):
    alignment_x = Quantity(type=float, a_eln=dict(component='NumberEditQuantity'))
    alignment_y = Quantity(type=float, a_eln=dict(component='NumberEditQuantity'))
    magnet_lens = Quantity(type=float, a_eln=dict(component='NumberEditQuantity'))
    x_or_y_scan = Quantity(
        type=MEnum('x', 'y'), a_eln=dict(component='EnumEditQuantity')
    )
    ext_or_int_ref = Quantity(
        type=MEnum('ext', 'int'), a_eln=dict(component='EnumEditQuantity')
    )
    beam_deflection_x_coarse = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )
    beam_deflection_x_fine = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )
    beam_deflection_x_crosspoint = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )
    beam_deflection_x_angle = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )
    beam_deflection_y_coarse = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )
    beam_deflection_y_fine = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )
    beam_deflection_y_crosspoint = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )
    beam_deflection_y_angle = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )


class RHEEDMeasurementSettings(ArchiveSection):
    datetime = Quantity(type=Datetime, a_eln=dict(component='DateTimeEditQuantity'))
    compensation_cage_on = Quantity(type=bool, a_eln=dict(component='BoolEditQuantity'))
    incidence_angle_deg = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )

    e_gun_STAIB = SubSection(section_def=EGunSTAIB)
    e_gun_FUG = SubSection(section_def=EGunFUG)
    deflection_unit_STAIB = SubSection(section_def=DeflectionUnitSTAIB)
    deflection_unit_FUG = SubSection(section_def=DeflectionUnitFUG)


# ---------------------------------------------------------
# 3. Sample and Substrate Context
# ---------------------------------------------------------
class SubstrateHolder(ArchiveSection):
    rotation_angle_alpha_deg = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )
    position_measured = Quantity(type=str, a_eln=dict(component='StringEditQuantity'))


class Sample(ArchiveSection):
    sample_reference = Quantity(
        type=ArchiveSection, a_eln=dict(component='ReferenceEditQuantity')
    )
    sample_id = Quantity(type=str, a_eln=dict(component='StringEditQuantity'))
    sample_azimuth_phi_deg = Quantity(
        type=float,
        description='Calculated automatically: sample_phi_holder_alpha_deg + rotation_angle_alpha_deg',
    )
    substrate_or_film = Quantity(
        type=MEnum('substrate', 'film'), a_eln=dict(component='EnumEditQuantity')
    )
    sample_surface_compound = Quantity(
        type=str, a_eln=dict(component='StringEditQuantity')
    )
    sample_azimuth_uvw = Quantity(type=str, a_eln=dict(component='StringEditQuantity'))
    sample_surface_hkl = Quantity(type=str, a_eln=dict(component='StringEditQuantity'))


# ---------------------------------------------------------
# 4. Result Sections
# ---------------------------------------------------------
class RHEEDResult(MeasurementResult):
    result_type = Quantity(type=MEnum('video', 'image', 'scan_point'))
    datetime = Quantity(type=Datetime, a_eln=dict(component='DateTimeEditQuantity'))

    measurement_settings = SubSection(section_def=RHEEDMeasurementSettings)
    substrate_holder = SubSection(section_def=SubstrateHolder)
    sample = SubSection(section_def=Sample)
    notes = Quantity(type=str, a_eln=dict(component='RichTextEditQuantity'))

    def normalize(self, archive, logger):
        super().normalize(archive, logger)
        if self.sample and self.substrate_holder:
            alpha = self.substrate_holder.rotation_angle_alpha_deg
            parent_measurement = self.m_parent 
            if parent_measurement:
                offset = parent_measurement.sample_phi_holder_alpha_deg
                if alpha is not None and offset is not None:
                    self.sample.sample_azimuth_phi_deg = alpha + offset


class RHEEDVideoResult(RHEEDResult):
    video_link = Quantity(type=str, a_eln=dict(component='StringEditQuantity'))
    start_time = Quantity(type=Datetime, a_eln=dict(component='DateTimeEditQuantity'))
    end_time = Quantity(type=Datetime, a_eln=dict(component='DateTimeEditQuantity'))
    frame_interval_s = Quantity(type=float, a_eln=dict(component='NumberEditQuantity'))
    number_of_frames = Quantity(type=int, a_eln=dict(component='NumberEditQuantity'))


class RHEEDImageResult(RHEEDResult):
    images = Quantity(type=str, shape=['*'], a_browser=dict(adaptor='RawFileAdaptor'))
    derived_from_video_link = Quantity(
        type=str, a_eln=dict(component='StringEditQuantity')
    )


class PointScan(ArchiveSection):
    source_file = Quantity(type=str, a_browser=dict(adaptor='RawFileAdaptor'))
    start_time = Quantity(type=Datetime)
    end_time = Quantity(type=Datetime)
    sensor_position_overview_picture = Quantity(
        type=str, a_browser=dict(adaptor='RawFileAdaptor')
    )
    sensor_definition_file = Quantity(
        type=str, a_browser=dict(adaptor='RawFileAdaptor')
    )
    derived_from_video_link = Quantity(type=str)


class RHEEDPointScanResult(RHEEDResult):
    point_scans = SubSection(section_def=PointScan, repeats=True)


# ---------------------------------------------------------
# 5. Top-Level Measurement Entry
# ---------------------------------------------------------
class RHEEDMeasurement(Measurement, EntryData):
    measurement_id = Quantity(type=str, a_eln=dict(component='StringEditQuantity'), description="Auto-generated")
    
    data_file = Quantity(type=str, a_eln=dict(component='FileEditQuantity'), a_browser=dict(adaptor='RawFileAdaptor'))
    
    mbe_experiment_ref = Quantity(type=ArchiveSection, a_eln=dict(component='ReferenceEditQuantity'), description="Reference to the higher-level MBE Experiment ID")
    sample_phi_holder_alpha_deg = Quantity(type=float, a_eln=dict(component='NumberEditQuantity'))
    sample_ref = Quantity(type=ArchiveSection, a_eln=dict(component='ReferenceEditQuantity'))
    color_table = Quantity(type=str, a_browser=dict(adaptor='RawFileAdaptor'))
    
    instrument_settings = SubSection(section_def=InstrumentSettings)
    results = SubSection(section_def=RHEEDResult, repeats=True)

    def normalize(self, archive, logger):
        # 1. PARSE THE DATA (Only if the file is mapped and results are empty to prevent overwriting edits)
        if self.data_file and not self.results:
            try:
                with archive.m_context.raw_file(self.data_file, 'r') as f:
                    mainfile_path = f.name
                
                mainfile_dir = os.path.dirname(mainfile_path)
                all_files = os.listdir(mainfile_dir)
                
                self._parse_all_data(mainfile_path, mainfile_dir, all_files, logger)
            except Exception as e:
                if logger: logger.error(f'Error parsing RHEED metadata CSV: {e}')

        # 2. AUTO-GENERATE MEASUREMENT ID
        if not self.measurement_id and self.results:
            first_result = self.results[0]
            if getattr(first_result, 'sample', None) and getattr(first_result.sample, 'sample_id', None):
                s_id = first_result.sample.sample_id
                dt = getattr(first_result, 'datetime', None)
                if dt:
                    dt_str = dt.strftime("%Y-%m-%d_%H-%M-%S")
                    self.measurement_id = f"RHD_{s_id}_{dt_str}"
                    
        super().normalize(archive, logger)

    def _parse_all_data(self, mainfile_path, mainfile_dir, all_files, logger):
        # A. Parse main CSV
        df_meta = pd.read_csv(mainfile_path)
        df_meta.columns = df_meta.columns.str.strip()
        if 'date' in df_meta.columns and 'time' in df_meta.columns:
            df_meta['parsed_datetime'] = pd.to_datetime(
                df_meta['date'].astype(str) + ' ' + df_meta['time'].astype(str), errors='coerce'
            )
            
        if 'm8_id' in df_meta.columns:
            valid_ids = df_meta['m8_id'].dropna().astype(str)
            if not valid_ids.empty:
                self.measurement_id = f"RHD_{valid_ids.iloc[0].split('_')[0]}"

        # B. Parse Excel Settings
        excel_files = [f for f in all_files if f.endswith('.xlsx') and 'MBE' in f]
        if excel_files:
            try:
                excel_path = os.path.join(mainfile_dir, excel_files[0])
                _df_excel = pd.read_excel(excel_path, sheet_name='RHEED settings')
                if logger: logger.info(f"Loaded {len(_df_excel)} rows from RHEED settings.")
                self.instrument_settings = InstrumentSettings()
            except Exception as e:
                if logger: logger.warning(f'Could not parse Excel settings: {e}')

        # C. Parse Rotation Log
        df_rot = None
        rot_path = os.path.join(mainfile_dir, 'rotation.txt')
        if os.path.exists(rot_path):
            try:
                df_rot = pd.read_csv(rot_path, sep=r'\s+|,', engine='python')
            except Exception as e:
                if logger: logger.warning(f'Could not parse rotation log: {e}')

        # D. Match Files and Construct Results
        assigned_files = set()
        time_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}___\d{2}-\d{2}-\d{2}\.\d{3})')

        # Explicitly named files
        for _, row in df_meta.iterrows():
            fname = str(row.get('file_name', '')).strip()
            if fname and fname != 'nan':
                assigned_files.add(fname)
                result = self._create_result_instance(fname, all_files)
                if not result: continue
                
                if fname.endswith('.dst'):
                    result.video_link = str(row.get('file_path', ''))

                if 'parsed_datetime' in row and pd.notna(row['parsed_datetime']):
                    result.datetime = row['parsed_datetime'].isoformat()

                self._populate_schema_from_row(result, row)
                self.results.append(result)

        # Unassigned Timestamp Matching
        unassigned = [f for f in all_files if f not in assigned_files and f.endswith(('.tif', '.pgm', '.asc', '.csv'))]
        for fname in unassigned:
            match = time_pattern.search(fname)
            if not match: continue

            try:
                file_dt = datetime.strptime(match.group(1), "%Y-%m-%d___%H-%M-%S.%f")
            except ValueError: continue

            result = self._create_result_instance(fname, all_files)
            if not result: continue
            result.datetime = file_dt.isoformat()

            if 'parsed_datetime' in df_meta.columns:
                past_meta = df_meta[df_meta['parsed_datetime'] <= file_dt]
                if not past_meta.empty:
                    best_row = past_meta.sort_values(by='parsed_datetime', ascending=False).iloc[0]
                    self._populate_schema_from_row(result, best_row)

            if df_rot is not None and 'parsed_datetime' in df_rot.columns:
                past_rot = df_rot[df_rot['parsed_datetime'] <= file_dt]
                if not past_rot.empty:
                    best_rot = past_rot.sort_values(by='parsed_datetime', ascending=False).iloc[0]
                    if result.substrate_holder is None: result.substrate_holder = SubstrateHolder()
                    result.substrate_holder.rotation_angle_alpha_deg = float(best_rot.iloc[-1])

            self.results.append(result)

    def _create_result_instance(self, fname, all_files):
        if fname.endswith(('.tif', '.pgm')) and 'sensor' not in fname.lower():
            res = RHEEDImageResult()
            if fname in all_files: res.images = [fname]
            return res
        elif fname.endswith(('.asc', '.csv')) and 'sensor' not in fname.lower():
            return RHEEDPointScanResult()
        elif fname.endswith('.dst'):
            return RHEEDVideoResult()
        return None

    def _populate_schema_from_row(self, result_obj, row):
        def _safe_float(val):
            try: return float(val)
            except (ValueError, TypeError): return None

        sample = Sample()
        settings = RHEEDMeasurementSettings()
        holder = SubstrateHolder()
        egun = EGunFUG()
        deflect = DeflectionUnitFUG()

        m8_val = str(row.get('m8_id', ''))
        if '_' in m8_val:
            parts = m8_val.split('_')
            sample.sample_id = parts[0]
            holder.position_measured = parts[1]
        elif m8_val and m8_val != 'nan':
            sample.sample_id = m8_val

        if pd.notna(row.get('azimuth')): sample.sample_azimuth_uvw = str(row['azimuth'])
        if pd.notna(row.get('substrate')):
            sample.sample_surface_compound = str(row['substrate'])
            sample.substrate_or_film = 'substrate'
        elif pd.notna(row.get('film')):
            sample.sample_surface_compound = str(row['film'])
            sample.substrate_or_film = 'film'

        alpha = _safe_float(row.get('mani_angle'))
        if alpha is not None: holder.rotation_angle_alpha_deg = alpha

        e_kev = _safe_float(row.get('energy_kev'))
        if e_kev is not None: egun.electron_energy_keV = e_kev

        emis = _safe_float(row.get('emission_uA'))
        if emis is not None: egun.emission_current_uA = emis

        fil_a = _safe_float(row.get('filament_a'))
        if fil_a is not None: egun.filament_current_A = fil_a

        fil_v = _safe_float(row.get('filament_v'))
        if fil_v is not None: egun.filament_voltage_V = fil_v

        grid_v = _safe_float(row.get('grid_v'))
        if grid_v is not None: egun.grid_voltage_V = grid_v

        x_al = _safe_float(row.get('x_align'))
        if x_al is not None: deflect.alignment_x = x_al

        if pd.notna(row.get('comments')): result_obj.notes = str(row['comments'])

        settings.e_gun_FUG = egun
        settings.deflection_unit_FUG = deflect

        result_obj.sample = sample
        result_obj.substrate_holder = holder
        result_obj.measurement_settings = settings


# ---------------------------------------------------------
# 6. Raw File Pointer Section
# ---------------------------------------------------------
class RawFileRHEEDData(EntryData):
    """Placeholder for the raw RHEED metadata CSV to point to the generated ELN."""
    m_def = Section(label='Raw RHEED Metadata File')

    measurement = Quantity(
        type=RHEEDMeasurement,
        a_eln=dict(component=ELNComponentEnum.ReferenceEditQuantity),
        description='The editable ELN archive generated from this raw metadata file.',
    )

m_package.__init_metainfo__()