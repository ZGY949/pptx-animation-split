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
pptx_animation_split/  源码命令行的兼容入口
skills/                完整 Skill；引擎只维护在 scripts/pptx_animation_split/
tests/                 回归与文件操作测试
examples/              可公开的演示课件
docs/                  来源基线、限制、验证和发布准备
tools/                 源码整理、同版打包和隔离检查
```

README 的中文首页为 `README.md`，英文版为 `README.en.md`；配套文档沿用相同命名，例如 `docs/LIMITATIONS.md` 与 `docs/LIMITATIONS.en.md`。修改用途、命令、支持范围或验证结论时，对应的中英文文档需同步更新。语言导航参考 [Ant Design 的 README](https://github.com/ant-design/ant-design/blob/master/README.md)：入口放在标题下，当前语言加粗，另一语言使用相对链接；交叉引用优先指向同语言文档，方便在 GitHub 和下载的源码中阅读和切换。

## 工具与 Skill 同步

引擎只维护在 `skills/pptx-animation-split/scripts/pptx_animation_split/`，根目录 `pptx_animation_split/__init__.py` 让原来的 `python3 -m pptx_animation_split` 用法继续可用；wheel 直接安装这份引擎，工具 ZIP 也从这里生成。标准 skills CLI 安装复制完整 Skill 文件夹，包含引擎及配套资源。修改 `SKILL.md` 不会自动修改 Python 算法，不编辑已解压的发行包来开发。

版本只在引擎目录的 `_version.py` 维护，插件使用的 SemVer 由它转换生成。中文正式指令为 `skills/pptx-animation-split/SKILL.md`，英文为 `SKILL.en.md`。安装说明维护在 `docs/TOOL*.md` 与 `docs/SKILL_INSTALL*.md`，限制、来源和许可也以根目录正式文档为准；生成的 Skill 副本及 `bundle.json` 一同提交，保证直接从 GitHub 安装时完整可用。`.gitattributes` 统一文本为 LF，以减少检出造成的哈希差异。

修改引擎、Skill 指令或共享文档后先同步，再检查：

```sh
python3 tools/sync_skill.py
python3 tools/sync_skill.py --check
```

同步只生成参考资料、许可证和文件清单，不复制第二套引擎。`--check` 不写文件，正式构建和本地试装都会拒绝不同步的资源。不要把安装说明命名为其他位置的 `SKILL.md`，避免被安装器误当成技能入口。

本地试装构建（输出目录必须尚不存在）：

```sh
python3 tools/build_release.py dist/local-check --local
```

脚本检查两份引擎完全一致、实际入口版本、三个样例及自定义路线，并确认运行没有修改安装包。新包、自带引擎清单、SHA-256 和验证记录一起生成。`--local` 的发布清单标记为不可正式发布，允许保留工作区未提交改动；正式构建要求干净提交和指向该提交的版本标签，见 [发布清单](docs/RELEASE_CHECKLIST.md)。构建、测试都不会上传或发布。

新增打包或更新行为时优先运行对应测试；改动 CLI 共用入口后再跑现有回归。更新检查通过模拟发布、断网、限流、不兼容版本和混版元数据测试；远端新增版本通知仍需在该版本真正发布后核对，不能把模拟结果写成端到端已验收。

本项目采用 [MIT 许可证](LICENSE)。提交贡献时请确保有权提供相应代码，并保留引用代码所需的来源和许可说明。
