import importlib
import os
import sys
import types


class DynamicImporter:
    module: types.ModuleType
    module_dir: str
    module_file: str

    def __init__(self, module_file: str):
        self.module_dir, self.module_file = os.path.split(module_file)

    def __enter__(self):
        self.open()
        self.load()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.unload()
        self.close()
        return False

    def open(self):
        sys.path.append(self.module_dir)

    def close(self):
        sys.path.remove(self.module_dir)

    def load(self):
        self.module = importlib.import_module(self.module_file)

    def unload(self):
        pass  # TODO

    def reload(self):
        self.unload()
        self.load()
