# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer

logger = logging.getLogger(__name__)

"""
Here you can do PCB scripting.
E.g placing components, layer switching, mass renaming, etc.
"""


def transform_pcb(transformer: PCB_Transformer): ...
