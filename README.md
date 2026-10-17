# WHITE ALBUM2 EXTENDED EDITION（PC）粤文化补丁

把粤语字幕视频的译文做进 PC 版游戏（译文采集自 raymondsakura 的公开 YouTube 频道，字幕文件为 ic 系列 ASS）。字体用俊羽圓體（YuPearl），粤字缺字用源泉圓體（GenSen Rounded TC）补。
PS3 版见 [WA2-PS3-Cantonese-Patch](https://github.com/760194962/WA2-PS3-Cantonese-Patch)。

外传译名《雪融方恨遲，留待至他朝再次飄雪時》（雪が解け、そして雪が降るまで）。

本仓库只放工具、脚本和记录。游戏文件、字幕 ASS、字体都不提交；发布包也不含任何游戏文件。

## 目前进度（v0.1-beta）

- IC（1001–1013，含二周目分支）：11093 句里 11009 句换成粤文。字幕没有的只有千晶的两场（1008_020、1010_020），
  保持日文，清单见 `notes/untranslated_pc.txt`。
- 外传 5000–5004：1897 段里 1896 段换成粤文。Special Contents 的 5002 分页不同，单独对齐。
- 主程序（WA2.exe）和 Special Contents（WA2_Special.exe）都打补丁。
- 自动找回的 55 句经审查后采用 53 句（`notes/review_list.md`、`notes/review_gaps.tsv`）。
- 英文按字宽排（俊羽圓體重画半角字 + 改 exe 的半角前进量），同 PS3 版。
- 还没做：CC、coda；千晶的两场；开场视频字幕；实机只测过序章和回放记录。

## 发布包

`py tools/make_release.py v0.1-beta` → `output/release/WA2EE_Cantonese_v0.1-beta.zip`（约 4.9MB）。
用家双击「安裝補丁.bat」、把游戏文件夹拖进去即可；补丁程序（`tools/release/apply.py`，只用 Python 标准库）
先核对原版文件的 SHA-1，原文件备份到游戏文件夹的「粵語補丁備份」，「還原原版.bat」可还原。
补丁内容：exe 的差异、script.pak 里改过的字段（只有粤文）、fnt.pak 里重画过的字格。

## 构建

素材放在仓库文件夹里（都不提交）：`WHITE ALBUM2/`、`WHITE ALBUM2 Special Contents/`（游戏）、`ic_ass/*.ass`、
`fonts/YuPearl-1.011/tw/*.ttf`、`fonts/GenSenRounded2TC-{L,R,M}.otf`。第一次构建前把原版文件复制到
`backup_original/main/`、`backup_original/special/`（WA2.exe / WA2_Special.exe、script.pak、fnt.pak）。

```
pip install numpy pillow fonttools opencc-python-reimplemented capstone
```

流程见 `notes/build.md`；引擎（字库、字码表、exe 改动）见 `notes/pc_engine.md`。
