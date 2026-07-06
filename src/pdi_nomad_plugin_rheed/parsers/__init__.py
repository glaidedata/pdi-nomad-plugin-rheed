from nomad.config.models.plugins import ParserEntryPoint

class RheedParserEntryPoint(ParserEntryPoint):
    def load(self):
        from pdi_nomad_plugin_rheed.parsers.parser import RheedParser
        return RheedParser(**self.dict())

rheed_parser = RheedParserEntryPoint(
    name='RheedParser',
    description='Parser for RHEED experiment data, driven by a master metadata CSV.',
    # This regex is case-insensitive and matches any CSV containing "rheed_meta" 
    # e.g., m84266_A_RHEED_meta_final.csv, test_rheed_meta.csv, RHEED_meta.csv
    mainfile_name_re=r'^.*[rR][hH][eE][eE][dD]_[mM][eE][tT][aA].*\.csv$',
)