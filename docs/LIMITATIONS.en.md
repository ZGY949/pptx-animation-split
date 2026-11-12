# Supported features and known limitations

[简体中文](LIMITATIONS.md) | **English**

## How splitting works

Source slides follow the presentation order in `presentation.xml`. Automatic-animation and click end states are retained. With Previous, After Previous, and delays belong to the same group. When an object enters and exits within that group, the tool also saves its fully visible state before the exit, followed by the restored state. Objects exiting together share one visible state. These are static illustrations based on visibility events, not captured frames of fades or motion. Zero-duration events without a visible interval and infinite loops do not add transient states.

Visibility changes within a group are replayed in start- and end-time order while preserving objects and paragraph placeholders. A click is merged only when all its events are media controls and its generated scene matches the previous output state. Distinct source slides and media steps containing visual changes are never merged. Other restored click states remain. Object triggers follow a defined route; finite repeats do not add a slide per cycle, and infinite loops produce a representative state.

When an unsupported structure is detected, the tool stops without producing an output by default. `--allow-partial` is only for creating a draft that must be checked manually slide by slide; it returns exit code 3. Passing structural validation does not establish that these effects have been reproduced. The parser may still miss unsupported cases.

## Specific support conditions

| Type | Current behavior or conditions |
| --- | --- |
| Entrance and exit | Replay final visibility for whole objects or paragraphs. Intermediate poses during entrance or exit effects, such as flying, rotating, or zooming, are not preserved. |
| Paragraphs | Use transparent placeholders to preserve text, fonts, line breaks, and positions without deleting paragraphs. |
| Equations | Process both Choice/Fallback compatibility branches, preserving original structures and required namespaces; filter legacy OLE/VML previews according to visibility. |
| Object-click triggers (experimental) | Standard `interactiveSeq` structures with a unique `onClick` target. Ordinary clicks run first by default, followed by trigger sequences in file order. One button may control multiple sequences and advance through multiple click steps; custom routes are supported. If a trigger object is hidden, use an executable route instead. |
| Finite repetition | Explicit whole-cycle `repeatCount` or `repeatDur`, using the end time after repetition and the visibility order in the final cycle. Repeating the same scaling effect is not mistaken for cumulative scaling. |
| Infinite loops | Explicitly labeled as a representative state after one completed cycle. Loops do not generate infinitely many slides or claim to reproduce arbitrary stopping moments. Common until-next-click and until-end-of-slide markers are supported. |
| Automatic effects and delays | Recognize the main sequence, On Click/With Previous/After Previous combinations, numeric delays, and evaluable `onBegin` / `onEnd` timing-node dependencies. |
| Text color | Some effects using `style.color` with an explicit target color, optionally restricted to a paragraph. |
| Rotation | Whole-object final rotation with an explicit `by` angle. |
| Image and shape scaling | Positive `by` factors, centered on the object; image cropping is preserved. |
| Text and group scaling | Content containing text supports only uniform scaling, with font sizes determined from local run properties, paragraph defaults, or local list styles. Font sizes and spacing are adjusted. |
| Motion paths | Top-level objects with `origin=layout` and unrotated path axes. Explicit numeric `M/L/C/Z/E` commands and their lowercase relative forms; end positions of multi-segment paths, cubic Bézier curves, closed paths, and successive paths are supported. |
| Temporary emphasis | Some recognized emphasis effects that use `fill=remove` or auto-reverse and restore their initial state at the end retain that original state. |
| Internal navigation | Internal slide links lead to the target source slide's first output state. Custom shows expand in their original order, retaining repeated source slides. |
| Slide transitions | Remove transitions and automatic slide advance so static states can be read manually. |

Only motion-path end positions are calculated. A closed path that returns to its starting point may produce consecutive static slides with the same appearance. Successive paths use the source object's original layout center as their reference; a later path is not mistaken for a displacement relative to the preceding step.

The following cases are not yet supported or cause the tool to stop when detected: nonstandard or ambiguous interactive triggers; repetitions ending partway through a cycle; cumulative repetition; repetition or timing modifiers on containers outside the sequence; auto-reversing an entire repeated container; events depending on an infinite loop ending; effects that restore their original state after an infinite loop without a defined stopping point; other early-ending conditions; nested sequential sequences; indeterminate durations; cyclic timing dependencies; custom timing speed or filters; effects outside the main sequence; unknown behaviors; character-level or internal-object-element animation; moving, scaling, or rotating individual paragraphs; nonuniform text scaling; text scaling that depends on theme or master font sizes; scaling native mathematical equations; motion paths inside groups; formula-based paths; and overlapping effects on the same property of the same object. Entrance or exit effects that reverse to their original state are also unsupported.

Video and audio playback cannot be converted into static animation steps. Media files may remain in the output package; removing slide animations does not freeze GIFs, videos, or other media.

## Boundaries for object triggers and loops

An interactive deck can have multiple click routes. The default route follows the convention in the [README](../README.en.md), and the log lists the specific object IDs and names. The tool does not generate every possible permutation. Use `--click-order` to provide a JSON route organized by source slide number, and pass the same file when validating the result again. Triggering an effect again replaces that effect's previous retained transform rather than incorrectly enlarging the object repeatedly. Compatibility with actual presentation applications still requires further validation.

An infinite loop has no natural final state before it is stopped, and its appearance after stopping may depend on the click timing and application behavior. This tool outputs only the defined representative state. Even zero structural-validation errors do not establish that size, color, or position matches the exact moment the loop stops. If another animation in the same group changes the same property as an infinite loop, the tool refuses to guess their combined result.

## Visual limitations

The complex animation examples authored in WPS have been compared against actual playback, including spiral effects, toy-pinwheel effects, curved entrances and exits, scaling, and complex paths. See [VALIDATION.en.md](VALIDATION.en.md) for counts and combinations. This is not certification of every WPS preset. Microsoft PowerPoint, Windows WPS, and other WPS versions have not been validated. The new object-trigger logic passes semantic and structural tests, but the trigger-object list in the local Mac WPS interface could not be selected, and the constructed trigger inputs did not play successfully. These observations do not establish that all WPS versions lack support.

Small edge and font-rasterization differences remain between animation playback and static output in WPS on the same computer. Enlarged text is laid out again at the new font size, which may produce slight spacing or position differences from directly scaling its rendered appearance during animation. In the native example, a difference of approximately 7 pixels at the text's left edge was observed in a screenshot 2940 pixels wide. Shape edges also differ slightly. Three alternatives were compared: original-size text inside a scaled group, enlarged text inside a scaled group, and a fixed-size text box. None eliminated the difference. No fixed pixel offset was added to conceal the issue. Pixel-identical output cannot currently be guaranteed.

## File limitations

- Only `.pptx` is accepted. Legacy `.ppt`, macro-enabled `.pptm`, encrypted files, and damaged files need separate handling.
- PDF is not exported directly. Open the result in presentation software and export it there.
- Notes are attached only to the first output slide for each source slide.
- The extension list in `presentation.xml` is removed to avoid mismatched section numbering. Sections and other data in that extension list are not retained.
- Internal navigation has automated checks, but complex presentation actions, dynamic slide numbers, SmartArt, and elements within charts have not been fully validated.
- Font and equation compatibility and line wrapping depend on the actual application and installed fonts. Preserving XML does not guarantee identical display in every application.
- Source media, embedded objects, document properties, and some notes are retained. Transparent text may still be extracted. The tool does not remove sensitive content.
- Output XML is assembled in memory. Many clicks or large media files may increase processing time and file size; performance limits have not been established.
- The final save requires filesystem support for hard links. If a network or removable drive does not support them, output to a local disk first.

## What validation establishes

The program checks structure, relationship targets, content types, recognized object visibility, equation compatibility branches, legacy equation drawings, paragraph placeholders, movement and scaling, images, positions, internal navigation, and unexpected duplicate slides.

The validator shares some parsing and transformation logic with the converter, so both may have common blind spots. Exit code 0 means only that no errors were found within the scope of those checks. Check key slides in the actual presentation application before delivery.

Implementation references: [Microsoft path commands and coordinates](https://learn.microsoft.com/en-us/openspecs/office_standards/ms-oe376/20acd8bd-6ba0-461d-ae9f-f7e0f90e1ff7), [layout path origin](https://learn.microsoft.com/en-us/openspecs/office_standards/ms-oi29500/498c3cfa-652c-49b3-a82c-33fd94468af8), and [animation conditions](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.presentation.condition?view=openxml-3.0.1).
