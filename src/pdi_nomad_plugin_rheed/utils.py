from typing import TYPE_CHECKING

from nomad.utils import hash

if TYPE_CHECKING:
    from nomad.datamodel.data import ArchiveSection
    from nomad.datamodel.datamodel import EntryArchive


def get_reference(upload_id: str, entry_id: str) -> str:
    """
    Generate a reference string for an entry in NOMAD.
    Args:
        upload_id: The upload ID
        entry_id: The entry ID
    Returns:
        Reference string in the format ../uploads/{upload_id}/archive/{entry_id}#data
    """
    return f'../uploads/{upload_id}/archive/{entry_id}#data'


def get_entry_id_from_file_name(file_name: str, archive: 'EntryArchive') -> str:
    """
    Generate an entry ID from a file name and upload ID.
    Args:
        file_name: The file name
        archive: The entry archive
    Returns:
        Entry ID hash
    """
    return hash(archive.metadata.upload_id, file_name)


def create_archive(
    entity: 'ArchiveSection',
    archive: 'EntryArchive',
    file_name: str,
    overwrite: bool = False,
) -> str:
    """
    Create a new archive entry and return a reference to it.
    This creates a child archive that can be processed separately from the main file,
    which is essential for ELN entries that can be edited by users without overwriting
    parsed data.
    Args:
        entity: The archive section to store in the new entry
        archive: The parent archive
        file_name: The file name for the new entry
        overwrite: Whether to overwrite existing entry
    Returns:
        Reference string to the created archive entry
    """
    if overwrite or not archive.m_context.raw_path_exists(file_name):
        with archive.m_context.update_entry(
            file_name, write=True, process=True
        ) as entry:
            entry['data'] = entity.m_to_dict(with_root_def=True)

    return get_reference(
        archive.metadata.upload_id, get_entry_id_from_file_name(file_name, archive)
    )
