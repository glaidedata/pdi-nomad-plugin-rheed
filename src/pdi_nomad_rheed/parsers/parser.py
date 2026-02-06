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
                self.parse_pgm(mainfile, entry, filename, logger)
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

    def parse_pgm(self, mainfile, entry, filename, logger):
        """
        PGM Logic: Raw intensity data -> Heatmap with Scale Bar
        """
        img_array = self._read_pgm_robustly(mainfile, logger)

        if img_array is not None:
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
                yaxis=dict(
                    scaleanchor="x",
                    scaleratio=1,
                    autorange="reversed"
                )
            )

            entry.figures.append(PlotlyFigure(
                label='Intensity Map',
                figure=fig.to_plotly_json()
            ))

    def _read_pgm_robustly(self, filepath, logger):
        """
        Tries to read PGM using PIL. If that fails (due to value > maxval),
        falls back to manual text parsing for P2 (ASCII) files.
        """
        # Method 1: Try Standard PIL
        try:
            with Image.open(filepath) as img:
                if img.mode.startswith('I;16'):
                    img = img.convert('I')
                return np.array(img)
        # Method 2: Fallback for P2 files (SAFIRE output)
        # The test file claims maxval=16383 but contains 47934. 
        # PIL rejects this. ---> We parse it manually.
        except Exception as e:
            try:
                with open(filepath, 'r', encoding='latin-1') as f:
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
                logger.error(f"Manual PGM read also failed: {manual_error}")
                raise e
    
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

