import logging
from typing import Sequence

from faebryk.core.core import Module
from faebryk.core.util import (
    specialize_module,
)
from faebryk.library.can_attach_to_footprint_via_pinmap import (
    can_attach_to_footprint_via_pinmap,
)
from faebryk.library.can_be_decoupled import can_be_decoupled
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.Capacitor import Capacitor
from faebryk.library.Constant import Constant
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_datasheet_defined import has_datasheet_defined
from faebryk.library.has_defined_descriptive_properties import (
    has_defined_descriptive_properties,
)
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.has_single_electric_reference_defined import (
    has_single_electric_reference_defined,
)
from faebryk.library.I2C import I2C
from faebryk.library.Range import Range
from faebryk.library.Resistor import Resistor
from faebryk.library.Set import Set
from faebryk.library.Switch import Switch
from faebryk.library.UART_Base import UART_Base
from faebryk.library.USB2_0 import USB2_0
from faebryk.libs.picker.picker import DescriptiveProperties
from faebryk.libs.units import k, n, u
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class _RCFilter(Module):
    def __init__(self) -> None:
        super().__init__()

        class _IFS(Module.IFS()):
            input = Electrical()
            output = Electrical()
            lv = Electrical()

        self.IFs = _IFS(self)

        class _NODES(Module.NODES()):
            resistor = Resistor()
            capacitor = Capacitor()

        self.NODEs = _NODES(self)

        self.IFs.input.connect_via(self.NODEs.resistor, self.IFs.output)
        self.IFs.output.connect_via(self.NODEs.capacitor, self.IFs.lv)

        self.add_trait(can_bridge_defined(self.IFs.input, self.IFs.output))


# class BalancedCrystal(Module):
#     def __init__(self) -> None:
#         super().__init__()

#         class _PARAMS(Module.PARAMS()):
#             balance_capacitance = TBD[float]()

#         self.PARAMs = _PARAMS(self)

#         class _IFS(Module.IFS()):
#             unnamed = times(2, Electrical())
#             gnd = Electrical()

#         self.IFs = _IFS(self)

#         class _NODES(Module.NODES()):
#             crystal = Crystal()
#             capacitors = times(2, Capacitor)

#         self.NODEs = _NODES(self)

#         self.NODEs.capacitors[0].PARAMs.capacitance.merge(self.PARAMs.balance_capacitance)


class MultiCapacitor(Capacitor):
    def __init__(self, count: int) -> None:
        super().__init__()

        class _NODES(Module.NODES()):
            capacitors = times(count, Capacitor)

        self.NODEs = _NODES(self)

    @classmethod
    def with_values(cls, values: Sequence[float]):
        self = cls(len(values))
        for i, value in enumerate(values):
            self.NODEs.capacitors[i].PARAMs.capacitance.merge(Constant(value))
        return self


class ESP32_S3_WROOM_1_N16R8(Module):
    datasheet_pin_names = {
        "1": "GND",  # P GND
        "2": "3V3",  # P Power supply
        "3": "EN",  # I High: on, enables the chip. Low: off, the chip powers off. Note: Do not leave the EN pin floating.
        "4": "IO4",  # I/O/T RTC_GPIO4, GPIO4, TOUCH4, ADC1_CH3
        "5": "IO5",  # I/O/T RTC_GPIO5, GPIO5, TOUCH5, ADC1_CH4
        "6": "IO6",  # I/O/T RTC_GPIO6, GPIO6, TOUCH6, ADC1_CH5
        "7": "IO7",  # I/O/T RTC_GPIO7, GPIO7, TOUCH7, ADC1_CH6
        "8": "IO15",  # I/O/T RTC_GPIO15, GPIO15, U0RTS, ADC2_CH4, XTAL_32K_P
        "9": "IO16",  # I/O/T RTC_GPIO16, GPIO16, U0CTS, ADC2_CH5, XTAL_32K_N
        "10": "IO17",   # I/O/T RTC_GPIO17, GPIO17, U1TXD, ADC2_CH6
        "11": "IO18",   # I/O/T RTC_GPIO18, GPIO18, U1RXD, ADC2_CH7, CLK_OUT3
        "12": "IO8",   # I/O/T RTC_GPIO8, GPIO8, TOUCH8, ADC1_CH7, SUBSPICS1
        "13": "IO19",   # I/O/T RTC_GPIO19, GPIO19, U1RTS, ADC2_CH8, CLK_OUT2, USB_DIO20
        "14": "IO20",  # I/O/T RTC_GPIO20, GPIO20, U1CTS, ADC2_CH9, CLK_OUT1, USB_D+
        "15": "IO3",   # I/O/T RTC_GPIO3, GPIO3, TOUCH3, ADC1_CH2
        "16": "IO46",   # I/O/T GPIO46
        "17": "IO9",   # I/O/T RTC_GPIO9, GPIO9, TOUCH9, ADC1_CH8, FSPIHD, SUBSPIHD
        "18": "IO10",   # I/O/T RTC_GPIO10, GPIO10, TOUCH10, ADC1_CH9, FSPICS0, FSPIIO4, SUBSPICS0
        "19": "IO11",   # I/O/T RTC_GPIO11, GPIO11, TOUCH11, ADC2_CH0, FSPID, FSPIIO5, SUBSPID
        "20": "IO12",   # I/O/T RTC_GPIO12, GPIO12, TOUCH12, ADC2_CH1, FSPICLK, FSPIIO6, SUBSPICLK
        "21": "IO13",   # I/O/T RTC_GPIO13, GPIO13, TOUCH13, ADC2_CH2, FSPIQ, FSPIIO7, SUBSPIQ
        "22": "IO14",   # I/O/T RTC_GPIO14, GPIO14, TOUCH14, ADC2_CH3, FSPIWP, FSPIDQS, SUBSPIWP
        "23": "IO21",   # I/O/T RTC_GPIO21, GPIO21
        "24": "IO47",   # I/O/T SPICLK_P_DIFF, GPIO47, SUBSPICLK_P_DIFF
        "25": "IO48",   # I/O/T SPICLK_N_DIFF, GPIO48, SUBSPICLK_N_DIFF
        "26": "IO45",   # I/O/T GPIO45
        "27": "IO0",   # I/O/T RTC_GPIO0, GPIO0
        "28": "IO35",   # I/O/T SPIIO6, GPIO35, FSPID, SUBSPID
        "29": "IO36",   # I/O/T SPIIO7, GPIO36, FSPICLK, SUBSPICLK
        "30": "IO37",   # I/O/T SPIDQS, GPIO37, FSPIQ, SUBSPIQ
        "31": "IO38",   # I/O/T GPIO38, FSPIWP, SUBSPIWP
        "32": "IO39",   # I/O/T MTCK, GPIO39, CLK_OUT3, SUBSPICS1
        "33": "IO40",   # I/O/T MTDO, GPIO40, CLK_OUT2
        "34": "IO41",   # I/O/T MTDI, GPIO41, CLK_OUT1
        "35": "IO42",   # I/O/T MTMS, GPIO42
        "36": "RXD0",   # I/O/T U0RXD, GPIO44, CLK_OUT2
        "37": "TXD0",   # I/O/T U0TXD, GPIO43, CLK_OUT1
        "38": "IO2",   # I/O/T RTC_GPIO2, GPIO2, TOUCH2, ADC1_CH1
        "39": "IO1",   # I/O/T RTC_GPIO1, GPIO1, TOUCH1, ADC1_CH0
        "40": "GND",   # P GND
        "41": "EPAD",   # P GND
    }

    datasheet_name_to_gpio = {
        "IO4": 4,
        "IO5": 5,
        "IO6": 6,
        "IO7": 7,
        "IO15": 15,
        "IO16": 16,
        "IO17": 17,
        "IO18": 18,
        "IO8": 8,
        "IO19": 19,
        "IO20": 20,
        "IO3": 3,
        "IO46": 46,
        "IO9": 9,
        "IO10": 10,
        "IO11": 11,
        "IO12": 12,
        "IO13": 13,
        "IO14": 14,
        "IO21": 21,
        "IO47": 47,
        "IO48": 48,
        "IO45": 45,
        "IO0": 0,
        "IO35": 35,
        "IO36": 36,
        "IO37": 37,
        "IO38": 38,
        "IO39": 39,
        "IO40": 40,
        "IO41": 41,
        "IO42": 42,
        "RXD0": 44,
        "TXD0": 43,
        "IO2": 2,
        "IO1": 1,
    }

    def __init__(self) -> None:
        super().__init__()

        class _IFs(Module.IFS()):
            pwr3v3 = ElectricPower()
            gpio = {v: ElectricLogic() for v in self.datasheet_name_to_gpio.values()}
            enable = ElectricLogic()
            serial = UART_Base()
            boot_mode = ElectricLogic()

        self.IFs = _IFs(self)

        # Name some important aliases
        _gnd = self.IFs.pwr3v3.IFs.lv
        x = self.IFs

        gpio_pin_map = {
            pin: x.gpio[self.datasheet_name_to_gpio[io_name]]
            for pin, io_name in self.datasheet_pin_names.items()
            if io_name in self.datasheet_name_to_gpio
        }
        self.pinmap = {
            **gpio_pin_map,
            "1": _gnd,
            "2": x.pwr3v3.IFs.hv,
            "3": x.enable,
            "40": _gnd,
            "41": _gnd,
        }
        self.add_trait(can_attach_to_footprint_via_pinmap(self.pinmap))

        # Connect up basics
        ref = ElectricLogic.connect_all_module_references(self)
        self.add_trait(has_single_electric_reference_defined(ref))
        ref.connect(self.IFs.pwr3v3)

        x.serial.IFs.rx.connect(x.gpio[36].IFs.signal)
        x.serial.IFs.tx.connect(x.gpio[37].IFs.signal)
        x.boot_mode.connect(x.gpio[0].IFs.signal)

        # Configure specs
        # https://www.espressif.com/sites/default/files/documentation/esp32-c3_technical_reference_manual_en.pdf#uart
        x.serial.PARAMs.baud.merge(Range(0, 5000000))

        self.IFs.pwr3v3.PARAMs.voltage.merge(Range(3.0, 3.6))

        # Add basic properties
        self.add_trait(has_designator_prefix_defined("U"))

        self.add_trait(
            has_datasheet_defined(
                "https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf"
            )
        )
        self.add_trait(
            has_defined_descriptive_properties(
                {
                    DescriptiveProperties.manufacturer: "Espressif Systems",
                    DescriptiveProperties.partno: "ESP32-S3-WROOM-1-N16R8",
                }
            )
        )


class ESP32_S3_WROOM_1_N16R8_Kit(Module):
    def __init__(self) -> None:
        super().__init__()

        class _NODEs(Module.NODES()):
            uc = ESP32_S3_WROOM_1_N16R8()
            switches = times(2, Switch(Electrical))

        self.NODEs = _NODEs(self)

        class _IFs(Module.IFS()):
            # Pass through interfaces
            pwr3v3 = ElectricPower().connect(self.NODEs.uc.IFs.pwr3v3)
            gpio = {
                k: ElectricLogic().connect(gpio)
                for k, gpio in self.NODEs.uc.IFs.gpio.items()
            }
            serial = UART_Base().connect(self.NODEs.uc.IFs.serial)

            # Extensions
            usb = USB2_0()
            i2c = I2C()

        self.IFs = _IFs(self)

        # Important references to things
        _gnd = self.IFs.pwr3v3.IFs.lv
        _uc = self.NODEs.uc
        x = self.IFs

        # decouple power supply
        self.IFs.pwr3v3.get_trait(can_be_decoupled).decouple().builder(
            lambda c: specialize_module(c, MultiCapacitor.with_values([
                10 * u,  # 10uF
                10 * u,  # 10uF
                100 * n  # 100nF
            ]))
        )

        # boot and enable switches
        for el, switch in zip([_uc.IFs.boot_mode, _uc.IFs.enable], self.NODEs.switches):
            el.IFs.signal.connect_via(switch, _gnd)
            el.get_trait(ElectricLogic.can_be_pulled).pull(up=True).builder(
                lambda r: r.PARAMs.resistance.merge(10 * k)
            )

        # USB
        x.usb.IFs.usb_if.IFs.d.IFs.n.connect(x.gpio[19].IFs.signal)
        x.usb.IFs.usb_if.IFs.d.IFs.p.connect(x.gpio[20].IFs.signal)

        # I2C
        self.IFs.i2c.IFs.scl.connect(x.gpio[6].IFs.signal)
        self.IFs.i2c.IFs.sda.connect(x.gpio[7].IFs.signal)
        self.IFs.i2c.PARAMs.frequency.merge(
            Set(
                [
                    I2C.define_max_frequency_capability(speed)
                    for speed in [
                        I2C.SpeedMode.low_speed,
                        I2C.SpeedMode.standard_speed,
                    ]
                ]
                + [
                    Range(10 * k, 800 * k)
                ],  # TODO: should be range 200k-800k, but breaks parameter merge
            )
        )
