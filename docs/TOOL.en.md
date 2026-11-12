# PPTX Animation Split tool bundle

[简体中文](TOOL.md) | **English**

This is the directly usable Python tool bundle. Download the attachment ending in `-tool.zip` from a GitHub Release and extract it to a permanent directory. Python 3.10 or later is required, with no third-party runtime dependencies. This remains a preview tool with limited animation support.

## Use

Open a terminal in the extracted directory:

```sh
python3 run.py --version
python3 run.py split examples/demo.pptx demo-static.pptx
python3 run.py split "/path/to/source.pptx" "/path/to/source-static.pptx"
```

On Windows, replace `python3` with `py -3`. From any other working directory, use the absolute path to `run.py`. The demo expands from 1 slide to 3. The output directory must exist, and the destination must be a new file. Splitting validates before saving and never overwrites the source or an existing result.

Revalidate or inspect text:

```sh
python3 run.py verify "/path/to/source.pptx" "/path/to/source-static.pptx"
python3 run.py peek "/path/to/source-static.pptx" 1 3-5
```

Detected unsupported effects block output by default. Add `--allow-partial` only for a draft requiring manual review; exit `3` means unsupported effects remain, not full success. Exit `0` indicates success within the command's checking scope, `1` is an error, and `2` is a usage error. See the [limitations](LIMITATIONS.en.md) for object triggers, custom click order and other conditions. A route example is in `examples/click-order.json`; pass the same `--click-order` file when splitting and revalidating.

Use your actual presentation application to check formulas, first appearance of answers, paragraph positions and image crops. Structural checks do not establish visual equivalence. Small display differences in text enlargement remain, object triggers are experimental, and Windows and Microsoft PowerPoint have not been verified in actual use. Output may retain hidden text, media, notes and embedded objects.

## Update and uninstall

The historical `v0.1.0a3` has no update-check command. Upgrade manually first; only versions containing this feature can query subsequent releases.

Ordinary splitting through the tool bundle does not check the network. Query updates explicitly when needed:

```sh
python3 run.py check-update
python3 run.py check-update --json
```

The check reads public release information. It does not upload presentations, download code or replace the installation. Preview versions include preview releases by default; stable versions check stable releases unless `--pre` is specified. A newer release is offered only when matching bundles, compatible Python requirements and a compatible command interface are available. Offline checks or service rate limits do not prevent local use; view [Releases](https://github.com/ZGY949/pptx-animation-split/releases) manually.

To update, extract the new `-tool.zip` into a new directory, switch to its `run.py`, then check `--version`. Retain the old directory to roll back; do not merge new files into the old installation. To uninstall, delete the extracted tool directory and retain separately saved source files and results. The launcher rejects modified bundle files. For development, edit the full source project and rebuild.

For release notifications, select **Watch → Custom → Releases** on GitHub. See the [project](https://github.com/ZGY949/pptx-animation-split), [LICENSE](../LICENSE) and [attribution](../ATTRIBUTION.en.md). GitHub's automatically generated Source code ZIP contains the whole project; this tool bundle contains only runtime files and demonstration materials.
