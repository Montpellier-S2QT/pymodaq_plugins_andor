import numpy as np
import ctypes
from qtpy import QtWidgets, QtCore

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.utils import ThreadCommand, find_dict_in_list_from_key_val

from pymodaq_gui.parameter import utils as putils
from pymodaq_gui.parameter.utils import iter_children

from pymodaq.utils.data import Axis, DataFromPlugins, DataToExport
from pymodaq.control_modules.viewer_utility_classes import main, DAQ_Viewer_base, comon_parameters


from pymodaq_plugins_andor.daq_viewer_plugins.plugins_2D.daq_2Dviewer_AndorCCD import Andor_Camera_ReadOut
from pymodaq_plugins_andor.daq_viewer_plugins.plugins_2D.daq_2Dviewer_AndorCCD import Andor_Camera_AcqMode
from pymodaq_plugins_andor.daq_viewer_plugins.plugins_2D.daq_2Dviewer_AndorCCD import AndorCallback

from pymodaq_plugins_andor.hardware.andor_sdk2 import sdk2
from pymodaq_plugins_andor.hardware.shamrockCCD_compo import ShamrockCCDCompo

logger = set_logger(get_module_name(__file__))
camera_list = sdk2.AndorSDK.GetCamerasInfo()

class DAQ_1DViewer_ShamrockCCDCompositionMultispec(DAQ_Viewer_base):
    """
        =============== ==================

        =============== ==================

        See Also
        --------
        utility_classes.DAQ_Viewer_base
    """

    callback_signal = QtCore.Signal(int)
    hardware_averaging = True  # will use the accumulate acquisition mode if averaging is necessary
    params = comon_parameters + [
              {'title': 'Get Calibration:', 'name': 'get_calib', 'type': 'bool_push', 'value': False,
                'label': 'Update!'},
              {'title': 'Camera Settings:', 'name': 'camera_settings', 'type': 'group', 'expanded': True, 'children': [
                  {'title': 'Camera Models:', 'name': 'camera_model', 'type': 'list',
                   'limits': [f"{cam['model']}-{cam['serial']}" for cam in camera_list]},
                  {'title': 'Readout Modes:', 'name': 'readout', 'type': 'list',
                   'limits': Andor_Camera_ReadOut.names()[0:-1],
                   'value': 'FullVertBinning'},
                  {'title': 'Readout Speed:', 'name': 'readout_speed', 'type': 'list', 'limits': [],
                   'value': '0.05MHz'},
                  {'title': 'Readout Settings:', 'name': 'readout_settings', 'type': 'group', 'children': [
                      {'title': 'Single Track Settings:', 'name': 'st_settings', 'type': 'group', 'visible': False,
                       'children': [
                           {'title': 'Center pixel:', 'name': 'st_center', 'type': 'int', 'value': 1, 'default': 1,
                            'min': 1},
                           {'title': 'Height:', 'name': 'st_height', 'type': 'int', 'value': 1, 'default': 1, 'min': 1},
                       ]},
                      {'title': 'Multi Track Settings:', 'name': 'mt_settings', 'type': 'group', 'visible': False,
                       'children': [
                           {'title': 'Ntrack:', 'name': 'mt_N', 'type': 'int', 'value': 1, 'default': 1, 'min': 1},
                           {'title': 'Height:', 'name': 'mt_height', 'type': 'int', 'value': 1, 'default': 1, 'min': 1},
                           {'title': 'Offset:', 'name': 'mt_offset', 'type': 'int', 'value': 0, 'default': 0, 'min': 0},
                           {'title': 'Bottom:', 'name': 'mt_bottom', 'type': 'int', 'value': 0, 'default': 0, 'min': 0,
                            'readonly': True},
                           {'title': 'Gap:', 'name': 'mt_gap', 'type': 'int', 'value': 0, 'default': 0, 'min': 0,
                            'readonly': True},
                       ]},
                      {'title': 'Image Settings:', 'name': 'image_settings', 'type': 'group', 'visible': False,
                       'children': [
                           {'title': 'Binning along x:', 'name': 'bin_x', 'type': 'int', 'value': 1, 'default': 1,
                            'min': 1},
                           {'title': 'Binning along y:', 'name': 'bin_y', 'type': 'int', 'value': 1, 'default': 1,
                            'min': 1},
                           {'title': 'Start x:', 'name': 'im_startx', 'type': 'int', 'value': 1, 'default': 1,
                            'min': 0},
                           {'title': 'End x:', 'name': 'im_endx', 'type': 'int', 'value': 1024, 'default': 1024,
                            'min': 0},
                           {'title': 'Start y:', 'name': 'im_starty', 'type': 'int', 'value': 1, 'default': 1,
                            'min': 1},
                           {'title': 'End y:', 'name': 'im_endy', 'type': 'int', 'value': 256, 'default': 256,
                            'min': 1, },
                       ]},
                  ]},
                  {'title': 'Exposure (ms):', 'name': 'exposure', 'type': 'float', 'value': 0.01, 'default': 0.01,
                   'min': 0},

                  {'title': 'Image size:', 'name': 'image_size', 'type': 'group', 'children': [
                      {'title': 'Nx:', 'name': 'Nx', 'type': 'int', 'value': 0, 'default': 0, 'readonly': True},
                      {'title': 'Ny:', 'name': 'Ny', 'type': 'int', 'value': 0, 'default': 0, 'readonly': True},
                  ]},

                  {'title': 'Shutter Settings:', 'name': 'shutter', 'type': 'group', 'children': [
                      {'title': 'Open Shutter on:', 'name': 'shutter_type', 'type': 'list', 'value': 'high',
                       'limits': ['low', 'high']},
                      {'title': 'Shutter mode:', 'name': 'shutter_mode', 'type': 'list', 'value': 'Auto',
                       'limits': ['Auto', 'Always Opened', 'Always Closed', ]},
                      {'title': 'Closing time (ms):', 'name': 'shutter_closing_time', 'type': 'int', 'value': 0,
                       'tip': 'millisecs it takes to close'},
                      {'title': 'Opening time (ms):', 'name': 'shutter_opening_time', 'type': 'int', 'value': 10,
                       'tip': 'millisecs it takes to open'},
                  ]},
                  {'title': 'Temperature Settings:', 'name': 'temperature_settings', 'type': 'group', 'children': [
                      {'title': 'Set Point:', 'name': 'set_point', 'type': 'float', 'value': -60, 'default': -60},
                      {'title': 'Current value:', 'name': 'current_value', 'type': 'float', 'value': 0, 'default': 0,
                       'readonly': True},
                      {'title': 'Locked:', 'name': 'locked', 'type': 'led', 'value': False, 'default': False,
                       'readonly': True},
                  ]},
              ]},
              {'title': 'Shamrock Settings:', 'name': 'sham_settings', 'type': 'group', 'children': [
                    {'title': 'Spectro Settings:', 'name': 'spectro_settings', 'type': 'group', 'expanded': True,
                        'children': [
                        {'title': 'Spectro SN:', 'name': 'spectro_serialnumber', 'type': 'str', 'value': '',
                            'readonly': True},
                        {'title': 'Wavelength (nm):', 'name': 'spectro_wl', 'type': 'float', 'value': 600, 'min': 0,
                            'readonly': False},
                        {'title': 'Home Wavelength (nm):', 'name': 'spectro_wl_home', 'type': 'float', 'value': 600,
                            'min': 0,
                            'readonly': False},
                        {'title': 'Slit Width (um):', 'name': 'slit_width', 'type': 'float', 'value': 100, 'min': 0,
                            'readonly': False},
                        {'title': 'Input Port:', 'name': 'input_port', 'type': 'list'},
                        {'title': 'Output Port:', 'name': 'output_port', 'type': 'list'},
                        {'title': 'Grating Settings:', 'name': 'grating_settings', 'type': 'group', 'expanded': True,
                            'children': [
                                {'title': 'Grating:', 'name': 'grating', 'type': 'list'},
                                {'title': 'Lines (/mm):', 'name': 'lines', 'type': 'int', 'readonly': True},
                                {'title': 'Blaze WL (nm):', 'name': 'blaze', 'type': 'str', 'readonly': True},
                                {'title': 'Offset (steps):', 'name': 'grating_offset', 'type': 'int'},
                            ]},
                        {'title': 'Flip wavelength axis:', 'name': 'flip_wavelength', 'type': 'bool', 'value': False,
                            'visible': True},
                        {'title': 'Go to zero order:', 'name': 'zero_order', 'type': 'bool'},
                    ]},
              ]},
    ]


    def ini_attributes(self):
        self.controller: ShamrockCCDCompo = None

        self.x_axis: Axis = None
        self.is_calibrated = False

        self.x_axis = None
        self.y_axis = None
        self.data = None
        self.CCDSIZEX, self.CCDSIZEY = (None, None)
        self.data_pointer = None
        self.camera_done = False
        self.acquirred_image = None
        self.callback_thread = None
        self.Naverage = None
        self.data_shape = None  # 'Data2D' if sizey != 1 else 'Data1D'
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.updated_timer)


    def commit_settings(self, param):

        if param.name() == 'flip_wavelength':
            self.get_xaxis()

        elif param.name() == 'set_point':
            self.controller.andor.SetTemperature(param.value())

        elif param.name() == 'readout' or param.name() in iter_children(
                self.settings.child('camera_settings', 'readout_settings')):
            self.update_read_mode()

        elif param.name() == 'readout_speed':
            self.update_read_speed()

        elif param.name() == 'exposure':
            self.controller.andor.SetExposureTime(param.value() / 1000)  # temp should be in s
            (err, timings) = self.controller.andor.GetAcquisitionTimings()
            self.settings.child('camera_settings', 'exposure').setValue(timings['exposure'] * 1000)
            QtWidgets.QApplication.processEvents()

        elif param.name() in iter_children(self.settings.child('camera_settings', 'shutter'), []):
            self.set_shutter()

        elif param.name() in iter_children(
                self.settings.child('camera_settings', 'readout_settings', 'image_settings')):
            if self.settings.child('camera_settings', 'readout').value() == 'Image':
                self.set_image_area()

        elif param.name() == 'grating':
            index_grating = self.grating_list.index(param.value())
            self.get_set_grating(index_grating)
            self.set_wavelength(self.settings.child('sham_settings', 'spectro_settings', 'spectro_wl').value())

        elif param.name() == 'grating_offset':
            err, ind_grating = self.controller.shamrock.GetGratingSR(0)
            offset = int(self.settings.child('sham_settings', 'spectro_settings', 'grating_settings', 'grating_offset').value())
            err = self.controller.shamrock.SetGratingOffset(0, ind_grating, offset)

        elif param.name() == 'spectro_wl':
            self.set_wavelength(param.value())

        elif param.name() == 'zero_order':
            if param.value():
                param.setValue(False)
                self.emit_status(ThreadCommand('show_splash', "Moving to zero order, please wait!"))
                err = self.controller.shamrock.GotoZeroOrderSR(0)
                if err != 'SHAMROCK_SUCCESS':
                    raise Exception(err)
                self.emit_status(ThreadCommand('close_splash'))

        elif param.name() == 'slit_width':
            self.set_slitwidth(self.controller.shamrock.get_input_port(0), param.value())

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

        self.controller = self.ini_detector_init(old_controller=controller,
                                                        new_controller=ShamrockCCDCompo())

        print("Controller:", self.controller)
        print("Andor:", self.controller.andor)
        print("Shamrock:", self.controller.shamrock)

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

        initialized = True

        self.setCalibration()
        return '', initialized


    def ini_camera(self):


        #  %%%%%% Get image size and current binning
        # get info from camera
        model_param = self.settings.child('camera_settings', 'camera_model')
        cam_index = model_param.opts['limits'].index(model_param.value())
        self.controller.andor.SetCurrentCamera(camera_list[cam_index]['handle'])

        self.CCDSIZEX, self.CCDSIZEY = self.controller.andor.GetDetector()

        self.settings.child('camera_settings', 'readout_settings',
                            'st_settings', 'st_center').setLimits((1, self.CCDSIZEY))
        self.settings.child('camera_settings', 'readout_settings',
                            'st_settings', 'st_height').setLimits((1, self.CCDSIZEY))
        self.settings.child('camera_settings', 'readout_settings', 'image_settings', 'im_endy').setValue(self.CCDSIZEY)
        self.settings.child('camera_settings', 'readout_settings', 'image_settings',
                            'im_endy').setOpts(max=self.CCDSIZEY, default=self.CCDSIZEY)
        self.settings.child('camera_settings', 'readout_settings', 'image_settings', 'im_endx').setValue(self.CCDSIZEX)
        self.settings.child('camera_settings', 'readout_settings', 'image_settings',
                            'im_endx').setOpts(max=self.CCDSIZEX, default=self.CCDSIZEX)

        # get available readout speeds
        self.settings.child('camera_settings', 'readout_speed').setLimits(self.get_speeds_string())

        # get max exposure range
        err, maxexpo = self.controller.andor.GetMaximumExposure()
        if err == 'DRV_SUCCESS':
            self.settings.child('camera_settings', 'exposure').setLimits((0, maxexpo * 1000))

        # set default read mode (full vertical binning)
        self.update_read_mode()

        # %%%%%%% Set and Get temperature from camera
        # get temperature range
        (err, temp_range) = self.controller.andor.GetTemperatureRange()
        if err == "DRV_SUCCESS":
            self.settings.child('camera_settings', 'temperature_settings', 'set_point').setLimits(
                (temp_range[0], temp_range[1]))

        self.set_shutter()

        if not self.controller.andor.IsCoolerOn():  # gets 0 or 1
            self.controller.andor.CoolerON()

        self.controller.andor.SetTemperature(
            self.settings.child('camera_settings', 'temperature_settings', 'set_point').value())
        locked_status, temp = self.controller.andor.GetTemperature()
        self.settings.child('camera_settings', 'temperature_settings', 'current_value').setValue(temp)
        self.settings.child('camera_settings', 'temperature_settings', 'locked').setValue(
            locked_status == 'DRV_TEMP_STABILIZED')
        # set timer to update temperature info from controller
        self.timer.start(2000)

        callback = AndorCallback(self.controller.andor.WaitForAcquisition)
        self.callback_thread = QtCore.QThread()
        callback.moveToThread(self.callback_thread)
        callback.data_sig.connect(
            self.emit_data)  # when the wait for acquisition returns (with data taken), emit_data will be fired

        self.callback_signal.connect(callback.wait_for_acquisition)
        self.callback_thread.callback = callback
        self.callback_thread.start()


    def update_read_mode(self):
        read_mode = Andor_Camera_ReadOut[self.settings.child('camera_settings', 'readout').value()].value
        err = self.controller.andor.SetReadMode(read_mode)
        if err != 'DRV_SUCCESS':
            self.emit_status(ThreadCommand('Update_Status', [err, 'log']))
        else:
            self.settings.child('camera_settings', 'readout_settings').show()
            if read_mode == 0:  # FVB:
                self.settings.child('camera_settings', 'readout_settings').hide()
                self.settings.child('camera_settings', 'image_size', 'Nx').setValue(self.CCDSIZEX)
                self.settings.child('camera_settings', 'image_size', 'Ny').setValue(1)


            elif read_mode == 3:  # single track
                self.settings.child('camera_settings', 'readout_settings', 'mt_settings').hide()
                self.settings.child('camera_settings', 'readout_settings', 'st_settings').show()
                self.settings.child('camera_settings', 'readout_settings', 'image_settings').hide()

                err = self.set_single_track_area()

            elif read_mode == 1:  # multitrack
                self.settings.child('camera_settings', 'readout_settings', 'mt_settings').show()
                self.settings.child('camera_settings', 'readout_settings', 'st_settings').hide()
                self.settings.child('camera_settings', 'readout_settings', 'image_settings').hide()

                err = self.set_multi_track_area()



            elif read_mode == 2:  # random
                err = 'Random mode not implemented yet'

            elif read_mode == 4:  # image
                self.settings.child('camera_settings', 'readout_settings', 'mt_settings').hide()
                self.settings.child('camera_settings', 'readout_settings', 'st_settings').hide()
                self.settings.child('camera_settings', 'readout_settings', 'image_settings').show()

                self.set_image_area()


            elif read_mode == 5:  # croped
                err = 'Croped mode not implemented yet'
            self.emit_status(ThreadCommand('Update_Status', [err, 'log']))

            (err, timings) = self.controller.andor.GetAcquisitionTimings()
            self.settings.child('camera_settings', 'exposure').setValue(timings['exposure'] * 1000)

            self.x_axis = self.get_xaxis()
            self.y_axis = self.get_yaxis()

    def get_speeds_string(self):

        get_speeds = self.controller.andor.GetHSSpeed()
        speeds_str_arr = []

        for speed in get_speeds:
            speed_str = str("{:.2f}".format(speed))
            speeds_str_arr.append(speed_str + "MHz")

        return speeds_str_arr

    def set_speed_index(self, value):

        speeds_arr = self.get_speeds_string()
        return speeds_arr.index(value)

    def update_read_speed(self):
        read_speed_val = self.settings.child('camera_settings', 'readout_speed').value()

        err = self.controller.andor.SetHSSpeed(self.set_speed_index(read_speed_val))
        if err != 'DRV_SUCCESS':
            self.emit_status(ThreadCommand('Update_Status', [err, 'log']))

    def set_multi_track_area(self):

        N = self.settings.child('camera_settings', 'readout_settings', 'mt_settings', 'mt_N').value()
        height = self.settings.child('camera_settings', 'readout_settings', 'mt_settings', 'mt_height').value()
        offset = self.settings.child('camera_settings', 'readout_settings', 'mt_settings', 'mt_offset').value()
        (err, bottom, gap) = self.controller.andor.SetMultiTrack(N, height, offset)
        self.settings.child('camera_settings', 'readout_settings', 'mt_settings', 'mt_bottom').setValue(bottom)
        self.settings.child('camera_settings', 'readout_settings', 'mt_settings', 'mt_gap').setValue(gap)
        if err == 'DRV_SUCCESS':
            self.settings.child('camera_settings', 'image_size', 'Nx').setValue(self.CCDSIZEX)
            self.settings.child('camera_settings', 'image_size', 'Ny').setValue(N)
        return err

    def set_single_track_area(self):
        center = self.settings.child('camera_settings', 'readout_settings', 'st_settings', 'st_center').value()
        height = self.settings.child('camera_settings', 'readout_settings', 'st_settings', 'st_height').value()
        err = self.controller.andor.SetSingleTrack(center, height)
        if err == 'DRV_SUCCESS':
            self.settings.child('camera_settings', 'image_size', 'Nx').setValue(self.CCDSIZEX)
            self.settings.child('camera_settings', 'image_size', 'Ny').setValue(1)

        return err

    def set_image_area(self):

        binx = self.settings.child('camera_settings', 'readout_settings', 'image_settings', 'bin_x').value()
        biny = self.settings.child('camera_settings', 'readout_settings', 'image_settings', 'bin_y').value()
        startx = self.settings.child('camera_settings', 'readout_settings', 'image_settings', 'im_startx').value()
        endx = self.settings.child('camera_settings', 'readout_settings', 'image_settings', 'im_endx').value()
        starty = self.settings.child('camera_settings', 'readout_settings', 'image_settings', 'im_starty').value()
        endy = self.settings.child('camera_settings', 'readout_settings', 'image_settings', 'im_endy').value()
        err = self.controller.andor.SetImage(binx, biny, startx, endx, starty, endy)
        if err == 'DRV_SUCCESS':
            self.settings.child('camera_settings', 'image_size', 'Nx').setValue(int((endx - startx + 1) / binx))
            self.settings.child('camera_settings', 'image_size', 'Ny').setValue(int((endy - starty + 1) / biny))

        return err

    def get_ROI_size_x(self):
        self.CCDSIZEX, self.CCDSIZEY = self.controller.andor.GetDetector()
        return self.CCDSIZEX

    def get_pixel_size(self):
        err, (width, height) = self.controller.andor.GetPixelSize()
        if err == 'DRV_SUCCESS':
            return width, height
        else:
            pass
        return 0., 0.
    
    def set_shutter(self):
        typ = self.settings.child('camera_settings', 'shutter', 'shutter_type').opts['limits'].index(
                                        self.settings.child('camera_settings', 'shutter', 'shutter_type').value())
        mode = self.settings.child('camera_settings', 'shutter', 'shutter_mode').opts['limits'].index(
                                        self.settings.child('camera_settings', 'shutter', 'shutter_mode').value())

        self.controller.andor.SetShutter(typ, mode, self.settings.child('camera_settings', 'shutter', 'shutter_closing_time').value(),
                                          self.settings.child('camera_settings', 'shutter', 'shutter_opening_time').value())

    def updated_timer(self):
        """

        """
        locked_status, temp = self.controller.andor.GetTemperature()
        self.settings.child('camera_settings', 'temperature_settings', 'current_value').setValue(temp)
        self.settings.child('camera_settings', 'temperature_settings', 'locked').setValue(
            locked_status == 'DRV_TEMP_STABILIZED')

    def get_yaxis(self):
        """
            Obtain the vertical axis of the image.

            Returns
            -------
            1D numpy array
                Contains a vector of integer corresponding to the vertical camera pixels.
        """
        if self.controller.andor is not None:

            Ny = self.settings.child('camera_settings', 'image_size', 'Ny').value()
            self.y_axis = Axis(data=np.linspace(0, Ny - 1, Ny, dtype=int), label='Pixels', index=0)
        else:
            raise (Exception('Camera not defined'))
        return self.y_axis
    
    
    def ini_spectro(self):
        
        self.settings.child('sham_settings', 'spectro_settings', 'spectro_serialnumber').setValue(
            self.controller.shamrock.GetSerialNumberSR(0)[1].decode())

        # get grating info
        (err, Ngratings) = self.controller.shamrock.GetNumberGratingsSR(0)
        self.grating_list = []
        for ind_grating in range(1, Ngratings + 1):
            (err, lines, blaze, home, offset) = self.controller.shamrock.GetGratingInfoSR(0, ind_grating)
            self.grating_list.append(str(int(lines)))

        self.settings.child('sham_settings', 'spectro_settings', 'grating_settings', 'grating').setLimits(self.grating_list)
        err, ind_grating = self.controller.shamrock.GetGratingSR(0)
        self.settings.child('sham_settings', 'spectro_settings', 'grating_settings', 'grating').setValue(
            self.grating_list[ind_grating - 1])

        self.get_set_grating(ind_grating - 1)

        # idem pour les ports (PV/L2C/) :######
        if self.controller.shamrock.FlipperMirrorIsPresent(0, 1)[1] == 1:
            self.inputport_list = ["INPUT_FRONT", "INPUT_SIDE"]
            self.settings.child('sham_settings', 'spectro_settings', 'input_port').setLimits(self.inputport_list)
            err, inputport_index = self.controller.shamrock.get_input_port(0)
            self.settings.child('sham_settings', 'spectro_settings', 'input_port').setValue(self.inputport_list[inputport_index])
            self.set_inputport(inputport_index)
        else :
            self.inputport_list = ["SINGLE_INPUT_PORT"]
            self.settings.child('sham_settings', 'spectro_settings', 'input_port').setLimits(self.inputport_list)

        if self.controller.shamrock.FlipperMirrorIsPresent(0, 2)[1] == 1:
            self.outputport_list = ["OUTPUT_FRONT", "OUTPUT_SIDE"]
            self.settings.child('sham_settings', 'spectro_settings', 'output_port').setLimits(self.outputport_list)
            err, outputport_index = self.controller.shamrock.get_output_port(0)
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
        err = self.controller.shamrock.SetGratingSR(0, ind_grating + 1)
        err, ind_grating = self.controller.shamrock.GetGratingSR(0)

        (err, lines, blaze, home, offset) = self.controller.shamrock.GetGratingInfoSR(0, ind_grating)
        self.settings.child('sham_settings', 'spectro_settings', 'grating_settings', 'grating').setValue(
            self.grating_list[ind_grating - 1])
        self.settings.child('sham_settings', 'spectro_settings', 'grating_settings', 'lines').setValue(lines)
        self.settings.child('sham_settings', 'spectro_settings', 'grating_settings', 'blaze').setValue(blaze)
        self.settings.child('sham_settings', 'spectro_settings', 'grating_settings', 'grating_offset').setValue(offset)

        (err, wl_min, wl_max) = self.controller.shamrock.GetWavelengthLimitsSR(0, ind_grating)

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
        err = self.controller.shamrock.SetWavelengthSR(0, wavelength)
        self.emit_status(ThreadCommand('close_splash'))

        if err != 'SHAMROCK_SUCCESS':
            raise IOError(err)

        self.get_wavelength()

    def get_wavelength(self):
        err, wl = self.controller.shamrock.GetWavelengthSR(0)
        if err == "SHAMROCK_SUCCESS":
            self.settings.child('sham_settings', 'spectro_settings', 'spectro_wl').setValue(wl)
        return float(wl)

    def set_slitwidth(self, index, slitwidth):
        self.emit_status(ThreadCommand('show_splash', "Setting slit width, please wait!"))
        err = self.controller.shamrock.SetAutoSlitWidthSR(0, index, slitwidth)
        self.emit_status(ThreadCommand('close_splash'))

        if err != 'SHAMROCK_SUCCESS':
            raise IOError(err)

        self.get_slitwidth(index)

    def get_slitwidth(self,index):
        err, sw = self.controller.shamrock.GetAutoSlitWidthSR(0,index)
        if err == "SHAMROCK_SUCCESS":
            self.settings.child('sham_settings', 'spectro_settings', 'slit_width').setValue(sw)
        return float(sw)

    def set_inputport(self, index_inputport):
        self.emit_status(ThreadCommand('show_splash', "Setting input port, please wait!"))
        if index_inputport == 0 :
            strinputport = "INPUT_FRONT"
        elif index_inputport == 1 :
            strinputport = "INPUT_SIDE"
        err = self.controller.shamrock.set_input_port(0, strinputport)
        self.emit_status(ThreadCommand('close_splash'))

        if err != 'SHAMROCK_SUCCESS':
            raise IOError(err)

        self.get_inputport()

    def get_inputport(self):
        err, inputport = self.controller.shamrock.get_input_port(0)

        if err == "SHAMROCK_SUCCESS":
            self.settings.child('sham_settings', 'spectro_settings', 'input_port').setValue(self.inputport_list[inputport])

        return self.inputport_list[inputport]


    def set_outputport(self, index_outputport):
        self.emit_status(ThreadCommand('show_splash', "Setting output port, please wait!"))
        if index_outputport == 0:
            stroutputport = "OUTPUT_FRONT"
        elif index_outputport == 1:
            stroutputport = "OUTPUT_SIDE"
        err = self.controller.shamrock.set_output_port(0, stroutputport)
        self.emit_status(ThreadCommand('close_splash'))

        if err != 'SHAMROCK_SUCCESS':
            raise IOError(err)

        self.get_outputport()

    def get_outputport(self):
        err, outputport = self.controller.shamrock.get_output_port(0)

        if err == "SHAMROCK_SUCCESS":
            self.settings.child('sham_settings', 'spectro_settings', 'output_port').setValue(self.outputport_list[outputport])

        return self.outputport_list[outputport]
    
    
    def setCalibration(self):
        #setNpixels
        width, height = self.get_pixel_size()
        err = self.controller.shamrock.SetNumberPixelsSR(0, self.get_ROI_size_x())
        err = self.controller.shamrock.SetPixelWidthSR(0, width)
        self.get_wavelength()
        self.x_axis = self.get_xaxis()


    def getCalibration(self):

        (err, calib) = self.controller.shamrock.GetCalibrationSR(0, self.get_ROI_size_x())
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

        if self.controller.shamrock is None or np.abs(self.settings.child('sham_settings', 'spectro_settings', 'spectro_wl').value()) < 1e-3:
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
        
        try:
            self.controller.andor.CancelWait()  # first cancel the waitacquistion (if any)
            QtWidgets.QApplication.processEvents()
            self.controller.andor.AbortAcquisition()  # abort the camera actions
        except:
            pass
        return ""


    def close(self):

        if self.controller.andor is not None:
            err, temp = self.controller.andor.GetTemperature()
            print(temp)
            if temp < -20.:
                print(
                    "Camera temperature is still at {:d}°C. Closing it now may damage it! The cooling will be maintained "
                    "while shutting down camera. Keep it power plugged!!!".format(
                        temp))
                self.controller.andor.SetCoolerMode(1)
            self.timer.stop()
            self.controller.andor.close()

        if self.controller.shamrock is not None:
            self.controller.shamrock.close()


    def prepare_data(self):
        sizex = self.settings.child('camera_settings', 'image_size', 'Nx').value()
        sizey = self.settings.child('camera_settings', 'image_size', 'Ny').value()

        # Initialize data: self.data for the memory to store new data and self.data_average to store the average data
        image_size = sizex * sizey

        # code original : self.data = np.zeros((image_size,), dtype=int)
        self.data = np.zeros((image_size,), dtype=np.uint32)

        self.data_pointer = self.data.ctypes.data_as(ctypes.c_void_p)

        data_shape = 'Data2D' if sizey != 1 else 'Data1D'
        if data_shape != self.data_shape:
            self.data_shape = data_shape
            # init the viewers
            self.dte_signal_temp.emit(DataToExport('Camera',
                                                   data=[DataFromPlugins(name='Camera ',
                                                               data=[np.squeeze(
                                                                   self.data.reshape((sizey, sizex)).astype(float))],
                                                               dim=self.data_shape)]))


    def grab_data(self, Naverage=1, **kwargs):
        """
            Start new acquisition in two steps :
                * Initialize data: self.data for the memory to store new data and self.data_average to store the average data
                * Start acquisition with the given exposure in ms, in "1d" or "2d" mode

            =============== =========== =============================
            **Parameters**   **Type**    **Description**
            Naverage         int         Number of images to average
            =============== =========== =============================

            See Also
            --------
            daq_utils.ThreadCommand
        """
        
        if not self.is_calibrated:
            self.get_xaxis()
        
        try:
            self.camera_done = False

            self.ind_grabbed = 0  # to keep track of the current image in the average
            self.Naverage = Naverage  #

            self.prepare_data()
            if Naverage == 1:
                self.controller.andor.SetAcquisitionMode(1)
            else:
                self.controller.andor.SetAcquisitionMode(2)
                self.controller.andor.SetNumberAccumulations(Naverage)

            self.controller.andor.SetExposureTime(
                self.settings.child('camera_settings', 'exposure').value() / 1000)  # temp should be in s
            (err, timings) = self.controller.andor.GetAcquisitionTimings()
            self.settings.child('camera_settings', 'exposure').setValue(timings['exposure'] * 1000)
            # Start acquisition with the given exposure in ms, in "1d" or "2d" mode
            self.controller.andor.StartAcquisition()
            self.callback_signal.emit(self.Naverage)  # will trigger the wait for acquisition
            
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status', [str(e), "log"]))
    

    def emit_data(self):
        try:
            self.ind_grabbed += 1
            sizey = self.settings.child('camera_settings', 'image_size', 'Ny').value()
            sizex = self.settings.child('camera_settings', 'image_size', 'Nx').value()
            self.controller.andor.GetAcquiredDataNumpy(self.data_pointer, sizex * sizey)
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
