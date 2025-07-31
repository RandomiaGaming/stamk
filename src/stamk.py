from types import SimpleNamespace
import subprocess
import sys
import os
import sys
from glob import glob
import shutil
import PIL.Image
import wave

ENV = SimpleNamespace()

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
def SelectPaths(selectors=[], root=None):
    if selectors == None:
        selectors = []
    if isinstance(selectors, str):
        selectors = [ selectors ]
    if root == None:
        root = os.getcwd()
    root = os.path.abspath(root)
    oldCwd = os.getcwd()
    os.chdir(root)
    output = set()
    for selector in selectors:
        if not selector.startswith("!"):
            output.update([ os.path.abspath(matchPath) for matchPath in glob(selector, recursive=True, include_hidden=True) if os.path.isfile(matchPath) ])
    for selector in selectors:
        if selector.startswith("!"):
            selector = selector[1:]
            output.difference_update([ os.path.abspath(matchPath) for matchPath in glob(selector, recursive=True, include_hidden=True) if os.path.isfile(matchPath) ])
    os.chdir(oldCwd)
    return list(output)



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
def PrecompileMysteryImage(ENV):
    objDir=os.path.join(ROOT, "obj")
    os.makedirs(objDir, exist_ok=True)
    precompiledAssetsDir = os.path.join(objDir, "precompiled_assets")
    os.makedirs(precompiledAssetsDir, exist_ok=True)
    mysteryimageCPath = os.path.join(precompiledAssetsDir, "mysteryimage.c")
    if not os.path.exists(mysteryimageCPath):
        print("Precompiling mysteryimage...")
        assetsDir = os.path.join(ROOT, "src", "assets")
        mysteryimageTemplatePath = os.path.join(assetsDir, "mysteryimage.c.template")
        mysteryimageTemplate = ReadFile(mysteryimageTemplatePath)
        mysteryimagePath = os.path.join(assetsDir, "mysteryimage.bmp")
        mysteryimage = PIL.Image.open(mysteryimagePath).convert("RGB")
        mysteryimagePixels = mysteryimage.load()
        mysteryimageWidth, mysteryimageHeight = mysteryimage.size
        mysteryimageLength = mysteryimageWidth * mysteryimageHeight * 4
        mysteryimageBuffer = []
        for y in range(mysteryimageHeight):
            for x in range(mysteryimageWidth):
                r, g, b = mysteryimagePixels[x, y]
                mysteryimageBuffer.append(f"0xFF, 0x{r:02X}, 0x{g:02X}, 0x{b:02X}")
        mysteryimageBuffer = ", ".join(mysteryimageBuffer)
        mysteryimageTemplate = mysteryimageTemplate.replace("#width#", f"{mysteryimageWidth}")
        mysteryimageTemplate = mysteryimageTemplate.replace("#height#", f"{mysteryimageHeight}")
        mysteryimageTemplate = mysteryimageTemplate.replace("#length#", f"{mysteryimageLength}")
        mysteryimageTemplate = mysteryimageTemplate.replace("#buffer#", f"{mysteryimageBuffer}")
        WriteFile(mysteryimageCPath, mysteryimageTemplate)
def PrecompileMysterySong(ENV):
    objDir=os.path.join(ROOT, "obj")
    os.makedirs(objDir, exist_ok=True)
    precompiledAssetsDir = os.path.join(objDir, "precompiled_assets")
    os.makedirs(precompiledAssetsDir, exist_ok=True)
    mysterysongCPath = os.path.join(precompiledAssetsDir, "mysterysong.c")
    if not os.path.exists(mysterysongCPath):
        print("Precompiling mysterysong...")
        assetsDir = os.path.join(ROOT, "src", "assets")
        mysterysongTemplatePath = os.path.join(assetsDir, "mysterysong.c.template")
        mysterysongTemplate = ReadFile(mysterysongTemplatePath)
        mysterysongPath = os.path.join(assetsDir, "mysterysong.wav")
        mysterysong = wave.open(mysterysongPath, "rb")
        mysterysongChannels = mysterysong.getnchannels()
        mysterysongSampleRate = mysterysong.getframerate()
        mysterysongSamples = mysterysong.readframes(mysterysong.getnframes())
        mysterysongLength = len(mysterysongSamples)
        mysterysongBuffer = []
        for i in range(mysterysongLength):
            mysterysongBuffer.append(f"0x{mysterysongSamples[i]:02X}")
        mysterysongBuffer = ", ".join(mysterysongBuffer)
        mysterysongTemplate = mysterysongTemplate.replace("#channels#", f"{mysterysongChannels}")
        mysterysongTemplate = mysterysongTemplate.replace("#samplerate#", f"{mysterysongSampleRate}")
        mysterysongTemplate = mysterysongTemplate.replace("#length#", f"{mysterysongLength}")
        mysterysongTemplate = mysterysongTemplate.replace("#buffer#", f"{mysterysongBuffer}")
        WriteFile(mysterysongCPath, mysterysongTemplate)
def Compile(ENV):
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
def Link():
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

if os.geteuid() == 0:
    raise Exception("Stamk may not be run as root.")
ENV.RELEASE = "release" in [ arg.lower() for arg in sys.argv[1:] ]
ENV.PLATFORM = "LINUX"
if sys.platform == "win32" or sys.platform == "cygwin":
    ENV.PLATFORM = "WINDOWS"
elif sys.platform == "darwin" or sys.platform == "ios":
    ENV.PLATFORM = "MAC"
ENV.ROOT = os.path.abspath(os.getcwd())
os.chdir(ENV.ROOT)
ENV.RECIPE = os.path.join(ENV.ROOT, ".stamk")
if not os.path.isfile(ENV.RECIPE):
    raise Exception("Recipe file .stamk could not be found in the current directory.")
ENV.BIN = os.path.join(ENV.ROOT, "bin")
os.makedirs(ENV.BIN, exist_ok=True)
ENV.OBJ = os.path.join(ENV.ROOT, "obj")
os.makedirs(ENV.OBJ, exist_ok=True)
ENV.MUSL = os.path.join()
ENV.CC = ""
ENV.CXX = ""
ENV.SOURCES = []
ENV.INCLUDES = []
ENV.OBJECTS = []
print(ENV)
sys.exit(0)
print()
print(f"{"Release" if ENV["RELEASE"] else "Debug"} build for Linux with Musl.")
print()
InstallMusl(ENV)
BuildLibDrm(ENV)
BuildLibAlsa(ENV)
PrecompileMysteryImage(ENV)
PrecompileMysterySong(ENV)
Compile()
Link()
if RELEASE:
    RunCommand(f"strip -s \"{os.path.join(ROOT, "bin", "mystery")}\"")
print()
print("Build Succeeded!")
print()