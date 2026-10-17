"""Put the original game files back from backup_original/.   python tools/restore.py"""
import os, sys, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths
for sub, dst in (("main", paths.GAME), ("special", paths.SPECIAL)):
    src = os.path.join(paths.BACKUP, sub)
    for n in sorted(os.listdir(src)):
        shutil.copyfile(os.path.join(src, n), os.path.join(dst, n)); print("restored", os.path.join(dst, n))
