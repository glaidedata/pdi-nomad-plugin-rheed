import os
import re
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import plotly.graph_objs as go
from nomad.datamodel.metainfo.plot import PlotlyFigure
from PIL import Image

if TYPE_CHECKING:
    pass

from nomad.datamodel.data import ArchiveSection, EntryData
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
    ELNComponentEnum,
    SectionProperties,
)
from nomad.datamodel.metainfo.basesections import (
    CompositeSystemReference,
    Measurement,
    MeasurementResult,
)
from nomad.datamodel.metainfo.plot import PlotSection
from nomad.metainfo import Datetime, MEnum, Quantity, SchemaPackage, Section, SubSection

m_package = SchemaPackage()


# ------ Plot Helper ------
class RHEEDPlot(PlotSection):
    """Wrapper for plots to ensure they render correctly in the ELN overview."""

    m_def = Section(a_eln=ELNAnnotation(overview=True, lane_width='800px'))

# ------ Instrument & Hardware Settings ------
class ChamberGeometry(ArchiveSection):
    distance_sample_to_screen_mm = Quantity(
        type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity)
    )

class Camera(ArchiveSection):
    image_length_calibration_mm_per_px = Quantity(
        type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity)
    )

class InstrumentSettings(ArchiveSection):
    chamber_geometry = SubSection(section_def=ChamberGeometry)
    camera = SubSection(section_def=Camera)

class EGunSTAIB(ArchiveSection):
    electron_energy_keV = Quantity(type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity))
    emission_current_uA = Quantity(type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity))
    filament_current_A = Quantity(type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity))

class EGunFUG(ArchiveSection):
    electron_energy_keV = Quantity(type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity))
    emission_current_uA = Quantity(type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity))
    filament_current_A = Quantity(type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity))
    filament_voltage_V = Quantity(type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity))
    grid_voltage_V = Quantity(type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity))
    topaz_voltage_V = Quantity(type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity))

class DeflectionUnitSTAIB(ArchiveSection):
    grid = Quantity(type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity))
    focus = Quantity(type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity))
    beam_deflection_x = Quantity(type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity))
    beam_deflection_y = Quantity(type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity))
    beam_rocking = Quantity(type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity))

class DeflectionUnitFUG(ArchiveSection):
    alignment_x = Quantity(type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity))
    alignment_y = Quantity(type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity))
    magnet_lens = Quantity(type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity))
    x_or_y_scan = Quantity(type=MEnum('x', 'y'), a_eln=dict(component=ELNComponentEnum.EnumEditQuantity))
    ext_or_int_ref = Quantity(type=MEnum('ext', 'int'), a_eln=dict(component=ELNComponentEnum.EnumEditQuantity))
    beam_deflection_x_coarse = Quantity(type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity))
    beam_deflection_x_fine = Quantity(type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity))
    beam_deflection_x_crosspoint = Quantity(type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity))
    beam_deflection_x_angle = Quantity(type=float, description="corresponds to beam rocking", a_eln=dict(component=ELNComponentEnum.NumberEditQuantity))
    beam_deflection_y_coarse = Quantity(type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity))
    beam_deflection_y_fine = Quantity(type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity))
    beam_deflection_y_crosspoint = Quantity(type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity))
    beam_deflection_y_angle = Quantity(type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity))

class RHEEDMeasurementSettings(ArchiveSection):
    m_def = Section(label='Measurement Settings')
    datetime = Quantity(type=Datetime, a_eln=dict(component=ELNComponentEnum.DateTimeEditQuantity))
    compensation_cage_on = Quantity(type=bool, a_eln=dict(component=ELNComponentEnum.BoolEditQuantity))
    incidence_angle_deg = Quantity(type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity))
    
    egun_STAIB = SubSection(section_def=EGunSTAIB)
    egun_FUG = SubSection(section_def=EGunFUG)
    deflection_unit_STAIB = SubSection(section_def=DeflectionUnitSTAIB)
    deflection_unit_FUG = SubSection(section_def=DeflectionUnitFUG)

# ------ Substrate & Sample Definitions ------
class SubstrateHolder(ArchiveSection):
    rotation_angle_alpha_deg = Quantity(type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity))
    position_measured = Quantity(type=str, a_eln=dict(component=ELNComponentEnum.StringEditQuantity))
    sample_phi_holder_alpha_deg = Quantity(type=float, description="Fixed offset of sample azimuth phi to holder rotation angle in deg", a_eln=dict(component=ELNComponentEnum.NumberEditQuantity))

class RHEEDSample(ArchiveSection):
    sample_reference = SubSection(section_def=CompositeSystemReference)
    sample_id = Quantity(type=str, a_eln=dict(component=ELNComponentEnum.StringEditQuantity))
    sample_azimuth_phi_deg = Quantity(type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity))
    substrate_or_film = Quantity(type=MEnum('substrate', 'film'), a_eln=dict(component=ELNComponentEnum.EnumEditQuantity))
    sample_surface_compound = Quantity(type=str, description="Chemical formula, e.g., Al2O3 or Ga2O3", a_eln=dict(component=ELNComponentEnum.StringEditQuantity))
    sample_azimuth_uvw = Quantity(type=np.int32, shape=[3], description="3 integers indexing real space direction", a_eln=dict(component=ELNComponentEnum.NumberEditQuantity))
    sample_azimuth_hkl = Quantity(type=np.int32, shape=[3], description="3 integers indexing reciprocal space direction", a_eln=dict(component=ELNComponentEnum.NumberEditQuantity))

# ------  Results ------
class RHEEDResult(MeasurementResult):
    m_def = Section(label='RHEED Result')
    result_type = Quantity(
        type=MEnum('video', 'image', 'scan_point'),
        a_eln=dict(component=ELNComponentEnum.EnumEditQuantity),
    )
    notes = Quantity(
        type=str, a_eln=dict(component=ELNComponentEnum.RichTextEditQuantity)
    )


class RHEEDVideoResult(RHEEDResult):
    m_def = Section(label='Video Result')
    video_link = Quantity(
        type=str, a_eln=dict(component=ELNComponentEnum.URLEditQuantity)
    )


class RHEEDImageResult(RHEEDResult, PlotSection):
    m_def = Section(
        label='Image Result', a_eln=ELNAnnotation(overview=True, lane_width='600px')
    )
    images = Quantity(
        type=str,
        shape=['*'],
        a_browser=dict(adaptor='RawFileAdaptor'),
        a_eln=dict(component=ELNComponentEnum.FileEditQuantity),
    )
    derived_from_video_link = Quantity(
        type=str, a_eln=dict(component=ELNComponentEnum.URLEditQuantity)
    )
    timestamp = Quantity(
        type=Datetime, a_eln=dict(component=ELNComponentEnum.DateTimeEditQuantity)
    )
    sample = SubSection(section_def=CompositeSystemReference)
    plot = SubSection(
        section_def=RHEEDPlot,
        description='Interactive plot of the image.',
        a_eln=ELNAnnotation(overview=True),
    )


class RHEEDSensor(ArchiveSection):
    name = Quantity(type=str)
    position_label = Quantity(
        type=str, a_eln=dict(component=ELNComponentEnum.StringEditQuantity)
    )
    time = Quantity(type=np.float64, shape=['*'])
    intensity = Quantity(type=np.float64, shape=['*'])


class PointScan(PlotSection, ArchiveSection):
    m_def = Section(
        label='Point Scan Data', a_eln=ELNAnnotation(overview=True, lane_width='600px')
    )
    source_file = Quantity(
        type=str,
        a_browser=dict(adaptor='RawFileAdaptor'),
        a_eln=dict(component=ELNComponentEnum.FileEditQuantity),
    )
    start_time = Quantity(
        type=Datetime, a_eln=dict(component=ELNComponentEnum.DateTimeEditQuantity)
    )
    end_time = Quantity(
        type=Datetime, a_eln=dict(component=ELNComponentEnum.DateTimeEditQuantity)
    )
    sensor_position_overview_picture = Quantity(
        type=str,
        a_browser=dict(adaptor='RawFileAdaptor'),
        a_eln=dict(component=ELNComponentEnum.FileEditQuantity),
    )
    sensor_definition_file = Quantity(
        type=str,
        description="Expected .sn file",
        a_browser=dict(adaptor='RawFileAdaptor'),
        a_eln=dict(component=ELNComponentEnum.FileEditQuantity),
    )
    derived_from_video_link = Quantity(
        type=str, a_eln=dict(component=ELNComponentEnum.URLEditQuantity)
    )
    sensors = SubSection(section_def=RHEEDSensor, repeats=True)
    plot = SubSection(
        section_def=RHEEDPlot,
        description='Interactive plot of the scan.',
        a_eln=ELNAnnotation(overview=True),
    )


class RHEEDPointScanResult(RHEEDResult):
    m_def = Section(label='Point Scan Result')
    start_time = Quantity(
        type=Datetime, a_eln=dict(component=ELNComponentEnum.DateTimeEditQuantity)
    )
    end_time = Quantity(
        type=Datetime, a_eln=dict(component=ELNComponentEnum.DateTimeEditQuantity)
    )
    point_scans = SubSection(section_def=PointScan, repeats=True)


# ------ Main Container ------
class RHEEDMeasurement(Measurement, EntryData):
    m_def = Section(
        label='RHEED Measurement',
        a_eln=ELNAnnotation(
            overview=True,
            lane_width='800px',
            properties=SectionProperties(
                order=[
                    'name',
                    'measurement_id',
                    'mbe_process_ref',
                    'datetime_start',
                    'datetime_end',
                    'operator',
                    'instruments',
                    'sample',
                ]
            ),
        ),
    )

    data_file = Quantity(
        type=str,
        description='The dummy file that triggered this entry. Used to locate the data folder.',
        a_eln=dict(component=ELNComponentEnum.FileEditQuantity),
    )

    measurement_id = Quantity(
        type=str, a_eln=dict(component=ELNComponentEnum.StringEditQuantity)
    )

    # TODO
    # Future Improvement:
    # Right now, this is just a text string.
    # In the future, we will want to write logic that takes this string,
    # searches the NOMAD database for an MBE experiment with that ID, and creates a real clickable link.
    mbe_process_ref = Quantity(
        type=str,
        description='Growth run ID of the experiment',
        a_eln=dict(component=ELNComponentEnum.StringEditQuantity),
    )

    datetime_start = Quantity(
        type=Datetime, a_eln=dict(component=ELNComponentEnum.DateTimeEditQuantity)
    )
    datetime_end = Quantity(
        type=Datetime, a_eln=dict(component=ELNComponentEnum.DateTimeEditQuantity)
    )
    # TODO: Ask PDI if this should be a simple string or a User reference.
    operator = Quantity(
        type=str,
        description='Name of the person who performed the measurement.',
        a_eln=dict(component=ELNComponentEnum.StringEditQuantity),
    )

    sample = SubSection(
        section_def=RHEEDSample,
        description='Detailed RHEED sample information'
    )

    instrument_settings = SubSection(section_def=InstrumentSettings)
    substrate_holder = SubSection(section_def=SubstrateHolder)
    measurement_settings = SubSection(section_def=RHEEDMeasurementSettings)
    results = SubSection(section_def=RHEEDResult, repeats=True)

    def normalize(self, archive, logger):
        """
        Scans the directory and populates 'results'.
        """
        super().normalize(archive, logger)

        # 1. Get the absolute path to the directory containing the mainfile
        if not self.data_file:
            return

        # 2. Use raw_file to find the folder
        try:
            with archive.m_context.raw_file(self.data_file) as f:
                abs_filepath = f.name

            maindir = os.path.dirname(abs_filepath)
            files_in_dir = os.listdir(maindir)
        except Exception as e:
            logger.warning(f'Could not scan directory for {self.data_file}: {e}')
            return

        # 3. Clear existing results to prevent duplicates on reprocessing
        self.results = []

        # 4. Process Images
        image_files = [
            f for f in files_in_dir if f.lower().endswith(('.pgm', '.tiff', '.tif'))
        ]
        for img_filename in image_files:
            img_path = os.path.join(maindir, img_filename)
            img_result = RHEEDImageResult()
            img_result.result_type = 'image'
            img_result.images = [img_filename]

            self._extract_timestamp_filename(img_filename, img_result)

            try:
                if img_filename.lower().endswith('.pgm'):
                    self.parse_pgm(img_path, img_result, img_filename, logger)
                elif img_filename.lower().endswith(('.tiff', '.tif')):
                    self.parse_tiff(img_path, img_result, img_filename)
                self.results.append(img_result)
            except Exception as e:
                logger.error(f'Failed to parse image {img_filename}: {e}')

        # 5. Process Scans
        scan_files = [f for f in files_in_dir if f.lower().endswith(('.csv', '.asc'))]
        if scan_files:
            scan_collection = RHEEDPointScanResult()
            scan_collection.result_type = 'scan_point'
            for scan_filename in scan_files:
                scan_path = os.path.join(maindir, scan_filename)
                pt_scan = PointScan()
                pt_scan.source_file = scan_filename
                try:
                    self.parse_scan(scan_path, pt_scan, scan_filename, logger)
                    scan_collection.point_scans.append(pt_scan)
                except Exception as e:
                    logger.error(f'Failed to parse scan {scan_filename}: {e}')
            if scan_collection.point_scans:
                self.results.append(scan_collection)

    # ------ Helper Methods for Parsing ------
    def _extract_timestamp_filename(self, filename: str, entry):
        """
        Extracts timestamp from filename based on PDI conventions.
        Format: image_YYYY-MM-DD___HH-MM-SS.mmm.tif
        """
        try:
            clean_name = filename.rsplit('.', 1)[0]

            if clean_name.startswith('image_'):
                clean_name = clean_name.replace('image_', '')

            if '___' in clean_name:
                parts = clean_name.split('___')
                date_part = parts[0]
                time_part = parts[1]
                time_part = time_part.replace('-', ':')
                entry.timestamp = f'{date_part}T{time_part}Z'
            else:
                entry.timestamp = clean_name
        except Exception:
            pass

    def parse_pgm(self, mainfile, entry, filename, logger):
        """
        PGM Logic: Raw intensity data -> Heatmap with Scale Bar
        """
        img_array = self._read_pgm_robustly(mainfile, logger)

        if img_array is not None:
            fig = go.Figure(
                data=go.Heatmap(
                    z=img_array,
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title='Intensity', titleside='right'),
                )
            )

            fig.update_layout(
                title=f'RHEED Intensity: {filename}',
                template='plotly_white',
                autosize=False,
                width=700,
                height=600,
                yaxis=dict(scaleanchor='x', scaleratio=1, autorange='reversed'),
            )

            entry.plot = RHEEDPlot()
            entry.plot.figures.append(
                PlotlyFigure(label='Intensity Map', figure=fig.to_plotly_json())
            )

    def _read_pgm_robustly(self, filepath, logger):
        """
        Tries to read PGM using PIL. If that fails (due to value > maxval),
        falls back to manual text parsing for P2 (ASCII) files.
        """
        # Method 1: Try Standard PIL
        try:
            with Image.open(filepath) as img:
                if img.mode.startswith('I;16'):
                    converted_img = img.convert('I')
                return np.array(converted_img)
        # Method 2: Fallback for P2 files (SAFIRE output)
        except Exception as e:
            try:
                with open(filepath, encoding='latin-1') as f:
                    header_peek = f.read(50)
                    if not header_peek.strip().startswith('P2'):
                        raise e

                    f.seek(0)
                    content = f.read()
                    content = re.sub(r'#.*', '', content)
                    tokens = content.split()
                    width = int(tokens[1])
                    height = int(tokens[2])

                    data = np.array(tokens[4:], dtype=np.int32)
                    return data.reshape((height, width))

            except Exception as manual_error:
                logger.error(f'Manual PGM read also failed: {manual_error}')
                raise e

    def parse_tiff(self, mainfile, entry, filename):
        """
        TIFF Logic: Visual snapshot -> Standard Image Plot
        """
        with Image.open(mainfile) as img:
            img_rgb = img.convert('RGB')
            img_array = np.array(img_rgb)
            width, height = img.size

            fig = go.Figure()

            fig.add_trace(go.Image(z=img_array))

            fig.update_layout(
                title=f'RHEED Snapshot: {filename}',
                template='plotly_white',
                autosize=False,
                width=width,
                height=height,
                margin=dict(l=50, r=50, t=50, b=50),
                xaxis=dict(visible=True, title='pixels', ticks='outside'),
                yaxis=dict(
                    visible=True,
                    title='pixels',
                    ticks='outside',
                    scaleanchor='x',
                    scaleratio=1,
                    autorange='reversed',
                ),
            )

            entry.plot = RHEEDPlot()
            entry.plot.figures.append(
                PlotlyFigure(label='Snapshot', figure=fig.to_plotly_json())
            )

    def parse_scan(self, mainfile, entry, filename, logger):
        """
        Parses PDI 'Point Scan' files (space-separated, specific header).
        """
        # 1. Extract Timestamp (starttiem?) from Line 1 ("Recorded at ...")
        with open(mainfile) as f:
            first_line = f.readline().strip()
            if 'Recorded at' in first_line:
                raw_time = first_line.replace('Recorded at', '').strip()
                if raw_time:
                    try:
                        parts = raw_time.split()
                        MIN_TIMESTAMP_PARTS = 2
                        if len(parts) >= MIN_TIMESTAMP_PARTS:
                            entry.start_time = f'{parts[0]}T{parts[1]}Z'
                    except Exception:
                        logger.warning(f'Could not parse timestamp from: {raw_time}')

        # 2. Read Data Table
        try:
            # The structure is always: Time | Sensor1 | Sensor2 ...
            df = pd.read_csv(mainfile, skiprows=4, header=None, sep=r'\s+')

            if df.empty:
                logger.warning('Parsed dataframe is empty.')
                return

            time_data = df.iloc[:, 0].values
            sensor_data_block = df.iloc[:, 1:]

            fig = go.Figure()

            for i, col_index in enumerate(sensor_data_block.columns):
                intensity = sensor_data_block[col_index].values

                sensor_name = f'Sensor {i + 1}'

                sensor = RHEEDSensor()
                sensor.name = sensor_name
                sensor.time = time_data
                sensor.intensity = intensity
                entry.sensors.append(sensor)

                fig.add_trace(
                    go.Scatter(x=time_data, y=intensity, mode='lines', name=sensor_name)
                )

            fig.update_layout(
                title=f'Point Scan: {filename}',
                xaxis_title='Time [s]',
                yaxis_title='Intensity',
                template='plotly_white',
                showlegend=True,
                legend=dict(
                    title='Sensors',
                    yanchor='top',
                    y=0.99,
                    xanchor='left',
                    x=0.01,
                    bgcolor='rgba(255, 255, 255, 0.9)',
                    bordercolor='Black',
                    borderwidth=1,
                ),
            )

            entry.plot = RHEEDPlot()
            entry.plot.figures.append(
                PlotlyFigure(label='Scan Intensity', figure=fig.to_plotly_json())
            )

        except Exception as e:
            logger.error(f'Pandas parsing failed: {e}')
            raise e


# ------ Pointer Class ------
class RawFileRHEEDData(EntryData):
    """
    This is the entry that NOMAD creates when it sees the .rheed_metadata file.
    It contains nothing but a link to the actual RHEEDMeasurement ELN.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            overview=True, hide=['name', 'creation_time', 'last_processing_time']
        )
    )

    measurement = Quantity(
        type=RHEEDMeasurement,
        description='Link to the editable ELN entry.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
        ),
    )


m_package.__init_metainfo__()
