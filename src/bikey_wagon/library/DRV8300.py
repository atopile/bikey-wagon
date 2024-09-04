# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Module
from faebryk.core.util import tunnel
from faebryk.library import _F as F
from faebryk.library.can_attach_to_footprint_via_pinmap import (
    can_attach_to_footprint_via_pinmap,
)
from faebryk.library.can_be_decoupled import can_be_decoupled
from faebryk.library.Capacitor import Capacitor
from faebryk.library.has_datasheet_defined import has_datasheet_defined
from faebryk.library.has_defined_descriptive_properties import (
    has_defined_descriptive_properties,
)
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.has_single_electric_reference_defined import (
    has_single_electric_reference_defined,
)
from faebryk.library.MOSFET import MOSFET
from faebryk.library.NetTie import NetTie
from faebryk.library.Resistor import Resistor
from faebryk.libs.picker.picker import DescriptiveProperties
from faebryk.libs.units import k, n
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class DRV8300(Module):
    @classmethod
    def NODES(cls):
        # submodules
        class _NODES(super().NODES()):
            pass

        return _NODES

    @classmethod
    def PARAMS(cls):
        # parameters
        class _PARAMS(super().PARAMS()):
            pass

        return _PARAMS

    @classmethod
    def IFS(cls):
        # interfaces
        class _IFS(super().IFS()):
            gate_power = F.ElectricPower()
            mode = F.ElectricLogic()
            high_gate_inputs = times(3, F.ElectricLogic)
            low_gate_inputs = times(3, F.ElectricLogic)
            high_gate_outputs = times(3, F.Electrical)
            low_gate_outputs = times(3, F.Electrical)
            voltage_sense = times(3, F.Electrical)
            bootstrap = times(3, F.Electrical)
            deadtime = F.Electrical()

        return _IFS

    def __init__(self):
        # boilerplate
        super().__init__()
        self.IFs = self.IFS()(self)
        self.PARAMs = self.PARAMS()(self)
        self.NODEs = self.NODES()(self)

        # connections

        # traits
        x = self.IFs
        gnd = x.gate_power.IFs.lv
        self.pinmap = {
            "1": x.low_gate_inputs[0].IFs.signal,  # input_low_a.io
            "2": x.low_gate_inputs[1].IFs.signal,  # input_low_b.io
            "3": x.low_gate_inputs[2].IFs.signal,  # input_low_c.io
            "4": x.gate_power.IFs.hv,  # power_gate.vcc
            "5": x.mode.IFs.signal,  # mode.io
            "6": gnd,  # power_gate.gnd
            # 7, 8 unconnected
            "9": x.low_gate_outputs[2],  # output_low_c.io
            "10": x.low_gate_outputs[1],  # output_low_b.io
            "11": x.low_gate_outputs[0],  # output_low_a.io
            "12": x.voltage_sense[2],  # output_sense_c.io
            "13": x.high_gate_outputs[2],  # output_high_c.io
            "14": x.bootstrap[2],  # boostrap_c.io
            "15": x.voltage_sense[1],  # output_sense_b.io
            "16": x.high_gate_outputs[1],  # output_high_b.io
            "17": x.bootstrap[1],  # boostrap_b.io
            "18": x.voltage_sense[0],  # output_sense_a.io
            "19": x.high_gate_outputs[0],  # output_high_a.io
            "20": x.bootstrap[0],  # boostrap_a.io
            "21": x.deadtime,  # deadtime.io
            "22": x.high_gate_inputs[0].IFs.signal,  # input_high_a.io
            "23": x.high_gate_inputs[1].IFs.signal,  # input_high_b.io
            "24": x.high_gate_inputs[2].IFs.signal,  # input_high_c.io
            "25": gnd  # Thermal pad - power_gate.gnd
        }
        self.add_trait(can_attach_to_footprint_via_pinmap(self.pinmap))

        self.add_trait(
            has_datasheet_defined(
                "https://www.ti.com/lit/ds/symlink/drv8300.pdf"
            )
        )
        self.add_trait(
            has_defined_descriptive_properties(
                {
                    DescriptiveProperties.manufacturer: "Texas Instruments",
                    DescriptiveProperties.partno: "DRV8300DRGER",
                }
            )
        )

        self.add_trait(has_designator_prefix_defined("U"))

        ref = F.ElectricLogic.connect_all_module_references(self)
        self.add_trait(has_single_electric_reference_defined(ref))
        ref.connect(self.IFs.gate_power)

        # constraints
        x.gate_power.PARAMs.voltage.merge(F.Range(5, 20))


class DRV8300PowerStage(Module):
    def __init__(self):
        super().__init__()

        class _NODES(super().NODES()):
            ic = DRV8300()
            fets = times(6, MOSFET)
            gate_ilim_resistors = times(6, Resistor)
            shunts = times(3, Resistor)
            netties = times(6, lambda: NetTie(0.5))
            bootstrap_caps = times(3, Capacitor)
            deadtime_resistor = Resistor()

        self.NODEs = _NODES(self)

        _ifs = self.NODEs.ic.IFs

        class _PARAMS(super().PARAMS()):
            phase_current = F.TBD[float]()
            deadtime = F.Range(200 * n, 2000 * n)

        self.PARAMs = _PARAMS(self)

        class _IFS(super().IFS()):
            motor_power = F.ElectricPower()
            gate_power = tunnel(_ifs.gate_power)
            high_gate_inputs = tunnel(_ifs.high_gate_outputs)
            low_gate_inputs = tunnel(_ifs.low_gate_outputs)
            motor = times(3, F.Electrical)

            # TODO: check that the right interfaces are used, depending on config
            shunts = times(3, F.DifferentialPair)

        self.IFs = _IFS(self)

        self._3pwm_mode: bool | None = None

        # connections
        _n = self.NODEs
        _i = self.IFs
        for phase in range(3):
            # power stack
            _i.motor_power.IFs.hv.connect_via(
                [
                    _n.fets[phase*2],
                    _n.fets[phase*2+1],
                    _n.shunts[phase],
                ],
                _i.motor_power.IFs.lv
            )

            # gate driving
            _i.high_gate_inputs[phase].connect_via(
                _n.gate_ilim_resistors[phase],
                _n.fets[phase*2].IFs.gate
            )
            _i.low_gate_inputs[phase].connect_via(
                _n.gate_ilim_resistors[phase+1],
                _n.fets[phase*2+1].IFs.gate
            )

            # voltage sense ~ fets ~ motor
            (_ifs.voltage_sense[phase]
                .connect(_n.fets[phase*2].IFs.source)
                .connect(_i.motor[phase]))

            # shunt differential pairs
            _i.shunts[phase].IFs.p.connect_via(
                _n.netties[phase*2],
                _n.shunts[phase].IFs.unnamed[0]
            )
            _i.shunts[phase].IFs.n.connect_via(
                _n.netties[phase*2+1],
                _n.shunts[phase].IFs.unnamed[1]
            )

        # deadtime resistor
        gnd = self.IFs.gate_power.IFs.lv
        self.NODEs.ic.IFs.deadtime.connect_via(self.NODEs.deadtime_resistor, gnd)
        self.NODEs.deadtime_resistor.PARAMs.resistance.merge(
            self.PARAMs.deadtime / n / 5 * k
        )
        F.has_multi_picker.remove_if(
            self.NODEs.deadtime_resistor,
            lambda m: F.Constant(200 * n).is_mergeable_with(self.PARAMs.deadtime)
        )

        # bypass cap
        decouple_cap = _n.ic.IFs.gate_power.get_trait(
            can_be_decoupled
        ).decouple()
        decouple_cap.PARAMs.capacitance.merge(
            _n.bootstrap_caps[0].PARAMs.capacitance * F.Range(10, 20)
        )
        decouple_cap.PARAMs.rated_voltage.merge(
            _i.gate_power.PARAMs.voltage * F.Range(1.5, 10)
        )

        # traits
        ref = F.ElectricLogic.connect_all_module_references(self, gnd_only=True)
        self.add_trait(has_single_electric_reference_defined(ref))
        ref.IFs.lv.connect(self.IFs.gate_power.IFs.lv)

        ## remove gate limiting if they're zero
        for r in _n.gate_ilim_resistors:
            r.allow_removal_if_zero()

        # constraints
        self.IFs.motor_power.PARAMs.voltage.merge(F.Range(0, 100))
        for fet in self.NODEs.fets:
            fet.PARAMs.max_continuous_drain_current.merge(self.PARAMs.phase_current)
            fet.PARAMs.max_drain_source_voltage.merge(
                # TODO: this feels stupid. Is this the best way of achieving a range?
                # TODO: extract FOS
                _i.motor_power.PARAMs.voltage * F.Range(1.3, 100)
            )

        for shunt in _n.shunts:
            # TODO:
            # shunt.PARAMs.rated_power.
            pass

    def set_3pwm(self) -> list[F.ElectricLogic]:
        if self._3pwm_mode is None:
            self._3pwm_mode = True
            for high, low in zip(self.IFs.high_gate_inputs, self.IFs.low_gate_inputs):
                high.connect(low)

            self.NODEs.ic.IFs.mode.connect(self.IFs.gate_power.IFs.hv)

        elif not self._3pwm_mode:
            raise ValueError("6 PWM mode is already configured")

        return self.IFs.high_gate_inputs

    def set_6pwm(self) -> tuple[list[F.ElectricLogic], list[F.ElectricLogic]]:
        if self._3pwm_mode is None:
            self._3pwm_mode = False

        elif self._3pwm_mode:
            raise ValueError("3 PWM mode is already configured")

        return self.IFs.high_gate_inputs, self.IFs.low_gate_inputs
