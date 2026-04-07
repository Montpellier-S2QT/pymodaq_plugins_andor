
from easydict import EasyDict as edict
from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, comon_parameters_fun, main
from pymodaq_utils.utils import ThreadCommand
from pymodaq_plugins_andor.hardware.shamrockCCD_compo import ShamrockCCDCompo





class DAQ_Move_ShamrockMultispec_SlaveOnly(DAQ_Move_base):

    _controller_units = 'nm'
    is_multiaxes = True
    axes_names = ['Wavelength']  # "list of strings of the multiaxes
    _epsilon = 0.1

    params = [{'title': 'Spectro SN:', 'name': 'spectro_serialnumber', 'type': 'str', 'value': '',
                'readonly': True},
              {'title': 'Home Wavelength (nm):', 'name': 'spectro_wl_home', 'type': 'float', 'value': 600, 'min': 0,
               'readonly': False},

        ] + comon_parameters_fun(is_multiaxes, axes_names, epsilon=_epsilon)

    def commit_settings(self, param):
        """
            | Activate parameters changes on the hardware from parameter's name.
            |

        """
        pass

    def ini_stage(self, controller=None):
        """Actuator communication initialization

        Parameters
        ----------
        controller: (object) custom object of a PyMoDAQ plugin (Slave case). None if only one actuator by controller (Master case)

        Returns
        -------
        self.status (edict): with initialization status: three fields:
            * info (str)
            * controller (object) initialized controller
            *initialized: (bool): False if initialization failed otherwise True
        """
        if self.is_master:  # is needed when controller is master
            self.controller = ShamrockCCDCompo()

        else:
            self.controller = controller
            initialized = True

        self.settings.child('spectro_serialnumber').setValue(
            self.controller.shamrock.GetSerialNumberSR(0)[1].decode())

        initialized = True
        return '', initialized

    def set_wavelength(self, wavelength):
        self.emit_status(ThreadCommand('show_splash', "Setting wavelength, please wait!"))
        err = self.controller.shamrock.SetWavelengthSR(0, wavelength)
        self.emit_status(ThreadCommand('close_splash'))

        if err != 'SHAMROCK_SUCCESS':
            raise IOError(err)

        self.get_wavelength()

    def get_wavelength(self):
        err, wl = self.controller.shamrock.GetWavelengthSR(0)
        return float(wl)

    def get_actuator_value(self):
        """Get the current position from the hardware with scaling conversion.

        Returns
        -------
        float: The position obtained after scaling conversion.
        """
        pos = self.get_wavelength()
        ##

        pos = self.get_position_with_scaling(pos)
        return pos

    def move_abs(self, position):
        """ Move the actuator to the absolute target defined by position

        Parameters
        ----------
        position: (flaot) value of the absolute target positioning
        """

        position = self.check_bound(position)  # if user checked bounds, the defined bounds are applied here
        position = self.set_position_with_scaling(position)  # apply scaling if the user specified one

        self.set_wavelength(position)

        ##############################

        self.target_position = position
        self.poll_moving()  # start a loop to poll the current actuator value and compare it with target position

    def move_rel(self, position):
        """ Move the actuator to the relative target actuator value defined by position

        Parameters
        ----------
        position: (flaot) value of the relative target positioning
        """
        position = self.check_bound(self.current_position + position) - self.current_position
        self.target_position = position + self.current_position

        self.set_wavelength(self.target_position)
        ##############################

        self.poll_moving()

    def move_home(self):
        """

        """
        self.move_abs(self.settings.child('spectro_wl_home').value())

    def stop_motion(self):
        """
        Call the specific move_done function (depending on the hardware).

        See Also
        --------
        move_done
        """

        self.move_done()  # to let the interface know the actuator stopped. Direct call as the setwavelength call is
        # blocking anyway

    def close(self):
        """

        """
        pass

    def stop(self):
        pass


if __name__ == '__main__':
    main(__file__, True)
