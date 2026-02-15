import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

from nomad.parsing import MatchingParser

from pdi_nomad_plugin_rheed.schema_packages.schema_package import RHEEDMeasurement


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

        # Prepare the single RHEEDMeasurement Entry
        measurement = RHEEDMeasurement()
        measurement.name = 'RHEED Measurement Collection'

        # Save it to the archive
        archive.data = measurement
