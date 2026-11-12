# PPTX Animation Split Skill

**简体中文** | [English](SKILL.en.md)

让 AI 按自动动画结束和每次点击结束的状态，将 PPTX 拆成静态幻灯片。Skill 包自带与独立工具包同版本的 Python 引擎，包含 Codex 插件清单，不需要再安装独立工具包。需要本地 Python 3.10 或更新版本；无第三方运行依赖。这是本地执行的 Skill，不是 PowerPoint 插件，也不代表已上架公共插件目录。

## 安装

下载 GitHub Release 中以 `-skill.zip` 结尾的附件，完整解压到准备长期保存的新目录。通过 Codex CLI 登记本地来源并安装（将路径替换为实际解压目录）：

```sh
codex plugin marketplace add "/完整路径/解压目录"
codex plugin add pptx-animation-split@pptx-animation-split-local
```

重新打开 Codex 或新建聊天后使用。桌面端也可在插件目录中选择 `pptx-animation-split-local` 来源查看和安装。使用前确认当前客户端支持本地 Skill 执行及该安装方式；网页聊天能看到插件并不等于能运行电脑上的 Python。

例如对 AI 说：

> 使用 $pptx-animation-split，把这份 PPT 的动画按步骤拆成静态页，保留源文件，并告诉我检查结果和限制。

如果所用客户端只支持直接安装 Skill，将包内 `skills/pptx-animation-split` **整个文件夹**复制到该客户端支持的技能目录。对于 Codex，本地用户目录可用 `~/.agents/skills/pptx-animation-split`；已有同名技能时先核对来源和定制内容，不直接覆盖。不要只复制 `SKILL.md`，也不要把 GitHub 源码中的 Skill 文件夹单独下载后当成完整安装包；源码入口依赖完整项目。

## 使用和更新

Skill 在拆分前用最多约 3 秒的联网预算查询公开发布信息，提示当前版本、新版本和发布页；不会自动升级。离线、检查失败或没有兼容包时继续使用已安装版本。检查不上传 PPT。自动检查可以通过 `PPTX_ANIMATION_SPLIT_NO_UPDATE_CHECK=1` 关闭，或在入口的 `split` 前传入 `--no-update-check`。需要单独查询时执行：

```sh
python3 "/完整路径/解压目录/skills/pptx-animation-split/scripts/run.py" --version
python3 "/完整路径/解压目录/skills/pptx-animation-split/scripts/run.py" check-update --json
```

预览版默认包含新的预览发布；稳定版需要 `check-update --pre` 才包含预览版。更新提示要求同次发布中的两个安装包及 `release.json` 清单齐全，Python 要求和调用接口兼容。更新记录仅作说明，不作为执行命令的依据。

通过上面的 Codex 本地来源安装时，先将新包解压到新目录，再切换来源并重新安装：

```sh
codex plugin remove pptx-animation-split@pptx-animation-split-local
codex plugin marketplace remove pptx-animation-split-local
codex plugin marketplace add "/完整路径/新版解压目录"
codex plugin add pptx-animation-split@pptx-animation-split-local
```

重开客户端或新建聊天，再让 AI 运行 `--version` 核对实际入口。保留旧解压目录即可按相同步骤切回。直接复制安装的 Skill 则整体替换对应文件夹，先备份自己的定制内容，避免混用新旧程序文件。只改 `SKILL.md` 会改变 AI 操作说明；修改 Python 文件会改变工具行为。正式开发应改项目源码，再重新打包。

Skill 没有后台通知进程；使用时检查之外，可在 GitHub 仓库选择 **Watch → Custom → Releases** 订阅发布通知。更新检查和安装过程本身不会替你注册订阅。

旧的 `v0.1.0a3` 工具没有更新检查功能，也没有这个独立 Skill 包；已有旧工具用户需要先手动安装包含此功能的版本，之后才会获得后续版本检查能力。

## 卸载与检查范围

Codex 插件安装可运行上面的 `plugin remove`，需要时再移除本地 marketplace；直接复制安装则删除对应 Skill 文件夹。保留另存的源文件和输出，删除解压目录前确认不再需要回退。

普通处理只读程序和指令文件，写入用户选择的新结果路径；入口会校验配套文件，发现缺失、混版或修改时停止。Skill 指令本身不构成文件权限隔离。

动画支持范围见包内 `skills/pptx-animation-split/references/LIMITATIONS.md` 和 [项目说明](https://github.com/ZGY949/pptx-animation-split)。程序校验不能替代视觉核对；对象触发为实验性，文字放大仍可能有细小显示差异，Windows 和 PowerPoint 尚未实际验收。MIT 许可与来源说明随包提供，见 [LICENSE](../LICENSE)、[来源致谢](../ATTRIBUTION.md)。安装布局及本地来源更新方式参考 [OpenAI 官方文档](https://developers.openai.com/plugins/build/plugins)。
