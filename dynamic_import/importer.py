import importlib
import sys
import types


class DynamicImporter:
    ModuleDummy = type('ModuleDummy', (object,), {})

    def __init__(self, module_dir: str):
        self.path_appended = False
        self.module_dir = module_dir
        self.imported_modules = set()
        self.previous_modules = sys.modules.copy()
        self.modules = DynamicImporter.ModuleDummy()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    @staticmethod
    def module_family(module_name: str):
        family = [[]]
        for level in module_name.split('.'):
            family.append(family[-1] + [level])
        return ['.'.join(relative) for relative in family][1:]

    def open(self):
        self._path_appended = self.module_dir not in sys.path
        if self._path_appended:
            sys.path.append(self.module_dir)

    def close(self):
        if self._path_appended:
            sys.path.remove(self.module_dir)

    def import_module(self, module_name: str):
        module_parent = self.modules
        for level in self.module_family(module_name):
            self.imported_modules.add(level)
            setattr(module_parent, level.split('.')[-1], importlib.import_module(level))

    def unimport_all(self):
        for imported_module in sorted(self.imported_modules, key=lambda m: -len(m)):
            if imported_module not in self.previous_modules:
                if '.' not in imported_module:
                    continue
                parent_module = '.'.join(imported_module.split('.')[:-1])
                delattr(sys.modules[parent_module], imported_module.split('.')[-1])

        for imported_module in self.imported_modules:
            if imported_module not in self.previous_modules:
                for attr in dir(sys.modules[imported_module]):
                    if attr not in ['__name__', '__doc__'] and not isinstance(attr, types.ModuleType):
                        delattr(sys.modules[imported_module], attr)
                del sys.modules[imported_module]
        self.imported_modules = set()
        self.modules = DynamicImporter.ModuleDummy()

    def reload(self):
        imported_modules = self.imported_modules.copy()
        self.unimport_all()
        for module in imported_modules:
            self.import_module(module)
