from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

from nomad.datamodel.data import ArchiveSection, EntryData, EntryDataCategory
from nomad.datamodel.metainfo.annotations import ELNAnnotation, ELNComponentEnum
from nomad.datamodel.metainfo.plot import PlotSection
from nomad.datamodel.results import ELN, Results
from nomad.metainfo import Quantity, SchemaPackage, Section, SubSection

m_package = SchemaPackage()

# --- Helper Section for Plots ---


class RHEEDPlot(PlotSection):
    """
    Wrapper for plots to ensure they render correctly in the ELN overview.
    """

    m_def = Section(a_eln=ELNAnnotation(overview=True, lane_width='800px'))


# --- Data Sections ---


class RHEEDImage(ArchiveSection):
    """
    Schema for a single RHEED image (PGM or TIFF).
    """

    m_def = Section(
        label_quantity='image_file',
        a_eln=ELNAnnotation(overview=True, lane_width='600px'),
    )

    image_file = Quantity(
        type=str,
        description='The original RHEED image file.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.FileEditQuantity),
        a_browser=dict(adaptor='RawFileAdaptor'),
    )

    timestamp = Quantity(
        type=str,
        description='Timestamp extracted from the filename or file metadata.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity),
    )

    plot = SubSection(
        section_def=RHEEDPlot,
        description='Interactive plot of the image.',
        a_eln=ELNAnnotation(overview=True),
    )


class RHEEDSensor(Section):
    """
    Data for a single sensor in a point scan.
    """

    name = Quantity(type=str, description='Name or ID of the sensor.')
    time = Quantity(type=np.float64, shape=['*'], unit='s', description='Time vector.')
    intensity = Quantity(type=np.float64, shape=['*'], description='Intensity values.')


class RHEEDPointScan(ArchiveSection):
    """
    Entry for a RHEED Point Scan (exported as .asc or .csv).
    """

    m_def = Section(
        label_quantity='data_file',
        a_eln=ELNAnnotation(overview=True, lane_width='600px'),
    )

    data_file = Quantity(
        type=str,
        description='The source .asc or .csv file.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.FileEditQuantity),
        a_browser=dict(adaptor='RawFileAdaptor'),
    )

    timestamp = Quantity(
        type=str,
        description='Timestamp extracted from the file header.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity),
    )

    sensors = SubSection(
        section_def=RHEEDSensor,
        repeats=True,
        description='List of sensors extracted from the file.',
    )

    plot = SubSection(
        section_def=RHEEDPlot,
        description='Interactive plot of the scan.',
        a_eln=ELNAnnotation(overview=True),
    )


# --- The ELN Entry (Editable) ---


class ELNRHEEDMeasurement(EntryData, ArchiveSection):
    """
    The Editable ELN Entry. This is what the user interacts with.
    """

    m_def = Section(
        categories=[EntryDataCategory],
        label='RHEED Measurement',
        a_eln=ELNAnnotation(
            overview=True,
            lane_width='800px',
        ),
        a_template={
            'measurement_identifiers': {},
        },
    )

    name = Quantity(
        type=str,
        description='Short name for this measurement.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity, overview=True
        ),
    )

    lab_id = Quantity(
        type=str,
        description='Sample or Lab ID.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity, overview=True
        ),
    )

    description = Quantity(
        type=str,
        description='User comments.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.RichTextEditQuantity),
    )

    # We use SubSections to hold the actual data
    # Allows for future expansion (e.g. 1 measurement = multiple images)
    image = SubSection(
        section_def=RHEEDImage,
        description='RHEED Image Data',
        a_eln=ELNAnnotation(overview=True),
    )

    point_scan = SubSection(
        section_def=RHEEDPointScan,
        description='RHEED Point Scan Data',
        a_eln=ELNAnnotation(overview=True),
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        # Populate standard NOMAD results for search
        if not archive.results:
            archive.results = Results(eln=ELN())
        if not archive.results.eln:
            archive.results.eln = ELN()

        if self.name:
            archive.results.eln.names = [self.name]

        if self.lab_id:
            archive.results.eln.lab_ids = [self.lab_id]


# --- The Raw File Entry (The Pointer) ---


class RawFileRHEEDData(EntryData):
    """
    The Parser creates this. It points to the ELN entry.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            overview=True, hide=['name', 'creation_time', 'last_processing_time']
        )
    )

    measurement = Quantity(
        type=ELNRHEEDMeasurement,
        description='Link to the editable ELN entry.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity, label='Go to ELN Entry'
        ),
    )


m_package.__init_metainfo__()
