import numpy as np

from pymodaq.extensions.data_mixer.model import DataMixerModel
from pymodaq_data.data import DataToExport, DataCalculated, Axis

class DataMixerEnergyConversionModel(DataMixerModel):


    def process_dte(self, dte: DataToExport):

        x_axis = Axis(label='Energy (eV)', data=1239.8/dte[0].axes[0].data)

        dte_processed = DataToExport('computed')
        dte_processed.append(DataCalculated(name='EnergySpectrum',
                                            data=[np.transpose(dte[0].data)],
                                            label='Intensity',
                                            axes=[x_axis]))
        return dte_processed
