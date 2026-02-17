from typing import TYPE_CHECKING

from nomad.utils import hash

if TYPE_CHECKING:
    from nomad.datamodel.data import ArchiveSection
    from nomad.datamodel.datamodel import EntryArchive


def get_reference(upload_id: str, entry_id: str) -> str:
    return f'../uploads/{upload_id}/archive/{entry_id}#data'


def get_entry_id_from_file_name(file_name: str, archive: 'EntryArchive') -> str:
    return hash(archive.metadata.upload_id, file_name)


def create_archive(
    entity: 'ArchiveSection',
    archive: 'EntryArchive',
    file_name: str,
    overwrite: bool = False,
) -> str:
    """
    Creates a separate ELN entry for the data.
    If the entry already exists, it does NOT overwrite it unless forced.
    Returns a reference (link) to that entry.
    """
    if overwrite or not archive.m_context.raw_path_exists(file_name):
        with archive.m_context.update_entry(
            file_name, write=True, process=True
        ) as entry:
            entry['data'] = entity.m_to_dict(with_root_def=True)

    return get_reference(
        archive.metadata.upload_id, get_entry_id_from_file_name(file_name, archive)
    )
