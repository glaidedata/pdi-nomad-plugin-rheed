from nomad.config.models.plugins import ParserEntryPoint


class RHEEDParserEntryPoint(ParserEntryPoint):
    def load(self):
        from pdi_nomad_plugin_rheed.parsers.parser import RHEEDParser

        return RHEEDParser(**self.model_dump())


rheed_parser_entry_point = RHEEDParserEntryPoint(
    name='RHEEDParser',
    description='Parser for PDI RHEED measurements. Triggered by a .rheed_metadata file.',
    # CRITICAL CHANGE: Only trigger on specific dummy file extension!
    mainfile_name_re=r'.*\.rheed_metadata$',
    level=1,
)
