import logging
import os
import re
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import plotly.graph_objs as go
from PIL import Image

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

from nomad.datamodel.metainfo.plot import PlotlyFigure
from nomad.parsing import MatchingParser

from pdi_nomad_plugin_rheed.schema_packages.schema_package import (
    RHEEDImage,
    RHEEDPointScan,
    RHEEDSensor,
)


class RHEEDParser(MatchingParser):
    def parse(
        self,
        mainfile: str,
        archive: 'EntryArchive',
        logger: 'BoundLogger',
        child_archives: dict[str, 'EntryArchive'] = None,
    ) -> None:

        if logger is None:
            logger = logging.getLogger(__name__)

        filename = os.path.basename(mainfile)

        # 1. Image Files (PGM/TIFF) -> RHEEDImage
        if filename.lower().endswith(('.pgm', '.tiff', '.tif')):
            entry = RHEEDImage()
            archive.data = entry
            entry.image_file = filename
            self._extract_timestamp_filename(filename, entry)

            try:
                if filename.lower().endswith('.pgm'):
                    self.parse_pgm(mainfile, entry, filename, logger)
                elif filename.lower().endswith(('.tiff', '.tif')):
                    self.parse_tiff(mainfile, entry, filename)
            except Exception as e:
                logger.error(f'Failed to parse image: {e}')

        # 2. Scan Files (CSV/ASC) -> RHEEDPointScan
        elif filename.lower().endswith(('.csv', '.asc')):
            entry = RHEEDPointScan()
            archive.data = entry
            entry.data_file = filename

            try:
                self.parse_scan(mainfile, entry, filename, logger)
            except Exception as e:
                logger.error(f'Failed to parse scan: {e}')

    def _extract_timestamp_filename(self, filename: str, entry):
        """
        Extracts timestamp from filename based on PDI conventions.
        Format: image_YYYY-MM-DD___HH-MM-SS.mmm.tif
        """
        try:
            clean_name = filename.rsplit('.', 1)[0]

            if clean_name.startswith('image_'):
                clean_name = clean_name.replace('image_', '')

            if '___' in clean_name:
                parts = clean_name.split('___')
                date_part = parts[0]
                time_part = parts[1]
                time_part = time_part.replace('-', ':')
                entry.timestamp = f'{date_part} {time_part}'
            else:
                entry.timestamp = clean_name
        except Exception:
            pass

    def parse_pgm(self, mainfile, entry, filename, logger):
        """
        PGM Logic: Raw intensity data -> Heatmap with Scale Bar
        """
        img_array = self._read_pgm_robustly(mainfile, logger)

        if img_array is not None:
            fig = go.Figure(
                data=go.Heatmap(
                    z=img_array,
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title='Intensity', titleside='right'),
                )
            )

            fig.update_layout(
                title=f'RHEED Intensity: {filename}',
                template='plotly_white',
                autosize=False,
                width=700,
                height=600,
                yaxis=dict(scaleanchor='x', scaleratio=1, autorange='reversed'),
            )

            entry.figures.append(
                PlotlyFigure(label='Intensity Map', figure=fig.to_plotly_json())
            )

    def _read_pgm_robustly(self, filepath, logger):
        """
        Tries to read PGM using PIL. If that fails (due to value > maxval),
        falls back to manual text parsing for P2 (ASCII) files.
        """
        # Method 1: Try Standard PIL
        try:
            with Image.open(filepath) as img:
                if img.mode.startswith('I;16'):
                    converted_img = img.convert('I')
                return np.array(converted_img)
        # Method 2: Fallback for P2 files (SAFIRE output)
        except Exception as e:
            try:
                with open(filepath, encoding='latin-1') as f:
                    header_peek = f.read(50)
                    if not header_peek.strip().startswith('P2'):
                        raise e

                    f.seek(0)
                    content = f.read()
                    content = re.sub(r'#.*', '', content)
                    tokens = content.split()
                    width = int(tokens[1])
                    height = int(tokens[2])

                    data = np.array(tokens[4:], dtype=np.int32)
                    return data.reshape((height, width))

            except Exception as manual_error:
                logger.error(f'Manual PGM read also failed: {manual_error}')
                raise e

    def parse_tiff(self, mainfile, entry, filename):
        """
        TIFF Logic: Visual snapshot -> Standard Image Plot
        """
        with Image.open(mainfile) as img:
            img_rgb = img.convert('RGB')
            img_array = np.array(img_rgb)
            width, height = img.size

            fig = go.Figure()

            fig.add_trace(go.Image(z=img_array))

            fig.update_layout(
                title=f'RHEED Snapshot: {filename}',
                template='plotly_white',
                autosize=False,
                width=width,
                height=height,
                margin=dict(l=50, r=50, t=50, b=50),
                xaxis=dict(visible=True, title='pixels', ticks='outside'),
                yaxis=dict(
                    visible=True,
                    title='pixels',
                    ticks='outside',
                    scaleanchor='x',
                    scaleratio=1,
                    autorange='reversed',
                ),
            )

            entry.figures.append(
                PlotlyFigure(label='Snapshot', figure=fig.to_plotly_json())
            )

    def parse_scan(self, mainfile, entry, filename, logger):
        """
        Parses PDI 'Point Scan' files (space-separated, specific header).
        """
        # 1. Extract Timestamp from Line 1 ("Recorded at ...")
        with open(mainfile) as f:
            first_line = f.readline().strip()
            if 'Recorded at' in first_line:
                entry.timestamp = first_line.replace('Recorded at', '').strip()

        # 2. Read Data Table
        try:
            # The structure is always: Time | Sensor1 | Sensor2 ...
            df = pd.read_csv(mainfile, skiprows=4, header=None, sep=r'\s+')

            if df.empty:
                logger.warning('Parsed dataframe is empty.')
                return

            time_data = df.iloc[:, 0].values
            sensor_data_block = df.iloc[:, 1:]

            fig = go.Figure()

            for i, col_index in enumerate(sensor_data_block.columns):
                intensity = sensor_data_block[col_index].values

                sensor_name = f'Sensor {i + 1}'

                sensor = RHEEDSensor()
                sensor.name = sensor_name
                sensor.time = time_data
                sensor.intensity = intensity
                entry.sensors.append(sensor)

                fig.add_trace(
                    go.Scatter(x=time_data, y=intensity, mode='lines', name=sensor_name)
                )

            fig.update_layout(
                title=f'Point Scan: {filename}',
                xaxis_title='Time [s]',
                yaxis_title='Intensity',
                template='plotly_white',
                showlegend=True,
                legend=dict(
                    title='Sensors',
                    yanchor='top',
                    y=0.99,
                    xanchor='left',
                    x=0.01,
                    bgcolor='rgba(255, 255, 255, 0.9)',
                    bordercolor='Black',
                    borderwidth=1,
                ),
            )

            entry.figures.append(
                PlotlyFigure(label='Scan Intensity', figure=fig.to_plotly_json())
            )

        except Exception as e:
            logger.error(f'Pandas parsing failed: {e}')
            raise e
