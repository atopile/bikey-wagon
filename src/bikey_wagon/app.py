# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from numpy import isin

# from bikey_wagon.library.my_library_module import MyLibraryModule
# from bikey_wagon.modules.my_application_module import MyApplicationModule
from bikey_wagon.library.ESP32_S3_WROOM_1_N16R8 import ESP32_S3_WROOM_1_N16R8_Kit
from bikey_wagon.library.DRV8300 import DRV8300PowerStage
from faebryk.core.core import Module
from faebryk.core.util import get_node_children_all
from faebryk.library.Switch import _TSwitch
from faebryk.libs.picker.jlcpcb.pickers import StaticJLCPCBPartPicker

logger = logging.getLogger(__name__)

"""
This file is for the top-level application modules.
This should be the entrypoint for collaborators to start in to understand your project.
Treat it as the high-level design of your project.
Avoid putting any generic or reusable application modules here.
Avoid putting any low-level modules or parameter specializations here.
"""


class MyApp(Module):
    def __init__(self) -> None:
        super().__init__()

        # modules ------------------------------------
        class _NODEs(Module.NODES()):
            # submodule = MyApplicationModule()
            # my_part = MyLibraryModule()
            # pass
            r1 = F.Resistor()
            esp32 = ESP32_S3_WROOM_1_N16R8_Kit()
            pwr_stage = DRV8300PowerStage()

        class _PARAMs(Module.PARAMS()):
            pass

        self.NODEs = _NODEs(self)
        self.PARAMs = _PARAMs(self)

        # net names ----------------------------------
        nets = {
            # "in_5v": ...power.IFs.hv,
            # "gnd": ...power.IFs.lv,
        }
        for net_name, mif in nets.items():
            net = F.Net.with_name(net_name)
            net.IFs.part_of.connect(mif)

        # parametrization ----------------------------
        self.NODEs.r1.PARAMs.resistance.merge(F.Range(900, 1100))

        # specialize

        # default components for accessories
        for n in get_node_children_all(self):
            if isinstance(n, _TSwitch):
                F.has_multi_picker.add_to_module(
                    n,
                    float("inf"),
                    StaticJLCPCBPartPicker(
                        mfr="BZCN", mfr_pn="TSB008A2530A", lcsc_pn="C2888954"
                    ),
                )

        # set global params
        self.NODEs.pwr_stage.PARAMs.phase_current.merge(F.Range(50, 200))
