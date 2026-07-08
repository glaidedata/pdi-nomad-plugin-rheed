from nomad.datamodel.data import ArchiveSection, EntryData
from nomad.datamodel.metainfo.basesections import Measurement, MeasurementResult
from nomad.metainfo import Datetime, MEnum, Quantity, SchemaPackage, SubSection

m_package = SchemaPackage()


# ---------------------------------------------------------
# 1. Global Instrument Sections
# ---------------------------------------------------------
class ChamberGeometry(ArchiveSection):
    distance_sample_to_screen_mm = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )


class Camera(ArchiveSection):
    resolution_x_px = Quantity(type=int, a_eln=dict(component='NumberEditQuantity'))
    resolution_y_px = Quantity(type=int, a_eln=dict(component='NumberEditQuantity'))
    image_length_calibration_mm_per_px = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )


class InstrumentSettings(ArchiveSection):
    electronics_type = Quantity(
        type=MEnum('FUG', 'STAIB'), a_eln=dict(component='EnumEditQuantity')
    )
    chamber_geometry = SubSection(section_def=ChamberGeometry)
    camera = SubSection(section_def=Camera)


# ---------------------------------------------------------
# 2. Hardware Settings (Dynamic)
# ---------------------------------------------------------
class EGunSTAIB(ArchiveSection):
    electron_energy_keV = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )
    emission_current_uA = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )
    filament_current_A = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )


class EGunFUG(ArchiveSection):
    electron_energy_keV = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )
    emission_current_uA = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )
    filament_current_A = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )
    filament_voltage_V = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )
    grid_voltage_V = Quantity(type=float, a_eln=dict(component='NumberEditQuantity'))
    topaz_voltage_V = Quantity(type=float, a_eln=dict(component='NumberEditQuantity'))


class DeflectionUnitSTAIB(ArchiveSection):
    grid = Quantity(type=float, a_eln=dict(component='NumberEditQuantity'))
    focus = Quantity(type=float, a_eln=dict(component='NumberEditQuantity'))
    beam_deflection_x = Quantity(type=float, a_eln=dict(component='NumberEditQuantity'))
    beam_deflection_y = Quantity(type=float, a_eln=dict(component='NumberEditQuantity'))
    beam_rocking = Quantity(type=float, a_eln=dict(component='NumberEditQuantity'))


class DeflectionUnitFUG(ArchiveSection):
    alignment_x = Quantity(type=float, a_eln=dict(component='NumberEditQuantity'))
    alignment_y = Quantity(type=float, a_eln=dict(component='NumberEditQuantity'))
    magnet_lens = Quantity(type=float, a_eln=dict(component='NumberEditQuantity'))
    x_or_y_scan = Quantity(
        type=MEnum('x', 'y'), a_eln=dict(component='EnumEditQuantity')
    )
    ext_or_int_ref = Quantity(
        type=MEnum('ext', 'int'), a_eln=dict(component='EnumEditQuantity')
    )
    beam_deflection_x_coarse = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )
    beam_deflection_x_fine = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )
    beam_deflection_x_crosspoint = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )
    beam_deflection_x_angle = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )
    beam_deflection_y_coarse = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )
    beam_deflection_y_fine = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )
    beam_deflection_y_crosspoint = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )
    beam_deflection_y_angle = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )


class RHEEDMeasurementSettings(ArchiveSection):
    datetime = Quantity(type=Datetime, a_eln=dict(component='DateTimeEditQuantity'))
    compensation_cage_on = Quantity(type=bool, a_eln=dict(component='BoolEditQuantity'))
    incidence_angle_deg = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )

    e_gun_STAIB = SubSection(section_def=EGunSTAIB)
    e_gun_FUG = SubSection(section_def=EGunFUG)
    deflection_unit_STAIB = SubSection(section_def=DeflectionUnitSTAIB)
    deflection_unit_FUG = SubSection(section_def=DeflectionUnitFUG)


# ---------------------------------------------------------
# 3. Sample and Substrate Context
# ---------------------------------------------------------
class SubstrateHolder(ArchiveSection):
    rotation_angle_alpha_deg = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )
    position_measured = Quantity(type=str, a_eln=dict(component='StringEditQuantity'))


class Sample(ArchiveSection):
    sample_reference = Quantity(
        type=ArchiveSection, a_eln=dict(component='ReferenceEditQuantity')
    )
    sample_id = Quantity(type=str, a_eln=dict(component='StringEditQuantity'))
    sample_azimuth_phi_deg = Quantity(
        type=float,
        description='Calculated automatically: sample_phi_holder_alpha_deg + rotation_angle_alpha_deg',
    )
    substrate_or_film = Quantity(
        type=MEnum('substrate', 'film'), a_eln=dict(component='EnumEditQuantity')
    )
    sample_surface_compound = Quantity(
        type=str, a_eln=dict(component='StringEditQuantity')
    )
    sample_azimuth_uvw = Quantity(type=str, a_eln=dict(component='StringEditQuantity'))
    sample_surface_hkl = Quantity(type=str, a_eln=dict(component='StringEditQuantity'))


# ---------------------------------------------------------
# 4. Result Sections
# ---------------------------------------------------------
class RHEEDResult(MeasurementResult):
    result_type = Quantity(type=MEnum('video', 'image', 'scan_point'))
    datetime = Quantity(type=Datetime, a_eln=dict(component='DateTimeEditQuantity'))

    measurement_settings = SubSection(section_def=RHEEDMeasurementSettings)
    substrate_holder = SubSection(section_def=SubstrateHolder)
    sample = SubSection(section_def=Sample)
    notes = Quantity(type=str, a_eln=dict(component='RichTextEditQuantity'))

    def normalize(self, archive, logger):
        super().normalize(archive, logger)

        # Calculate derived Sample Azimuth Phi
        if self.sample and self.substrate_holder:
            alpha = self.substrate_holder.rotation_angle_alpha_deg

            parent_measurement = self.m_parent
            if parent_measurement:
                offset = parent_measurement.sample_phi_holder_alpha_deg

                if alpha is not None and offset is not None:
                    self.sample.sample_azimuth_phi_deg = alpha + offset


class RHEEDVideoResult(RHEEDResult):
    video_link = Quantity(type=str, a_eln=dict(component='StringEditQuantity'))
    start_time = Quantity(type=Datetime, a_eln=dict(component='DateTimeEditQuantity'))
    end_time = Quantity(type=Datetime, a_eln=dict(component='DateTimeEditQuantity'))
    frame_interval_s = Quantity(type=float, a_eln=dict(component='NumberEditQuantity'))
    number_of_frames = Quantity(type=int, a_eln=dict(component='NumberEditQuantity'))


class RHEEDImageResult(RHEEDResult):
    images = Quantity(type=str, shape=['*'], a_browser=dict(adaptor='RawFileAdaptor'))
    derived_from_video_link = Quantity(
        type=str, a_eln=dict(component='StringEditQuantity')
    )


class PointScan(ArchiveSection):
    source_file = Quantity(type=str, a_browser=dict(adaptor='RawFileAdaptor'))
    start_time = Quantity(type=Datetime)
    end_time = Quantity(type=Datetime)
    sensor_position_overview_picture = Quantity(
        type=str, a_browser=dict(adaptor='RawFileAdaptor')
    )
    sensor_definition_file = Quantity(
        type=str, a_browser=dict(adaptor='RawFileAdaptor')
    )
    derived_from_video_link = Quantity(type=str)


class RHEEDPointScanResult(RHEEDResult):
    point_scans = SubSection(section_def=PointScan, repeats=True)


# ---------------------------------------------------------
# 5. Top-Level Measurement Entry
# ---------------------------------------------------------
class RHEEDMeasurement(Measurement, EntryData):
    measurement_id = Quantity(
        type=str,
        a_eln=dict(component='StringEditQuantity'),
        description='Auto-generated: RHD_[sample_id]_[datetime]',
    )
    mbe_experiment_ref = Quantity(
        type=ArchiveSection,
        a_eln=dict(component='ReferenceEditQuantity'),
        description='Reference to the higher-level MBE Experiment ID',
    )
    sample_phi_holder_alpha_deg = Quantity(
        type=float, a_eln=dict(component='NumberEditQuantity')
    )
    sample_ref = Quantity(
        type=ArchiveSection, a_eln=dict(component='ReferenceEditQuantity')
    )
    color_table = Quantity(type=str, a_browser=dict(adaptor='RawFileAdaptor'))

    instrument_settings = SubSection(section_def=InstrumentSettings)
    results = SubSection(section_def=RHEEDResult, repeats=True)

    def normalize(self, archive, logger):
        super().normalize(archive, logger)

        if not self.measurement_id and self.results:
            first_result = self.results[0]
            if getattr(first_result, 'sample', None) and getattr(
                first_result.sample, 'sample_id', None
            ):
                s_id = first_result.sample.sample_id
                dt = getattr(first_result, 'datetime', None)
                if dt:
                    dt_str = dt.strftime('%Y-%m-%d_%H-%M-%S')
                    self.measurement_id = f'RHD_{s_id}_{dt_str}'


m_package.__init_metainfo__()
