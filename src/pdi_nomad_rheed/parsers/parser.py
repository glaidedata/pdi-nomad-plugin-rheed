import os
import logging
import re
import numpy as np
from PIL import Image
import plotly.graph_objs as go

from nomad.datamodel import EntryArchive
from nomad.parsing import MatchingParser
from nomad.datamodel.metainfo.plot import PlotlyFigure

from pdi_nomad_rheed.schema_packages.schema import RHEEDImage

class RHEEDParser(MatchingParser):
    def parse(self, mainfile: str, archive: EntryArchive, logger=None):
        if logger is None:
            logger = logging.getLogger(__name__)

        # Initialize the Entry
        entry = RHEEDImage()
        archive.data = entry

        filename = os.path.basename(mainfile)
        entry.image_file = filename

        # Extract Metadata (Timestamp)
        self._extract_timestamp(filename, entry)

        # Branch Logic based on file type
        try:
            if filename.lower().endswith('.pgm'):
                self.parse_pgm(mainfile, entry, filename)
            elif filename.lower().endswith(('.tiff', '.tif')):
                self.parse_tiff(mainfile, entry, filename)
                
        except Exception as e:
            logger.error(f"Failed to parse image file {filename}: {e}")

    def _extract_timestamp(self, filename: str, entry: RHEEDImage):
        """
        Extracts timestamp from filename based on PDI conventions.
        Format: image_YYYY-MM-DD___HH-MM-SS.mmm.tif
        """
        try:
            if "___" in filename:
                ts_part = filename.split("___")[-1]
                ts_clean = ts_part.rsplit('.', 1)[0]
                entry.timestamp = ts_clean
            else:
                match = re.search(r'(\d{4}-\d{2}-\d{2}.*\d{2}-\d{2}-\d{2})', filename)
                if match:
                    entry.timestamp = match.group(1)
        except Exception:
            pass

    def parse_pgm(self, mainfile, entry, filename):
        """
        PGM Logic: Raw intensity data -> Heatmap with Scale Bar
        """
        with Image.open(mainfile) as img:
            img_array = np.array(img)
            
            fig = go.Figure(data=go.Heatmap(
                z=img_array,
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title='Intensity', titleside='right')
            ))

            fig.update_layout(
                title=f"RHEED Intensity: {filename}",
                template='plotly_white',
                autosize=False,
                width=700,
                height=600,
                yaxis=dict(scaleanchor="x", scaleratio=1, autorange="reversed")
            )

            entry.figures.append(PlotlyFigure(
                label='Intensity Map',
                figure=fig.to_plotly_json()
            ))

    def parse_tiff(self, mainfile, entry, filename):
        """
        TIFF Logic: Visual snapshot -> Standard Image Plot
        """
        # For TIFFs with color palettes, we just want to see the image exactly as it is.
        
        with Image.open(mainfile) as img:
            img_rgb = img.convert('RGB')
            img_array = np.array(img_rgb)
            width, height = img.size
            
            fig = go.Figure()
            
            fig.add_trace(go.Image(z=img_array))
            
            fig.update_layout(
                title=f"RHEED Snapshot: {filename}",
                template='plotly_white',
                autosize=False,
                width=width,
                height=height,
                margin=dict(l=50, r=50, t=50, b=50), 
                xaxis=dict(visible=True, title="pixels", ticks="outside"),
                yaxis=dict(visible=True, title="pixels", ticks="outside", scaleanchor="x", scaleratio=1, autorange="reversed")
            )

            entry.figures.append(PlotlyFigure(
                label='Snapshot',
                figure=fig.to_plotly_json()
            ))

