# PPTX Animation Split

把带动画的 PPTX 拆成静态幻灯片：保留每张源页进入后自动动画结束的状态，以及各次点击结束后的状态，便于课件分发、打印或后续导出 PDF。

本项目是受 [PPspliT](https://github.com/maxonthegit/PPspliT) 启发、借助 AI 开发的 Python 工具，独立于原项目维护。它直接处理 PPTX，不需要启动 PowerPoint，也不是 PowerPoint 插件。

当前版本：`0.1.0a3`，发布准备版。只支持部分动画。采用 [MIT 许可证](LICENSE)，保留[来源致谢](ATTRIBUTION.md)；发布状态见[发布清单](docs/RELEASE_CHECKLIST.md)。

## 快速使用

需要 Python 3.10 或更新版本。运行工具只用 Python 标准库，不需要安装第三方运行依赖。当前本地验证环境为 macOS、Python 3.12，已在 WPS Office 12.1.29182 中核对演示课件与真实课件重点步骤；其他系统和演示软件尚待验证。

下载项目 ZIP 并解压，在终端进入项目文件夹后执行：

```sh
python3 --version
python3 -m pptx_animation_split --help
python3 -m pptx_animation_split split examples/demo.pptx demo-split.pptx
```

Windows 可将命令中的 `python3` 换为 `py -3`。演示课件应由 1 页变为 3 页：题目和提示 → 答案出现 → 提示退出。`split` 会自动检查输出文件结构和已支持的动画状态。

处理自己的课件时，使用完整路径，并给输出起一个新名字：

```sh
python3 -m pptx_animation_split split "/路径/源课件.pptx" "/路径/源课件_静态版.pptx"
```

输出不能与源文件相同，也不能覆盖已有文件。先生成临时结果，校验通过后再保存；输出目录必须已经存在。最终保存使用同目录硬链接以防覆盖；不支持硬链接的文件系统会报告错误，可改用本机磁盘目录。

拆分完请用实际使用的演示软件打开结果，核对公式、答案出现顺序、段落位置和图片裁剪。程序校验不能代替视觉检查。

遇到已检测出的未支持动画时，默认停止并不生成结果。只有为了排查问题、愿意逐页人工核对草稿时，才使用 `split 源文件.pptx 新结果.pptx --allow-partial`；此时返回退出码 `3`，结果可能不完整。

## 对象触发与重复播放

对象点击触发支持实验性自动展开：默认先完成普通点击，再按文件中触发序列的顺序（通常对应动画窗格顺序）依次点击各触发对象。一个对象控制的多步动画会依次展开；日志会列出 `shape:编号` 和对象名称。输出保存这一条确定路线，不能代表任意按钮顺序都得到相同画面。

需要调整路线时，可参照 `examples/click-order.json`：键是源页码，`next` 表示普通点击，`shape:4` 表示点击源页对象 4。没有列出的源页继续自动展开。

```sh
python3 -m pptx_animation_split split examples/interaction-repeat-cases.pptx trigger-split.pptx --click-order examples/click-order.json
python3 -m pptx_animation_split verify examples/interaction-repeat-cases.pptx trigger-split.pptx --click-order examples/click-order.json
```

有限次重复按完整周期计算持续时间和显隐先后，每个点击仍输出一个状态，不按重复次数增加页面。无限循环没有唯一终态，默认保留一轮完成后的代表状态，并在日志说明；它不能还原在任意时刻点击停止时的画面。停在半周期、重复累加等未支持情形仍会停止生成。

本机 macOS WPS 已实际播放有限重复和无限循环样例，但对象触发输入在该环境未成功播放，不能把这部分标为原软件对照通过；文字放大的少量像素差异仍未消除。详情见[验证记录](docs/VALIDATION.md)。

## 另外两个命令

重新校验已有结果：

```sh
python3 -m pptx_animation_split verify "/路径/源课件.pptx" "/路径/源课件_静态版.pptx"
```

按放映顺序抽查第 1、3～5 页文字：

```sh
python3 -m pptx_animation_split peek "/路径/源课件_静态版.pptx" 1 3-5
```

文字抽查会读到透明占位段落里的文字，不能用于判断文字是否可见。

| 退出码 | 含义 |
| --- | --- |
| `0` | 本命令已完成；拆分和校验仅代表检查范围内通过 |
| `1` | 文件、转换或校验失败；拆分命令不保存失败结果 |
| `2` | 命令参数用法错误 |
| `3` | 检测到未支持效果；仅明确使用 `--allow-partial` 的拆分会保存草稿，已有结果的校验也可能返回此码 |

## 支持范围

- 文字、图片、形状和分组的进入、退出，以及部分按段落显示或隐藏的动画。
- 点击、同时、之后和延时组合；进入页后自动执行的效果合并到首个静态状态。
- 实验性对象触发展开、可选自定义点击顺序，以及有限整周期重复和无限循环代表状态。
- 公式的兼容分支、旧式嵌入公式预览和段落占位；保留原生结构，不把公式改写为普通文字。
- 部分文字变色、按角度旋转、图片和形状缩放；本地字号明确的文字支持等比缩放。
- 满足特定条件的顶层对象直线、多段线、三次贝塞尔曲线和封闭路径终点，包括连续路径。
- 拆分后的内部页间链接重新定位到目标源页的首个静态状态，自定义放映按原顺序展开；移除切换和自动翻页设置。

具体条件和已知限制见[支持范围说明](docs/LIMITATIONS.md)。不支持旧版 `.ppt`、`.pptm` 或加密文件；不直接导出 PDF，不保留动画播放过程，也不保证完整还原所有 PowerPoint 效果。

工具在本地处理文件，不主动上传课件。输出会保留源课件的媒体、嵌入对象和部分备注；隐藏段落也可能仍含原文字，因此输出不是脱敏或彻底删除内容的工具。

## 可选安装

如果希望离开项目文件夹也能调用，可在自己的 Python 虚拟环境中安装本地项目：

```sh
python3 -m pip install .
pptx-animation-split --version
pptx-animation-split split "/路径/源课件.pptx" "/路径/源课件_静态版.pptx"
```

这是本地安装，不代表已在 PyPI 发布。安装时构建工具可能需要联网下载；直接使用前面的 `python3 -m` 方式不需要安装。

## 测试与来源

在项目根目录运行：

```sh
python3 -m unittest discover -s tests -v
```

现有 79 项测试包含 27 种三对象触发组合，以及文字、图片、形状、分组、延时显隐、曲线、缩放旋转、导航和文件保护。另有在 WPS 中制作并实际播放对照的[复杂动画样例](examples/README.md)，5 页拆为 13 个状态；新增触发与重复样例为 3 页拆为 8 个状态，实际验收边界另行记录。这些检查不代表所有预设效果和任意组合均已验收。查看[验证记录](docs/VALIDATION.md)、[贡献说明](CONTRIBUTING.md)和[来源致谢](ATTRIBUTION.md)。

感谢 Massimo Rimondini 的 PPspliT。作者关于独立实现和署名要求的说明见[原项目讨论](https://github.com/maxonthegit/PPspliT/issues/29#issuecomment-6727916615)。本项目不代表原作者提供支持或背书。
