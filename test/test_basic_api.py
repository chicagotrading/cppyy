import os
import py
import shutil
import subprocess
import tempfile
from pytest import raises, mark
from support import setup_make, IS_MAC, IS_LINUX

# reuse the example01
currpath = py.path.local(__file__).dirpath()
test_dct = str(currpath.join("example01Dict"))

def setup_module(mod):
    setup_make("example01")


class TestBASICAPI:
    @mark.xfail(IS_MAC, reason="evaluate is broken on macos")
    def test01_evaluate(self):
        import cppyy

        # we use evaluate as a way to set these flags in support, for example
        # for IS_CLANG_REPL, etc. let's make sure basic uses work
        out = cppyy.evaluate("""#define TEST01_EVALUATE
                                #ifdef TEST01_EVALUATE
                                    true
                                #else
                                    false
                                #endif""")
        assert out

        cppyy.evaluate("__cplusplus") >= 201100

        x = 42
        assert cppyy.evaluate(str(x)) == x

    @mark.xfail(IS_MAC, reason="unidentified IsDebugOutputEnabled issue on macos, also failing in test_fragile")
    def test02_cppdef(self):
        import cppyy
        assert cppyy.cppdef("namespace test02_NS { int x = 42; }")
        assert cppyy.gbl.test02_NS.x == 42

    def test03_add_library_path(self):
        import cppyy
        with raises(OSError, match="No such directory"):
            cppyy.add_library_path("not/a/real/path")

        with tempfile.TemporaryDirectory() as tpath:
            cppyy.add_library_path(tpath)

            # now we should actually see if load library can follow this...
            # first, try to load without moving to directory...
            with raises(RuntimeError, match="Could not load library"):
                cppyy.load_library("test.so")

            # then copy to our rpath, and make sure it can be loaded now
            shutil.copyfile(test_dct + ".so", tpath + "/test.so")
            cppyy.load_library("test.so")

    @mark.skipif(IS_LINUX == 0, reason="checks Linux dlerror text")
    def test03a_load_library_failure_reason(self):
        """load_library reports the dlopen failure reason"""

        import cppyy

        cxx = os.environ.get("CXX", "c++")
        with tempfile.TemporaryDirectory() as tpath:
            src = os.path.join(tpath, "empty.cxx")
            with open(src, "w") as out:
                print("", file=out)
            dep = os.path.join(tpath, "libdlerrdep.so")
            broken = os.path.join(tpath, "libdlerrbroken.so")
            subprocess.check_call([cxx, "-shared", "-fPIC", "-o", dep, src])
            subprocess.check_call(
                [cxx, "-shared", "-fPIC", "-o", broken, src,
                 "-L"+tpath, "-Wl,--no-as-needed", "-l:libdlerrdep.so"])
            os.remove(dep)   # makes the DT_NEEDED entry unresolvable

            with raises(RuntimeError, match="libdlerrdep.so"):
                cppyy.load_library(broken)

    def test04_add_include_path(self):
        import cppyy

        with tempfile.TemporaryDirectory() as tpath:
            cppyy.add_include_path(tpath)

            header = "test_add_include_path.h"
            with open(tpath + "/" + header, "w") as out:
                print("int test04f() { return 42; }", file=out)

            assert cppyy.include(header)
            assert cppyy.gbl.test04f() == 42
