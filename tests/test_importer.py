import os
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

    def modulename_a(self) -> str:
        return os.path.join(self.directory, "a")

    def modulename_pkg(self) -> str:
        return os.path.join(self.directory, "pkg")

    def modulename_b(self) -> str:
        return self.modulename_pkg() + ".b"

    def modulename_subpkg(self) -> str:
        return self.modulename_pkg() + ".subpkg"

    def modulename_c(self) -> str:
        return self.modulename_subpkg() + ".c"

    def modulename_d(self) -> str:
        return self.modulename_subpkg() + ".d"

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
def importer_a(module_tree):
    with DynamicImporter(module_tree.modulename_a()) as importer:
        yield importer


@pytest.fixture
def importer_b(module_tree):
    with DynamicImporter(module_tree.modulename_b()) as importer:
        yield importer


@pytest.fixture
def importer_c(module_tree):
    with DynamicImporter(module_tree.modulename_c()) as importer:
        yield importer


@pytest.fixture
def importer_d(module_tree):
    with DynamicImporter(module_tree.modulename_d()) as importer:
        yield importer


@pytest.fixture
def importer_pkg(module_tree):
    with DynamicImporter(module_tree.modulename_pkg()) as importer:
        yield importer


@pytest.fixture
def importer_subpkg(module_tree):
    with DynamicImporter(module_tree.modulename_subpkg()) as importer:
        yield importer


def test_TestModuleTree(module_tree):
    assert module_tree is not None


def test_importer_nocrash(module_tree: TestModuleTree):
    importer = DynamicImporter(module_tree.modulename_a())
    importer.open()
    importer.load()
    importer.close()
    importer.unload()

    with DynamicImporter(module_tree.modulename_a()) as importer2:
        importer2.reload()


def test_importer_load_correctly(module_tree: TestModuleTree, importer_a):
    assert importer_a.module.A == 1
    assert importer_a.module.AA == 2


def test_importer_unload_correctly(module_tree: TestModuleTree):
    importer = DynamicImporter(module_tree.modulename_a())
    importer.open()
    importer.load()
    assert importer.module.A == 1
    assert importer.module.AA == 2
    module = importer.module
    importer.unload()
    assert importer.module is None
    assert not hasattr(module, "A")
    importer.close()


def test_importer_reload_change_value(module_tree: TestModuleTree, importer_a):
    assert importer_a.module.A == 1
    assert importer_a.module.AA == 2
    module_tree.content_variables["AA"] = "5"
    module_tree.write_files()
    importer_a.reload()
    assert importer_a.module.A == 1
    assert importer_a.module.AA == 5


def test_importer_reload_remove_value(module_tree: TestModuleTree, importer_a):
    assert importer_a.module.A == 1
    assert importer_a.module.AA == 2
    module_tree.content_a = lambda: "A = 1"
    module_tree.write_files()
    importer_a.reload()
    assert importer_a.module.A == 1
    assert not hasattr(importer_a.module, "AA")


def test_subpackage_import(module_tree: TestModuleTree, importer_b):
    assert importer_b.module.B == 3


def test_subpackage_reload_parent_effects_children(module_tree: TestModuleTree, importer_subpkg):
    importer_subpkg.add_submodule("pkg.subpkg.c")
    importer_subpkg.add_submodule("pkg.subpkg.d")
    assert importer_subpkg.module.c.C == 4
    assert importer_subpkg.module.d.D == 5
    module_tree.content_variables["C"] = "0"
    module_tree.content_variables["D"] = "0"
    module_tree.write_files()
    importer_subpkg.reload()
    assert importer_subpkg.module.c.C == 0
    assert importer_subpkg.module.d.D == 0


def test_subpackage_reload_recursive_reload(module_tree: TestModuleTree, importer_pkg):
    importer_pkg.add_submodule("b")
    importer_pkg.add_submodule("subpkg.c")
    importer_pkg.add_submodule("subpkg.d")


def test_effect_normal_import(module_tree: TestModuleTree, importer_a):
    assert importer_a.module.A == 1
    import a
    assert a.A == 1
    module_tree.content_variables["A"] = "0"
    module_tree.write_files()
    import importlib
    importlib.reload(importer_a.module)
    #importer_a.reload()
    assert a.A == 0

