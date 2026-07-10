from nomad.datamodel.context import ServerContext
from nomad.datamodel.datamodel import EntryArchive
from nomad.parsing.parser import MatchingParser
from nomad_measurements.utils import create_archive

from pdi_nomad_plugin_rheed.schema_packages.schema_package import (
    RawFileRHEEDData,
    RHEEDMeasurement,
)


class RheedParser(MatchingParser):
    def parse(
        self,
        mainfile: str,
        archive: EntryArchive,
        logger=None,
        child_archives=None,
    ) -> None:
        logger = logger or archive.m_context.logger

        data_file = mainfile.rsplit('/', maxsplit=1)[-1]
        if isinstance(archive.m_context, ServerContext):
            data_file = mainfile.split('/raw/', 1)[1]

        # 1. Instantiate the main ELN schema
        entry = RHEEDMeasurement()
        entry.data_file = data_file

        # 2. Create the separate editable .archive.json file to preserve ELN edits
        archive_name = f'{"".join(data_file.split(".")[:-1])}.archive.json'
        eln_ref = create_archive(entry, archive, archive_name)

        # 3. Link the raw metadata CSV file to the generated ELN
        archive.data = RawFileRHEEDData(measurement=eln_ref)
