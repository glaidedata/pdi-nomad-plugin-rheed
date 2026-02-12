from typing import TYPE_CHECKING

import numpy as np

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


# ------ Settings ------
class RHEEDMeasurementSettings(ArchiveSection):
    m_def = Section(label='Measurement Settings')
    distance_sample_to_screen_mm = Quantity(
        type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity)
    )
    image_length_calibration_mm_per_px = Quantity(
        type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity)
    )
    electron_energy_keV = Quantity(
        type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity)
    )
    emission_current_uA = Quantity(
        type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity)
    )
    compensation_cage_on = Quantity(
        type=bool, a_eln=dict(component=ELNComponentEnum.BoolEditQuantity)
    )
    beam_deflection_x = Quantity(
        type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity)
    )
    beam_deflection_y = Quantity(
        type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity)
    )
    beam_rocking = Quantity(
        type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity)
    )
    incidence_angle_deg = Quantity(
        type=float, a_eln=dict(component=ELNComponentEnum.NumberEditQuantity)
    )


# ------  Results ------
class RHEEDResult(MeasurementResult):
    m_def = Section(label='RHEED Result')
    result_type = Quantity(
        type=MEnum('video', 'image', 'scan_point'),
        a_eln=dict(component=ELNComponentEnum.EnumEditQuantity),
    )
    sample_azimuth_phi_deg = Quantity(
        type=float,
        description='User adds this manually, not derived from the video',
        a_eln=dict(component=ELNComponentEnum.NumberEditQuantity),
    )
    sample_rotation_alpha_deg = Quantity(
        type=float,
        description='Manually measured or inserted by the user',
        a_eln=dict(component=ELNComponentEnum.NumberEditQuantity),
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
    measurement_id = Quantity(
        type=str, a_eln=dict(component=ELNComponentEnum.StringEditQuantity)
    )

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
    operator = Quantity(
        type=str,
        description='Optional (or rely on NOMAD authors)',
        a_eln=dict(component=ELNComponentEnum.StringEditQuantity),
    )

    sample = SubSection(
        section_def=CompositeSystemReference,
        description='Reference to sample, default is the sample in the center of the sample holder',
    )

    measurement_settings = SubSection(section_def=RHEEDMeasurementSettings)
    results = SubSection(section_def=RHEEDResult, repeats=True)


m_package.__init_metainfo__()
