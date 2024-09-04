# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Module

logger = logging.getLogger(__name__)


# Files in /modules are for application-specific modules
# Non-application-specific modules should not be placed in /modules but in /library
# If you come from a classical EDA background, think of these as hiearchical sheets


class MyApplicationModule(Module):
    def __init__(self) -> None:
        super().__init__()

        class _NODEs(Module.NODES()):
            submodule = MyApplicationModuleSubmodule()
            pass

        class _IFs(Module.IFS()):
            pass

        class _PARAMs(Module.PARAMS()):
            pass

        self.IFs = _IFs(self)
        self.NODEs = _NODEs(self)
        self.PARAMs = _PARAMs(self)

        # self.add_trait()
        # self.add_trait()
        # self.add_trait()


class MyApplicationModuleSubmodule(Module):
    def __init__(self) -> None:
        super().__init__()

        class _NODEs(Module.NODES()):
            pass

        class _IFs(Module.IFS()):
            pass

        class _PARAMs(Module.PARAMS()):
            pass

        self.IFs = _IFs(self)
        self.NODEs = _NODEs(self)
        self.PARAMs = _PARAMs(self)

        # self.add_trait()
        # self.add_trait()
        # self.add_trait()
