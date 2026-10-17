"""All locations in one place (PC / WHITE ALBUM2 EXTENDED EDITION).
The repo folder holds the materials (never committed):
  WHITE ALBUM2/                    main game (WA2.exe, script.pak, fnt.pak ...)
  WHITE ALBUM2 Special Contents/   WA2_Special.exe and its paks
  ic_ass/*.ass                     Cantonese subtitles (ic)
  fonts/YuPearl-1.011/tw/*.ttf     俊羽圓體; fonts/GenSenRounded2TC-M.otf fallback
Override with WA2_DATA / WA2_WORK or config.json {"data_dir": ..., "work_dir": ...}."""
import os, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_cfg = {}
if os.path.exists(os.path.join(ROOT, "config.json")):
    _cfg = json.load(open(os.path.join(ROOT, "config.json"), encoding="utf-8"))
DATA = os.environ.get("WA2_DATA") or _cfg.get("data_dir") or ROOT
WORK = os.environ.get("WA2_WORK") or _cfg.get("work_dir") or os.path.join(ROOT, "work")
os.makedirs(WORK, exist_ok=True)
GAME = os.path.join(DATA, "WHITE ALBUM2")
SPECIAL = os.path.join(DATA, "WHITE ALBUM2 Special Contents")
BACKUP = os.path.join(DATA, "backup_original")            # untouched copies of every game file the patch replaces
ASS_DIR = os.path.join(DATA, "ic_ass")
FONT_DIR = os.path.join(DATA, "fonts")
_yp = [os.path.join(FONT_DIR, "YuPearl-%s.ttf"), os.path.join(FONT_DIR, "YuPearl-1.011", "tw", "YuPearl-%s.ttf")]
YUPEARL = _yp[0] if os.path.exists(_yp[0] % "Medium") else _yp[1]
GENSEN = os.path.join(FONT_DIR, "GenSenRounded2TC-M.otf")
JP_DIR = os.path.join(WORK, os.environ.get("WA2_JP", "pc_jp")) + os.sep   # extracted Japanese scripts (main script.pak; pc_jp_special for Special Contents)
ALIGN_PKL = os.path.join(WORK, "ic_align.pkl")
MAP_PKL = os.path.join(WORK, "ic_map.pkl")
TOOLS = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(ROOT, "output")
