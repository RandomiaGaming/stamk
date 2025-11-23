#!/bin/env python

import pathlib
import types
import subprocess
import sys
import os
import sys
import glob
import shutil

# Helpers
def WriteFile(filePath, contents, binary=False):
    filePath = os.path.abspath(filePath)
    dirPath = os.path.dirname(filePath)
    os.makedirs(dirPath, exist_ok=True)
    with open(filePath, "wb" if binary else "w", encoding=(None if binary else "UTF-8")) as file:
        file.write(contents)
def ReadFile(filePath, defaultContents=None, binary=False):
    filePath = os.path.abspath(filePath)
    if not os.path.exists(filePath):
        if defaultContents != None:
            return defaultContents
    with open(filePath, "rb" if binary else "r", encoding=(None if binary else "UTF-8")) as file:
        return file.read()
def RunCommand(command, echo=False, capture=False, input=None, check=True, env=None):
    result = subprocess.run(command, capture_output=(not echo), input=input, check=check, shell=True, text=True,)
    if capture and not check:
        return (result.stdout + result.stderr).strip(), result.returncode
    elif capture:
        return (result.stdout + result.stderr).strip()
    elif not check:
        return result.returncode
    else:
        return
def RunVsDevCommand(command, echo=False, capture=False, input=None, check=True):
    vsdevcmd_path = "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\Common7\\Tools\\VsDevCmd.bat"
    if not os.path.exists(vsdevcmd_path):
        raise Exception("VsDevCmd.bat could not be found. You may need to install Visual Studio or add the \"Desktop development with c++\" workload.")
    fullCommand = f"cmd /c \"\"{vsdevcmd_path}\" -arch=x64 -no_logo && {command}\""
    env = os.environ.copy()
    env["VSCMD_SKIP_SENDTELEMETRY"] = "1"
    return RunCommand(fullCommand, echo=echo, capture=capture, input=input, check=check, env=env)
def SelectPaths(root, selectors):
    if isinstance(selectors, str):
        selectors = [ selectors ]
    root = os.path.abspath(root)
    oldCwd = os.getcwd()
    os.chdir(root)
    output = set()
    for selector in selectors:
        if not selector.startswith("!"):
            output.update([ os.path.abspath(matchPath) for matchPath in glob.glob(selector, recursive=True, include_hidden=True) if os.path.isfile(matchPath) ])
    for selector in selectors:
        if selector.startswith("!"):
            selector = selector[1:]
            output.difference_update([ os.path.abspath(matchPath) for matchPath in glob.glob(selector, recursive=True, include_hidden=True) if os.path.isfile(matchPath) ])
    os.chdir(oldCwd)
    return list(output)

""" Commands in .stamk
# - Comment
windows - This line only applys to Windows builds
mac - This line only applys to MacOS builds
linux - This line only applys to Linux builds
binary - Sets the name of the output binary in ./build/bin
source - Source glob or negative glob
asset - Asset glob or negative glob
object - Object glob or negative glob 
include - Extra include directory
depends - A dependency name
"""
def ParseRecipe(recipe):
    output = types.SimpleNamespace()
    output.BINARYNAME = None
    output.SOURCEGLOBS = []
    output.ASSETGLOBS = []
    output.OBJECTGLOBS = []
    output.INCLUDEDIRS = []
    output.DEPENDSNAMES = []

    if recipeLine == "":
        return
    if recipeLine.startswith("#"):
        return
    if not ":" in recipeLine:
        raise Exception(f"Command must contain a \":\" \"{recipeLine}\".")
    command, body = recipeLine.split(":", 1)
    if command == "windows":
        if ENV.PLATFORM == "WINDOWS":
            ApplyRecipeLine(body, ENV)
        else:
            return
    elif command == "mac":
        if ENV.PLATFORM == "MAC":
            ApplyRecipeLine(body, ENV)
        else:
            return
    elif command == "linux":
        if ENV.PLATFORM == "LINUX":
            ApplyRecipeLine(body, ENV)
        else:
            return
    elif command == "binary":
        if ENV.BINARYNAME != None:
            raise Exception("Binary name has already been set.")
        else:
            ENV.BINARYNAME = body
    elif command == "source":
        ENV.SOURCEGLOBS.append(body)
    elif command == "asset":
        ENV.ASSETGLOBS.append(body)
    elif command == "object":
        ENV.OBJECTGLOBS.append(body)
    elif command == "include":
        ENV.INCLUDEDIRS.append(body)
    elif command == "depends":
        ENV.DEPENDS.append(body)
    else:
        raise Exception(f"Unknown command: {command}.")
    return output
"""
Environment Vars
CC - String - The absolute path of the C compiler. - Set automatically.
CXX - String - The absolute path of the C++ compiler. - Set automatically.
PLATFORM - String - "WINDOWS", "MAC", or "LINUX". - Set automatically.
ROOT - String - The absolute path of the folder containing the .stamk file. - Set by current directory.
OBJ - String - The absolute path to the obj folder which is always ROOT/obj. - Set by ROOT.
BIN - String - The absolute path to the bin folder which is always ROOT/bin. - Set by ROOT.
DEBUG - Bool - Weather the build should be stripped or include symbols. - Set by args.
BINARYNAME - String - The name of the output binary. - Set by recipe.
SOURCEGLOBS - String Array - Globs and negative globs specifying source file paths relative to ROOT or absolute. - Set by recipe.
ASSETGLOBS - String Array - Globs and negative globs specifying asset file paths relative to ROOT or absolute. - Set by recipe.
OBJECTGLOBS - String Array - Globs and negative globs specifying object file paths relative to ROOT or absolute. - Set by recipe.
INCLUDEDIRS - String Array - Folder paths relative to ROOT or absolute to include headers from. - Set by recipe.
DEPENDS - String Array - Dependency names from the list of stamk supported dependencies. - Set by recipe.
BINARY - String - The absolute path of the output binary. Set by BINARYNAME and BIN.
SOURCES - String Array - Absolute paths to source files. - Set by SOURCEGLOBS and ROOT.
ASSETS - String Array - Absolute paths to asset files. - Set by ASSETGLOBS and ROOT.
OBJECTS - String Array - Globs and negative globs specifying object file paths relative to ROOT or absolute. - Set by recipe.
"""

def InitEnv():
    ENV = types.SimpleNamespace()
    
    ENV.CC = os.path.join(os.path.abspath(os.path.dirname(__file__)), "musl", "bin", "gcc")
    ENV.CXX = os.path.join(os.path.abspath(os.path.dirname(__file__)), "musl", "bin", "g++")
    ENV.PLATFORM = "LINUX"
    if sys.platform == "win32" or sys.platform == "cygwin":
        ENV.PLATFORM = "WINDOWS"
    elif sys.platform == "darwin" or sys.platform == "ios":
        ENV.PLATFORM = "MAC"

    ENV.ROOT = os.path.abspath(os.getcwd())
    ENV.OBJ = os.path.join(ENV.ROOT, "obj")
    os.makedirs(ENV.OBJ, exist_ok=True)
    ENV.BIN = os.path.join(ENV.ROOT, "bin")
    os.makedirs(ENV.BIN, exist_ok=True)

    ENV.DEBUG = None
    for arg in sys.argv[1:]:
        if arg == "--release":
            if ENV.DEBUG != None: raise Exception(f"Target has already been set for this build.")
            ENV.DEBUG = False
        elif arg == "-r":
            if ENV.DEBUG != None: raise Exception(f"Target has already been set for this build.")
            ENV.DEBUG = False
        elif arg == "--debug":
            if ENV.DEBUG != None: raise Exception(f"Target has already been set for this build.")
            ENV.DEBUG = True
        elif arg == "-d":
            if ENV.DEBUG != None: raise Exception(f"Target has already been set for this build.")
            ENV.DEBUG = True
        else:
            raise Exception(f"Unknown command line flag \"{arg}\".")
    if ENV.DEBUG == None: ENV.DEBUG = False

    recipePath = os.path.join(ENV.ROOT, ".stamk")
    if not os.path.isfile(recipePath):
        raise Exception("Recipe file .stamk could not be found in the current directory.")
    ENV.BINARYNAME = None
    ENV.SOURCEGLOBS = []
    ENV.ASSETGLOBS = []
    ENV.OBJECTGLOBS = []
    ENV.INCLUDEDIRS = []
    ENV.DEPENDS = []
    for recipeLine in ReadFile(recipePath).splitlines():
        ApplyRecipeLine(recipeLine, ENV)

    if ENV.BINARYNAME == None:
        ENV.BINARY = os.path.join(ENV.BIN, os.path.basename(ENV.ROOT))
    else:
        if "\\" in ENV.BINARYNAME or "/" in ENV.BINARYNAME:
            raise Exception("Binary name may not contain \\ or /.")
        ENV.BINARY = os.path.join(ENV.BIN, ENV.BINARYNAME)
    ENV.SOURCES = SelectPaths(ENV.ROOT, ENV.SOURCEGLOBS)
    ENV.ASSETS = SelectPaths(ENV.ROOT, ENV.ASSETGLOBS)
    ENV.OBJECTS = SelectPaths(ENV.ROOT, ENV.OBJECTGLOBS)
    ENV.INCLUDEDIRS = [ includeDir if os.path.isabs(includeDir) else os.path.join(ENV.ROOT, includeDir) for includeDir in ENV.INCLUDEDIRS ]

    return ENV

def PrecompileAssets(ENV):
    
    packedAssetsDir = os.path.join(ENV.OBJ, "packed_assets")
    os.makedirs(packedAssetsDir, exist_ok=True)
    assetCppPaths = []
    for assetPath in ENV.ASSETS:
        assetName = "".join(c if c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" else "_" for c in os.path.basename(assetPath))
        if assetName and assetName[0].isdigit(): assetName = f"_{assetName}"
        assetCppPath = os.path.join(ENV.PACK, assetName + ".cpp")
        assetPathParsed = Path(assetPath)
        assetCppPathParsed = Path(assetCppPath)
        if not os.path.exists(assetCppPath) or assetPathParsed.stat().st_mtime > assetCppPathParsed.stat().st_mtime:
            assetBinary = ReadFile(assetPath, binary=True)
            assetCpp = f"#include <cstdint>\nconst uint32_t {assetName}_length = {len(assetBinary)};\nconst uint8_t {assetName}_buffer[] = " + "{ " + ", ".join(str(b) for b in assetBinary) + " };\n"
            WriteFile(assetCppPath, assetCpp)
        assetCppPaths.append(assetCppPath)
    return assetCppPaths
def Compile(sourcePath, objectPath):
    objDir=os.path.join(ROOT, "obj")
    os.makedirs(objDir, exist_ok=True)
    objectsDir = os.path.join(objDir, "objects")
    os.makedirs(objectsDir, exist_ok=True)
    sourcePaths = SelectPaths(selectors=[ "src/**/*.c", "obj/precompiled_assets/*.c" ], root=ROOT)
    includeDirs = [ os.path.join(objDir, "libdrm_build", "include"), os.path.join(objDir, "libdrm_build", "include", "libdrm"), os.path.join(objDir, "libalsa_build", "include") ]
    muslGccPath = os.path.join(objDir, "musl", "bin", "gcc")
    commandPath = os.path.join(objDir, "command.txt")
    for sourcePath in sourcePaths:
        objectPath = os.path.join(objectsDir, os.path.splitext(os.path.basename(sourcePath))[0] + ".o")
        if not os.path.exists(objectPath):
            print(f"Compiling {sourcePath}...")
            command = ""
            command += f" -c -DLINUX {"" if RELEASE else "-g -O0"} -Wall -Wextra -Werror -std=c2x "
            command += f" {" ".join([ f"-I\"{includeDir}\"" for includeDir in includeDirs ])} "
            command += f" \"{sourcePath}\" -o \"{objectPath}\" "
            WriteFile(commandPath, command)
            oldCwd = os.getcwd()
            os.chdir(objDir)
            output, code = RunCommand(f"\"{muslGccPath}\" @command.txt", capture=True, check=False)
            if code != 0:
                raise Exception(output)
            os.chdir(oldCwd)
def Link(objectPaths, binaryPath):
    raise Exception("Not implamented")
    buildDir = os.path.join(PROJROOT, "build")
    os.makedirs(buildDir, exist_ok=True)
    commandPath = os.path.join(buildDir, "command.txt")
    binDir = os.path.join(buildDir, "bin")
    os.makedirs(binDir, exist_ok=True)
    binaryPath = os.path.join(binDir, "PowerCuesApi.exe" if WINDOWS else "PowerCuesApi")
    command = ""
    if WINDOWS:
        command += f" {"/release" if RELEASE else "/debug"}"
        command += f" #OBJPATHS#"
        command += f" /LIBPATH:\"{os.path.join(cacheDir, f"vcpkg_installed\\x64-windows-static{"" if RELEASE else "\\debug"}\\lib")}\""
        command += f" /LIBPATH:\"{os.path.join(PROJROOT, f"cef\\{"Release" if RELEASE else "Debug"}")}\""
        command += f" libusb-1.0.lib /OUT:#OUTPATH#"
        command += f" /DELAYLOAD:\"api-ms-win-core-winrt-error-l1-1-0.dll\" /DELAYLOAD:\"api-ms-win-core-winrt-l1-1-0.dll\" /DELAYLOAD:\"api-ms-win-core-winrt-string-l1-1-0.dll\" /DELAYLOAD:\"advapi32.dll\" /DELAYLOAD:\"comctl32.dll\" /DELAYLOAD:\"comdlg32.dll\" /DELAYLOAD:\"credui.dll\" /DELAYLOAD:\"cryptui.dll\" /DELAYLOAD:\"d3d11.dll\" /DELAYLOAD:\"d3d9.dll\" /DELAYLOAD:\"dwmapi.dll\" /DELAYLOAD:\"dxgi.dll\" /DELAYLOAD:\"dxva2.dll\" /DELAYLOAD:\"esent.dll\" /DELAYLOAD:\"gdi32.dll\" /DELAYLOAD:\"hid.dll\" /DELAYLOAD:\"imagehlp.dll\" /DELAYLOAD:\"imm32.dll\" /DELAYLOAD:\"msi.dll\" /DELAYLOAD:\"netapi32.dll\" /DELAYLOAD:\"ncrypt.dll\" /DELAYLOAD:\"ole32.dll\" /DELAYLOAD:\"oleacc.dll\" /DELAYLOAD:\"propsys.dll\" /DELAYLOAD:\"psapi.dll\" /DELAYLOAD:\"rpcrt4.dll\" /DELAYLOAD:\"rstrtmgr.dll\" /DELAYLOAD:\"setupapi.dll\" /DELAYLOAD:\"shell32.dll\" /DELAYLOAD:\"shlwapi.dll\" /DELAYLOAD:\"uiautomationcore.dll\" /DELAYLOAD:\"urlmon.dll\" /DELAYLOAD:\"user32.dll\" /DELAYLOAD:\"usp10.dll\" /DELAYLOAD:\"uxtheme.dll\" /DELAYLOAD:\"wer.dll\" /DELAYLOAD:\"wevtapi.dll\" /DELAYLOAD:\"wininet.dll\" /DELAYLOAD:\"winusb.dll\" /DELAYLOAD:\"wsock32.dll\" /DELAYLOAD:\"wtsapi32.dll\""
        WriteFile(commandPath, command)
        oldCwd = os.getcwd()
        os.chdir(buildDir)
        RunVsDevCommand(f"cl @command.txt")
        os.chdir(oldCwd)
    else:
        command += f" -static -static-libstdc++ -static-libgcc {"" if RELEASE else "-g"} "
        command += f" {" ".join([ f"\"{objectPath}\"" for objectPath in reversed(objectPaths) ])} "
        command += f" -o \"{binaryPath}\" "
        WriteFile(commandPath, command)
        oldCwd = os.getcwd()
        os.chdir(buildDir)
        output, code = RunMuslCommand(f"g++ @command.txt", capture=True, check=False)
        if code != 0:
            raise Exception(output)
        os.chdir(oldCwd)
    return binaryPath

# Libraries
def BuildLibDrm(ENV):
    libdrmDir = os.path.join(ENV["OBJ"], "libdrm")
    if not os.path.exists(libdrmDir):
        print("Cloning libdrm...")
        RunCommand(f"git clone https://gitlab.freedesktop.org/mesa/libdrm.git \"{libdrmDir}\"")
    
    muslGccPath = os.path.join(ENV["MUSL"], "gcc")
    libdrmBuildDir = os.path.join(ENV["OBJ"], "libdrm_build")
    if not os.path.exists(libdrmBuildDir):
        print("Building libdrm...")
        oldCwd = os.getcwd()
        os.chdir(libdrmDir)
        RunCommand(f"CC=\"{muslGccPath}\" meson setup build --reconfigure --prefix=\"{libdrmBuildDir}\" --default-library=static -Dintel=disabled -Dradeon=disabled -Damdgpu=disabled -Dnouveau=disabled -Dvmwgfx=disabled -Detnaviv=disabled -Dfreedreno=disabled -Dexynos=disabled -Domap=disabled -Dtegra=disabled -Dcairo-tests=disabled -Dvalgrind=disabled -Dman-pages=disabled")
        RunCommand(f"ninja -j$(nproc) -C build")
        RunCommand(f"ninja -C build install")
        shutil.rmtree(os.path.join(libdrmBuildDir, "lib", "pkgconfig"))
        os.chdir(oldCwd)
    ENV["INCLUDES"].append(os.path.join(libdrmBuildDir, "include"))
    ENV["INCLUDES"].append(os.path.join(libdrmBuildDir, "include", "libdrm"))
def BuildLibAlsa(ENV):
    objDir=os.path.join(ROOT, "obj")
    os.makedirs(objDir, exist_ok=True)
    libalsaDir = os.path.join(objDir, "libalsa")
    if not os.path.exists(libalsaDir):
        print("Cloning libalsa...")
        RunCommand(f"git clone https://github.com/alsa-project/alsa-lib.git \"{libalsaDir}\"")
    muslGccPath = os.path.join(objDir, "musl", "bin", "gcc")
    libalsaBuildDir = os.path.join(objDir, "libalsa_build")
    if not os.path.exists(libalsaBuildDir):
        print("Building libalsa...")
        oldCwd = os.getcwd()
        os.chdir(libalsaDir)
        RunCommand("autoreconf -i")
        RunCommand(f"CC=\"{muslGccPath}\" ./configure --prefix=\"{libalsaBuildDir}\" --disable-shared --enable-static --disable-python --disable-hwdep --disable-topology --disable-aload --disable-mixer --disable-seq --disable-rawmidi --disable-ucm --disable-old-symbols --without-versioned")
        RunCommand(f"make -j$(nproc)")
        RunCommand(f"make install")
        shutil.rmtree(os.path.join(libalsaBuildDir, "bin"))
        shutil.rmtree(os.path.join(libalsaBuildDir, "lib", "pkgconfig"))
        os.remove(os.path.join(libalsaBuildDir, "lib", "libasound.la"))
        shutil.rmtree(os.path.join(libalsaBuildDir, "share", "aclocal"))
        os.chdir(oldCwd)

# Main
print(ParseRecipe(ReadFile("/important_data/EpsilonTheatrics/stamk/example_project/.stamk")))
sys.exit(0)

os.chdir("/important_data/EpsilonTheatrics/stamk/example_project/")
if os.geteuid() == 0:
    raise Exception("Stamk may not be run as root.")
ENV = InitEnv()
print(ENV)
os.chdir(ENV.ROOT)

if ENV.TARGET == "RELEASE":
    RunCommand(f"strip -s \"{ENV.BINARY}\"")
sys.exit(0)