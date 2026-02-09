from nomad.config.models.plugins import ParserEntryPoint

class RHEEDParserEntryPoint(ParserEntryPoint):
    def load(self):
        from pdi_nomad_rheed.parsers.parser import RHEEDParser
        return RHEEDParser(**self.dict(exclude={'name', 'description', 'plugin_type', 'python_package', 'load', 'mainfile_contents_re'}))

rheed_parser_entry_point = RHEEDParserEntryPoint(
    name='RHEEDParser',
    description='Parser for PDI RHEED images (PGM/TIFF) and Point Scans (ASC/CSV)',
    mainfile_name_re=r'.*\.(pgm|tiff|tif|PGM|TIFF|TIF|asc|csv)$',
    level=1
)