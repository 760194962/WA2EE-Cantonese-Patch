# PC 版构建流程

```
py tools/pc_kcap.py "backup_original/main/script.pak" work/pc_jp          # 解日文脚本（一次）
py tools/run_ic.py          # 字幕 01–12 集 ↔ PC 脚本（1001–1013，不含 1012_030_2）
py tools/make_map.py        # 映射 + 2nd run 字幕
py tools/pc_gaps.py         # 仍是日文的句子 → notes/review_gaps.tsv（审查表）、work/gaps_report.md
py tools/novel_map.py       # 外传 5000–5004；Special 版：WA2_JP=pc_jp_special WA2_SUFFIX=_special
py tools/pc_text.py         # 最终文本 work/pc_text.pkl（只收审查表第 2 栏写「采用」的句子）
py tools/build.py --weight Regular --install   # 编码、重画字库、改 exe → output/<字重>/，--install 装进游戏
py tools/restore.py         # 还原原版文件
```

## 对齐时处理的事情

- 字幕的打字机效果（一句拆成很多条首尾相接、不到 0.4 秒的字幕）合并成最后完整的一条（align.py `ass_lines`）。
- 翻译注：以「（」开头且和别的字幕同时出现的，不参与对齐（align.py `drop_notes`）。
- 台词从第 1 个字段算起（PC 脚本第一句在第 1 或第 2 个字段）；资源名（ギター.tga）、合称说话人（春希＆かずさ）、
  只出现一次的说话人（留守番電話）不算台词（scr.py）。
- 1012_030_2 是 1012_030 后半段逐句相同的副本（回想），不参与对齐，最后按同一句照搬。
- 第 7 集演唱会时伊緒、武也的旁白式对话（字幕的 Io、Takeya 样式）在 PC 脚本里没有。
- 字幕没有的只有千晶的两场：1008_020（千晶和话剧社社员看演唱会）、1010_020（千晶和武也）。

## 编码和字库

- cp932 能编、字库有的字照用；NEC 选定 IBM 扩展（0xED/0xEE）改成同字的 IBM 编码（0xFA–0xFC）。
- cp932 编不出的：「—」→「―」、「〜」→「～」等字形相同的字（同 PS3 的 NORM）；其余用新字码
  0xF040–0xF0FC、0x8540–0x85FC、0x8640–0x86FC（共 564 个，现用 413 个）。
- ü、ó 画在脚本从不使用的半角「#」「]」位置（halfwidth.py，和其他半角字一样按字宽）。
- 字库里全部 6716 个汉字用俊羽圓體重画；俊羽圓體没有的粤字（约 130 个）用同字重的源泉圓體 TC（fonts/GenSenRounded2TC-L/R/M.otf）。
- 打包时改动过的项目用字面量 LZSS（不压缩）写入，未改动的项目保留原样：fnt.pak 约 40MB、script.pak 约 5MB。

## exe 改动（exepatch.py）

- 文件末尾新增一节 `.yue`（可读写执行）：+0 区段表（原 59 段 + 新 3 段）、+0x200 半角字宽表、+0x300 跳转代码。
- 两处 `mov reg, 0x4a14b8` 改指向新区段表；半角前进量（主程序 0x4471e8、Special 0x448d20）改成
  「字号 × 字宽 / 28 + 字距/2」。
- 俊羽圓體 1.011 的 Regular 字重拉丁字母和数字画出来是坏的（汉字正常），Regular 版半角字改用 Medium 画。
