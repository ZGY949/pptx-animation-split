# PPTX Animation Split

[简体中文](README.md) | **English**

Split an animated PPTX into static slides. Each source slide produces a snapshot after its initial automatic animations finish, followed by a snapshot at the end of each click step. Use the result to share course slides, print them, or export them to PDF in presentation software.

This Python tool was developed with AI assistance and inspired by [PPspliT](https://github.com/maxonthegit/PPspliT). It is maintained independently of that project. It edits PPTX files directly, without starting PowerPoint, and is not a PowerPoint add-in.

The project remains an alpha preview supporting a subset of animations. See [Releases](https://github.com/ZGY949/pptx-animation-split/releases) for public versions and run `python3 -m pptx_animation_split --version` for the local version. The project uses the [MIT License](LICENSE) and retains [attribution](ATTRIBUTION.en.md). See the [release checklist](docs/RELEASE_CHECKLIST.en.md) for preparation status.

## Choose a bundle

Each release builds two bundles from one source snapshot: choose `-tool.zip` for direct use or `-skill.zip` for use through an AI. The Skill bundle includes the matching tool and Codex plugin manifests. Each has instructions for its audience; downloading both is unnecessary. See the [tool guide](docs/TOOL.en.md) and [Skill guide](docs/SKILL.en.md) for installation, updates and removal. GitHub's automatically generated Source code ZIP still contains the full project.

Find the tool and Skill bundles in the [v0.1.0a4 preview](https://github.com/ZGY949/pptx-animation-split/releases/tag/v0.1.0a4). The existing `v0.1.0a3` still offers only GitHub's source downloads and requires a manual first upgrade. The source workflow below remains available.

## Quick start

Requires Python 3.10 or later. The tool uses only the Python standard library, with no third-party runtime dependencies. Command-line help and log messages are currently in Chinese. Local validation has used macOS and Python 3.12, with visual checks of demonstration slides and selected steps in a real course deck in WPS Office 12.1.29182. Other operating systems and presentation applications have not yet been validated.

Download and extract the project ZIP, open a terminal in the project directory, and run:

```sh
python3 --version
python3 -m pptx_animation_split --help
python3 -m pptx_animation_split split examples/demo.pptx demo-split.pptx
```

On Windows, replace `python3` with `py -3`. The demonstration should expand from 1 slide to 3: question and hint → answer appears → hint exits. The `split` command automatically checks the output file structure and supported animation states.

For your own slides, use full paths and choose a new output filename:

```sh
python3 -m pptx_animation_split split "/path/to/source.pptx" "/path/to/source-static.pptx"
```

The output must differ from the source and must not overwrite an existing file. The tool creates a temporary result, validates it, and then saves it. The output directory must already exist. The final save uses a hard link within the same directory to prevent overwriting files. If the filesystem does not support hard links, the tool reports an error; try a directory on a local disk.

Open the result in the presentation application you intend to use. Check equations, the order in which answers appear, paragraph positions, and image cropping. Programmatic validation does not replace visual checks.

When the tool detects an unsupported animation, it stops without producing an output by default. Use `split source.pptx new-output.pptx --allow-partial` only for troubleshooting when you are prepared to check every output slide manually. This saves a potentially incomplete draft and returns exit code `3`.

## Object triggers and repetition

Object-click triggers have experimental support for automatic expansion. By default, the tool finishes ordinary click steps first, then clicks each trigger object in the order of the trigger sequences stored in the file, which usually matches the animation pane order. Multiple steps controlled by one object are expanded in sequence. The log lists each object's `shape:ID` and name. The output represents this one defined route; different button orders may produce different results.

To customize the route, use `examples/click-order.json` as a starting point. Its keys are source slide numbers. `next` means an ordinary click, and `shape:4` means clicking object 4 on that source slide. Source slides not listed in the file still use automatic expansion.

```sh
python3 -m pptx_animation_split split examples/interaction-repeat-cases.pptx trigger-split.pptx --click-order examples/click-order.json
python3 -m pptx_animation_split verify examples/interaction-repeat-cases.pptx trigger-split.pptx --click-order examples/click-order.json
```

For finite repetitions, complete cycles determine duration and the order of visibility changes. Each click still produces one state; repeating an effect does not add a slide for every repetition. An infinite loop has no unique final state, so the tool keeps a representative state after one completed cycle and explains this in the log. It cannot reproduce the appearance of a loop stopped at an arbitrary moment. Unsupported cases, such as stopping partway through a cycle or accumulating repeated effects, still prevent output generation.

Finite-repeat and infinite-loop examples have been played in the local macOS WPS environment. The object-trigger input could not be played successfully in that environment, so comparison against the original presentation application remains incomplete for object triggers. Small pixel differences in enlarged text also remain unresolved. See the [validation record](docs/VALIDATION.en.md).

## Two other commands

Validate an existing result again:

```sh
python3 -m pptx_animation_split verify "/path/to/source.pptx" "/path/to/source-static.pptx"
```

Inspect text on output slides 1 and 3–5, in presentation order:

```sh
python3 -m pptx_animation_split peek "/path/to/source-static.pptx" 1 3-5
```

Text inspection also reads text in transparent placeholder paragraphs. It cannot determine whether that text is visible.

| Exit code | Meaning |
| --- | --- |
| `0` | The command completed. For splitting and validation, this only confirms checks within the supported scope. |
| `1` | A file, conversion, or validation failure occurred. The split command does not save a failed result. |
| `2` | Invalid command-line arguments. |
| `3` | An unsupported effect was detected. Splitting saves a draft only when `--allow-partial` is explicitly used. Validation of an existing result may also return this code. |

## Supported features

- Entrance and exit effects for text, images, shapes, and groups, plus some animations that show or hide individual paragraphs.
- Combinations of On Click, With Previous, After Previous, and delays. Effects that run automatically when a slide opens are included in its first static state.
- Experimental object-trigger expansion, optional custom click order, finite whole-cycle repetitions, and a representative state for infinite loops.
- Formula compatibility branches, previews of legacy embedded equations, and paragraph placeholders. Original structures are preserved rather than rewriting equations as plain text.
- Some text-color changes, rotations by a specified angle, and image and shape scaling. Uniform text scaling is supported when font sizes are explicitly defined locally.
- End positions of straight, multi-segment, cubic Bézier, and closed motion paths on top-level objects under specific conditions, including successive paths.
- Internal slide links remapped to the first static state of the target source slide. Custom shows expand in their original order. Slide transitions and automatic slide advance are removed.

See [supported conditions and known limitations](docs/LIMITATIONS.en.md) for details. Legacy `.ppt`, `.pptm`, and encrypted files are not supported. The tool does not export PDF directly or preserve animation playback, and it does not guarantee faithful reproduction of every PowerPoint effect.

Files are processed locally; the tool does not actively upload presentations. The output retains media, embedded objects, and some notes from the source. Hidden paragraphs may also retain their original text, so the output is not a tool for redaction or permanent content removal.

## Optional installation

To run the tool from outside the project directory, install the local project in your own Python virtual environment:

```sh
python3 -m pip install .
pptx-animation-split --version
pptx-animation-split split "/path/to/source.pptx" "/path/to/source-static.pptx"
```

This installs the local project; it does not mean the package has been published on PyPI. Installation may download build tools from the internet. The `python3 -m` workflow above does not require installation.

## Tests and attribution

Run from the project root:

```sh
python3 -m unittest discover -s tests -v
```

Animation regressions cover 27 combinations of triggers for three objects, as well as text, images, shapes, groups, delayed visibility changes, curves, scaling, rotation, navigation and file protection. Additional tests cover update checks, matching bundles and isolated installation. The [complex animation examples](examples/README.en.md) authored in WPS and compared against playback expand from 5 source slides to 13 states. The trigger and repetition examples expand from 3 slides to 8 states, with the limits of actual validation recorded separately. These checks do not establish support for every preset effect or arbitrary combination. See the [validation record](docs/VALIDATION.en.md), [contribution guide](CONTRIBUTING.en.md), and [attribution](ATTRIBUTION.en.md).

Thanks to Massimo Rimondini for PPspliT. The author's clarification on independent implementations and attribution is available in the [original project discussion](https://github.com/maxonthegit/PPspliT/issues/29#issuecomment-6727916615). This project does not imply support or endorsement by the original author.
