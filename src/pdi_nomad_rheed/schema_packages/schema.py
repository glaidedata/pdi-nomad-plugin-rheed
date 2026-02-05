from nomad.metainfo import Quantity, SchemaPackage, Section
from nomad.datamodel.data import EntryData, EntryDataCategory
from nomad.datamodel.metainfo.plot import PlotSection
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
    ELNComponentEnum,
)

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
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.FileEditQuantity
        ),
        a_browser=dict(adaptor='RawFileAdaptor')
    )

    timestamp = Quantity(
        type=str,
        description='Timestamp extracted from the filename or file metadata.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity)
    )

m_package.__init_metainfo__()