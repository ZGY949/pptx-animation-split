# 参与改进

**简体中文** | [English](CONTRIBUTING.en.md)

本项目独立维护 Python 实现。原 PPspliT 插件的问题应先在原插件中复现，不能仅凭本工具的行为认定原项目有相同问题。

反馈本工具的问题时，请说明操作系统、Python 版本、完整命令、终端日志，以及预期和实际结果。有条件时附一份可以公开分享的最小示例，标明源页、点击次数和异常位置。不要提交未经许可的老师课件或学生资料。

修改转换规则时，保留对应回归用例，并运行：

```sh
python3 -m unittest discover -s tests -v
```

如有可使用的真实课件，再做针对性拆分、校验和视觉核对；分别记录结果，不把结构检查写成显示效果通过。新增动画支持请同步更新[支持范围说明](docs/LIMITATIONS.md)的中英文版。

当前目录结构：

```text
pptx_animation_split/  转换引擎、校验和命令行
tests/                 回归与文件操作测试
examples/              可公开的演示课件
docs/                  来源基线、限制、验证和发布准备
tools/                 源码整理工具
```

README 的中文首页为 `README.md`，英文版为 `README.en.md`；配套文档沿用相同命名，例如 `docs/LIMITATIONS.md` 与 `docs/LIMITATIONS.en.md`。修改用途、命令、支持范围或验证结论时，对应的中英文文档需同步更新。语言导航参考 [Ant Design 的 README](https://github.com/ant-design/ant-design/blob/master/README.md)：入口放在标题下，当前语言加粗，另一语言使用相对链接；交叉引用优先指向同语言文档，方便在 GitHub 和下载的源码中阅读和切换。

本项目采用 [MIT 许可证](LICENSE)。提交贡献时请确保有权提供相应代码，并保留引用代码所需的来源和许可说明。
