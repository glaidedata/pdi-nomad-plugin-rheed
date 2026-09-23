import csv
import os
import posixpath
import re
from copy import deepcopy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from nomad.datamodel.data import ArchiveSection, EntryData
from nomad.datamodel.metainfo.annotations import (
    ELNComponentEnum,
    Filter,
    SectionDisplayAnnotation,
)
from nomad.datamodel.metainfo.basesections import Measurement, MeasurementResult
from nomad.datamodel.metainfo.plot import PlotlyFigure, PlotSection
from nomad.metainfo import (
    Datetime,
    File,
    MEnum,
    Quantity,
    SchemaPackage,
    Section,
    SubSection,
)
from PIL import Image

m_package = SchemaPackage()
SOURCE_TIMEZONE = ZoneInfo('Europe/Berlin')
MBE_EXPERIMENT_LAB_ID = 'data.lab_id#pdi_nomad_plugin.mbe.processes.ExperimentMbePDI'
IMAGE_PREVIEW_MAX_DIMENSION = 512
CURRENT_DERIVED_DATA_VERSION = 1


def _search_nomad_entries(owner, user_id, query):
    """Import NOMAD search lazily so the PDI plugin remains optional."""
    from nomad.search import search

    return search(owner=owner, user_id=user_id, query=query)


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
        type=float, description='Calculated automatically'
    )
    substrate_or_film = Quantity(
        type=MEnum('substrate', 'film'), a_eln=dict(component='EnumEditQuantity')
    )
    sample_surface_compound = Quantity(
        type=str, a_eln=dict(component='StringEditQuantity')
    )
    sample_surface_hkl = Quantity(type=str, a_eln=dict(component='StringEditQuantity'))
    sample_azimuth_uvw = Quantity(type=str, a_eln=dict(component='StringEditQuantity'))


# ---------------------------------------------------------
# 4. Result Sections
# ---------------------------------------------------------
class RHEEDResult(MeasurementResult, PlotSection):
    m_def = Section(
        a_display=SectionDisplayAnnotation(visible=Filter(exclude=['figures']))
    )

    result_type = Quantity(type=MEnum('video', 'image', 'scan_point'))
    datetime = Quantity(type=Datetime, a_eln=dict(component='DateTimeEditQuantity'))

    measurement_settings = SubSection(section_def=RHEEDMeasurementSettings)
    substrate_holder = SubSection(section_def=SubstrateHolder)
    sample = SubSection(section_def=Sample)
    notes = Quantity(type=str, a_eln=dict(component='RichTextEditQuantity'))

    def normalize(self, archive, logger):
        """Triggers the math to calculate the final sample azimuth angle from the holder offset."""
        super().normalize(archive, logger)
        self._populate_sample_phi()

    def _populate_sample_phi(self):
        """Calculate sample azimuth from the measurement holder offset and alpha."""
        if self.sample and self.substrate_holder:
            alpha = self.substrate_holder.rotation_angle_alpha_deg
            parent_measurement = self.m_parent
            if parent_measurement:
                offset = parent_measurement.sample_phi_holder_alpha_deg
                if alpha is not None and offset is not None:
                    self.sample.sample_azimuth_phi_deg = alpha + offset


class RHEEDVideoResult(RHEEDResult):
    m_def = Section(
        a_display=SectionDisplayAnnotation(visible=Filter(exclude=['figures']))
    )

    video_link = Quantity(type=str, a_eln=dict(component='StringEditQuantity'))
    start_time = Quantity(type=Datetime, a_eln=dict(component='DateTimeEditQuantity'))
    end_time = Quantity(type=Datetime, a_eln=dict(component='DateTimeEditQuantity'))
    frame_interval_s = Quantity(type=float, a_eln=dict(component='NumberEditQuantity'))
    number_of_frames = Quantity(type=int, a_eln=dict(component='NumberEditQuantity'))


class RHEEDPlot(PlotSection):
    """Container for a NOMAD Plotly figure."""


class RHEEDImageResult(RHEEDResult):
    m_def = Section(
        a_display=SectionDisplayAnnotation(visible=Filter(exclude=['figures']))
    )

    images = Quantity(type=File, a_browser=dict(adaptor='RawFileAdaptor'))
    derived_from_video_link = Quantity(
        type=str, a_eln=dict(component='StringEditQuantity')
    )


class RHEEDSensor(ArchiveSection):
    sensor_name = Quantity(type=str)
    sensor_id = Quantity(type=int)
    relative_time = Quantity(type=float, shape=['*'], unit='second')
    intensity = Quantity(type=float, shape=['*'])


class RHEEDSensors(PlotSection):
    """Point-scan sensors and their combined intensity plot."""

    m_def = Section(
        a_display=SectionDisplayAnnotation(visible=Filter(exclude=['figures']))
    )

    sensors = SubSection(section_def=RHEEDSensor, repeats=True)


class SensorPositionOverview(PlotSection):
    """Sensor-position overview raw file and its TIFF plot."""

    m_def = Section(
        a_display=SectionDisplayAnnotation(visible=Filter(exclude=['figures']))
    )

    file = Quantity(type=File, a_browser=dict(adaptor='RawFileAdaptor'))


class PointScan(ArchiveSection):
    source_file = Quantity(type=File, a_browser=dict(adaptor='RawFileAdaptor'))
    start_time = Quantity(type=Datetime)
    end_time = Quantity(type=Datetime)
    sensors = SubSection(section_def=RHEEDSensors)
    sensor_position_overview_picture = SubSection(section_def=SensorPositionOverview)
    sensor_definition_file = Quantity(
        type=File, a_browser=dict(adaptor='RawFileAdaptor')
    )
    derived_from_video_link = Quantity(type=str)


class RHEEDPointScanResult(RHEEDResult):
    m_def = Section(
        a_display=SectionDisplayAnnotation(visible=Filter(exclude=['figures']))
    )

    point_scans = SubSection(section_def=PointScan, repeats=True)


# ---------------------------------------------------------
# 5. Top-Level Measurement Entry
# ---------------------------------------------------------
class RHEEDMeasurement(Measurement, EntryData):
    measurement_id = Quantity(
        type=str,
        a_eln=dict(component='StringEditQuantity'),
        description='Auto-generated',
    )
    data_file = Quantity(
        type=str,
        a_eln=dict(component='FileEditQuantity'),
        a_browser=dict(adaptor='RawFileAdaptor'),
    )
    mbe_experiment_ref = Quantity(
        type=ArchiveSection, a_eln=dict(component='ReferenceEditQuantity')
    )
    sample_phi_holder_alpha_deg = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )
    sample_ref = Quantity(
        type=ArchiveSection, a_eln=dict(component='ReferenceEditQuantity')
    )
    rheed_settings_source = Quantity(
        type=MEnum('local', 'linked_mbe'),
        description=(
            'Successful source of the RHEED settings. This parser-managed marker '
            'prevents repeated fallback loads from overwriting later ELN edits.'
        ),
    )
    derived_data_version = Quantity(
        type=int,
        description='Internal version of parser-derived RHEED data reconciliation.',
    )
    color_table = Quantity(type=File, a_browser=dict(adaptor='RawFileAdaptor'))

    instrument_settings = SubSection(section_def=InstrumentSettings)
    results = SubSection(section_def=RHEEDResult, repeats=True)

    def normalize(self, archive, logger):
        """Main trigger: locates uploaded files in the server context and starts the parsing process."""
        mainfile_data = self._get_mainfile_data(archive, logger)
        local_excel_loaded = self.rheed_settings_source == 'local'
        if mainfile_data:
            mainfile_path, mainfile_dir, all_files = mainfile_data
            if not self.results:
                try:
                    local_excel_loaded = self._parse_all_data(
                        mainfile_path, mainfile_dir, all_files, logger
                    )
                    self.derived_data_version = CURRENT_DERIVED_DATA_VERSION
                except Exception as e:
                    if logger:
                        logger.error(f'Error parsing RHEED metadata CSV: {e}')
            elif self._needs_derived_data_migration():
                try:
                    migration_succeeded = self._migrate_derived_data(
                        mainfile_path, mainfile_dir, all_files, logger
                    )
                    if migration_succeeded:
                        self.derived_data_version = CURRENT_DERIVED_DATA_VERSION
                except Exception as error:
                    if logger:
                        logger.error(f'Could not migrate RHEED derived data: {error}')

            if self.results and self.rheed_settings_source is None:
                local_excel_loaded = self._parse_excel_settings(
                    mainfile_dir, all_files, logger, preserve_existing=True
                )

        self._autogenerate_measurement_id()
        if self.lab_id is None and self.measurement_id:
            self.lab_id = self.measurement_id
        self._link_mbe_experiment(archive, logger)
        if not local_excel_loaded and self.rheed_settings_source != 'linked_mbe':
            self._parse_linked_mbe_excel_settings(logger)
        super().normalize(archive, logger)
        for result in self.results:
            result._populate_sample_phi()

    def _get_mainfile_data(self, archive, logger):
        """Return the local mainfile path and sibling files without parsing results."""
        if not self.data_file:
            return None
        try:
            with archive.m_context.raw_file(self.data_file, 'r') as file:
                mainfile_path = file.name
            mainfile_dir = os.path.dirname(mainfile_path)
            return mainfile_path, mainfile_dir, os.listdir(mainfile_dir)
        except Exception as error:
            if logger:
                logger.error(f'Could not access RHEED metadata CSV: {error}')
            return None

    def _needs_derived_data_migration(self):
        """Return whether this archive predates the current derived-data format."""
        return (self.derived_data_version or 0) < CURRENT_DERIVED_DATA_VERSION

    def _migrate_derived_data(self, mainfile_path, mainfile_dir, all_files, logger):
        """Parse into a detached section before reconciling parser-owned data."""
        parsed = RHEEDMeasurement(data_file=self.data_file)
        parsed._parse_all_data(
            mainfile_path,
            mainfile_dir,
            all_files,
            logger,
            parse_excel_settings=False,
        )
        return self._reconcile_derived_data(parsed, logger)

    @staticmethod
    def _normalized_file_basename(value):
        """Return a comparable basename from a NOMAD raw-file value."""
        if isinstance(value, (list, tuple)):
            value = value[0] if value else None
        if not value:
            return None
        return str(value).replace('\\', '/').rsplit('/', maxsplit=1)[-1]

    def _result_identity(self, result):
        """Build a stable result identity without relying on result-list position."""
        source = None
        if isinstance(result, RHEEDImageResult):
            source = result.images
        elif isinstance(result, RHEEDPointScanResult) and result.point_scans:
            source = result.point_scans[0].source_file
        elif isinstance(result, RHEEDVideoResult):
            source = result.name or result.video_link

        source = self._normalized_file_basename(
            source
        ) or self._normalized_file_basename(result.name)
        return (type(result).__name__, source) if source else None

    def _reconcile_derived_data(self, parsed, logger):  # noqa: PLR0912
        """Refresh parser-owned fields while preserving populated ELN values."""
        existing_by_identity = {}
        for result in self.results:
            identity = self._result_identity(result)
            if identity:
                existing_by_identity.setdefault(identity, []).append(result)

        reconciliation_plan = []
        for fresh_result in parsed.results:
            identity = self._result_identity(fresh_result)
            if not identity:
                if logger:
                    logger.warning(
                        'RHEED derived-data migration found a fresh result without '
                        'a stable identity; leaving the archive unchanged'
                    )
                return False

            matches = existing_by_identity.get(identity, [])
            if len(matches) == 1:
                reconciliation_plan.append((matches[0], fresh_result))
            elif len(matches) > 1:
                if logger:
                    logger.warning(
                        f'Ambiguous legacy RHEED result identity {identity}; '
                        'leaving the archive unchanged'
                    )
                return False
            else:
                reconciliation_plan.append((None, fresh_result))

        updates = []
        new_results = []
        for existing, fresh_result in reconciliation_plan:
            if existing is None:
                new_results.append(fresh_result.m_copy(deep=True))
                continue
            updates.append(
                (
                    existing,
                    fresh_result,
                    [figure.m_copy(deep=True) for figure in fresh_result.figures],
                    [
                        point_scan.m_copy(deep=True)
                        for point_scan in getattr(fresh_result, 'point_scans', [])
                    ],
                )
            )

        for existing, fresh, figures, point_scans in updates:
            self._refresh_parser_owned_result_data(
                existing, fresh, figures, point_scans
            )
            self._merge_editable_result_data(existing, fresh)

        self.color_table = parsed.color_table
        self.results.extend(new_results)
        return True

    def _refresh_parser_owned_result_data(self, existing, fresh, figures, point_scans):
        """Replace data that is always reconstructed from uploaded raw files."""
        existing.result_type = fresh.result_type
        existing.figures = figures
        if isinstance(existing, RHEEDImageResult) and isinstance(
            fresh, RHEEDImageResult
        ):
            existing.images = fresh.images
        if isinstance(existing, RHEEDPointScanResult) and isinstance(
            fresh, RHEEDPointScanResult
        ):
            existing.point_scans = point_scans

    def _merge_editable_result_data(self, existing, fresh):
        """Fill missing editable values and apply narrow, proven legacy corrections."""
        if existing.sample and fresh.sample:
            self._correct_legacy_sample_id(existing, fresh)
        if existing.substrate_holder and fresh.substrate_holder:
            old_alpha = existing.substrate_holder.rotation_angle_alpha_deg
            fresh_alpha = fresh.substrate_holder.rotation_angle_alpha_deg
            if old_alpha in (None, -1) and fresh_alpha is not None:
                existing.substrate_holder.rotation_angle_alpha_deg = fresh_alpha
        self._fill_missing_section(existing, fresh)

    def _correct_legacy_sample_id(self, existing, fresh):
        """Restore the holder suffix only for the known old growth-only form."""
        if not existing.substrate_holder:
            return
        holder_position = existing.substrate_holder.position_measured
        fresh_sample_id = fresh.sample.sample_id
        if not holder_position or not fresh_sample_id:
            return
        suffix = f'_{holder_position}'
        if not fresh_sample_id.endswith(suffix):
            return
        growth_id = fresh_sample_id[: -len(suffix)]
        if existing.sample.sample_id == growth_id:
            existing.sample.sample_id = fresh_sample_id

    def _fill_missing_section(self, existing, fresh):
        """Recursively fill non-repeating editable subsection values."""
        for name, quantity in fresh.m_def.all_quantities.items():
            if not fresh.m_is_set(quantity) or existing.m_is_set(quantity):
                continue
            existing.m_set(quantity, deepcopy(fresh.m_get(quantity)))

        for subsection in fresh.m_def.all_sub_sections.values():
            if subsection.repeats:
                continue
            fresh_subsections = fresh.m_get_sub_sections(subsection)
            if not fresh_subsections:
                continue
            existing_subsections = existing.m_get_sub_sections(subsection)
            if not existing_subsections:
                existing.m_add_sub_section(
                    subsection, fresh_subsections[0].m_copy(deep=True)
                )
            else:
                self._fill_missing_section(
                    existing_subsections[0], fresh_subsections[0]
                )

    @staticmethod
    def _derive_growth_id(sample_id, holder_position):
        """Remove the known holder-position suffix from a full sample ID."""
        suffix = f'_{holder_position}'
        if sample_id.endswith(suffix) and len(sample_id) > len(suffix):
            return sample_id[: -len(suffix)]
        return None

    def _get_single_growth_id(self):
        """Return the one growth ID shared by every parsed result sample."""
        growth_ids = set()
        for result in self.results:
            sample_id = getattr(getattr(result, 'sample', None), 'sample_id', None)
            holder_position = getattr(
                getattr(result, 'substrate_holder', None), 'position_measured', None
            )
            if not sample_id or not holder_position:
                return None
            growth_id = self._derive_growth_id(sample_id, holder_position)
            if growth_id is None:
                return None
            growth_ids.add(growth_id)

        if len(growth_ids) == 1:
            return growth_ids.pop()
        return None

    def _link_mbe_experiment(self, archive, logger):
        """Link the single visible PDI MBE experiment matching this growth ID."""
        if self.mbe_experiment_ref:
            return

        main_author = getattr(getattr(archive, 'metadata', None), 'main_author', None)
        user_id = getattr(main_author, 'user_id', main_author)
        if not user_id:
            return

        growth_id = self._get_single_growth_id()
        if growth_id is None:
            return

        try:
            response = _search_nomad_entries(
                owner='all',
                user_id=user_id,
                query={
                    'search_quantities': {
                        'id': MBE_EXPERIMENT_LAB_ID,
                        'str_value': growth_id,
                    }
                },
            )
        except Exception as error:
            if logger:
                logger.warning(
                    f'Could not resolve MBE experiment for growth ID {growth_id}: {error}'
                )
            return

        matches = response.data
        if len(matches) != 1:
            if len(matches) > 1 and logger:
                logger.warning(
                    f'Ambiguous MBE experiment matches for growth ID {growth_id}'
                )
            return

        match = matches[0]
        upload_id = match.get('upload_id')
        entry_id = match.get('entry_id')
        if upload_id and entry_id:
            self.mbe_experiment_ref = f'../uploads/{upload_id}/archive/{entry_id}#data'

    def _autogenerate_measurement_id(self):
        """Creates a standardized ID based on the sample name and timestamp."""
        if not self.measurement_id and self.results:
            first_result = self.results[0]
            if getattr(first_result, 'sample', None) and getattr(
                first_result.sample, 'sample_id', None
            ):
                s_id = first_result.sample.sample_id
                dt = getattr(first_result, 'datetime', None)
                if dt:
                    dt_str = dt.strftime('%Y-%m-%d_%H-%M-%S')
                    self.measurement_id = f'RHD_{s_id}_{dt_str}'

    # --- PARSING LOGIC ---
    def _parse_all_data(
        self, mainfile_path, mainfile_dir, all_files, logger, parse_excel_settings=True
    ):
        """Master controller that orchestrates reading all files and mapping the data."""
        df_meta = self._load_and_prep_csv(mainfile_path)
        df_rot = self._parse_rotation_log(mainfile_dir, logger)
        self._set_color_table(all_files)

        assigned_files = self._process_explicit_files(
            df_meta, df_rot, mainfile_dir, all_files, logger
        )
        self._process_unassigned_files(
            df_meta,
            df_rot,
            mainfile_dir,
            all_files,
            assigned_files,
            os.path.basename(mainfile_path),
            logger,
        )
        return (
            self._parse_excel_settings(mainfile_dir, all_files, logger)
            if parse_excel_settings
            else False
        )

    def _raw_sibling_path(self, filename):
        """Return a sibling's upload-relative raw path without local path leakage."""
        sibling_name = str(filename).replace('\\', '/').rsplit('/', maxsplit=1)[-1]
        data_file = str(self.data_file or '')
        if os.path.isabs(data_file) or re.match(r'^[A-Za-z]:[\\/]', data_file):
            return sibling_name

        raw_directory = posixpath.dirname(data_file.replace('\\', '/'))
        return (
            posixpath.join(raw_directory, sibling_name)
            if raw_directory and raw_directory != '.'
            else sibling_name
        )

    def _load_and_prep_csv(self, mainfile_path):
        """Reads the master CSV and formats the timestamp columns for easy matching."""
        df_meta = pd.read_csv(mainfile_path)
        df_meta.columns = df_meta.columns.str.strip()
        if 'date' in df_meta.columns and 'time' in df_meta.columns:
            time_fixed = df_meta['time'].astype(str).str.replace('-', ':', regex=False)
            timestamp_strings = df_meta['date'].astype(str) + ' ' + time_fixed
            df_meta['parsed_datetime'] = timestamp_strings.map(
                self._parse_csv_source_datetime
            )
        if 'm8_id' in df_meta.columns:
            valid_ids = df_meta['m8_id'].dropna().astype(str)
            if not valid_ids.empty:
                self.measurement_id = f'RHD_{valid_ids.iloc[0].split("_")[0]}'
        return df_meta

    @staticmethod
    def _parse_source_datetime(timestamp, formats):
        """Interpret a RHEED wall-clock timestamp in the PDI Berlin timezone."""
        for timestamp_format in formats:
            try:
                return datetime.strptime(timestamp, timestamp_format).replace(
                    tzinfo=SOURCE_TIMEZONE
                )
            except ValueError:
                continue
        raise ValueError(f'Invalid RHEED timestamp: {timestamp}')

    def _parse_csv_source_datetime(self, timestamp):
        """Return a localized CSV timestamp or pandas' missing timestamp value."""
        try:
            return self._parse_source_datetime(
                timestamp,
                ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S'),
            )
        except ValueError:
            return pd.NaT

    def _parse_excel_settings(
        self, mainfile_dir, all_files, logger, preserve_existing=False
    ):
        """Extracts static instrument configurations from the MBE Excel file."""
        excel_files = [f for f in all_files if f.endswith('.xlsx') and 'MBE' in f]
        if not excel_files:
            return False

        try:
            excel_path = os.path.join(mainfile_dir, excel_files[0])
            df_excel = pd.read_excel(
                excel_path, sheet_name='RHEED settings', header=None
            )
            return self._populate_excel_settings(
                df_excel,
                logger,
                source='local',
                preserve_existing=preserve_existing,
            )
        except Exception as error:
            if logger:
                logger.warning(f'Could not parse local Excel settings: {error}')
            return False

    def _get_linked_mbe_experiment(self):
        """Return the lazily resolved MBE experiment archive section, when linked."""
        return self.mbe_experiment_ref

    def _parse_linked_mbe_excel_settings(self, logger):
        """Load RHEED settings through the linked MBE experiment's upload context."""
        try:
            experiment = self._get_linked_mbe_experiment()
            data_file = getattr(experiment, 'data_file', None)
            if not data_file:
                if logger:
                    logger.warning(
                        'Linked MBE experiment has no data_file for RHEED settings'
                    )
                return False

            experiment_context = experiment.m_root().m_context
            with experiment_context.raw_file(str(data_file), 'rb') as excel_file:
                df_excel = pd.read_excel(
                    excel_file, sheet_name='RHEED settings', header=None
                )
            return self._populate_excel_settings(
                df_excel,
                logger,
                source='linked_mbe',
                preserve_existing=True,
            )
        except Exception as error:
            if logger:
                logger.warning(
                    f'Could not parse RHEED settings from linked MBE experiment: {error}'
                )
            return False

    def _populate_excel_settings(  # noqa: PLR0912
        self, df_excel, logger, source, preserve_existing=False
    ):
        """Populate static RHEED settings from the documented field/value rows."""
        if logger:
            logger.info(f'Loaded {len(df_excel)} rows from RHEED settings.')

        field_row_index = None
        for index, row in df_excel.iterrows():
            non_empty = [
                str(value).strip()
                for value in row
                if pd.notna(value) and str(value).strip()
            ]
            if non_empty and non_empty[0].lower() == 'field':
                field_row_index = index
                break

        if field_row_index is None or field_row_index + 1 >= len(df_excel):
            raise ValueError('Could not locate field row and following value row')

        field_row = df_excel.iloc[field_row_index]
        value_row = df_excel.iloc[field_row_index + 1]
        values = {
            str(field).strip(): value_row.iloc[column]
            for column, field in enumerate(field_row)
            if pd.notna(field) and str(field).strip().lower() != 'field'
        }

        settings = InstrumentSettings()
        electronics_type = values.get('electronics_type')
        if pd.notna(electronics_type):
            settings.electronics_type = str(electronics_type).strip()

        distance = self._safe_float(values.get('distance_sample_to_screen_mm'))
        if distance is not None:
            settings.chamber_geometry = ChamberGeometry(
                distance_sample_to_screen_mm=distance
            )

        camera_values = {
            'image_length_calibration_mm_per_px': self._safe_float(
                values.get('image_length_calibration_mm_per_px')
            ),
            'resolution_x_px': self._safe_float(values.get('resolution_x_px')),
            'resolution_y_px': self._safe_float(values.get('resolution_y_px')),
        }
        if any(value is not None for value in camera_values.values()):
            settings.camera = Camera()
            calibration = camera_values['image_length_calibration_mm_per_px']
            if calibration is not None:
                settings.camera.image_length_calibration_mm_per_px = calibration
            if camera_values['resolution_x_px'] is not None:
                settings.camera.resolution_x_px = int(camera_values['resolution_x_px'])
            if camera_values['resolution_y_px'] is not None:
                settings.camera.resolution_y_px = int(camera_values['resolution_y_px'])

        offset = self._safe_float(values.get('sample_phi_holder_alpha_deg'))
        if preserve_existing:
            self._merge_excel_settings(settings, offset)
        else:
            self.instrument_settings = settings
            if offset is not None:
                self.sample_phi_holder_alpha_deg = offset
        self.rheed_settings_source = source
        return True

    def _merge_excel_settings(self, settings, offset):  # noqa: PLR0912
        """Fill missing settings from a workbook without replacing ELN values."""
        if self.instrument_settings is None:
            self.instrument_settings = settings
        else:
            current = self.instrument_settings
            if (
                current.electronics_type is None
                and settings.electronics_type is not None
            ):
                current.electronics_type = settings.electronics_type

            if settings.chamber_geometry:
                if current.chamber_geometry is None:
                    current.chamber_geometry = settings.chamber_geometry
                elif current.chamber_geometry.distance_sample_to_screen_mm is None:
                    current.chamber_geometry.distance_sample_to_screen_mm = (
                        settings.chamber_geometry.distance_sample_to_screen_mm
                    )

            if settings.camera:
                if current.camera is None:
                    current.camera = settings.camera
                else:
                    for field in (
                        'image_length_calibration_mm_per_px',
                        'resolution_x_px',
                        'resolution_y_px',
                    ):
                        if getattr(current.camera, field) is None:
                            value = getattr(settings.camera, field)
                            if value is not None:
                                setattr(current.camera, field, value)

        if self.sample_phi_holder_alpha_deg is None and offset is not None:
            self.sample_phi_holder_alpha_deg = offset

    def _parse_rotation_log(self, mainfile_dir, logger):  # noqa: PLR0912
        """Discover and read a timestamped EPIC rotation-angle log."""
        for filename in sorted(os.listdir(mainfile_dir)):
            if not filename.lower().endswith('.txt'):
                continue

            rotation_path = os.path.join(mainfile_dir, filename)
            try:
                with open(rotation_path, encoding='utf-8-sig') as rotation_file:
                    lines = rotation_file.readlines()

                header_index = next(
                    (
                        index
                        for index, line in enumerate(lines)
                        if {
                            value.strip().lstrip("'").lower()
                            for value in next(csv.reader([line]))
                        }
                        >= {'date', 'rotation.deg'}
                    ),
                    None,
                )
                if header_index is None:
                    continue

                records = []
                date_and_alpha_count = 2
                date_time_and_alpha_count = 3
                date_time_steps_and_alpha_count = 4
                for line in lines[header_index + 1 :]:
                    if not line.strip():
                        continue
                    parts = (
                        [part.strip() for part in next(csv.reader([line]))]
                        if ',' in line
                        else line.split()
                    )
                    if len(parts) == date_and_alpha_count:
                        date_and_time = parts[0].split(maxsplit=1)
                        steps = None
                        alpha = parts[1]
                    elif len(parts) == date_time_and_alpha_count:
                        if ',' in line:
                            date_and_time = parts[0].split(maxsplit=1)
                            steps = parts[1]
                            alpha = parts[2]
                        else:
                            date_and_time = parts[:2]
                            steps = None
                            alpha = parts[2]
                    elif len(parts) == date_time_steps_and_alpha_count:
                        date_and_time = parts[:2]
                        steps = parts[2]
                        alpha = parts[3]
                    else:
                        raise ValueError(f'Invalid rotation data row: {line.strip()}')

                    if len(date_and_time) != date_and_alpha_count:
                        raise ValueError(f'Invalid rotation timestamp: {line.strip()}')
                    parsed_datetime = self._parse_source_datetime(
                        ' '.join(date_and_time),
                        ('%d/%m/%Y %H:%M:%S.%f', '%d/%m/%Y %H:%M:%S'),
                    )
                    records.append(
                        {
                            'date': date_and_time[0],
                            'time': date_and_time[1],
                            'steps': int(steps) if steps is not None else None,
                            'parsed_datetime': parsed_datetime,
                            'alpha': float(alpha),
                        }
                    )

                return pd.DataFrame.from_records(
                    records,
                    columns=['date', 'time', 'steps', 'parsed_datetime', 'alpha'],
                )
            except Exception as error:
                if logger:
                    logger.warning(f'Could not parse rotation log {filename}: {error}')
        return None

    def _process_explicit_files(self, df_meta, df_rot, mainfile_dir, all_files, logger):
        """Maps files that are explicitly named in the CSV rows (like video links)."""
        assigned_files = set()
        for _, row in df_meta.iterrows():
            source_name = str(row.get('file_name', '')).strip()
            if source_name and source_name != 'nan':
                fname = os.path.basename(source_name.replace('\\', '/'))
                assigned_files.add(fname)
                if fname.lower().endswith(('.asc', '.csv')):
                    self._process_point_scan_file(
                        fname,
                        mainfile_dir,
                        all_files,
                        df_rot,
                        logger,
                        explicit_row=row,
                    )
                    continue

                result = self._create_result_instance(fname, all_files)
                if not result:
                    continue

                if fname.endswith('.dst'):
                    result.video_link = str(row.get('file_path', ''))
                if 'parsed_datetime' in row and pd.notna(row['parsed_datetime']):
                    result.datetime = row['parsed_datetime'].isoformat()

                self._populate_schema_from_row(result, row)
                explicit_alpha = self._safe_float(row.get('mani_angle'))
                if (explicit_alpha is None or explicit_alpha == -1) and pd.notna(
                    row.get('parsed_datetime')
                ):
                    self._match_unassigned_rotation(
                        result, row['parsed_datetime'], df_rot
                    )
                self.results.append(result)
                self._populate_image_plot(result, mainfile_dir, fname, logger)
        return assigned_files

    def _process_unassigned_files(  # noqa: PLR0913, PLR0917
        self,
        df_meta,
        df_rot,
        mainfile_dir,
        all_files,
        assigned_files,
        metadata_filename,
        logger,
    ):
        """Scans the upload folder for supported files not named by CSV rows."""
        time_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}___\d{2}-\d{2}-\d{2}\.\d{3})')
        unassigned = [
            f
            for f in all_files
            if f != metadata_filename
            and f not in assigned_files
            and f.lower().endswith(('.tif', '.pgm', '.asc', '.csv'))
        ]

        for fname in unassigned:
            if fname.lower().endswith(('.asc', '.csv')):
                self._process_point_scan_file(
                    fname,
                    mainfile_dir,
                    all_files,
                    df_rot,
                    logger,
                    metadata=df_meta,
                )
                continue

            match = time_pattern.search(fname)
            if not match:
                continue
            try:
                file_dt = self._parse_source_datetime(
                    match.group(1), ('%Y-%m-%d___%H-%M-%S.%f',)
                )
            except ValueError:
                continue

            result = self._create_result_instance(fname, all_files)
            if not result:
                continue
            result.datetime = file_dt.isoformat()

            self._match_unassigned_metadata(result, file_dt, df_meta)
            self._match_unassigned_rotation(result, file_dt, df_rot)

            self.results.append(result)
            self._populate_image_plot(result, mainfile_dir, fname, logger)

    def _process_point_scan_file(  # noqa: PLR0913, PLR0917
        self,
        fname,
        mainfile_dir,
        all_files,
        df_rot,
        logger,
        explicit_row=None,
        metadata=None,
    ):
        """Parse and finish one explicit or unassigned point-scan result."""
        result = self._create_result_instance(fname, all_files)
        if not isinstance(result, RHEEDPointScanResult):
            return

        point_scan, start_time, end_time = self._parse_point_scan(
            os.path.join(mainfile_dir, fname), logger
        )
        if point_scan is None:
            return

        self._associate_scan_auxiliaries(point_scan, start_time, end_time, all_files)
        result.point_scans.append(point_scan)
        result.datetime = start_time.isoformat()
        if explicit_row is not None:
            self._populate_schema_from_row(result, explicit_row)
            explicit_alpha = self._safe_float(explicit_row.get('mani_angle'))
            if explicit_alpha is None or explicit_alpha == -1:
                self._match_unassigned_rotation(result, start_time, df_rot)
        elif metadata is not None:
            self._match_scan_metadata(result, start_time, end_time, metadata)
            self._match_unassigned_rotation(result, start_time, df_rot)

        self._populate_point_scan_plots(result, point_scan, mainfile_dir, logger)
        self.results.append(result)

    def _populate_image_plot(self, result, mainfile_dir, fname, logger):
        """Store a TIFF image or PGM intensity array in a Plotly figure."""
        if not isinstance(result, RHEEDImageResult):
            return

        try:
            image_path = os.path.join(mainfile_dir, fname)
            if fname.lower().endswith('.pgm'):
                trace = go.Heatmap(
                    z=self._downsample_preview_array(self._read_ascii_pgm(image_path))
                )
            elif fname.lower().endswith(('.tif', '.tiff')):
                trace = go.Image(
                    z=self._downsample_preview_array(self._read_tiff_array(image_path))
                )
            else:
                return

            result.figures.append(
                PlotlyFigure(
                    label='RHEED image',
                    figure=go.Figure(data=[trace]).to_plotly_json(),
                )
            )
        except Exception as error:
            if logger:
                logger.warning(f'Could not create image preview for {fname}: {error}')

    def _read_tiff_array(self, image_path):
        """Read TIFF RGB data without changing its shape or pixel values."""
        with Image.open(image_path) as image:
            return np.asarray(image)

    def _read_ascii_pgm(self, image_path):
        """Read an ASCII P2 PGM while retaining values above its declared maximum."""
        with open(image_path, encoding='ascii') as pgm_file:
            tokens = []
            for line in pgm_file:
                tokens.extend(line.split('#', maxsplit=1)[0].split())

        header_token_count = 4
        if len(tokens) < header_token_count or tokens[0] != 'P2':
            raise ValueError('Expected an ASCII P2 PGM header')

        width, height, declared_maximum = (
            int(value) for value in tokens[1:header_token_count]
        )
        if width <= 0 or height <= 0 or declared_maximum <= 0:
            raise ValueError('PGM dimensions and declared maximum must be positive')

        values = [int(value) for value in tokens[header_token_count:]]
        if len(values) != width * height:
            raise ValueError('PGM pixel count does not match its dimensions')
        return np.asarray(values).reshape(height, width)

    @staticmethod
    def _downsample_preview_array(array):
        """Bound a 2D or RGB(A) preview with deterministic index sampling."""
        preview_array = np.asarray(array)
        height, width = preview_array.shape[:2]
        largest_dimension = max(height, width)
        if largest_dimension <= IMAGE_PREVIEW_MAX_DIMENSION:
            return preview_array

        scale = IMAGE_PREVIEW_MAX_DIMENSION / largest_dimension
        preview_height = max(1, int(height * scale))
        preview_width = max(1, int(width * scale))
        row_indices = np.linspace(0, height - 1, preview_height, dtype=int)
        column_indices = np.linspace(0, width - 1, preview_width, dtype=int)
        return preview_array[row_indices][:, column_indices]

    def _populate_point_scan_plots(self, result, point_scan, mainfile_dir, logger):
        """Store sensor traces and an optional sensor-position overview in Plotly."""
        sensor_traces = [
            go.Scatter(
                x=sensor.relative_time.magnitude,
                y=sensor.intensity,
                name=f'{sensor.sensor_name} ({sensor.sensor_id})',
            )
            for sensor in point_scan.sensors.sensors
        ]
        sensor_figure = go.Figure(data=sensor_traces).update_layout(
            showlegend=True,
            xaxis_title='Time (s)',
            yaxis_title='Intensity',
        )
        sensor_figure_json = sensor_figure.to_plotly_json()
        point_scan.sensors.figures.append(
            PlotlyFigure(label='Sensor intensities', figure=sensor_figure_json)
        )
        result.figures.append(
            PlotlyFigure(
                label='Sensor intensities', figure=deepcopy(sensor_figure_json)
            )
        )

        overview = point_scan.sensor_position_overview_picture
        if not overview:
            return

        try:
            overview_path = os.path.join(mainfile_dir, os.path.basename(overview.file))
            overview_trace = go.Image(
                z=self._downsample_preview_array(self._read_tiff_array(overview_path))
            )
            overview_figure_json = go.Figure(data=[overview_trace]).to_plotly_json()
            overview.figures.append(
                PlotlyFigure(
                    label='Sensor position overview', figure=overview_figure_json
                )
            )
            result.figures.append(
                PlotlyFigure(
                    label='Sensor position overview',
                    figure=deepcopy(overview_figure_json),
                )
            )
        except Exception as error:
            if logger:
                logger.warning(
                    f'Could not create point-scan overview preview for '
                    f'{overview.file}: {error}'
                )

    def _set_color_table(self, all_files):
        """Link the first available color table without interpreting its LUT values."""
        color_tables = sorted(f for f in all_files if f.lower().endswith('.col'))
        if color_tables:
            self.color_table = self._raw_sibling_path(color_tables[0])

    def _associate_scan_auxiliaries(self, point_scan, start_time, end_time, all_files):
        """Link timestamped scan auxiliary files using scan-interval priority."""
        sensor_definitions = [f for f in all_files if f.lower().endswith('.sn')]
        overview_images = [
            f for f in all_files if f.lower().endswith('.tif') and 'sensor' in f.lower()
        ]
        sensor_definition_filename = self._select_scan_auxiliary(
            sensor_definitions, start_time, end_time
        )
        if sensor_definition_filename:
            point_scan.sensor_definition_file = self._raw_sibling_path(
                sensor_definition_filename
            )
        overview_filename = self._select_scan_auxiliary(
            overview_images, start_time, end_time
        )
        if overview_filename:
            point_scan.sensor_position_overview_picture = SensorPositionOverview(
                file=self._raw_sibling_path(overview_filename)
            )

    def _select_scan_auxiliary(self, filenames, start_time, end_time):
        """Select a timestamped auxiliary by exact, during, before, then after."""
        timestamp_pattern = re.compile(
            r'(\d{4}-\d{2}-\d{2}___\d{2}-\d{2}-\d{2}\.\d{3})'
        )
        candidates = []
        for filename in filenames:
            match = timestamp_pattern.search(filename)
            if not match:
                continue
            try:
                timestamp = self._parse_source_datetime(
                    match.group(1), ('%Y-%m-%d___%H-%M-%S.%f',)
                )
            except ValueError:
                continue
            candidates.append((timestamp, filename))

        candidates.sort(key=lambda candidate: (candidate[0], candidate[1]))
        exact = [candidate for candidate in candidates if candidate[0] == start_time]
        if exact:
            return exact[0][1]

        during = [
            candidate
            for candidate in candidates
            if start_time < candidate[0] <= end_time
        ]
        if during:
            return during[0][1]

        before = [candidate for candidate in candidates if candidate[0] < start_time]
        if before:
            latest_timestamp = before[-1][0]
            return next(
                filename
                for timestamp, filename in before
                if timestamp == latest_timestamp
            )

        after = [candidate for candidate in candidates if candidate[0] > end_time]
        if after:
            return after[0][1]
        return None

    def _parse_point_scan(self, fname, logger):  # noqa: PLR0911, PLR0912
        """Read an ASC point scan and return its parsed data and observed interval."""
        try:
            with open(fname, encoding='utf-8-sig') as scan_file:
                lines = scan_file.readlines()
        except OSError as error:
            if logger:
                logger.warning(f'Could not read point scan {fname}: {error}')
            return None, None, None

        minimum_header_lines = 4
        if len(lines) < minimum_header_lines:
            if logger:
                logger.warning(f'Point scan {fname} is missing its header lines')
            return None, None, None

        timestamp_match = re.match(
            r'^Recorded at\s+(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2}\.\d+)',
            lines[0].strip(),
        )
        if not timestamp_match:
            if logger:
                logger.warning(f'Point scan {fname} has no valid Recorded at timestamp')
            return None, None, None

        try:
            start_time = self._parse_source_datetime(
                f'{timestamp_match.group(1)} {timestamp_match.group(2)}',
                ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S'),
            )
        except ValueError:
            if logger:
                logger.warning(
                    f'Point scan {fname} has an invalid Recorded at timestamp'
                )
            return None, None, None

        sensor_names = re.findall(r'Sensor\s+\S+', lines[1])
        sensor_ids = [int(value) for value in re.findall(r'\d+', lines[2])]
        if not sensor_names or len(sensor_names) != len(sensor_ids):
            if logger:
                logger.warning(
                    f'Point scan {fname} has mismatched sensor labels and IDs'
                )
            return None, None, None

        data_start = next(
            (
                index + 1
                for index, line in enumerate(lines[3:], start=3)
                if not line.strip()
            ),
            len(lines),
        )
        rows = []
        for line in lines[data_start:]:
            if not line.strip():
                continue
            try:
                row = [float(value) for value in line.split()]
            except ValueError:
                if logger:
                    logger.warning(f'Point scan {fname} has a non-numeric data row')
                return None, None, None
            if len(row) != len(sensor_names) + 1:
                if logger:
                    logger.warning(f'Point scan {fname} has an incomplete data row')
                return None, None, None
            rows.append(row)

        if not rows:
            if logger:
                logger.warning(f'Point scan {fname} has no numeric data rows')
            return None, None, None

        point_scan = PointScan(
            source_file=self._raw_sibling_path(fname),
            start_time=start_time.isoformat(),
            sensors=RHEEDSensors(),
        )
        relative_time = [row[0] for row in rows]
        point_scan.end_time = (
            start_time + timedelta(seconds=relative_time[-1])
        ).isoformat()
        for index, (sensor_name, sensor_id) in enumerate(
            zip(sensor_names, sensor_ids, strict=True)
        ):
            point_scan.sensors.sensors.append(
                RHEEDSensor(
                    sensor_name=sensor_name,
                    sensor_id=sensor_id,
                    relative_time=relative_time,
                    intensity=[row[index + 1] for row in rows],
                )
            )
        return point_scan, start_time, start_time + timedelta(seconds=relative_time[-1])

    def _match_scan_metadata(self, result, start_time, end_time, df_meta):
        """Apply the documented metadata priority to a point-scan interval."""
        if 'parsed_datetime' not in df_meta.columns:
            return

        candidates = df_meta.dropna(subset=['parsed_datetime'])
        exact = candidates[candidates['parsed_datetime'] == start_time]
        if not exact.empty:
            self._populate_schema_from_row(
                result, exact.iloc[0], include_rotation=False
            )
            return

        during = candidates[
            (candidates['parsed_datetime'] > start_time)
            & (candidates['parsed_datetime'] <= end_time)
        ]
        if not during.empty:
            self._populate_schema_from_row(
                result,
                during.sort_values('parsed_datetime', kind='stable').iloc[0],
                include_rotation=False,
            )
            return

        before = candidates[candidates['parsed_datetime'] < start_time]
        if not before.empty:
            self._populate_schema_from_row(
                result,
                before.sort_values(
                    'parsed_datetime', ascending=False, kind='stable'
                ).iloc[0],
                include_rotation=False,
            )
            return

        after = candidates[candidates['parsed_datetime'] > end_time]
        if not after.empty:
            self._populate_schema_from_row(
                result,
                after.sort_values('parsed_datetime', kind='stable').iloc[0],
                include_rotation=False,
            )

    def _match_unassigned_metadata(self, result, file_dt, df_meta):
        """Finds the closest preceding CSV log entry for a given image's timestamp."""
        if 'parsed_datetime' in df_meta.columns:
            past_meta = df_meta[df_meta['parsed_datetime'] <= file_dt]
            if not past_meta.empty:
                best_row = past_meta.sort_values(
                    by='parsed_datetime', ascending=False
                ).iloc[0]
                self._populate_schema_from_row(result, best_row, include_rotation=False)

    def _match_unassigned_rotation(self, result, result_timestamp, df_rot):
        """Assign the latest rotation-log alpha at or before a result timestamp."""
        alpha = self._select_rotation_alpha(result_timestamp, df_rot)
        if alpha is not None:
            if result.substrate_holder is None:
                result.substrate_holder = SubstrateHolder()
            result.substrate_holder.rotation_angle_alpha_deg = alpha

    @staticmethod
    def _select_rotation_alpha(result_timestamp, df_rot):
        """Return the latest rotation alpha at or before a timezone-aware timestamp."""
        if df_rot is None or 'parsed_datetime' not in df_rot.columns:
            return None

        preceding = df_rot[df_rot['parsed_datetime'] <= result_timestamp]
        if preceding.empty:
            return None
        latest = preceding.sort_values('parsed_datetime', kind='stable').iloc[-1]
        return float(latest['alpha'])

    def _create_result_instance(self, fname, all_files):
        """Instantiates the correct schema SubSection (Image, Video, or Point Scan) based on file extension."""
        fname = os.path.basename(str(fname).replace('\\', '/'))
        lower_name = fname.lower()
        if lower_name.endswith(('.tif', '.pgm')):
            res = RHEEDImageResult()
            res.name = fname
            res.result_type = 'image'
            if fname in all_files:
                res.images = self._raw_sibling_path(fname)
            return res
        elif lower_name.endswith(('.asc', '.csv')):
            res = RHEEDPointScanResult()
            res.name = fname
            res.result_type = 'scan_point'
            return res
        elif lower_name.endswith('.dst'):
            res = RHEEDVideoResult()
            res.name = fname
            res.result_type = 'video'
            return res
        return None

    # --- REFACTORED SCHEMA MAPPING LOGIC ---
    def _safe_float(self, val):
        """Safely converts string values to floats, returning None instead of crashing on empty cells."""
        if pd.isna(val):
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    def _populate_schema_from_row(self, result_obj, row, include_rotation=True):
        result_obj.sample = self._create_sample_from_row(row)
        result_obj.substrate_holder = self._create_holder_from_row(
            row, include_rotation
        )

        settings = RHEEDMeasurementSettings()
        settings.e_gun_FUG = self._create_egun_from_row(row)
        settings.deflection_unit_FUG = self._create_deflection_from_row(row)
        result_obj.measurement_settings = settings

        if pd.notna(row.get('comments')):
            result_obj.notes = str(row['comments'])

        if isinstance(result_obj, RHEEDVideoResult):
            if pd.notna(row.get('parsed_datetime')):
                result_obj.start_time = row['parsed_datetime'].isoformat()

            comments = str(row.get('comments', ''))

            interval_match = re.search(r'frame_interval_s=([\d\.]+)', comments)
            frames_match = re.search(r'number_of_frames=([\d]+)', comments)

            if interval_match:
                result_obj.frame_interval_s = float(interval_match.group(1))
            if frames_match:
                result_obj.number_of_frames = int(frames_match.group(1))

            if (
                getattr(result_obj, 'frame_interval_s', None)
                and getattr(result_obj, 'number_of_frames', None)
                and pd.notna(row.get('parsed_datetime'))
            ):
                end_dt = row['parsed_datetime'] + pd.Timedelta(
                    seconds=(result_obj.number_of_frames - 1)
                    * result_obj.frame_interval_s
                )
                result_obj.end_time = end_dt.isoformat()

    def _create_sample_from_row(self, row):
        """Extracts sample ID, orientation, and compound details from a CSV row."""
        sample = Sample()
        m8_val = str(row.get('m8_id', ''))
        if m8_val and m8_val != 'nan':
            sample.sample_id = m8_val

        if pd.notna(row.get('azimuth')):
            sample.sample_azimuth_uvw = str(row['azimuth'])

        if pd.notna(row.get('substrate')):
            sample.sample_surface_compound = str(row['substrate'])
            sample.substrate_or_film = 'substrate'
            if pd.notna(row.get('substrate_orientation')):
                sample.sample_surface_hkl = str(row['substrate_orientation'])
        elif pd.notna(row.get('film')):
            sample.sample_surface_compound = str(row['film'])
            sample.substrate_or_film = 'film'
            if pd.notna(row.get('film_orientation')):
                sample.sample_surface_hkl = str(row['film_orientation'])
        return sample

    def _create_holder_from_row(self, row, include_rotation=True):
        """Extracts the substrate position and manual manipulation angle."""
        holder = SubstrateHolder()
        m8_val = str(row.get('m8_id', ''))
        if '_' in m8_val:
            holder.position_measured = m8_val.rsplit('_', maxsplit=1)[1]

        alpha = self._safe_float(row.get('mani_angle'))
        if include_rotation and alpha is not None and alpha != -1:
            holder.rotation_angle_alpha_deg = alpha
        return holder

    def _create_egun_from_row(self, row):
        """Extracts E-Gun settings like energy, emission, and filament currents."""
        egun = EGunFUG()

        e_kev = self._safe_float(row.get('energy_kev'))
        if e_kev is not None:
            egun.electron_energy_keV = e_kev

        emis = self._safe_float(row.get('emission_uA'))
        if emis is not None:
            egun.emission_current_uA = emis

        fil_a = self._safe_float(row.get('filament_a'))
        if fil_a is not None:
            egun.filament_current_A = fil_a

        fil_v = self._safe_float(row.get('filament_v'))
        if fil_v is not None:
            egun.filament_voltage_V = fil_v

        grid_v = self._safe_float(row.get('grid_v'))
        if grid_v is not None:
            egun.grid_voltage_V = grid_v

        return egun

    def _create_deflection_from_row(self, row):
        """Extracts beam deflection and alignment settings."""
        deflect = DeflectionUnitFUG()
        field_map = {
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
        }
        for csv_field, schema_field in field_map.items():
            value = self._safe_float(row.get(csv_field))
            if value is not None:
                setattr(deflect, schema_field, value)
        return deflect


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
