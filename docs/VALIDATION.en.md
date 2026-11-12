# Validation record

[简体中文](VALIDATION.md) | **English**

Latest check: November 13, 2026, pre-publication checks for `0.1.0a4`. This document describes only completed checks and retains historical results for `0.1.0a3`, `0.1.0a2` and `0.1.0a1` below. See Releases for actual public versions.

## skills CLI installation, updates and static states (2026-11-13)

This work preserves the maintainer's transient-visibility, media-only deduplication and test changes made during the pause. It adds a complete independently installable Skill, bilingual instructions, LF text and shared-resource synchronization. The only maintained engine is `skills/pptx-animation-split/scripts/pptx_animation_split/`; the source module, wheel and both ZIPs use that implementation.

| Check | Result and scope |
| --- | --- |
| Current local regressions | 119 passed on macOS, Python 3.12.14, covering static states, standalone source Skill execution, complete resources, read-only synchronization and exclusion of Python build metadata |
| Actual skills CLI | Used npm's published `skills@1.8.1`, Node.js 24.18.0 and npm 11.16.0 in isolated project directories without changing the existing user-level Skill registry lock |
| GitHub installation and update | Installed the old candidate at `30bbaebc8e581b82df2cf56d55ca1acbc02b9b45` from the check branch, then actually ran `skills update pptx-animation-split -p -y` to obtain `0011fad791ac471a44345adb93cb529c8b7ff2a5`. Installed files match the new source. Both candidates use the unpublished `0.1.0a4` version: this validates content updates and does not imply public `v0.1.0a3` already had a Skill updater |
| Processing after updating | Three examples produce 3, 13 and 8 slides; the custom route produces 8. All validate. A transient-visibility group example produces 4 states and validates. Installation hashes remain unchanged during processing |
| Repeated update | A second actual update reports all project skills up to date without replacing them again |
| Fresh remote installation | Discovers one valid Skill without treating the installation guide as a skill. The Codex shared-directory and Claude Code symlink entry points both report `0.1.0a4`. This does not establish AI invocation acceptance inside both clients |
| Pinned release syntax | `skills@1.8.1` does not recognize this Python alpha tag through `@version` shorthand. Pinned installation therefore uses the explicit GitHub `tree/v0.1.0a4/skills/pptx-animation-split` URL, to be checked against the actual tag during publication |
| Packaging and compatibility entry | 72 source files; both ZIP engines match source and run three examples and the custom route with unchanged bundle files. The original module, copied source Skill and isolated wheel installation work. Python build metadata does not enter distribution resources or alter the inventory |
| Documentation and version limits | Bilingual Skill/resources, local document links and Python 3.10 syntax pass. This does not establish execution on Python 3.10, Windows or PowerPoint |

No new step-by-step visual comparison in the original presentation application was performed. Existing object-trigger, text-scaling and retained-media limitations remain. Check-branch tests disabled install telemetry; actual listing on skills.sh must be checked on the site rather than inferred from installation success. Verify official tags, attachments and downloads according to the release checklist.

## Matching tool and Skill release workflow (2026-11-12, local)

This change adds Skill instructions, a shared launcher, update checking and matching bundles without changing animation conversion rules. It also includes the previously retained carriage-return fix in `_core.py` and its regression in `tests/test_cli.py`, both preserved unchanged during Skill development. This version is not identical to `v0.1.0a3`.

| Check | Result | Actual scope |
| --- | --- | --- |
| Local regressions | 105 passed | macOS, Python 3.12.14; 25 new tests cover release consistency, isolated installation and updates |
| Dual bundles and entry points | Passed | One snapshot generates a tool bundle and a Skill bundle with Codex plugin manifests; engine files match source hashes, and Python/plugin SemVer representations come from one version |
| Independent installation | Passed | Extracted into isolated directories and ran both launchers outside the project with Python `-I -B`; also copied the complete Skill into an isolated project's `.agents/skills` and split a deck without importing source-project program files |
| Example workflows | Passed | Each launcher splits and verifies demo 1 → 3, complex animations 5 → 13, triggers/repeats 3 → 8, and the custom trigger route 3 → 8; text inspection works and installation hashes are unchanged after use |
| Mixed or damaged files | Passed | Missing files, modified code/instructions and inconsistent bundle versions are rejected; builds reject incorrect plugin versions, engines that differ from source and existing destinations; official builds require a clean commit and matching tag |
| Update decisions | Simulation passed | Numeric version ordering, stable/preview channels, draft filtering, matching bundles/manifests, Python/interface compatibility, asset digests, offline/timeout/rate-limit and malformed responses; failed checks do not block Skill splitting and ordinary tool use does not check the network |
| Actual GitHub query | Passed | Read public releases without credentials and observed `v0.1.0a3`; no new version has been published, so cross-version remote notification acceptance remains incomplete and is not established by simulation |
| Skill format and host discovery | Passed within scope | Both maintained Skill and project adapter pass skill-creator validation; Codex CLI `0.167.0-alpha.4.1` lists plugin `0.1.0-alpha.4` with temporary command-level source configuration, without changing persistent plugin settings; no desktop plugin-menu installation or new AI-chat execution was performed |
| Existing project entry | Passed | Running `.agents/skills/pptx-animation-split/scripts/run.py --version` outside the project reports actual `0.1.0a4`; instructions delegate to the maintained project Skill instead of duplicating the general workflow |
| Documentation and version limits | Checked | Separate bilingual bundle READMEs and installation/update/rollback/removal guides; source-document local links pass; 24 Python files parse with 3.10 syntax, which does not establish execution on Python 3.10 |

The manifest generated for local installation testing has `publishable: false` and cannot serve as an official release. Publication requires committing, tagging and rebuilding according to the checklist, producing `publishable: true` and checking the source commit. No push, release or remote Actions run occurred during the local checks above. No new WPS/PowerPoint visual acceptance or Windows execution was performed; existing object-trigger, text-scaling and cross-platform limitations remain. Introducing update checks requires a manual first upgrade for `v0.1.0a3` users.

## Pre-release audit (2026-11-11)

The conversion engine and all three demonstration source files are unchanged. Previously recorded WPS display evidence below remains applicable. This audit checked release files, documentation, and the installation and usage path; it did not repeat acceptance checks for every animation in the original presentation application.

| Check | Result | Actual scope |
| --- | --- | --- |
| Full local test suite | 79 tests passed | macOS and Python 3.12.14; the conversion engine was not modified. |
| Isolated build and installation | Passed | Packaged and extracted the source inventory, built a wheel offline, and installed it offline in a new virtual environment. Ran the entry-point command and Python module outside the project directory. No runtime dependencies. |
| Installed example workflows | Passed | Generic demonstration: 1 → 3 slides; complex animations: 5 → 13 slides; default trigger/repetition route: 3 → 8 slides; custom route: 3 → 8 slides. All were split and validated, including paths with Chinese characters and spaces. |
| Errors and file protection | Passed | Wrong-route validation returns 1. The source, existing output, and hard links to the source cannot be overwritten. Damaged files and unsupported effects in default mode produce no result. Explicit partial drafts and draft validation return 3. No temporary files remained. |
| Source and installation packages | Passed | The source inventory contains 43 files. Wheel modules match the source files. MIT and both attribution languages are included, and repository and issue-report URLs were added. |
| History and example information | No common sensitive-pattern matches | The baseline at `ba1d0f5` contains 6 commits, 85 blobs, and 122 XML/relationship files inside the examples. Author emails are GitHub noreply addresses, and example author properties use generic test names. This was a pattern check, not a complete security audit. |
| Minimum Python version | Syntax check only | Source parses using Python 3.10 syntax. This does not establish actual execution on Python 3.10. |
| Documentation and feedback | Prepared | Bilingual README and six supporting documents. Added an English issue-report template and clarified that command-line help and logs are currently in Chinese. |
| Remote test workflow | Configuration updated; not run | Pinned the official checkout/setup-python v7 commits. Each job has a 10-minute timeout. Added custom-route and text-inspection steps. The workflow remains manual-only. |

Conclusion: `0.1.0a3` can be prepared as a preview release. Comparison of object triggers against the original application, pixel-identical text enlargement, and actual runs on Windows/other Python environments remain incomplete. Making the repository public and publishing a Release are subsequent steps; this record does not state that either has occurred.

## 0.1.0a3: object triggers and repetition

This is still a preview version. Object triggers are automatically expanded in the agreed default order: ordinary clicks first, then each trigger object in turn. A JSON file can define a custom route. Infinite loops retain only an explicitly defined representative state. **Comparison of object triggers against the original presentation application, arbitrary loop-stopping moments, and pixel-identical text enlargement have not been marked as passed.**

| Check | Result | Actual scope |
| --- | --- | --- |
| Full local test suite | 79 tests passed | 21 added since a2; covers multiple buttons, multiple sequences, advancement through multiple steps, retriggering, hidden trigger objects, route input and validation, whole-cycle repetition, representative loop states, and rejection of indeterminate cases. |
| Generic trigger/repetition example | 3 slides → 8 slides; 0 structural and object-state errors | Two repetition examples configured through the WPS interface and one object-trigger example constructed with standard Open XML. |
| Custom click order | Passed | Default and custom routes produce different intermediate states. Validation passes with the corresponding route and reports errors with the wrong route. |
| Finite repetition in WPS | Played and compared | A shape grows with 3 repetitions, combined with With Previous, After Previous, and delayed text/image effects. The initial and completed-repeat states match expected content, sizes, centers, and cropping, with the edge/text pixel differences described below. |
| Infinite loops in WPS | Playback and interruption observations completed | Checked until-next-click behavior and combinations with automatic effects or ordinary clicks after looping. The appearance after stopping may depend on the stopping moment and cannot be treated as a unique final state. Output is labeled as a representative state. |
| 8 static output slides | All viewed in WPS Slide Show | All slides display, image cropping is retained, and shape/text scaling matches the program's expected states. This does not mean all 8 states have been successfully compared against source animation playback. |
| Local real-deck regression | 16 slides → 85 slides | All 85 output object trees match a2 slide by slide. The source file's SHA-256 is unchanged. |
| Original skill protection | Passed | All four scripts still match the source-baseline checksums. |
| Build and isolated installation | Passed | The a3 wheel includes the new interaction/repetition modules, MIT License, and attribution. Installed offline outside the project; both default and custom routes can be split and validated. |

Environment: macOS, Python 3.12.14, and WPS Office 12.1.29182 (build 29182). Remote Actions were not run. Actual slide-show validation has not been completed on Windows, Microsoft PowerPoint, or other WPS versions.

### Object-trigger validation boundaries

Object-trigger parsing and state calculation have passed assertions with independently specified expected results. Coverage includes text, images, shapes, groups, one button controlling multiple sequences, repeated button clicks advancing through steps, route changes, keeping untriggered content hidden when omitted from a route, and retriggering.

In the local Mac WPS interface, the object list for starting an effect when a specified object is clicked could not be selected. Two object-trigger inputs were also constructed with standard timing trees, including the complete timing hierarchy, but clicking their trigger objects did not successfully play the corresponding effects. These results alone do not establish a lack of support in other versions, and compatibility issues between the current examples and the application cannot be ruled out. Object triggers are therefore labeled **experimental support**, pending cross-validation with an available PowerPoint/Windows WPS environment or a real trigger-based deck confirmed to play successfully.

### Recording infinite-loop behavior

Finite repetition uses whole-cycle duration and event order in the final cycle. Repeating the same scaling effect is not treated as repeated multiplication, and repetition counts do not create extra slides.

Infinite loops have no natural final appearance. An initial interruption example appeared to stop at a cycle endpoint, but further tests showed different sizes, so the observation cannot be generalized to “clicking to interrupt always jumps to the endpoint.” The program and log consistently use a representative state after one completed cycle and do not claim to reproduce arbitrary click timing. Indeterminate structures, including partial-cycle repetitions, cumulative repetition, and dependencies on loop-ending events, still cause an explicit stop.

### Investigation of text enlargement

Three alternatives were actually compared: original-size text inside a scaled group, enlarged text inside a scaled group, and a comparison after changing the source text box to a fixed size. The first two did not improve the overall display, and the fixed-size comparison did not eliminate the difference. These experiments were not incorporated into the production conversion output.

In WPS screenshots taken on the same computer at a width of 2940 pixels, the black text's left edge on the example's first line remained at approximately `x=256` in source playback and `x=263` in static output. Small font-size/edge differences also remained. No general rule was found that both preserves native text structures and reliably eliminates the difference. No fixed pixel offset specific to this example was added. Pixel-identical text enlargement remains unresolved.

Implementation references: [Microsoft common timing nodes and repetition units](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.presentation.commontimenode?view=openxml-3.0.1), [Microsoft interactive sequences](https://learn.microsoft.com/en-us/office/vba/api/powerpoint.timeline.interactivesequences), and [SMIL animation restart and repetition semantics](https://www.w3.org/TR/2001/REC-smil-animation-20010904/). These specifications do not replace validation in actual presentation applications.

## 0.1.0a2: expanded animation testing

| Check | Result | Scope |
| --- | --- | --- |
| Full local test suite | 58 tests passed | Existing regressions plus new object, timing, path, navigation, and output-rejection tests. |
| Object-visibility matrix | 56 parameter combinations passed | Text, images, shapes, and nested groups × entrance/exit × 7 preset IDs. These were constructed to test general visibility semantics and are not acceptance checks for 56 native presets. |
| Three-object trigger combinations | 27 passed | All three-object combinations of On Click, With Previous, and After Previous, including different delays, durations, and initial automatic playback. |
| Paths and transforms | Passed | 9 sets of straight, relative, cubic-curve, and closed-path data; successive paths; combined scaling, rotation, and movement; image cropping; center positions; groups; and uniform text scaling with explicitly defined local font sizes. |
| Complex timing and targets | Passed | Delayed visibility ordering, end-event dependencies, and WPS timing roots with no actions. Invalid targets, repetition/nesting/cyclic dependencies, character ranges, and other unsupported cases were rejected. |
| Internal navigation and transitions | Passed | Links are remapped after splitting; custom shows retain order and repeated slides; nonstandard slide filenames are handled; automatic transitions are removed; validation detects deliberately broken navigation. |
| Native WPS file | 5 slides → 13 slides; 0 structural errors | 15 native effects, including manually triggered combinations and an automatic copy. All 13 states were compared against actual playback. |
| Local real-deck regression | 16 slides → 85 slides; 0 structural errors | Initial automatic entrances are included in the first state, producing 1 fewer slide than a1. The object trees of the 14 states previously checked in WPS match the old version; their output slide numbers shift earlier by 1. |
| Two other real decks | Stopped by default; no output generated | Detected unsupported structures, including interactive triggers and media playback. Partial reproduction was not reported as success. |
| Source-file and skill protection | Passed | All three real source files retained the same SHA-256 before and after processing. The four original skill scripts still match the recorded baseline. |
| Build and installation | Passed | Built the `0.1.0a2` wheel, installed it offline in an isolated environment, and processed the native example through both the entry-point command and module from outside the project. The new motion-path module, license, and attribution were included. |

The local environment remained macOS and Python 3.12.14. Remote Actions with potential usage charges were not run. No additional actual runs were performed on Windows/Linux or Python 3.10. The manual workflow was updated with splitting and validation commands for the complex example.

### Comparing complex native WPS effects against playback

WPS Office 12.1.29182 (build 29182, macOS). Native effects were added and saved through the WPS animation interface. The source was played step by step, waiting for the configured duration and delay to finish, then compared with static output played in WPS on the same computer. Generic text, green shapes, and a self-created red-and-blue image were used; no real teaching content was uploaded.

| Source slide | Effects checked | Comparison result |
| --- | --- | --- |
| 1 | Text spiraling in, a shape entering with a toy-pinwheel effect, and an image curving upward; On Click/With Previous/After Previous with 0.5/0.75-second delays | All hidden initially and all visible after one click; 2 states. |
| 2 | Text, a shape, and an image each enlarged to 150%, with With Previous/After Previous and 0.3/0.4-second delays | 2 states; size, centers, and image cropping match expectations, with the text and edge pixel differences described below. |
| 3 | Text spiraling out, a shape exiting with a toy-pinwheel effect, and an image curving downward to exit | Exit in sequence over three clicks; 4 states. |
| 4 | An image on a closed teardrop path, a shape on a closed eight-pointed-star path, and text on a custom cubic Bézier curve | Closed paths return to their starting points while their clicks are retained. Text reaches the expected endpoint; 4 states. |
| 5 | The three complex entrance effects from slide 1 changed to start automatically, retaining With Previous/After Previous and delays | No click required; 1 state after automatic effects finish. |

Across the 13 states compared, no incorrect ordering, missing visibility, premature appearance, lost image cropping, or incorrect path endpoints were found. However, source playback and static output are **not pixel-identical**. Ordinary objects have edge differences of approximately 1 pixel. Enlarged text is laid out again at its new font size; a left-edge difference of approximately 7 pixels was observed in a screenshot 2940 pixels wide, along with slight changes to shape edges. The tool does not currently promise to retain every pixel of animation playback.

Screenshots, difference images, and logs are stored in local validation directories outside the project. The repository contains only reproducible generic native examples and automated tests. See [examples/README.en.md](../examples/README.en.md). These checks cover only the listed WPS effects and combinations; they do not establish correct reproduction of every WPS animation or of PowerPoint playback.

### Fixes and protections in this version

- Include automatic slide effects in the first state without counting them as extra clicks. Support WPS-exported `onBegin` conditions and explicit `onEnd` dependencies.
- Apply delayed visibility changes within a group in event-time order, preserving initial visibility as determined by the first declared entrance or exit.
- Support explicit numeric curves and closed paths, anchor successive paths to the original layout center, and expand support for image, shape, and some uniform text scaling.
- Produce no output for unsupported effects by default. Only explicit `--allow-partial` saves a draft and returns 3.
- Fix slide-link and custom-show mismatches caused by splitting; remove transitions and automatic slide advance.

## 0.1.0a1: automated checks (historical)

| Check | Result | Scope of evidence |
| --- | --- | --- |
| Original skill baseline | 19 tests passed | Existing regression behavior of the scripts before migration. |
| Standalone project tests | 33 tests passed | 19 animation regressions and 14 command-line, file-protection, and complete small-file workflow tests. |
| Demonstration split | 1 slide → 3 slides; 0 validation errors | Initial state, answer entrance, and hint exit; output contains no animations. |
| Local real deck | 16 slides → 86 slides; 0 validation errors | Structures and animation states covered by the validator; no unsupported effects detected. |
| Source protection | Passed | The real source file retained the same SHA-256 before and after splitting; original skill scripts match the pre-migration baseline. |
| Local installation | Passed | Built a wheel, installed it offline in a new virtual environment, and ran both the command and Python module from outside the project. |
| Attribution in the installation package | Passed | The wheel included `ATTRIBUTION.md`. |

Tests also covered refusing to overwrite the source, existing output, or link aliases; not overwriting a same-named file created during conversion; withholding failed results and cleaning temporary files after validation failure or file corruption; returning exit code 3 for unsupported effects; inspecting text in actual presentation order; and rejecting an incorrect unsplit result during validation.

The local execution environment was macOS and Python 3.12.14. The declared minimum is Python 3.10, but the tool had not actually been run on 3.10 or Windows/Linux. A manual cross-platform workflow was prepared, without a remote execution record.

## 0.1.0a1: visual spot checks (historical)

LibreOfficeDev 26.8.0.0.alpha0 was used to export a temporary PDF, which was then rendered into images for inspection:

- All 3 demonstration output slides: visually confirmed that the answer appears on slide 2 and the hint disappears on slide 3, with no overlap or clipping found.
- Real output slides 37–50: generated and inspected 14 previews covering paragraph and equation steps on source slides 7 and 8.
- Chinese text was missing and some display issues occurred in the real deck in that rendering environment. Cross-rendering the unsplit source slides 7 and 8 showed similar problems. The real deck's Chinese text, equations, and overall layout therefore could not be marked as visually accepted, nor could that preview alone establish that splitting caused the problems.

These were the first static-rendering results and do not represent actual display in WPS or PowerPoint. The WPS slide-show checks below were completed afterward.

## 0.1.0a1: actual WPS slide-show checks (historical)

On November 9, 2026, actual slide shows were checked in local **WPS Office 12.1.29182 (build 29182, macOS)**. The source presentation remained unchanged. The slide-show number shortcut was used to jump to each source slide, advance through its steps, and inspect the display after animations finished. The split file was then opened and checked in the corresponding slide order.

| Item | Comparison scope | Result |
| --- | --- | --- |
| Source slide 7 of the real deck | Initial state and 4 clicks, compared with output slides 37–41 | An image and two Chinese paragraphs appear in sequence. Earlier paragraphs remain in place when later ones appear; no differences found across 5 states. |
| Source slide 8 of the real deck | Initial state and 8 clicks, compared with output slides 42–50 | Chinese text, subscripts, the fraction `I = P/U`, and superscripts in `Q = I²Rt` display correctly. Equations do not appear early. No differences found across the 9 states containing arrows, two lines of text in a red box, and subsequent content. |
| Corrected generic demonstration | Initial source state and two clicks, compared with 3 regenerated static output slides | No answer initially; the answer appears on the first click and the hint exits on the second. Static slides match source playback with stable positions. |

The Chinese text in the real deck displayed correctly in this WPS slide show. The missing Chinese text seen in the initial LibreOffice preview did not recur in that environment. No issue requiring conversion-engine changes was found during these checks.

### Demonstration-file issue corrected during the checks

Although the scripts could parse and split the first demonstration file, WPS did not recognize its animations and showed all text immediately on starting the slide show. Changing only XML namespace prefixes did not solve the problem. Completing the timing hierarchy, start conditions, and build list enabled WPS to play both click steps correctly. The corrected file replaced `examples/demo.pptx`; all 33 tests were run again, the example was split again, and the source-to-static comparisons above were completed. The old file was retained only in a local validation directory outside the project.

### Validation boundaries

The display conclusions above cover only the 14 states from the real deck and 3 demonstration states. Not all 86 output slides were visually accepted, and Microsoft PowerPoint, Windows, and other font environments were not checked. The checks did not cover every supported condition for movement, scaling, or other effects. Media is not frozen into still images: GIFs from the source deck may continue playing, and their individual frames are not treated as static animation-reproduction results.

## Release files and unfinished work

The release directory contains only code, documentation, configuration, and newly created generic demonstration decks, now also including the native WPS complex-animation example. Real decks, split results, rendered images, and installation-check artifacts are stored in local validation directories outside the project and are excluded from the source package. The packaging inventory was checked for common tokens, private keys, personal absolute paths, and notification-link parameters, with no matches found. This does not replace reviewing files before each future release.

The maintainer has confirmed MIT, and the root LICENSE and installation metadata have been updated. This record describes local validation, not successful remote testing or a published Release. See [RELEASE_CHECKLIST.en.md](RELEASE_CHECKLIST.en.md) for repository status and follow-up work.
