# 来源与致谢

**简体中文** | [English](ATTRIBUTION.en.md)

本项目受 [PPspliT](https://github.com/maxonthegit/PPspliT) 启发。原项目作者为 **Massimo Rimondini**，其 PowerPoint 插件使用 VBA，将动画步骤拆成静态幻灯片。

本项目从本地 `pptx-animation-split` 技能中的 Python 脚本整理而来，包含借助 AI 完成的实现和修复。原本地脚本使用了 `PPspliT (Python re-implementation, entry-effect subset)` 的标记；现保留来源关系，采用独立项目名称，避免与原 VBA 插件混淆。未将原插件程序、安装包或 VBA 源码复制进本项目，也未对原插件作出兼容性或修复承诺。

原本地脚本没有记录所参考的上游提交，也没有逐行移植清单。因此不能把它宣称为经过审计的完全独立重写，也不能给出精确的上游代码对应范围。本次迁入前的文件校验值见 [source-baseline.json](docs/source-baseline.json)。

## 作者对独立发布的说明

2026 年 11 月 9 日（北京时间），Massimo Rimondini 在 [Issue #29 的回复](https://github.com/maxonthegit/PPspliT/issues/29#issuecomment-6727916615)中说明：

- 原项目保持 VBA PowerPoint 插件的方向，其他实现适合单独维护。
- 其他语言的实现可独立分发。
- 如果以 PPspliT 的部分代码为基础，应适当署名并提供原项目链接；完全独立的实现也欢迎注明来源。

本项目保留以上致谢和回链。原项目许可原文位于 [src/license.txt](https://github.com/maxonthegit/PPspliT/blob/master/src/license.txt)，不是 MIT 许可证。上述回复也不应被表述为“原项目改用 MIT”。

本项目维护者于 2026 年 11 月 9 日确认采用 [MIT 许可证](LICENSE)，版权署名为 `ZGY949`。该许可在相关权利允许的范围内适用，不替代第三方的署名和许可条件；本来源说明与原项目回链应一并保留。

## 技术资料

- [Open XML 路径坐标](https://learn.microsoft.com/en-us/openspecs/office_standards/ms-oi29500/498c3cfa-652c-49b3-a82c-33fd94468af8)
- [Open XML 路径原点](https://learn.microsoft.com/en-us/openspecs/office_standards/ms-oe376/a94c52e0-eb04-42b7-8b57-966bbd1f6061)
- [Open XML 缩放行为](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.presentation.animatescale)

演示课件为本项目生成的通用示例，不含老师课件、教材截图或学生资料。
