import sys
import platform
import os
import sys
import lib_stamk
import shutil
from pathlib import Path

WINDOWS=(platform.system() == "Windows")
RELEASE=("release" in [ arg.lower() for arg in sys.argv[1:] ])
PROJROOT=(os.path.abspath(os.getcwd()))

muslLicenseUrl="https://git.musl-libc.org/cgit/musl/plain/COPYRIGHT"

def LinkVsCodeDir():
    vscodeDir = os.path.join(PROJROOT, ".vscode")
    vscodeDirStat = Path(vscodeDir)
    vscodeDirTarget = os.path.join(PROJROOT, "minibuild", "vscode_windows" if WINDOWS else "vscode_linux")
    vscodeDirTargetStat = Path(vscodeDirTarget)
    vscodeDirNeedsNewLink = True
    if WINDOWS:
        if vscodeDirStat.is_symlink():
            if vscodeDirStat.resolve() == vscodeDirTargetStat:
                vscodeDirNeedsNewLink = False
            else:
                vscodeDirStat.unlink()
        elif vscodeDirStat.is_dir():
            shutil.rmtree(vscodeDir)
        else:
            os.remove(vscodeDir)
        if vscodeDirNeedsNewLink:
            os.symlink(vscodeDirTarget, vscodeDir, target_is_directory=True)
    else:
        if vscodeDirStat.is_dir():
            if RunCommand(f"findmnt \"{vscodeDir}\"", check=False) == 0:
                vscodeDirNeedsNewLink = False
            else:
                shutil.rmtree(vscodeDir)
        elif vscodeDirStat.is_symlink():
            vscodeDirStat.unlink()
        else:
            os.remove(vscodeDir)
        if vscodeDirNeedsNewLink:
            os.makedirs(vscodeDir, exist_ok=True)
            print("Sudo password needed to bind vscode_linux to .vscode.")
            RunCommand(f"sudo bash -c \'mount --bind \"{vscodeDirTarget}\" \"{vscodeDir}\" && mount -o remount,bind,ro \"{vscodeDir}\"\'", echo=True)

def InstallDependencies():
    includeDirs = []
    objectPaths = []
    buildDir = os.path.join(PROJROOT, "build")
    os.makedirs(buildDir, exist_ok=True)
    if WINDOWS:
        # TODO
        windowsPackageNames = [ "libusb", "openssl" ]
        windowsPackageNames = [ "{ \"name\": \"" + package + "\" }" for package in windowsPackageNames]
        vcpkgJson = "{ \"name\": \"powercues\", \"version-string\": \"1.0.0\", \"dependencies\": [ " + ", ".join(windowsPackageNames) + " ] }"
        vcpkgJsonPath = os.path.join(buildDir, "vcpkg.json")
        if not os.path.exists(vcpkgJsonPath):
            WriteFile(vcpkgJsonPath, vcpkgJson)
        oldCwd = os.getcwd()
        os.chdir(buildDir)
        RunVsDevCommand(f"vcpkg x-update-baseline --add-initial-baseline", echo=True)
        RunVsDevCommand(f"vcpkg x-set-installed --triplet=x64-windows-static", echo=True)
        os.chdir(oldCwd)
    else:
        libusbDir = os.path.join(buildDir, "libusb")
        if not os.path.exists(libusbDir):
            print("Cloning libusb...")
            RunCommand(f"git clone git@github.com:libusb/libusb.git {libusbDir}")

        libusbBuildDir = os.path.join(buildDir, "libusb_build")
        libusbAPath = os.path.join(libusbBuildDir, "lib/libusb-1.0.a")
        libusbIncludePath = os.path.join(libusbBuildDir, "include")
        if not os.path.exists(libusbBuildDir):
            print("Building libusb...")
            oldCwd = os.getcwd()
            os.chdir(libusbDir)
            RunCommand("./bootstrap.sh")
            RunCommand(f"./configure --host=x86_64-linux-musl --enable-static --disable-shared --prefix=\"{libusbBuildDir}\"")
            RunCommand("make -j$(nproc)")
            RunCommand("make install")
            os.chdir(oldCwd)
        
        objectPaths.append(libusbAPath)
        includeDirs.append(libusbIncludePath)

        opensslDir = os.path.join(buildDir, "openssl")
        if not os.path.exists(opensslDir):
            print("Cloning openssl...")
            RunCommand(f"git clone git@github.com:openssl/openssl.git {opensslDir}")

        opensslBuildDir = os.path.join(opensslDir, "build")
        opensslAPath = os.path.join(opensslBuildDir, "lib64/libssl.a")
        libcryptoAPath = os.path.join(opensslBuildDir, "lib64/libcrypto.a")
        opensslIncludePath = os.path.join(opensslBuildDir, "include")
        if not os.path.exists(opensslBuildDir):
            print("Building openssl...")
            oldCwd = os.getcwd()
            os.chdir(opensslDir)
            RunCommand(f"./Configure linux-x86_64 no-shared no-dso no-tests --prefix=\"{opensslBuildDir}\"")
            RunCommand("make -j$(nproc)")
            RunCommand("make install_sw")
            os.chdir(oldCwd)
        
        objectPaths.append(libcryptoAPath)
        objectPaths.append(opensslAPath)
        includeDirs.append(opensslIncludePath)
    return includeDirs, objectPaths

def PreCompileAssets(assetPaths):
    objDir = os.path.join(PROJROOT, "obj")
    os.makedirs(objDir, exist_ok=True)
    assetsCppDir = os.path.join(objDir, "assets_cpp")
    os.makedirs(assetsCppDir, exist_ok=True)
    assetCppPaths = []
    for assetPath in assetPaths:
        assetName = "".join(c if c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" else "_" for c in os.path.basename(assetPath))
        assetCppPath = os.path.join(assetsCppDir, assetName + ".cpp")
        assetPathParsed = Path(assetPath)
        assetCppPathParsed = Path(assetCppPath)
        if not os.path.exists(assetCppPath) or assetPathParsed.stat().st_mtime > assetCppPathParsed.stat().st_mtime:
            assetBinary = ReadFile(assetPath, binary=True)
            assetCpp = f"#include <cstdint>\nconst uint32_t {assetName}_Length = {len(assetBinary)};\nconst uint8_t {assetName}_Data[] = " + "{ " + ", ".join(str(b) for b in assetBinary) + " };\n"
            WriteFile(assetCppPath, assetCpp)
        assetCppPaths.append(assetCppPath)
    return assetCppPaths

def CompileSources(sourcePaths, includeDirs):
    objDir = os.path.join(PROJROOT, "obj")
    os.makedirs(objDir, exist_ok=True)
    platformObjDir = os.path.join(objDir, "obj_windows" if WINDOWS else "obj_linux")
    os.makedirs(platformObjDir, exist_ok=True)
    commandPath = os.path.join(objDir, "command.txt")
    objectPaths = []
    for sourcePath in sourcePaths:
        objectPath = os.path.join(platformObjDir, os.path.splitext(os.path.basename(sourcePath))[0] + (".obj" if WINDOWS else ".o"))
        isCpp = os.path.splitext(sourcePath)[1].lower() == ".cpp"
        command = ""
        sourcePathParsed = Path(sourcePath)
        objectPathParsed = Path(objectPath)
        objectPaths.append(objectPath)
        if not os.path.exists(objectPath) or sourcePathParsed.stat().st_mtime > objectPathParsed.stat().st_mtime:
            print(sourcePath)
            if WINDOWS:
                command += f" /nologo /c /EHsc /std:c++17 {"/MT" if RELEASE else "/MTd /Od /Z7"} "
                command += f" /DWINDOWS "
                command += f" /D_UNICODE /DUNICODE /DWIN32 /D_WINDOWS /D__STDC_CONSTANT_MACROS /D__STDC_FORMAT_MACROS /D_WIN32 /DWINVER=0x0A00 /D_WIN32_WINNT=0x0A00 /DNTDDI_VERSION=NTDDI_WIN10_FE /DNOMINMAX /DWIN32_LEAN_AND_MEAN /D_HAS_EXCEPTIONS=0 /DPSAPI_VERSION=1 /DCEF_USE_SANDBOX /DCEF_USE_ATL /D_HAS_ITERATOR_DEBUGGING=0 "
                for includeDir in includeDirs:
                    command += f" /I \"{includeDir}\" "
                command += f" /Fo:\"{objectPath}\" \"{sourcePath}\" "
                WriteFile(commandPath, command)
                oldCwd = os.getcwd()
                os.chdir(objDir)
                RunVsDevCommand(f"cl @command.txt")
                os.chdir(oldCwd)
            else:
                command += f" -c -DLINUX {"" if RELEASE else "-g -O0"} -Wall {"-std=c++23" if isCpp else "-std=c23"} "
                command += f" {" ".join([ f"-I\"{includeDir}\"" for includeDir in includeDirs ])} "
                command += f" \"{sourcePath}\" -o \"{objectPath}\" "
                WriteFile(commandPath, command)
                oldCwd = os.getcwd()
                os.chdir(objDir)
                output, code = RunCommand(f"{"/mnt/ImportantData/EpsilonTheatrics/PowerCues/PowerCuesCLI/build/musl/bin/x86_64-linux-musl-g++" if isCpp else "/mnt/ImportantData/EpsilonTheatrics/PowerCues/PowerCuesCLI/build/musl/bin/x86_64-linux-musl-gcc"} @command.txt", capture=True, check=False)
                if code != 0:
                    raise Exception(output)
                os.chdir(oldCwd)
    return objectPaths

def LinkObjects(objectPaths):
    objDir = os.path.join(PROJROOT, "obj")
    os.makedirs(objDir, exist_ok=True)
    commandPath = os.path.join(objDir, "command.txt")
    binDir = os.path.join(PROJROOT, "bin")
    os.makedirs(binDir, exist_ok=True)
    binaryPath = os.path.join(binDir, "powercues.exe" if WINDOWS else "powercues")
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
        os.chdir(objDir)
        RunVsDevCommand(f"cl @command.txt")
        os.chdir(oldCwd)
    else:
        command += f" -static -static-libstdc++ -static-libgcc {"" if RELEASE else "-g"} "
        command += f" {" ".join([ f"\"{objectPath}\"" for objectPath in objectPaths ])} "
        command += f" -o \"{binaryPath}\" "
        WriteFile(commandPath, command)
        oldCwd = os.getcwd()
        os.chdir(objDir)
        output, code = RunCommand(f"g++ @command.txt", capture=True, check=False)
        if code != 0:
            raise Exception(output)
        os.chdir(oldCwd)
    return binaryPath

def main():
    if os.geteuid() == 0:
        raise Exception("This script should not be run as root.")
    os.chdir(PROJROOT)
    print()
    print(f"{"Release" if RELEASE else "Debug"} build for {"Windows" if WINDOWS else "Linux"}.")
    LinkVsCodeDir()
    assetPaths = GatherPaths(root=PROJROOT, targetDirs=[ "assets" ])
    #sourcePaths = GatherPaths(root=PROJROOT, targetDirs=[ "src" ], ignoreDirs=[ "src/old" ], targetExts=[ ".c", ".cpp", ".cc", ".c++", ".C" ])
    sourcePaths = GatherPaths(root=PROJROOT, targetPaths=[ "src/test.cpp" ])
    sourcePaths.extend(PreCompileAssets(assetPaths))
    includeDirs, objectPaths = InstallDependencies()
    objectPaths.extend(CompileSources(sourcePaths, includeDirs))
    LinkObjects(objectPaths)
    print()
    print("Build Succeeded!")
    print()
    return 0

try:
    sys.exit(main())
except Exception as ex:
    print()
    print(f"\033[0m\033[31mERROR: {str(ex)}\033[0m")
    print()