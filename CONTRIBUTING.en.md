# Contributing

[简体中文](CONTRIBUTING.md) | **English**

This project independently maintains a Python implementation. Before reporting a problem with the original PPspliT add-in, reproduce it in that add-in. Behavior in this tool alone does not establish that the original project has the same problem.

When reporting an issue with this tool, include your operating system, Python version, complete command, terminal log, and expected and actual results. If possible, attach a minimal example you have permission to share publicly, identifying the source slide, number of clicks, and location of the problem. Do not submit teachers' course slides or student information without permission.

When changing conversion rules, retain a corresponding regression case and run:

```sh
python3 -m unittest discover -s tests -v
```

If you have a real presentation you are permitted to use, also perform targeted splitting, validation, and visual checks. Record these results separately; passing a structural check does not establish that the visual result is correct. When adding animation support, update both language versions of the [limitations document](docs/LIMITATIONS.en.md).

Current directory structure:

```text
pptx_animation_split/  Conversion engine, validation, and command-line interface
tests/                 Regression and file-operation tests
examples/              Demonstration decks suitable for public sharing
docs/                  Source baseline, limitations, validation, and release preparation
tools/                 Source packaging tools
```

The Chinese project homepage is `README.md`, and its English version is `README.en.md`. Supporting documents follow the same convention, such as `docs/LIMITATIONS.md` and `docs/LIMITATIONS.en.md`. Keep each pair in sync when changing the purpose, commands, supported features, or validation conclusions. Language navigation follows the approach used in the [Ant Design README](https://github.com/ant-design/ant-design/blob/master/README.md): place the entry below the title, show the current language in bold, and link to the other language using a relative path. Cross-references should lead to the document in the same language, so navigation works on GitHub and in downloaded source files.

This project uses the [MIT License](LICENSE). Ensure you have the right to contribute the code you submit, and retain any attribution and license information required for referenced code.
