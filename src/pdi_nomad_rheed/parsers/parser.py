import os
import logging
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

        # 1. Initialize the Entry
        entry = RHEEDImage()
        archive.data = entry

        filename = os.path.basename(mainfile)
        entry.image_file = filename

        # 2. Open and Process the Image (PGM or TIFF)
        try:
            with Image.open(mainfile) as img:
                # Convert to numpy array to get intensity values
                img_array = np.array(img)
                
                # 3. Create Visualization (Heatmap with Scale Bar)
                fig = go.Figure(data=go.Heatmap(
                    z=img_array,
                    colorscale='Viridis',
                    showscale=True,  # This adds the scale bar
                    colorbar=dict(
                        title='Intensity',
                        titleside='right'
                    )
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

                # 4. Attach figure to the entry
                entry.figures.append(PlotlyFigure(
                    label='Intensity Map',
                    figure=fig.to_plotly_json()
                ))
                
        except Exception as e:
            logger.error(f"Failed to parse image file {filename}: {e}")