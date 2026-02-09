from nomad.config.models.plugins import SchemaPackageEntryPoint
from pydantic import Field


class RHEEDSchemaEntryPoint(SchemaPackageEntryPoint):
    parameter: int = Field(0, description='Custom configuration parameter')

    def load(self):
        from pdi_nomad_plugin_rheed.schema_packages.schema_package import m_package

        return m_package


rheed_schema_entry_point = RHEEDSchemaEntryPoint(
    name='RHEEDSchema',
    description='Schema for PDI RHEED images and scans',
)
