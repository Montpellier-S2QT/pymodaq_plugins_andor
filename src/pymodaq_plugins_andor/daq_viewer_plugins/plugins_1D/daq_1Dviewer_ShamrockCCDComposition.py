import numpy as np
from qtpy import QtWidgets

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.utils import ThreadCommand

from pymodaq_gui.parameter import utils as putils

from pymodaq.utils.data import Axis, DataFromPlugins, DataToExport
from pymodaq.control_modules.viewer_utility_classes import main, comon_parameters

from pymodaq_plugins_andor.daq_viewer_plugins.plugins_2D.daq_2Dviewer_AndorCCD import DAQ_2DViewer_AndorCCD
from pymodaq_plugins_andor.daq_move_plugins.daq_move_Shamrock import DAQ_Move_Shamrock

from pymodaq_plugins_andor.hardware.andor_sdk2 import sdk2
from pymodaq_plugins_andor.hardware.shamrockCCD_compo import ShamrockCCDCompo

logger = set_logger(get_module_name(__file__))
camera_list = sdk2.AndorSDK.GetCamerasInfo()

class DAQ_1DViewer_ShamrockCCDComposition(DAQ_2DViewer_AndorCCD):
    """
        =============== ==================

        =============== ==================

        See Also
        --------
        utility_classes.DAQ_Viewer_base
    """

    params_camera = DAQ_2DViewer_AndorCCD.params_camera
    params_shamrock = DAQ_Move_Shamrock.params_shamrock
    putils.get_param_dict_from_name(params_shamrock, 'andor_lib', pop=True)

    d = putils.get_param_dict_from_name(params_shamrock, 'spectro_wl')
    if d is not None:
        d['readonly'] = False
    d = putils.get_param_dict_from_name(params_shamrock, 'flip_wavelength')
    if d is not None:
        d['visible'] = True

    params = comon_parameters + [{'title': 'Get Calibration:', 'name': 'get_calib', 'type': 'bool_push', 'value': False,
               'label': 'Update!'}, ] + params_camera + [
                 {'title': 'Shamrock Settings:', 'name': 'sham_settings', 'type': 'group', 'children': params_shamrock},
             ]


    def ini_attributes(self):
        self.controller: ShamrockCCDCompo = None
        self.camera_controller = None
        self.shamrock_controller = None

        self.x_axis: Axis = None
        self.is_calibrated = False

        super().ini_attributes()


    def commit_settings(self, param):

        if param.name() == 'flip_wavelength':
            self.get_xaxis()
            
        elif 'camera_settings' in putils.get_param_path(param):
            super().commit_settings(param)

        if param.name() == 'grating':
            index_grating = self.grating_list.index(param.value())
            self.get_set_grating(index_grating)
            self.set_wavelength(self.settings.child('spectro_settings', 'spectro_wl').value())

        elif param.name() == 'grating_offset':
            err, ind_grating = self.shamrock_controller.GetGratingSR(0)
            offset = int(self.settings.child('spectro_settings', 'grating_settings', 'grating_offset').value())
            err = self.shamrock_controller.SetGratingOffset(0, ind_grating, offset)
            if err != 'SHAMROCK_SUCCESS':
                raise Exception(err)

        elif param.name() == 'spectro_wl':
            self.set_wavelength(param.value())

        elif param.name() == 'zero_order':
            if param.value():
                param.setValue(False)
                self.emit_status(ThreadCommand('show_splash', "Moving to zero order, please wait!"))
                err = self.shamrock_controller.GotoZeroOrderSR(0)
                if err != 'SHAMROCK_SUCCESS':
                    raise Exception(err)
                self.emit_status(ThreadCommand('close_splash'))

        elif param.name() == 'slit_width':
            self.set_slitwidth(self.shamrock_controller.get_input_port(0), param.value())

        elif param.name() == 'input_port':
            index_input_port = self.inputport_list.index(param.value())
            self.set_inputport(index_input_port)

        elif param.name() == 'output_port':
            index_output_port = self.outputport_list.index(param.value())
            self.set_outputport(index_output_port)
    
        QtWidgets.QApplication.processEvents()
        
        if param.name() == 'spectro_wl':
            self.is_calibrated = False
            self.get_xaxis()
            
        elif param.name() == 'slit_width':
            self.is_calibrated = False
            
        elif param.name() == 'zero_order':
            self.is_calibrated = False
            
        elif param.name() == 'flip_wavelength':
            self.get_xaxis()
            
        elif param.name() == 'readout' or param.name() in \
            putils.iter_children(self.settings.child('camera_settings', 'readout_settings')):
            self.get_xaxis()
            
        elif param.name() == 'get_calib':
            if param.value():
                self.get_xaxis()
                param.setValue(False)
                
        elif param.name() == 'grating':
            if param.value():
                self.get_xaxis()


    def ini_detector(self, controller=None):

        if self.is_master:
            self.controller = ShamrockCCDCompo()
            self.camera_controller = self.controller.andor
            self.shamrock_controller = self.controller.shamrock
            
            initialized = True
            
        else:
            self.controller = controller
            initialized = True
            
        print("Controller:", self.controller)
        print("Andor:", self.camera_controller)
        print("Shamrock:", self.shamrock_controller)

        # init camera
        self.emit_status(ThreadCommand('show_splash', "Set/Get Camera's settings"))
        self.ini_camera()

        # init axes from image
        self.x_axis = self.get_xaxis()
        self.y_axis = self.get_yaxis()

        self.emit_status(ThreadCommand('close_splash'))
        QtWidgets.QApplication.processEvents()

        #init spectro
        self.emit_status(ThreadCommand('show_splash', "Set/Get Shamrock's settings"))
        self.ini_spectro()

        self.emit_status(ThreadCommand('close_splash'))
        QtWidgets.QApplication.processEvents()

        self.setCalibration()
        return '', initialized
    
    
    def ini_spectro(self):
        
        self.settings.child('sham_settings', 'spectro_settings', 'spectro_serialnumber').setValue(
            self.shamrock_controller.GetSerialNumberSR(0)[1].decode())

        # get grating info
        (err, Ngratings) = self.shamrock_controller.GetNumberGratingsSR(0)
        self.grating_list = []
        for ind_grating in range(1, Ngratings + 1):
            (err, lines, blaze, home, offset) = self.shamrock_controller.GetGratingInfoSR(0, ind_grating)
            self.grating_list.append(str(int(lines)))

        self.settings.child('sham_settings', 'spectro_settings', 'grating_settings', 'grating').setLimits(self.grating_list)
        err, ind_grating = self.shamrock_controller.GetGratingSR(0)
        self.settings.child('sham_settings', 'spectro_settings', 'grating_settings', 'grating').setValue(
            self.grating_list[ind_grating - 1])

        self.get_set_grating(ind_grating - 1)

        # idem pour les ports (PV/L2C/) :######
        if self.shamrock_controller.FlipperMirrorIsPresent(0, 1)[1] == 1:
            self.inputport_list = ["INPUT_FRONT", "INPUT_SIDE"]
            self.settings.child('sham_settings', 'spectro_settings', 'input_port').setLimits(self.inputport_list)
            err, inputport_index = self.shamrock_controller.get_input_port(0)
            self.settings.child('sham_settings', 'spectro_settings', 'input_port').setValue(self.inputport_list[inputport_index])
            self.set_inputport(inputport_index)
        else :
            self.inputport_list = ["SINGLE_INPUT_PORT"]
            self.settings.child('sham_settings', 'spectro_settings', 'input_port').setLimits(self.inputport_list)

        if self.shamrock_controller.FlipperMirrorIsPresent(0, 2)[1] == 1:
            self.outputport_list = ["OUTPUT_FRONT", "OUTPUT_SIDE"]
            self.settings.child('sham_settings', 'spectro_settings', 'output_port').setLimits(self.outputport_list)
            err, outputport_index = self.shamrock_controller.get_output_port(0)
            self.settings.child('sham_settings', 'spectro_settings', 'output_port').setValue(self.outputport_list[outputport_index])
            self.set_outputport(outputport_index)
        else :
            self.outputport_list = ["SINGLE_OUTPUT_PORT"]
            self.settings.child('sham_settings', 'spectro_settings', 'output_port').setLimits(self.outputport_list)
    
    
    def get_set_grating(self, ind_grating):
        """
        set the current grating to ind_grating+1. ind_grating corresponds to the index in the GUI grating list while the SDK index starts at 1...

        """
        self.emit_status(ThreadCommand('show_splash', "Moving grating please wait"))
        err = self.shamrock_controller.SetGratingSR(0, ind_grating + 1)
        if err != 'SHAMROCK_SUCCESS':
            raise Exception(err)
        err, ind_grating = self.shamrock_controller.GetGratingSR(0)
        if err != 'SHAMROCK_SUCCESS':
            raise Exception(err)

        (err, lines, blaze, home, offset) = self.shamrock_controller.GetGratingInfoSR(0, ind_grating)
        self.settings.child('sham_settings', 'spectro_settings', 'grating_settings', 'grating').setValue(
            self.grating_list[ind_grating - 1])
        self.settings.child('sham_settings', 'spectro_settings', 'grating_settings', 'lines').setValue(lines)
        self.settings.child('sham_settings', 'spectro_settings', 'grating_settings', 'blaze').setValue(blaze)
        self.settings.child('sham_settings', 'spectro_settings', 'grating_settings', 'grating_offset').setValue(offset)

        (err, wl_min, wl_max) = self.shamrock_controller.GetWavelengthLimitsSR(0, ind_grating)

        if err == "SHAMROCK_SUCCESS":
            self.settings.child('sham_settings', 'spectro_settings',
                                'spectro_wl').setOpts(limits=(wl_min, wl_max),
                                                      tip=f'Possible values are within {wl_min} and {wl_max} for'
                                                          f' the selected grating')
            self.settings.child('sham_settings', 'spectro_settings',
                                'spectro_wl_home').setOpts(limits=(wl_min, wl_max),
                                                           tip=f'Possible values are within {wl_min} and {wl_max} for'
                                                               f' the selected grating')

        self.emit_status(ThreadCommand('close_splash'))


    def set_wavelength(self, wavelength):
        self.emit_status(ThreadCommand('show_splash', "Setting wavelength, please wait!"))
        err = self.shamrock_controller.SetWavelengthSR(0, wavelength)
        self.emit_status(ThreadCommand('close_splash'))

        if err != 'SHAMROCK_SUCCESS':
            raise Exception(err)

        self.get_wavelength()


    def get_wavelength(self):
        err, wl = self.shamrock_controller.GetWavelengthSR(0)
        if err == "SHAMROCK_SUCCESS":
            self.settings.child('sham_settings', 'spectro_settings', 'spectro_wl').setValue(wl)
        return float(wl)


    def set_slitwidth(self, index, slitwidth):
        self.emit_status(ThreadCommand('show_splash', "Setting slit width, please wait!"))
        err = self.shamrock_controller.SetAutoSlitWidthSR(0, index, slitwidth)
        self.emit_status(ThreadCommand('close_splash'))

        if err != 'SHAMROCK_SUCCESS':
            raise Exception(err)

        self.get_slitwidth(index)


    def get_slitwidth(self,index):
        err, sw = self.shamrock_controller.GetAutoSlitWidthSR(0,index)
        if err == "SHAMROCK_SUCCESS":
            self.settings.child('sham_settings', 'spectro_settings', 'slit_width').setValue(sw)
        return float(sw)


    def set_inputport(self, index_inputport):
        self.emit_status(ThreadCommand('show_splash', "Setting input port, please wait!"))
        if index_inputport == 0 :
            strinputport = "INPUT_FRONT"
        elif index_inputport == 1 :
            strinputport = "INPUT_SIDE"
        else:
            raise Exception('Invalid input port number')

        err = self.shamrock_controller.set_input_port(0, strinputport)
        self.emit_status(ThreadCommand('close_splash'))

        if err != 'SHAMROCK_SUCCESS':
            raise IOError(err)

        self.get_inputport()


    def get_inputport(self):
        err, inputport = self.shamrock_controller.get_input_port(0)

        if err == "SHAMROCK_SUCCESS":
            self.settings.child('sham_settings', 'spectro_settings', 'input_port').setValue(self.inputport_list[inputport])

        return self.inputport_list[inputport]


    def set_outputport(self, index_outputport):
        self.emit_status(ThreadCommand('show_splash', "Setting output port, please wait!"))
        if index_outputport == 0:
            stroutputport = "OUTPUT_FRONT"
        elif index_outputport == 1:
            stroutputport = "OUTPUT_SIDE"
        else:
            raise Exception('Invalid output port number')

        err = self.shamrock_controller.set_output_port(0, stroutputport)
        self.emit_status(ThreadCommand('close_splash'))

        if err != 'SHAMROCK_SUCCESS':
            raise Exception(err)

        self.get_outputport()


    def get_outputport(self):
        err, outputport = self.shamrock_controller.get_output_port(0)

        if err == "SHAMROCK_SUCCESS":
            self.settings.child('sham_settings', 'spectro_settings', 'output_port').setValue(self.outputport_list[outputport])

        return self.outputport_list[outputport]
    
    
    def setCalibration(self):
        #setNpixels
        width, height = self.get_pixel_size()

        err = self.shamrock_controller.SetNumberPixelsSR(0, self.get_ROI_size_x())
        if err != "SHAMROCK_SUCCESS":
            raise Exception(err)

        err = self.shamrock_controller.SetPixelWidthSR(0, width)

        if err != "SHAMROCK_SUCCESS":
            raise Exception(err)

        self.get_wavelength()
        self.x_axis = self.get_xaxis()


    def getCalibration(self):

        (err, calib) = self.shamrock_controller.GetCalibrationSR(0, self.get_ROI_size_x())
        if err != "SHAMROCK_SUCCESS":
            raise Exception(err)

        calib = np.array(calib)
        self.is_calibrated = True

        return calib


    def get_xaxis(self):
        """
            Obtain the horizontal axis of the image.

            Returns
            -------
            1D numpy array
                Contains a vector of integer corresponding to the horizontal camera pixels.
        """

        if self.shamrock_controller is None or np.abs(self.settings.child('sham_settings', 'spectro_settings', 'spectro_wl').value()) < 1e-3:
            nx = self.get_ROI_size_x()
            calib = np.linspace(0, nx, nx-1)
            self.x_axis = Axis(data=calib, label='Wavelength (nm)')
            
        else:
            calib = self.getCalibration()

            if (calib.astype('int') != 0).all():  # check if calib values are equal to zero
                if self.settings.child('sham_settings', 'spectro_settings', 'flip_wavelength').value():
                    calib = calib[::-1]

            else:
                self.settings.child('sham_settings', 'spectro_settings', 'flip_wavelength').setValue(False)
                #self.emit_status(ThreadCommand('Update_Status', ['Impossible to flip wavelength', "log"]))

            self.x_axis = Axis(data=calib, label='Wavelength (nm)')
            
        return self.x_axis


    def stop(self):
        if self.camera_controller is not None:
            super().stop()
        if self.shamrock_controller is not None:
            self.shamrock_controller.stop()


    def close(self):
        self.stop()
        if self.shamrock_controller is not None:
            self.shamrock_controller.close()
        super().close()


    def grab_data(self, Naverage=1, **kwargs):
        self.get_xaxis()
        super().grab_data(Naverage, **kwargs)


    def emit_data(self):
        """
            overloadded function from DAQ_2DViewer_AndorCCD
        """
        try:
            self.ind_grabbed += 1
            sizey = self.settings.child('camera_settings', 'image_size', 'Ny').value()
            sizex = self.settings.child('camera_settings', 'image_size', 'Nx').value()
            self.camera_controller.GetAcquiredDataNumpy(self.data_pointer, sizex * sizey)
            self.dte_signal.emit(
                DataToExport('Spectro',
                             data=[
                                 DataFromPlugins(name='Camera',
                                                 data=[np.atleast_1d(np.squeeze(self.data.reshape(
                                                     (sizey, sizex)))).astype(float)],
                                                 dim=self.data_shape,
                                                 axes=[self.x_axis]),
                             ]))
            QtWidgets.QApplication.processEvents()  # here to be sure the timeevents are executed even if in continuous grab mode

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status', [str(e), 'log']))


if __name__ == '__main__':
    main(__file__, True)
