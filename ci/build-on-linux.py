import os
import glob
import subprocess
import sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out_dir = os.path.join(root, "out", "windows")
os.makedirs(out_dir, exist_ok=True)

app_exe = os.path.join(out_dir, "Capri.exe")
setup_exe = os.path.join(out_dir, "Capri-Setup.exe")
icon_ico = os.path.join(root, "assets", "chip.ico")
icon_png = os.path.join(root, "assets", "chip.png")
manifest = os.path.join(root, "app", "app.manifest")

net48_dir = "/tmp/net48/build/.NETFramework/v4.8"
facades_dir = os.path.join(net48_dir, "Facades")
winmd_dir = "/tmp/winmd/ref/netstandard2.0"

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
    f"/reference:/tmp/winmd/Windows.winmd",
    f"/reference:UAC={os.path.join(winmd_dir, 'Windows.Foundation.UniversalApiContract.winmd')}",
    f"/reference:FC={os.path.join(winmd_dir, 'Windows.Foundation.FoundationContract.winmd')}",
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
    f"/reference:{os.path.join(facades_dir, 'System.Runtime.WindowsRuntime.dll')}",
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
