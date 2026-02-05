from nomad.config.models.plugins import SchemaPackageEntryPoint

class RHEEDSchemaEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from pdi_nomad_rheed.schema_packages.schema import m_package
        return m_package

rheed_schema_entry_point = RHEEDSchemaEntryPoint(
    name='RHEEDSchema',
    description='Schema for PDI RHEED images',
)