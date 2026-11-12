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
skills/                 Skill instructions, launcher and UI metadata; no second engine
tests/                 Regression and file-operation tests
examples/              Demonstration decks suitable for public sharing
docs/                  Source baseline, limitations, validation, and release preparation
tools/                 Source packaging, matching bundles and isolated checks
```

The Chinese project homepage is `README.md`, and its English version is `README.en.md`. Supporting documents follow the same convention, such as `docs/LIMITATIONS.md` and `docs/LIMITATIONS.en.md`. Keep each pair in sync when changing the purpose, commands, supported features, or validation conclusions. Language navigation follows the approach used in the [Ant Design README](https://github.com/ant-design/ant-design/blob/master/README.md): place the entry below the title, show the current language in bold, and link to the other language using a relative path. Cross-references should lead to the document in the same language, so navigation works on GitHub and in downloaded source files.

## Keep the tool and Skill synchronized

Maintain the engine only in `pptx_animation_split/`. The source Skill's `scripts/run.py` calls it directly; packaging copies that same engine into both bundles. Editing `skills/pptx-animation-split/SKILL.md` does not automatically change the Python algorithm. Develop in the source project rather than an extracted release bundle.

Maintain the version only in `pptx_animation_split/__init__.py`; the plugin's SemVer representation is generated from it. Maintain installation and removal instructions in `docs/TOOL*.md` and `docs/SKILL*.md`, which become each bundle's README. Limitations and attribution are also generated from the maintained documents.

Build for local testing into a new output directory:

```sh
python3 tools/build_release.py dist/local-check --local
```

The script checks identical engines, actual entry-point versions, three examples and a custom route, and verifies that running the tool leaves bundle files unchanged. It generates both archives, engine inventories, SHA-256 checksums and a validation record together. A `--local` release manifest is marked unsuitable for publication and permits uncommitted workspace changes. Official builds require a clean commit and a version tag pointing to that commit; see the [release checklist](docs/RELEASE_CHECKLIST.en.md). Neither building nor testing uploads or publishes anything.

Run targeted tests for packaging or update changes; run existing regressions after changing the shared CLI entry point. Update tests cover simulated releases, offline operation, rate limits, incompatible versions and mixed metadata. Verify real newer-release notifications after a new release exists; simulation is not end-to-end release acceptance.

This project uses the [MIT License](LICENSE). Ensure you have the right to contribute the code you submit, and retain any attribution and license information required for referenced code.
