import logging
from typing import Callable, Sequence

from faebryk.core.module import Module
from faebryk.library import _F as F
from faebryk.library.can_attach_to_footprint_via_pinmap import (
    can_attach_to_footprint_via_pinmap,
)
from faebryk.libs.library import L
from faebryk.libs.picker.picker import DescriptiveProperties
from faebryk.libs.units import P, Quantity

logger = logging.getLogger(__name__)


class MultiCapacitor(F.Capacitor):
    capacitors: list[F.Capacitor]

    @classmethod
    def explicit(
        cls,
        values: Sequence[Quantity],
        builder: Callable[[F.Capacitor], None] = lambda _: None,
    ):
        self = cls()

        for value in values:
            cap = F.Capacitor()

            def _build_capacitance(v):
                def __(cap: F.Capacitor):
                    cap.capacitance.merge(v)

                return __

            cap.builder(builder).builder(_build_capacitance(value))
            self.unnamed[0].connect_via(cap, self.unnamed[1])
            self.add(cap, container=self.capacitors)

        return self


class ESP32_S3_WROOM_1_N16R8(Module):
    pwr3v3: F.ElectricPower
    gpio = L.d_field(
        lambda: {
            v: F.ElectricLogic()
            for v in ESP32_S3_WROOM_1_N16R8.datasheet_name_to_gpio.values()
        }
    )
    enable: F.ElectricLogic
    serial: F.UART_Base
    boot_mode: F.ElectricLogic

    def __preinit__(self) -> None:
        super().__preinit__()

        # Name some important aliases
        _gnd = self.pwr3v3.lv

        gpio_pin_map = {
            pin: self.gpio[self.datasheet_name_to_gpio[io_name]]
            for pin, io_name in self.datasheet_pin_names.items()
            if io_name in self.datasheet_name_to_gpio
        }
        self.pinmap = {
            **gpio_pin_map,
            "1": _gnd,
            "2": self.pwr3v3.hv,
            "3": self.enable,
            "40": _gnd,
            "41": _gnd,
        }
        self.add(can_attach_to_footprint_via_pinmap(self.pinmap))

        # Connect up basics
        ref = F.ElectricLogic.connect_all_module_references(self)
        self.add(F.has_single_electric_reference_defined(ref))
        ref.connect(self.pwr3v3)

        self.serial.rx.connect(self.gpio[36].signal)
        self.serial.tx.connect(self.gpio[37].signal)
        self.boot_mode.connect(self.gpio[0].signal)

        # Configure specs
        # https://www.espressif.com/sites/default/files/documentation/esp32-c3_technical_reference_manual_en.pdf#uart
        self.serial.baud.merge(F.Range(0, 5000000))

        self.pwr3v3.voltage.merge(F.Range(3.0 * P.V, 3.6 * P.V))

        # Add basic properties
        self.add(F.has_designator_prefix_defined("U"))

        self.add(
            F.has_datasheet_defined(
                "https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf"
            )
        )
        self.add(
            F.has_descriptive_properties_defined(
                {
                    DescriptiveProperties.manufacturer: "Espressif Systems",
                    DescriptiveProperties.partno: "ESP32-S3-WROOM-1-N16R8",
                }
            )
        )

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
        "10": "IO17",  # I/O/T RTC_GPIO17, GPIO17, U1TXD, ADC2_CH6
        "11": "IO18",  # I/O/T RTC_GPIO18, GPIO18, U1RXD, ADC2_CH7, CLK_OUT3
        "12": "IO8",  # I/O/T RTC_GPIO8, GPIO8, TOUCH8, ADC1_CH7, SUBSPICS1
        "13": "IO19",  # I/O/T RTC_GPIO19, GPIO19, U1RTS, ADC2_CH8, CLK_OUT2, USB_DIO20
        "14": "IO20",  # I/O/T RTC_GPIO20, GPIO20, U1CTS, ADC2_CH9, CLK_OUT1, USB_D+
        "15": "IO3",  # I/O/T RTC_GPIO3, GPIO3, TOUCH3, ADC1_CH2
        "16": "IO46",  # I/O/T GPIO46
        "17": "IO9",  # I/O/T RTC_GPIO9, GPIO9, TOUCH9, ADC1_CH8, FSPIHD, SUBSPIHD
        "18": "IO10",  # I/O/T RTC_GPIO10, GPIO10, TOUCH10, ADC1_CH9, FSPICS0, FSPIIO4, SUBSPICS0
        "19": "IO11",  # I/O/T RTC_GPIO11, GPIO11, TOUCH11, ADC2_CH0, FSPID, FSPIIO5, SUBSPID
        "20": "IO12",  # I/O/T RTC_GPIO12, GPIO12, TOUCH12, ADC2_CH1, FSPICLK, FSPIIO6, SUBSPICLK
        "21": "IO13",  # I/O/T RTC_GPIO13, GPIO13, TOUCH13, ADC2_CH2, FSPIQ, FSPIIO7, SUBSPIQ
        "22": "IO14",  # I/O/T RTC_GPIO14, GPIO14, TOUCH14, ADC2_CH3, FSPIWP, FSPIDQS, SUBSPIWP
        "23": "IO21",  # I/O/T RTC_GPIO21, GPIO21
        "24": "IO47",  # I/O/T SPICLK_P_DIFF, GPIO47, SUBSPICLK_P_DIFF
        "25": "IO48",  # I/O/T SPICLK_N_DIFF, GPIO48, SUBSPICLK_N_DIFF
        "26": "IO45",  # I/O/T GPIO45
        "27": "IO0",  # I/O/T RTC_GPIO0, GPIO0
        "28": "IO35",  # I/O/T SPIIO6, GPIO35, FSPID, SUBSPID
        "29": "IO36",  # I/O/T SPIIO7, GPIO36, FSPICLK, SUBSPICLK
        "30": "IO37",  # I/O/T SPIDQS, GPIO37, FSPIQ, SUBSPIQ
        "31": "IO38",  # I/O/T GPIO38, FSPIWP, SUBSPIWP
        "32": "IO39",  # I/O/T MTCK, GPIO39, CLK_OUT3, SUBSPICS1
        "33": "IO40",  # I/O/T MTDO, GPIO40, CLK_OUT2
        "34": "IO41",  # I/O/T MTDI, GPIO41, CLK_OUT1
        "35": "IO42",  # I/O/T MTMS, GPIO42
        "36": "RXD0",  # I/O/T U0RXD, GPIO44, CLK_OUT2
        "37": "TXD0",  # I/O/T U0TXD, GPIO43, CLK_OUT1
        "38": "IO2",  # I/O/T RTC_GPIO2, GPIO2, TOUCH2, ADC1_CH1
        "39": "IO1",  # I/O/T RTC_GPIO1, GPIO1, TOUCH1, ADC1_CH0
        "40": "GND",  # P GND
        "41": "EPAD",  # P GND
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


class ESP32_S3_WROOM_1_N16R8_Kit(Module):
    pwr3v3: F.ElectricPower
    gpio: dict[int, F.ElectricLogic] = L.d_field(
        lambda: {
            v: F.ElectricLogic()
            for v in ESP32_S3_WROOM_1_N16R8.datasheet_name_to_gpio.values()
        }
    )
    enable: F.ElectricLogic
    serial: F.UART_Base
    boot_mode: F.ElectricLogic
    usb: F.USB2_0
    i2c: F.I2C

    uc: ESP32_S3_WROOM_1_N16R8
    switches = L.list_field(2, F.Switch(F.Electrical))

    def __preinit__(self):
        super().__preinit__()

        self.connect_interfaces_by_name(self.uc, allow_partial=True)

        # Important references to things
        _gnd = self.pwr3v3.lv

        # decouple power supply
        self.pwr3v3.get_trait(F.can_be_decoupled).decouple().builder(
            lambda c: c.specialize(
                MultiCapacitor.explicit(
                    [
                        10 * P.microfarads,  # 10uF
                        10 * P.microfarads,  # 10uF
                        100 * P.nanofarads,  # 100nF
                    ]
                ),
            )
        )

        # boot and enable switches
        for el, switch in zip([self.uc.boot_mode, self.uc.enable], self.switches):
            el.signal.connect_via(switch, _gnd)
            el.get_trait(F.ElectricLogic.can_be_pulled).pull(up=True).builder(
                lambda r: r.resistance.merge(F.Range(4.7 * P.kiloohms, 10 * P.kiloohms))
            )

        # USB
        self.usb.usb_if.d.n.connect(self.gpio[19].signal)
        self.usb.usb_if.d.p.connect(self.gpio[20].signal)

        # I2C
        self.i2c.scl.connect(self.gpio[6].signal)
        self.i2c.sda.connect(self.gpio[7].signal)
        self.i2c.frequency.merge(
            F.Set(
                [
                    F.I2C.define_max_frequency_capability(speed)
                    for speed in [
                        F.I2C.SpeedMode.low_speed,
                        F.I2C.SpeedMode.standard_speed,
                    ]
                ]
                + [
                    F.Range(10_000, 800_000)
                ],  # TODO: should be range 200k-800k, but breaks parameter merge
            )
        )
