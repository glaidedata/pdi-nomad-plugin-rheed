from unittest.mock import MagicMock

from nomad.datamodel import EntryArchive, EntryMetadata

from pdi_nomad_plugin_rheed.parsers.parser import RheedParser
from pdi_nomad_plugin_rheed.schema_packages.schema_package import RawFileRHEEDData


def test_parser_creates_pointer(tmp_path):
    """
    Verifies that the Parser correctly:
    1. Creates a RawFileRHEEDData entry (Pointer).
    2. Routes the target file name to the ELN payload.
    """
    # 1. Create a temporary dummy CSV file for the parser to trigger on
    test_file = tmp_path / 'm84266_A_RHEED_meta_final.csv'
    test_file.write_text(
        'm8_id,date,time,file_name\nm84266_A,2026-03-13,16:33:40,dummy.tif\n'
    )

    parser = RheedParser()
    archive = EntryArchive()
    archive.metadata = EntryMetadata(
        upload_id='test_upload_id', entry_id='test_entry_id'
    )

    # Mock the server context so create_archive doesn't try to write to a real database
    archive.m_context = MagicMock()

    # 2. Run the parser
    parser.parse(str(test_file), archive)

    # 3. Assertions
    # Ensure the main archive became the lightweight pointer
    assert isinstance(archive.data, RawFileRHEEDData), (
        'Parser did not create the RawFileRHEEDData pointer.'
    )

    data_dict = archive.data.m_to_dict()

    assert 'measurement' in data_dict, 'Pointer did not attach a measurement reference.'

    assert (
        isinstance(data_dict['measurement'], str) and len(data_dict['measurement']) > 0
    ), 'The generated reference link is empty or invalid.'
