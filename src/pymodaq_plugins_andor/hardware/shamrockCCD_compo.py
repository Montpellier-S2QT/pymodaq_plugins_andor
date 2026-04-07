from pymodaq_plugins_andor.hardware.andor_sdk2 import sdk2
from pymodaq_plugins_andor.hardware import shamrock_sdk

class ShamrockCCDCompo:

    def __init__(self):
        self.andor = sdk2.AndorSDK()
        self.shamrock = shamrock_sdk.ShamrockSDK()

