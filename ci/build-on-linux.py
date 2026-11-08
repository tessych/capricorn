import os
import glob
import subprocess
import sys
import urllib.request
import zipfile
import io

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out_dir = os.path.join(root, "out", "windows")
os.makedirs(out_dir, exist_ok=True)

cache_dir = os.path.expanduser("~/.cache/capri-build")
os.makedirs(cache_dir, exist_ok=True)

net48_dir = os.path.join(cache_dir, "net48", "build", ".NETFramework", "v4.8")
facades_dir = os.path.join(net48_dir, "Facades")
winmd_dir = os.path.join(cache_dir, "winmd")
winmd_ref_dir = os.path.join(winmd_dir, "ref", "netstandard2.0")
winrt_runtime_dir = os.path.join(cache_dir, "winrt_runtime")

def ensure_deps():
    if not os.path.exists(os.path.join(net48_dir, "mscorlib.dll")):
        print("[Capri] Downloading .NET 4.8 reference assemblies...")
        url = "https://api.nuget.org/v3-flatcontainer/microsoft.netframework.referenceassemblies.net48/1.0.3/microsoft.netframework.referenceassemblies.net48.1.0.3.nupkg"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp:
            data = io.BytesIO(resp.read())
        with zipfile.ZipFile(data) as zf:
            zf.extractall(os.path.join(cache_dir, "net48"))

    if not os.path.exists(os.path.join(winmd_dir, "Windows.winmd")):
        print("[Capri] Downloading Windows 10 WinRT metadata...")
        os.makedirs(winmd_dir, exist_ok=True)
        url = "https://api.nuget.org/v3-flatcontainer/directwindowswinmd.net/10.0.15063/directwindowswinmd.net.10.0.15063.nupkg"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp:
            data = io.BytesIO(resp.read())
        with zipfile.ZipFile(data) as zf:
            for item in zf.namelist():
                if item.endswith("Windows.winmd"):
                    with open(os.path.join(winmd_dir, "Windows.winmd"), "wb") as f:
                        f.write(zf.read(item))

    if not os.path.exists(os.path.join(winmd_ref_dir, "Windows.Foundation.UniversalApiContract.winmd")):
        print("[Capri] Downloading Windows SDK Contracts...")
        url = "https://api.nuget.org/v3-flatcontainer/microsoft.windows.sdk.contracts/10.0.19041.1/microsoft.windows.sdk.contracts.10.0.19041.1.nupkg"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp:
            data = io.BytesIO(resp.read())
        with zipfile.ZipFile(data) as zf:
            for item in zf.namelist():
                if item.startswith("ref/netstandard2.0/"):
                    target = os.path.join(winmd_dir, item)
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with open(target, "wb") as f:
                        f.write(zf.read(item))

    if not os.path.exists(os.path.join(winrt_runtime_dir, "System.Runtime.WindowsRuntime.dll")):
        print("[Capri] Downloading System.Runtime.WindowsRuntime...")
        os.makedirs(winrt_runtime_dir, exist_ok=True)
        for pkg in ["system.runtime.windowsruntime", "system.runtime.interopservices.windowsruntime"]:
            url = f"https://api.nuget.org/v3-flatcontainer/{pkg}/4.3.0/{pkg}.4.3.0.nupkg" if "interop" in pkg else f"https://api.nuget.org/v3-flatcontainer/{pkg}/4.6.0/{pkg}.4.6.0.nupkg"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as resp:
                data = io.BytesIO(resp.read())
            with zipfile.ZipFile(data) as zf:
                for item in zf.namelist():
                    if item.startswith("ref/netstandard2.0/") or item.startswith("ref/netstandard1.3/"):
                        target = os.path.join(winrt_runtime_dir, os.path.basename(item))
                        with open(target, "wb") as f:
                            f.write(zf.read(item))

ensure_deps()

app_exe = os.path.join(out_dir, "Capri.exe")
setup_exe = os.path.join(out_dir, "Capri-Setup.exe")
icon_ico = os.path.join(root, "assets", "chip.ico")
icon_png = os.path.join(root, "assets", "chip.png")
manifest = os.path.join(root, "app", "app.manifest")

shared = [
    "csc",
    "/nologo",
    "/target:winexe",
    "/platform:anycpu",
    "/optimize+",
    "/utf8output",
    "/warn:4",
    "/define:LINUX_CROSS",
    f"/win32manifest:{manifest}",
    f"/win32icon:{icon_ico}",
    "/nostdlib+",
    f"/reference:{os.path.join(net48_dir, 'mscorlib.dll')}",
    f"/reference:{os.path.join(net48_dir, 'System.dll')}",
    f"/reference:{os.path.join(net48_dir, 'System.Core.dll')}",
    f"/reference:{os.path.join(net48_dir, 'System.Drawing.dll')}",
    f"/reference:{os.path.join(net48_dir, 'System.Windows.Forms.dll')}",
]

winmd_refs = [
    f"/reference:{os.path.join(winmd_dir, 'Windows.winmd')}",
    f"/reference:UAC={os.path.join(winmd_ref_dir, 'Windows.Foundation.UniversalApiContract.winmd')}",
    f"/reference:FC={os.path.join(winmd_ref_dir, 'Windows.Foundation.FoundationContract.winmd')}",
]

references = [
    f"/reference:{os.path.join(net48_dir, 'System.Runtime.Serialization.dll')}",
    f"/reference:{os.path.join(net48_dir, 'System.IO.Compression.dll')}",
    f"/reference:{os.path.join(net48_dir, 'System.IO.Compression.FileSystem.dll')}",
    f"/reference:{os.path.join(net48_dir, 'System.Security.dll')}",
    f"/reference:{os.path.join(net48_dir, 'UIAutomationClient.dll')}",
    f"/reference:{os.path.join(net48_dir, 'UIAutomationTypes.dll')}",
    f"/reference:{os.path.join(net48_dir, 'WindowsBase.dll')}",
    f"/reference:{os.path.join(net48_dir, 'System.Speech.dll')}",
] + winmd_refs + [
    f"/reference:{os.path.join(facades_dir, 'netstandard.dll')}",
    f"/reference:{os.path.join(facades_dir, 'System.Runtime.dll')}",
    f"/reference:{os.path.join(winrt_runtime_dir, 'System.Runtime.WindowsRuntime.dll')}",
    f"/reference:{os.path.join(facades_dir, 'System.Runtime.InteropServices.WindowsRuntime.dll')}",
]

resources = [
    f"/resource:{icon_ico},Capri.Chip.ico",
    f"/resource:{os.path.join(root, 'assets', 'fonts', 'ShareTechMono-Regular.ttf')},Capri.Font.Mono.ttf",
    f"/resource:{os.path.join(root, 'assets', 'cursor.png')},Capri.Cursor.png",
    f"/resource:{os.path.join(root, 'assets', 'lines-russian.txt')},Capri.Lines.Russian.txt",
    f"/resource:{os.path.join(root, 'assets', 'vbcable', 'VBCABLE_Driver_Pack45.zip')},Capri.VBCABLE.zip",
]

for spr in glob.glob(os.path.join(root, "assets", "sprites", "*.png")):
    resources.append(f"/resource:{spr},Capri.Sprite.{os.path.basename(spr)}")

for wav in glob.glob(os.path.join(root, "assets", "voice", "*.wav")):
    resources.append(f"/resource:{wav},Capri.Voice.{os.path.basename(wav)}")

source_names = [
    'Capri', 'Asides', 'Bolts', 'Commentary', 'Lookout', 'Brain', 'PlanBrain', 'Talk',
    'Mainframe', 'MainframeMods', 'MainframeModsWindow', 'MainframeSlide', 'Mods',
    'ModDirectory', 'CodeMods', 'SoundsLike', 'SkinMods', 'SkillMods', 'ArtColors',
    'MainframeTips', 'TipChecks', 'MediumChecks', 'FreeKeyChecks', 'Neon', 'Notice',
    'Engine', 'Ledges', 'Voice', 'Ears', 'MicMix', 'CableSetup', 'Packaged',
    'Dictation', 'HearingStatus', 'Agent', 'Hands', 'GameHud', 'Computer', 'Arrange',
    'Mixer', 'Usage', 'Network', 'Play', 'VoicePack', 'Startup', 'Presence', 'Player',
    'Ocr', 'GameEars', 'GameNotes', 'GameKeys', 'Frames', 'Reminders', 'GameSense',
    'GameWatch', 'SelfKnow', 'Care', 'Clips', 'ClipSettings', 'ClipChecks', 'Minis',
    'Chess', 'ChessBoard', 'Files', 'FileFinder', 'Websites', 'Ink', 'Clones',
    'ChaosScreen', 'Icons', 'FollowUps', 'WatchAlong', 'CallMode', 'Husk', 'CallEars',
    'CallPanel', 'Reactions', 'ToolChecks', 'ErrorChecks', 'SmokeRun', 'AssemblyInfo'
]
sources = [os.path.join(root, "app", f"{name}.cs") for name in source_names]

app_cmd = shared + references + resources + ["/unsafe+", f"/out:{app_exe}"] + sources

print("[Capri] Compiling Capri.exe...")
res = subprocess.run(app_cmd, capture_output=True, text=True)
if res.returncode != 0:
    print("Capri.exe compilation failed:")
    errors = [l for l in res.stdout.splitlines() if "error" in l.lower()]
    for e in errors[:25]:
        print(e)
    if not errors:
        print(res.stdout)
        print(res.stderr)
    sys.exit(1)

print(f"[Capri] Successfully built {app_exe}")

setup_sources = [
    os.path.join(root, "app", f"{s}.cs") for s in ["Setup", "Neon", "Notice", "VoicePack", "Startup", "AssemblyInfo"]
]
setup_cmd = shared + [
    f"/out:{setup_exe}",
    f"/reference:{os.path.join(net48_dir, 'Microsoft.CSharp.dll')}",
    f"/reference:{os.path.join(net48_dir, 'System.IO.Compression.dll')}",
    f"/reference:{os.path.join(net48_dir, 'System.IO.Compression.FileSystem.dll')}",
    f"/resource:{app_exe},Capri.App.exe",
    f"/resource:{icon_ico},Capri.Chip.ico",
    f"/resource:{icon_png},Capri.Chip.png",
] + setup_sources

print("[Capri] Compiling Capri-Setup.exe...")
res = subprocess.run(setup_cmd, capture_output=True, text=True)
if res.returncode != 0:
    print("Capri-Setup.exe compilation failed:")
    print(res.stdout)
    print(res.stderr)
    sys.exit(1)

print(f"[Capri] Successfully built {setup_exe}")
