# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.module import Module
from faebryk.library import _F as F
from faebryk.library.Capacitor import Capacitor
from faebryk.library.MOSFET import MOSFET
from faebryk.library.NetTie import net_tie
from faebryk.library.Resistor import Resistor
from faebryk.libs.library import L
from faebryk.libs.picker.picker import DescriptiveProperties
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class DRV8300(Module):
    gate_power: F.ElectricPower
    mode: F.ElectricLogic
    high_gate_inputs = L.list_field(3, F.ElectricLogic)
    low_gate_inputs = L.list_field(3, F.ElectricLogic)
    high_gate_outputs = L.list_field(3, F.Electrical)
    low_gate_outputs = L.list_field(3, F.Electrical)
    voltage_sense = L.list_field(3, F.Electrical)
    bootstrap = L.list_field(3, F.Electrical)
    deadtime: F.Electrical

    def __preinit__(self):
        super().__preinit__()

        gnd = self.gate_power.lv
        self.pinmap = {
            "1": self.low_gate_inputs[0].signal,  # input_low_a.io
            "2": self.low_gate_inputs[1].signal,  # input_low_b.io
            "3": self.low_gate_inputs[2].signal,  # input_low_c.io
            "4": self.gate_power.hv,  # power_gate.vcc
            "5": self.mode.signal,  # mode.io
            "6": gnd,  # power_gate.gnd
            # 7, 8 unconnected
            "9": self.low_gate_outputs[2],  # output_low_c.io
            "10": self.low_gate_outputs[1],  # output_low_b.io
            "11": self.low_gate_outputs[0],  # output_low_a.io
            "12": self.voltage_sense[2],  # output_sense_c.io
            "13": self.high_gate_outputs[2],  # output_high_c.io
            "14": self.bootstrap[2],  # boostrap_c.io
            "15": self.voltage_sense[1],  # output_sense_b.io
            "16": self.high_gate_outputs[1],  # output_high_b.io
            "17": self.bootstrap[1],  # boostrap_b.io
            "18": self.voltage_sense[0],  # output_sense_a.io
            "19": self.high_gate_outputs[0],  # output_high_a.io
            "20": self.bootstrap[0],  # boostrap_a.io
            "21": self.deadtime,  # deadtime.io
            "22": self.high_gate_inputs[0].signal,  # input_high_a.io
            "23": self.high_gate_inputs[1].signal,  # input_high_b.io
            "24": self.high_gate_inputs[2].signal,  # input_high_c.io
            "25": gnd,  # Thermal pad - power_gate.gnd
        }
        self.add_trait(F.can_attach_to_footprint_via_pinmap(self.pinmap))

        self.add_trait(
            F.has_datasheet_defined("https://www.ti.com/lit/ds/symlink/drv8300.pdf")
        )
        self.add(
            F.has_descriptive_properties_defined(
                {
                    DescriptiveProperties.manufacturer: "Texas Instruments",
                    DescriptiveProperties.partno: "DRV8300DRGER",
                }
            )
        )

        self.add_trait(F.has_designator_prefix_defined("U"))

        ref = F.ElectricLogic.connect_all_module_references(self)
        self.add_trait(F.has_single_electric_reference_defined(ref))
        ref.connect(self.gate_power)

        # constraints
        self.gate_power.voltage.merge(F.Range(5, 20))


class DRV8300PowerStage3PWM(Module):
    ic: DRV8300
    fets = L.list_field(6, MOSFET)
    gate_ilim_resistors = L.list_field(6, Resistor)
    shunts = L.list_field(3, Resistor)
    netties = L.list_field(6, net_tie(0.5))
    bootstrap_caps = L.list_field(3, Capacitor)
    deadtime_resistor: Resistor

    phase_current: F.TBD[float]
    deadtime = L.d_field(lambda: F.Range(200 * P.nanoseconds, 2000 * P.nanoseconds))

    motor_power: F.ElectricPower
    gate_power: F.ElectricPower
    gate_inputs = L.list_field(3, F.ElectricLogic)
    motor = L.list_field(3, F.Electrical)

    # TODO: check that the right interfaces are used, depending on config
    shunt_outputs = L.list_field(3, F.DifferentialPair)

    def __preinit__(self):
        self.gate_power.voltage.merge(F.Range(12, 24))

        # connections
        for phase in range(3):
            # power stack
            self.motor_power.hv.connect_via(
                [
                    self.fets[phase],
                    self.fets[phase + 3],
                    self.shunts[phase],
                ],
                self.motor_power.lv,
            )

            # gate driving
            self.ic.high_gate_outputs[phase].connect_via(
                self.gate_ilim_resistors[phase], self.fets[phase].gate
            )
            self.ic.low_gate_outputs[phase].connect_via(
                self.gate_ilim_resistors[phase + 3], self.fets[phase + 3].gate
            )

            # voltage sense ~ fets ~ motor
            (
                self.ic.voltage_sense[phase]
                .connect(self.fets[phase + 3].source)
                .connect(self.motor[phase])
            )

            # shunt differential pairs
            self.shunt_outputs[phase].p.connect_via(
                self.netties[phase], self.shunts[phase].unnamed[0]
            )

            self.shunt_outputs[phase].n.connect_via(
                self.netties[phase + 3], self.shunts[phase].unnamed[1]
            )

        # TODO: configuration for the 3 vs. 6pwm mode
        self.gate_power.connect(self.ic.mode)

        # deadtime resistor
        gnd = self.gate_power.lv
        self.ic.deadtime.connect_via(self.deadtime_resistor, gnd)
        self.deadtime_resistor.resistance.merge(
            self.deadtime / P.nanoseconds / 5 * P.kiloohms
        )
        F.has_multi_picker.remove_if(
            self.deadtime_resistor,
            lambda m: F.Constant(200 * P.nanoseconds).is_mergeable_with(self.deadtime),
        )

        ### bootstrap caps
        for bs in self.bootstrap_caps:
            bs.rated_voltage.override(self.gate_power.voltage * F.Range(1.5, 10))
            bs.capacitance.merge(F.Range(100, 200) * P.nanofarads)

        ### bypass cap
        decouple_cap = self.ic.gate_power.get_trait(F.can_be_decoupled).decouple()
        # > 10x the bootstrap caps
        decouple_cap.capacitance.override(
            self.bootstrap_caps[0].capacitance * F.Range(10, 20)
        )
        decouple_cap.rated_voltage.override(
            self.gate_power.voltage * F.Range(1.5, 10)
        )

        # traits
        ref = F.ElectricLogic.connect_all_module_references(self, gnd_only=True)
        self.add_trait(F.has_single_electric_reference_defined(ref))
        ref.lv.connect(self.gate_power.lv)

        ## remove gate limiting if they're zero
        for r in self.gate_ilim_resistors:
            r.allow_removal_if_zero()

        # constraints
        self.motor_power.voltage.merge(F.Range(0, 100))
        for fet in self.fets:
            fet.max_continuous_drain_current.merge(self.phase_current)
            fet.max_drain_source_voltage.merge(
                # TODO: this feels stupid. Is this the best way of achieving a range?
                # TODO: extract FOS
                self.motor_power.voltage
                * F.Range(1.3, 100)
            )

        for shunt in self.shunts:
            shunt.resistance.merge(F.Range(0 * P.ohms, 5 * P.milliohms))
            shunt.rated_power.merge(
                self.phase_current * self.phase_current * shunt.resistance
            )
