# Attribution and acknowledgments

[简体中文](ATTRIBUTION.md) | **English**

This project was inspired by [PPspliT](https://github.com/maxonthegit/PPspliT), a VBA PowerPoint add-in by **Massimo Rimondini** that expands animation steps into static slides.

This project was assembled from Python scripts in the local `pptx-animation-split` skill, including implementations and fixes developed with AI assistance. The original local scripts carried the label `PPspliT (Python re-implementation, entry-effect subset)`. This project retains that provenance while using a separate name to avoid confusion with the original VBA add-in. The original add-in program, installer, and VBA source code have not been copied into this project. This project makes no commitment to compatibility with, or fixes for, the original add-in.

The original local scripts did not record the upstream commit consulted or a line-by-line porting inventory. They therefore cannot be described as an audited, fully independent rewrite, and the precise extent of correspondence with upstream code cannot be established. File checksums recorded before the scripts were moved into this project are in [source-baseline.json](docs/source-baseline.json).

## The author's clarification on independent distribution

On November 9, 2026, Beijing time, Massimo Rimondini clarified the following in his [reply to Issue #29](https://github.com/maxonthegit/PPspliT/issues/29#issuecomment-6727916615):

- The original project will remain a VBA PowerPoint add-in; other implementations are better maintained separately.
- Implementations in other languages may be distributed independently.
- Implementations based on portions of PPspliT code should give proper credit and link to the original project. A reference is also welcome for fully independent implementations.

This project retains the acknowledgment and link above. The original project's license is in [src/license.txt](https://github.com/maxonthegit/PPspliT/blob/master/src/license.txt) and is not the MIT License. The reply must not be described as a change of the original project's license to MIT.

The maintainer of this project confirmed the [MIT License](LICENSE) on November 9, 2026, with copyright attributed to `ZGY949`. That license applies to the extent permitted by the relevant rights and does not replace third-party attribution or licensing requirements. Retain this attribution document and the link to the original project together.

## Technical references

- [Open XML path coordinates](https://learn.microsoft.com/en-us/openspecs/office_standards/ms-oi29500/498c3cfa-652c-49b3-a82c-33fd94468af8)
- [Open XML path origin](https://learn.microsoft.com/en-us/openspecs/office_standards/ms-oe376/a94c52e0-eb04-42b7-8b57-966bbd1f6061)
- [Open XML scaling behavior](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.presentation.animatescale)

The demonstration decks are generic examples created for this project. They contain no teachers' course slides, textbook screenshots, or student information.
