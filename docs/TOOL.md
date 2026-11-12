# PPTX Animation Split 工具包

**简体中文** | [English](TOOL.en.md)

这是直接使用的 Python 工具包。下载 GitHub Release 中以 `-tool.zip` 结尾的附件，解压到准备长期保存的目录；需要 Python 3.10 或更新版本，无第三方运行依赖。当前仍是预览工具，动画支持范围有限。

## 使用

在解压目录打开终端：

```sh
python3 run.py --version
python3 run.py split examples/demo.pptx demo-static.pptx
python3 run.py split "/路径/源课件.pptx" "/路径/源课件_静态版.pptx"
```

Windows 可将 `python3` 换为 `py -3`。也可以从任何工作目录用 `run.py` 的绝对路径调用。演示文件从 1 页拆成 3 页。输出目录须存在，输出文件须为新路径；拆分自动校验后保存，不覆盖源文件或已有结果。

重新校验与文字抽查：

```sh
python3 run.py verify "/路径/源课件.pptx" "/路径/源课件_静态版.pptx"
python3 run.py peek "/路径/源课件_静态版.pptx" 1 3-5
```

遇到未支持效果默认不生成结果。只有明确需要人工核对的草稿时才加 `--allow-partial`；退出码 `3` 表示存在未支持效果，不是完整通过。`0` 仅表示命令检查范围内通过，`1` 为错误，`2` 为参数错误。对象触发、自定义点击顺序及其他限制见 [支持范围](LIMITATIONS.md)。自定义路线示例在 `examples/click-order.json`，拆分与重新校验须传入同一个 `--click-order` 文件。

用实际演示软件核对公式、答案出现顺序、段落位置和图片裁剪。结构校验不能替代视觉检查。文字放大仍可能有少量显示差异，对象触发仍属实验性支持；Windows 和 Microsoft PowerPoint 尚未实际验收。输出可能保留隐藏文字、媒体、备注和嵌入对象。

## 更新和卸载

历史 `v0.1.0a3` 没有更新检查命令，首次升级需手动下载安装；装上包含此功能的版本后，才可查询后续发布。

工具包的普通拆分命令不会联网检查；需要时主动查询：

```sh
python3 run.py check-update
python3 run.py check-update --json
```

查询只读取公开发布信息，不上传 PPT，不下载或替换程序。预览版默认也检查预览发布；稳定版默认只检查稳定发布，可用 `--pre` 包含预览版。更高版本须同时具备配套安装包、兼容的 Python 要求和调用接口，才会作为可用更新提示。离线或服务限流时可继续用本地工具，手动查看 [Releases](https://github.com/ZGY949/pptx-animation-split/releases)。

更新时将新的 `-tool.zip` 解压到新目录，改用新目录中的 `run.py`，再运行 `--version`；保留旧目录即可回退，不要把新文件覆盖混入旧目录。卸载时删除工具解压目录，保留另存的源文件和处理结果。安装包发现文件被修改时会拒绝运行；定制开发请修改完整源码后重新打包。

想收到发布通知，可在 GitHub 仓库选择 **Watch → Custom → Releases**。源码、完整文档和 MIT 许可见 [项目主页](https://github.com/ZGY949/pptx-animation-split)、[LICENSE](../LICENSE) 与 [来源致谢](../ATTRIBUTION.md)。GitHub 自动生成的 Source code ZIP 包含整个项目；本工具包只包含运行所需文件和演示材料。
