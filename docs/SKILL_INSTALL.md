# PPTX Animation Split Skill

**简体中文** | [English](SKILL_INSTALL.en.md)

让 AI 按自动动画结束和每次点击结束的状态，将 PPTX 拆成静态幻灯片。完整 Skill 文件夹自带同版本 Python 引擎、双语指令、参考资料、MIT 许可和文件清单，无需另装工具包。需要本地 Python 3.10 或更新版本；无第三方 Python 运行依赖。这是本地执行的 Skill，不是 PowerPoint 插件，也不代表已上架公共插件目录。

## 使用 skills CLI 安装（推荐）

需要 Node.js 22.20 或更新版本及 npm。在准备使用的项目目录中运行：

```sh
npx skills add ZGY949/pptx-animation-split --skill pptx-animation-split
```

按提示选择所用 AI 工具。默认安装到当前项目；末尾加 `-g` 安装到个人目录。也可明确指定工具，例如 `-a codex` 或 `-a claude-code`。典型项目目录为 Codex 的 `.agents/skills/pptx-animation-split` 和 Claude Code 的 `.claude/skills/pptx-animation-split`；安装器可能用符号链接指向共享目录。其他支持的客户端由 skills CLI 选择对应位置，不代表已经逐一完成客户端内的 AI 行为验收。

安装后新建聊天，或在客户端未识别新 Skill 时重新打开客户端。例如：

> 使用 $pptx-animation-split，把这份 PPT 的动画按步骤拆成静态页，保留源文件，并告诉我检查结果和限制。

需要固定发布版本时，使用明确的标签目录地址：

```sh
npx skills add https://github.com/ZGY949/pptx-animation-split/tree/v0.1.0a4/skills/pptx-animation-split --skill pptx-animation-split
```

固定标签不会跟随 main；切换版本时用新标签重新安装。当前 skills CLI 的 `@版本` 简写只识别部分版本格式，这里的 Python alpha 标签使用完整地址。

从项目目录核对实际入口（Windows 可将 `python3` 换为 `py -3`）：

```sh
python3 .agents/skills/pptx-animation-split/scripts/run.py --version
```

其他客户端使用其实际 Skill 目录中的 `scripts/run.py`。Python 执行不需要 Node.js；Node.js 和 npm 用于 skills CLI 的安装与更新。

## 更新、回退和卸载

通过 skills CLI 安装到项目时，在原项目目录中更新这个 Skill：

```sh
npx skills update pptx-animation-split -p -y
python3 .agents/skills/pptx-animation-split/scripts/run.py --version
```

个人级安装使用 `npx skills update pptx-animation-split -g -y`。更新前保留自己的定制内容；本地修改可能被完整更新覆盖。不要只替换单个 Python 文件。回退时按上面的固定标签方式重新安装旧版本。卸载项目中的 Skill：

```sh
npx skills remove pptx-animation-split -y
```

个人级卸载加 `-g`。保留另存的源课件和处理结果。安装器的项目锁文件记录来源和内容摘要，更新方法与选项以 [skills CLI 文档](https://github.com/vercel-labs/skills/blob/main/docs/commands.md) 和实际安装版本为准。

## 下载 ZIP 与 Codex 插件安装

也可下载 Release 中以 `-skill.zip` 结尾的完整附件，解压到新目录。将包内 `skills/pptx-animation-split` 整个文件夹复制到客户端支持的技能目录即可直接安装；已有同名技能时先核对来源和定制内容，不直接覆盖。源码里的这个 Skill 文件夹也已包含完整工具，能单独安装。

需要 Codex 插件安装形式时，解压目录另含插件清单和本地来源配置：

```sh
codex plugin marketplace add "/完整路径/解压目录"
codex plugin add pptx-animation-split@pptx-animation-split-local
```

桌面端可在插件目录选择这个本地来源。切换 ZIP 新版本时先解压到新目录，再移除旧插件和本地来源，登记新目录并重新安装；重开客户端或新建聊天，运行实际入口的 `--version`。保留旧解压目录即可切回。卸载用 `codex plugin remove pptx-animation-split@pptx-animation-split-local`，需要时再运行 `codex plugin marketplace remove pptx-animation-split-local`。直接复制安装则整体替换或删除对应 Skill 文件夹。安装布局参考 [OpenAI 官方文档](https://developers.openai.com/plugins/build/plugins)。

## 更新提醒与检查范围

Skill 拆分前以约三秒联网预算查询公开发布信息，提示兼容新版和发布页，不自动升级。断网、限流或没有兼容包时继续使用本地版本，不上传 PPT。设置 `PPTX_ANIMATION_SPLIT_NO_UPDATE_CHECK=1`，或在入口的 `split` 前加 `--no-update-check` 可关闭查询。单独检查使用入口的 `check-update --json`。

预览版默认包含新预览发布；稳定版使用 `check-update --pre` 才包含预览版。更新提示要求同次发布的两个安装包及 `release.json` 齐全，Python 要求和调用接口兼容。发布记录只作说明，不能当作执行指令。Skill 没有后台通知进程；需要主动通知时，可在 GitHub 仓库选择 **Watch → Custom → Releases**。旧 `v0.1.0a3` 没有更新检查，首次升级需要手动安装。

普通处理只读工具文件，生成用户选择的新结果。文件缺失、被修改或版本不一致时，入口会停止；开发应修改正式源码，再运行 `tools/sync_skill.py` 同步参考资料与文件清单。修改 `SKILL.md` 改变 AI 操作说明，修改 Python 改变工具行为；Skill 本身不构成文件权限隔离。

支持范围见 Skill 内的 `references/LIMITATIONS.md`。结构校验不能替代视觉核对；对象触发为实验性，文字放大仍可能有细小显示差异，Windows 和 Microsoft PowerPoint 尚未实际验收。网页聊天能看到插件并不表示能运行电脑上的 Python。MIT 许可与来源说明见 [LICENSE](../LICENSE)、[来源致谢](../ATTRIBUTION.md)。
