import re,glob,os,collections
import os,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import paths
JP=paths.JP_DIR
def load(name): return [x.decode("cp932","replace") for x in open(JP+name+".txt","rb").read().split(b",")]
_spk=None
def speakers():
    global _spk
    if _spk: return _spk
    c=collections.Counter()
    for f in glob.glob(JP+"*.txt"):
        t=[x.decode("cp932","replace") for x in open(f,"rb").read().split(b",")]
        for i in range(1,len(t)):
            if t[i].startswith(("「","（","『")) and 0<len(t[i-1])<=9 and not re.search("[。、！？…]|\\\\n",t[i-1]): c[t[i-1]]+=1
    _spk={k for k,v in c.items() if v>=2 and not k.startswith("『")}|{"？？？"}
    return _spk
def is_text(s):
    if s=="" or s in speakers(): return False
    if re.fullmatch(r"[\x21-\x7e]+",s): return False
    if re.search(r"\.(tga|ani|amp|bmp|png|ogg|wav)$",s,re.I): return False          # resource names (ギター.tga)
    if re.fullmatch(r"[^「（『。、！？…\\]{1,12}[＆・][^「（『。、！？…\\]{1,12}",s): return False   # joint speakers (春希＆かずさ)
    return True
def _speaker_at(t,i):     # one-off speaker labels (留守番電話, 女性観客１): short, no punctuation, a quoted line follows
    return (0<len(t[i])<=10 and not re.search(r"[。、！？…「」『』（）\\]",t[i])
            and i+1<len(t) and t[i+1][:1] in "「『（")
def lines(name, a=1):
    t=load(name); return [(i,t[i]) for i in range(a,len(t)) if is_text(t[i]) and not _speaker_at(t,i)]
