

from pymodaq.control_modules.move_utility_classes import (DAQ_Move_base, comon_parameters_fun,
                                                          main, DataActuatorType, DataActuator)
from pymodaq_utils.utils import ThreadCommand
from pymodaq_plugins_andor.hardware.shamrockCCD_compo import ShamrockCCDCompo


class DAQ_Move_Shamrock_SlaveOnly(DAQ_Move_base):

    _controller_units = 'nm'
    is_multiaxes = True
    axes_names = ['Wavelength']  # list of strings of the multiaxes
    _epsilon = 0.1
    data_actuator_type = DataActuatorType.DataActuator

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
            initialized = True

        else:
            self.controller = controller
            initialized = True

        print(controller)
        self.shamrock_controller = controller.shamrock
        self.settings.child('spectro_serialnumber').setValue(
            self.shamrock_controller.GetSerialNumberSR(0)[1].decode())

        return '', initialized

    def set_wavelength(self, wavelength):
        self.emit_status(ThreadCommand('show_splash', "Setting wavelength, please wait!"))
        err = self.shamrock_controller.SetWavelengthSR(0, wavelength)
        if err != 'SHAMROCK_SUCCESS':
            raise Exception(err)
        self.emit_status(ThreadCommand('close_splash'))
        self.get_wavelength()

    def get_wavelength(self):
        err, wl = self.shamrock_controller.GetWavelengthSR(0)
        if err != 'SHAMROCK_SUCCESS':
            raise Exception(err)
        return float(wl)

    def get_actuator_value(self):
        """Get the current position from the hardware with scaling conversion.

        Returns
        -------
        float: The position obtained after scaling conversion.
        """
        pos = DataActuator(data=self.get_wavelength(),
                           units=self.axis_unit)
        pos = self.get_position_with_scaling(pos)
        return pos

    def move_abs(self, value):
        """ Move the actuator to the absolute target defined by position

        Parameters
        ----------
        value: (flaot) value of the absolute target positioning
        """

        value = self.check_bound(value)  # if user checked bounds, the defined bounds are applied here
        self.target_value = value
        value = self.set_position_with_scaling(value)

        self.set_wavelength(value.value(self.axis_unit))
        self.emit_status(ThreadCommand('Update_Status', ['moved wl absolute']))

    def move_rel(self, value: DataActuator):
        """ Move the actuator to the relative target actuator value defined by value

        Parameters
        ----------
        value: (float) value of the relative target positioning
        """
        value = self.check_bound(self.current_position + value) - self.current_position
        self.target_value = value + self.current_position

        self.set_wavelength(self.target_value.value(self.axis_unit))
        self.emit_status(ThreadCommand('Update_Status', ['moved wl relative']))

    def move_home(self):
        """Call the reference method of the controller"""

        self.move_abs(self.settings['spectro_wl_home'])
        self.emit_status(ThreadCommand('Update_Status', ['Some info you want to log']))

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
