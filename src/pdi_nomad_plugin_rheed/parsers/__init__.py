from nomad.config.models.plugins import ParserEntryPoint


class RHEEDParserEntryPoint(ParserEntryPoint):
    def load(self):
        from pdi_nomad_plugin_rheed.parsers.parser import RHEEDParser

        return RHEEDParser(**self.model_dump())


rheed_parser_entry_point = RHEEDParserEntryPoint(
    name='RHEEDParser',
    description='Parser for PDI RHEED images and Scans',
    mainfile_name_re=r'.*\.(pgm|tiff|tif|PGM|TIFF|TIF|asc|csv)$',
    level=1,
)
