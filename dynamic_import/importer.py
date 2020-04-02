import importlib
import os
import sys
import types
import typing


class DynamicImporter:
    def __init__(self, module_file: str):
        self.module: typing.Optional[types.ModuleType] = None
        self._path_appended = False
        self.module_dir, self.module_file = os.path.split(module_file)

    def __enter__(self):
        self.open()
        self.module = importlib.import_module(self.module_file)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def open(self):
        self._path_appended = self.module not in sys.path
        if self._path_appended:
            sys.path.append(self.module_dir)

    def close(self):
        if self._path_appended:
            sys.path.remove(self.module_dir)

    def add_submodule(self, module_name):
        importlib.import_module(module_name)

    def reload(self, module=None):
        if module is None:
            module = self.module
        if module.__name__.split(".")[0] != self.module.__name__.split(".")[0]:
            return

        for attr in dir(module):
            if attr in ["__name__", "__doc__"]:
                continue
            if isinstance(getattr(module, attr), types.ModuleType):
                self.reload(getattr(module, attr))
            else:
                delattr(module, attr)

        importlib.reload(module)
