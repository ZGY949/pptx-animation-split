# Demonstration decks

[简体中文](README.md) | **English**

`demo.pptx` is a newly created, generic 1-slide demonstration, not taken from a teacher's course deck. Its base presentation was created with python-pptx, then Open XML animations were added for testing. Running this project does not require python-pptx.

The example's animation timing hierarchy, start conditions, and build list have been completed, and its playback has been checked in macOS WPS Office 12.1.29182. The original example passed only automated splitting checks; WPS did not recognize its animations. The current file replaces that example with the corrected version.

The deck has 2 click steps:

1. Initial state: the question “What is 6 x 7?” and a hint are visible; the answer is hidden.
2. After the first click: “Answer: 42” appears.
3. After the second click: the hint exits; the question and answer remain.

Run from the project root:

```sh
python3 -m pptx_animation_split split examples/demo.pptx demo-split.pptx
```

The output should contain 3 slides. Use a new output filename; do not overwrite the example source file.

## Complex animations authored in WPS

The animations in `animation-cases.pptx` were added and saved through the animation interface in macOS WPS Office 12.1.29182, then assembled into a 5-slide test file. The text, green shapes, and red-and-blue images are generic assets created for this purpose and contain no teaching materials. The document's author property was changed to a generic test name, and opaque WPS tracking properties were removed.

| Source slide | Effects and combinations | Output states |
| --- | --- | --- |
| 1 | Text spirals in; a shape enters with a toy-pinwheel effect using With Previous and a 0.5-second delay; an image curves upward using After Previous and a 0.75-second delay | 2 |
| 2 | A shape, text, and an image each grow to 150%; text uses With Previous and a 0.3-second delay; the image uses After Previous and a 0.4-second delay | 2 |
| 3 | Text spirals out, a shape exits with a toy-pinwheel effect, and an image curves downward to exit, each on a separate click | 4 |
| 4 | An image follows a closed teardrop path, a shape follows a closed eight-pointed-star path, and text follows a custom cubic Bézier curve, each on a separate click | 4 |
| 5 | The same three entrance effects as slide 1, with the first effect starting automatically when the slide opens; With Previous, After Previous, and delays are retained | 1 |

```sh
python3 -m pptx_animation_split split examples/animation-cases.pptx animation-cases-split.pptx
```

The output should contain 13 slides. The first two paths on source slide 4 return to their starting points; the corresponding click states are retained even though their final appearance is unchanged. Source slide 5 requires no click and produces one static state after the automatic effects finish.

The source was played step by step in the WPS environment above and compared against all 13 output slides. Visibility, path end positions, and image cropping matched expectations. Small pixel differences remain in text scaling and shape edges; see the [validation record](../docs/VALIDATION.en.md). This is not a complete catalog of WPS effects.

## Object-trigger and repetition examples

`interaction-repeat-cases.pptx` contains 3 source slides and expands to 8 slides by default:

| Source slide | Content and origin | Output states |
| --- | --- | --- |
| 1 | Shape growth set to repeat 3 times through the WPS interface, with With Previous and After Previous combinations for text and an image | 2 |
| 2 | Shape looping until the next click, configured through WPS; text grows with the shape, and the image grows on the next ordinary click | 3 |
| 3 | Constructed with a standard Open XML timing tree: an ordinary click enlarges a shape and an image; clicking a star triggers text enlargement | 3 |

```sh
python3 -m pptx_animation_split split examples/interaction-repeat-cases.pptx interaction-repeat-split.pptx
```

The output during the loop on source slide 2 is a representative state, not a prediction for an arbitrary stopping moment. The source object trigger on slide 3 could not be played successfully in the local Mac WPS environment, so this slide has not passed comparison against actual playback in the original application. It provides reproducible semantic, structural, and static-output checks. The effects on the first two slides were configured through the WPS interface and actually played.

`click-order.json` demonstrates changing source slide 3 to “click the star first, then make an ordinary click.” Other source slides keep the default order. Pass `--click-order examples/click-order.json` to both splitting and validation commands. Do not overwrite the example source files.
