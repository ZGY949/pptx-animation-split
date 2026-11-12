# PPTX Animation Split Skill

[简体中文](SKILL_INSTALL.md) | **English**

Let an AI expand a PPTX into static slides after automatic animations and each click. The complete Skill directory includes the matching Python engine, bilingual instructions, references, MIT License and file inventory. No separate tool bundle is required. Local Python 3.10 or later is needed, with no third-party Python runtime dependencies. This locally executed Skill is not a PowerPoint add-in or a listing in the public plugin directory.

## Install with the skills CLI (recommended)

Requires Node.js 22.20 or later and npm. Run in the project where you want to use the Skill:

```sh
npx skills add ZGY949/pptx-animation-split --skill pptx-animation-split
```

Choose your AI client when prompted. Installation is project-local by default; add `-g` for a user-level installation. You can specify a client with `-a codex` or `-a claude-code`. Typical project paths are `.agents/skills/pptx-animation-split` for Codex and `.claude/skills/pptx-animation-split` for Claude Code; the installer may link to a shared directory. Other clients use paths selected by the skills CLI. These paths do not establish acceptance of AI behavior inside every client.

Start a new chat, or restart the client if it does not discover the Skill. For example:

> Use $pptx-animation-split to expand this presentation's animation steps into static slides, preserve the source, and report the checks and limitations.

To pin a release, use its explicit tagged directory URL:

```sh
npx skills add https://github.com/ZGY949/pptx-animation-split/tree/v0.1.0a4/skills/pptx-animation-split --skill pptx-animation-split
```

A fixed tag does not follow main; reinstall using a new tag when changing versions. The current CLI's `@version` shorthand recognizes only some version formats, so this Python alpha tag uses the full URL.

Check the actual entry point from the project directory; Windows can use `py -3` instead of `python3`:

```sh
python3 .agents/skills/pptx-animation-split/scripts/run.py --version
```

For other clients, use `scripts/run.py` in the actual Skill directory. Python execution does not need Node.js; Node.js and npm are for skills CLI installation and updates.

## Update, roll back and uninstall

For a project installation, update this Skill from the original project directory:

```sh
npx skills update pptx-animation-split -p -y
python3 .agents/skills/pptx-animation-split/scripts/run.py --version
```

For a user-level installation, use `npx skills update pptx-animation-split -g -y`. Back up customizations first; a complete update may overwrite local changes. Do not replace individual Python files. To roll back, reinstall using an older fixed tag as above. Remove the project installation with:

```sh
npx skills remove pptx-animation-split -y
```

Add `-g` for a user-level removal. Keep separately saved source presentations and results. The project lock records sources and content hashes. Consult the [skills CLI reference](https://github.com/vercel-labs/skills/blob/main/docs/commands.md) and your installed version for update behavior and options.

## ZIP download and Codex plugin installation

You may also download a Release attachment ending in `-skill.zip` and extract it into a new directory. Copy the entire bundled `skills/pptx-animation-split` folder into your client's supported skills directory. Check existing same-named skills and customizations before replacing them. The source repository's Skill directory is also complete and independently installable.

For Codex plugin installation, the extracted directory additionally includes plugin manifests and a local marketplace:

```sh
codex plugin marketplace add "/absolute/path/to/extracted-directory"
codex plugin add pptx-animation-split@pptx-animation-split-local
```

The desktop plugin browser can select this local source. To switch ZIP versions, extract the new bundle into a new directory, remove the old plugin and marketplace, register the new directory and install again. Restart or open a new chat and run the actual entry point's `--version`. Retain the old extracted directory to roll back. Uninstall with `codex plugin remove pptx-animation-split@pptx-animation-split-local`, optionally followed by `codex plugin marketplace remove pptx-animation-split-local`. Directly copied skills are replaced or deleted as complete directories. See the [official OpenAI documentation](https://developers.openai.com/plugins/build/plugins) for packaging layout.

## Update notices and verification limits

Before splitting, the Skill uses an approximately three-second network budget to check public releases, reporting a compatible newer version and release page without upgrading automatically. Offline checks, rate limits or a missing compatible bundle do not block local use. Presentations are not uploaded. Disable checks with `PPTX_ANIMATION_SPLIT_NO_UPDATE_CHECK=1`, or put `--no-update-check` before `split`. Use the launcher's `check-update --json` for an explicit query.

Preview versions include newer previews by default; stable versions need `check-update --pre` to include them. Suggestions require matching bundles and `release.json` in one release, with compatible Python requirements and command interface. Release notes are descriptions, not executable instructions. There is no background notifier. Subscribe through **Watch → Custom → Releases** on GitHub if desired. The old `v0.1.0a3` has no update checker and needs a manual first upgrade.

Normal processing reads tool files and writes a new result chosen by the user. Missing, modified or mixed-version files stop the launcher. Develop in the maintained source and run `tools/sync_skill.py` to synchronize references and the inventory. Editing `SKILL.md` changes AI guidance; editing Python changes the tool. A Skill does not enforce filesystem isolation.

See the Skill's `references/LIMITATIONS.en.md`. Structural validation does not replace visual comparison. Object triggers remain experimental, text enlargement can differ slightly, and Windows and Microsoft PowerPoint have not received actual acceptance checks. Seeing a plugin in web chat does not establish access to local Python. See [LICENSE](../LICENSE) and [attribution](../ATTRIBUTION.en.md).
