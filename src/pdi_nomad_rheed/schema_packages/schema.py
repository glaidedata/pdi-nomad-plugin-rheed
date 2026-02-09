import numpy as np
from nomad.metainfo import Quantity, SchemaPackage, SubSection, Section
from nomad.datamodel.data import EntryData, EntryDataCategory
from nomad.datamodel.metainfo.plot import PlotSection
from nomad.datamodel.metainfo.annotations import ELNAnnotation, ELNComponentEnum

m_package = SchemaPackage()

class RHEEDImage(EntryData, PlotSection):
    '''
    Schema for a single RHEED image (PGM or TIFF).
    Contains full intensity information visualized as a heatmap.
    '''
    m_def = Section(categories=[EntryDataCategory])

    image_file = Quantity(
        type=str,
        description='The original RHEED image file.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.FileEditQuantity),
        a_browser=dict(adaptor='RawFileAdaptor')
    )

    timestamp = Quantity(
        type=str,
        description='Timestamp extracted from the filename or file metadata.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity)
    )

class RHEEDSensor(Section):
    '''
    Data for a single sensor in a point scan.
    '''
    name = Quantity(
        type=str,
        description='Name or ID of the sensor (e.g. Sensor 1).'
    )

    time = Quantity(
        type=np.float64,
        shape=['*'],
        unit='s',
        description='Time vector for this sensor.'
    )
    
    intensity = Quantity(
        type=np.float64,
        shape=['*'],
        description='Averaged intensity values.'
    )

class RHEEDPointScan(EntryData, PlotSection):
    '''
    Entry for a RHEED Point Scan (exported as .asc or .csv).
    '''
    m_def = Section(categories=[EntryDataCategory])

    data_file = Quantity(
        type=str,
        description='The source .asc or .csv file.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.FileEditQuantity),
        a_browser=dict(adaptor='RawFileAdaptor')
    )

    timestamp = Quantity(
        type=str,
        description='Timestamp extracted from the file header.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity)
    )

    sensors = SubSection(
        section_def=RHEEDSensor,
        repeats=True,
        description='List of sensors extracted from the file.'
    )

m_package.__init_metainfo__()