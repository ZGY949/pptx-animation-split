# 演示课件

`demo.pptx` 是新生成的 1 页通用演示文件，不来自老师课件。创建基础课件时使用了 python-pptx，再加入用于测试的 Open XML 动画；运行本项目不依赖 python-pptx。

示例的动画时间层级、开始条件和构建列表已补齐，并在 macOS WPS Office 12.1.29182 中实际播放核对。原示例仅通过自动拆分检查，WPS 未识别其动画；当前文件已替换为修正版本。

课件有 2 次点击：

1. 初始状态：题目 “What is 6 x 7?” 和提示可见，答案不可见。
2. 第一次点击后：“Answer: 42” 出现。
3. 第二次点击后：提示退出，题目和答案保留。

在项目根目录运行：

```sh
python3 -m pptx_animation_split split examples/demo.pptx demo-split.pptx
```

输出应为 3 页。结果必须使用新文件名；不要覆盖示例源文件。
