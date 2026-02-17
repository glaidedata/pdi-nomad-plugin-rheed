import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

from nomad.datamodel.context import ServerContext
from nomad.parsing import MatchingParser

from pdi_nomad_plugin_rheed.schema_packages.schema_package import (
    RawFileRHEEDData,
    RHEEDMeasurement,
)
from pdi_nomad_plugin_rheed.utils import create_archive


class RHEEDParser(MatchingParser):
    def parse(
        self,
        mainfile: str,
        archive: 'EntryArchive',
        logger: 'BoundLogger',
        child_archives: dict[str, 'EntryArchive'] = None,
    ) -> None:

        if logger is None:
            logger = logging.getLogger(__name__)
        logger.info('RHEEDParser.parse', mainfile=mainfile)

        # 1. Resolve proper path for the data_file
        mainfile_name = os.path.basename(mainfile)
        data_file_path = mainfile_name

        # If running on the server, we need the path relative to the upload root
        if isinstance(archive.m_context, ServerContext):
            if '/raw/' in mainfile:
                data_file_path = mainfile.split('/raw/', 1)[1]

        # 2. Create the Shell for the ELN Entry
        eln_entry = RHEEDMeasurement()
        eln_entry.name = 'RHEED Measurement'
        eln_entry.data_file = data_file_path

        # 3. Generate a filename for the separate ELN archive
        eln_filename = f'{mainfile_name.rsplit(".", 1)[0]}.archive.json'

        # 4. Create (or retrieve) the ELN Archive
        eln_reference = create_archive(eln_entry, archive, eln_filename)

        # 5. Set the current entry to be the Pointer
        archive.data = RawFileRHEEDData(measurement=eln_reference)
        archive.metadata.entry_name = f'{mainfile_name} Data File'
