import os
import sys
import tempfile

import pytest

from dynamic_import.importer import DynamicImporter


class TestModuleTree:
    """
    Creates a 4-file test package tree in the following form:
    .
    |- __init__.py
    |- a.py
    |- pkg
     |- __init__.py
     |- b.py
     |- subpkg
      |- __init__.py
      |- c.py
      |- d.py

    See functions below for the specific contents of the four files.
    """

    def content_a(self) -> str:
        return f"A = {self.content_variables['A']}\nAA = {self.content_variables['AA']}"

    def content_b(self) -> str:
        return f"B = {self.content_variables['B']}\nimport pkg.subpkg.c\nimport pkg.subpkg.d"

    def content_c(self) -> str:
        return f"import os\nC = {self.content_variables['C']}"

    def content_d(self) -> str:
        return f"import pkg.b\nD = {self.content_variables['D']}\nDD = {self.content_variables['DD']}"

    def __init__(self, directory: str):
        self.content_variables = {
            "A": "1",
            "AA": "2",
            "B": "3",
            "C": "4",
            "D": "5",
            "DD": "lambda: -pkg.b.B"
        }
        self.directory = directory
        os.makedirs(os.path.join(directory, "pkg", "subpkg"), exist_ok=True)
        open(os.path.join(self.directory, "__init__.py"), "w").close()
        open(os.path.join(self.directory, "pkg", "__init__.py"), "w").close()
        open(os.path.join(self.directory, "pkg", "subpkg", "__init__.py"), "w").close()
        self.write_files()

    def filename_a(self) -> str:
        return os.path.join(self.directory, "a.py")

    def filename_b(self) -> str:
        return os.path.join(self.directory, "pkg", "b.py")

    def filename_c(self) -> str:
        return os.path.join(self.directory, "pkg", "subpkg", "c.py")

    def filename_d(self) -> str:
        return os.path.join(self.directory, "pkg", "subpkg", "d.py")

    def write_files(self):
        with open(self.filename_a(), "w") as file:
            file.write(self.content_a())
        with open(self.filename_b(), "w") as file:
            file.write(self.content_b())
        with open(self.filename_c(), "w") as file:
            file.write(self.content_c())
        with open(self.filename_d(), "w") as file:
            file.write(self.content_d())


@pytest.fixture
def module_tree():
    with tempfile.TemporaryDirectory() as tempdir:
        yield TestModuleTree(tempdir)


@pytest.fixture
def importer(module_tree):
    modules = len(sys.modules)
    with DynamicImporter(module_tree.directory) as importer:
        yield importer
        importer.unimport_all()
    assert len(sys.modules) == modules


def test_TestModuleTree(module_tree):
    assert module_tree is not None


def test_importer_nocrash(module_tree: TestModuleTree):
    importer = DynamicImporter(module_tree.directory)
    importer.open()
    importer.import_module('a')
    importer.close()
    importer.unimport_all()

    with DynamicImporter(module_tree.directory) as importer2:
        importer2.reload()


def test_importer_load_correctly(module_tree: TestModuleTree, importer):
    importer.import_module('a')
    assert importer.modules.a.A == 1
    assert importer.modules.a.AA == 2

def test_importer_unload_correctly(module_tree: TestModuleTree):
    importer = DynamicImporter(module_tree.directory)
    importer.open()
    importer.import_module('a')
    assert importer.modules.a.A == 1
    assert importer.modules.a.AA == 2
    module = importer.modules.a
    importer.unimport_all()
    assert not hasattr(importer.modules, 'a')
    assert not hasattr(module, "A")
    importer.close()


def test_importer_reload_change_value(module_tree: TestModuleTree, importer):
    importer.import_module('a')
    assert importer.modules.a.A == 1
    assert importer.modules.a.AA == 2
    module_tree.content_variables["AA"] = "5"
    module_tree.write_files()
    importer.reload()
    assert importer.modules.a.A == 1
    assert importer.modules.a.AA == 5


def test_importer_reload_remove_value(module_tree: TestModuleTree, importer):
    importer.import_module('a')
    assert importer.modules.a.A == 1
    assert importer.modules.a.AA == 2
    module_tree.content_a = lambda: "A = 1"
    module_tree.write_files()
    importer.reload()
    assert importer.modules.a.A == 1
    assert not hasattr(importer.modules.a, "AA")


def test_subpackage_import(module_tree: TestModuleTree, importer):
    importer.import_module('pkg.b')
    assert importer.modules.pkg.b.B == 3


def test_subpackage_reload_parent_effects_children(module_tree: TestModuleTree, importer):
    importer.import_module('pkg.subpkg.c')
    importer.import_module('pkg.subpkg.d')
    assert importer.modules.pkg.subpkg.c.C == 4
    assert importer.modules.pkg.subpkg.d.D == 5
    module_tree.content_variables["C"] = "0"
    module_tree.content_variables["D"] = "0"
    module_tree.write_files()
    importer.reload()
    assert importer.modules.pkg.subpkg.c.C == 0
    assert importer.modules.pkg.subpkg.d.D == 0


def test_subpackage_reload_recursive_reload(module_tree: TestModuleTree, importer):
    importer_pkg.add_submodule("b")
    importer_pkg.add_submodule("subpkg.c")
    importer_pkg.add_submodule("subpkg.d")


def test_effect_normal_import(module_tree: TestModuleTree, importer):
    assert importer.modules.a.A == 1
    import a
    assert a.A == 1
    module_tree.content_variables["A"] = "0"
    module_tree.write_files()
    import importlib
    importlib.reload(importer.modules.a)
    # importer_a.reload()
    assert a.A == 0
