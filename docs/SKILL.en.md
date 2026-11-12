# PPTX Animation Split Skill

[简体中文](SKILL.md) | **English**

Let an AI split a PPTX into static slides after automatic animations and each click. The Skill bundle includes the same version of the Python engine as the standalone tool bundle, plus Codex plugin manifests. No separate tool bundle is required. Local Python 3.10 or later is needed, with no third-party runtime dependencies. This is a locally executed Skill, not a PowerPoint add-in, and it is not a listing in the public plugin directory.

## Install

Download the GitHub Release attachment ending in `-skill.zip` and extract the complete archive into a new permanent directory. Register the local source and install through Codex CLI, substituting the actual extracted directory:

```sh
codex plugin marketplace add "/absolute/path/to/extracted-directory"
codex plugin add pptx-animation-split@pptx-animation-split-local
```

Restart Codex or start a new chat. In the desktop plugin directory, you can also select the `pptx-animation-split-local` source to browse and install. Confirm that your client supports local Skill execution and this installation method. Seeing a plugin in web chat does not establish access to Python on your computer.

For example, ask the AI:

> Use $pptx-animation-split to expand this presentation's animation steps into static slides, preserve the source, and report the checks and limitations.

If your client supports only direct Skill installation, copy the **entire** `skills/pptx-animation-split` folder from the bundle into its supported skills location. For Codex, `~/.agents/skills/pptx-animation-split` is a user-level location. If a skill with that name already exists, inspect its source and customizations before replacing it. Do not copy only `SKILL.md` or treat the Skill directory downloaded separately from the source repository as a complete bundle; the source launcher needs the whole project.

## Use and update

Before splitting, the Skill uses a network budget of approximately three seconds to check public releases, reporting the current version, newer version and release page. It does not upgrade automatically. Offline, failed checks or the absence of a compatible bundle leave the installed version usable. Presentations are not uploaded. Disable automatic checks with `PPTX_ANIMATION_SPLIT_NO_UPDATE_CHECK=1`, or put `--no-update-check` before `split`. To query explicitly:

```sh
python3 "/absolute/path/to/extracted-directory/skills/pptx-animation-split/scripts/run.py" --version
python3 "/absolute/path/to/extracted-directory/skills/pptx-animation-split/scripts/run.py" check-update --json
```

Preview versions include newer previews by default; stable versions need `check-update --pre` to include previews. Update suggestions require both matching bundles and `release.json` in the same release, plus compatible Python requirements and command interface. Release notes are descriptions, not instructions to execute.

For the Codex local-source installation above, extract the new bundle into a new directory, then switch sources and reinstall:

```sh
codex plugin remove pptx-animation-split@pptx-animation-split-local
codex plugin marketplace remove pptx-animation-split-local
codex plugin marketplace add "/absolute/path/to/new-extracted-directory"
codex plugin add pptx-animation-split@pptx-animation-split-local
```

Restart the client or start a new chat, then have the AI run `--version` to check the actual entry point. Retain the old extracted directory to switch back using the same steps. For directly copied skills, replace the complete Skill folder after backing up your customizations; do not mix program files from different releases. Editing `SKILL.md` changes the AI workflow; editing Python changes the tool. Develop in the maintained source project and rebuild packages.

The Skill has no background notification process. Besides checking during use, users can subscribe through **Watch → Custom → Releases** on GitHub. Installation and update checking do not subscribe on their behalf.

The older `v0.1.0a3` tool has neither update checking nor this standalone Skill bundle. Existing users must manually install a version containing this feature before it can check subsequent releases.

## Uninstall and verification scope

For a Codex plugin installation, use `plugin remove` above and optionally remove the local marketplace. For directly copied skills, delete the corresponding Skill directory. Keep separately saved presentations and outputs, and retain the extracted bundle if rollback is still needed.

Normal processing reads program and instruction files and writes a new output chosen by the user. The launcher checks bundle files and stops when they are missing, modified or mixed across versions. Skill instructions themselves do not enforce filesystem isolation.

See the bundled `skills/pptx-animation-split/references/LIMITATIONS.en.md` and the [project](https://github.com/ZGY949/pptx-animation-split) for support conditions. Program validation cannot replace visual comparison. Object triggers remain experimental, text enlargement can have small display differences, and Windows and PowerPoint have not been verified in actual use. The MIT License and attribution ship with the bundle; see [LICENSE](../LICENSE) and [attribution](../ATTRIBUTION.en.md). Installation layout and local-source updates follow the [official OpenAI documentation](https://developers.openai.com/plugins/build/plugins).
