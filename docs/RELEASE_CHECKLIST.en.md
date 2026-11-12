# GitHub release preparation checklist

[简体中文](RELEASE_CHECKLIST.md) | **English**

Repository: [ZGY949/pptx-animation-split](https://github.com/ZGY949/pptx-animation-split) became public on November 11, 2026 with the [v0.1.0a3 preview](https://github.com/ZGY949/pptx-animation-split/releases/tag/v0.1.0a3). That release provides only GitHub's automatic source downloads, with no PyPI package. This release targets [v0.1.0a4](https://github.com/ZGY949/pptx-animation-split/releases/tag/v0.1.0a4), providing matching tool and Skill bundles; see Releases for actual public status and attachments. The original checklist below retains historical first-publication checks.

## Publish matching tool and Skill bundles

1. Update `skills/pptx-animation-split/scripts/pptx_animation_split/_version.py`, maintained source and bilingual documents, run `python3 tools/sync_skill.py` and pass `--check`, and review the README's bundle publication status. Maintain only one engine.
2. Run relevant tests and build local test bundles with `python3 tools/build_release.py dist/local-check --local`. Review file scope, actual entry versions and limitations. Local `release.json` has `publishable: false`; do not upload it as an official build.
3. Obtain the necessary Git authorization, commit the complete change, confirm a clean workspace and create the matching version tag pointing to that commit. Pushing and publishing follow the maintainer's separate authorization.
4. From that clean tagged commit, run `python3 tools/build_release.py dist/release`. The script rejects dirty workspaces, missing or misplaced tags, inconsistent versions/engines and failed example runs. Review `validation.json`, both ZIP files and `SHA256SUMS.txt`. Confirm `release.json` has `publishable: true`, the correct version, source commit, compatibility requirements and attachment hashes.
5. Upload the generated `-tool.zip`, `-skill.zip`, `release.json`, `validation.json` and `SHA256SUMS.txt` together to one GitHub Release. Mark preview status and known limitations clearly, and do not mix artifacts from different builds. GitHub's source ZIP remains the full project.
6. After publication, download and verify attachment hashes, run the check from an older version that already supports it, verify the notification, matching URLs and compatibility decision, then test the downloaded bundles. When introducing update checking, `v0.1.0a3` has no such command and requires a manual upgrade. Check real release-manifest reads first; verify cross-version notifications after a subsequent compatible release. Actual remote reads currently cover existing release metadata; future newer-release notifications have not received remote acceptance testing.

Version checks do not replace programs, upload presentations or subscribe users to notifications. See the [tool guide](TOOL.en.md) and [Skill guide](SKILL_INSTALL.en.md) for installation, updates, rollback and removal. The manual Tests workflow includes dual-bundle builds; it has not been run remotely for this change and does not publish automatically.

## Prepared

- [x] Standalone Python project that runs without the original skill directory.
- [x] Commands for splitting, validation, and text inspection, plus an optional local installation entry point.
- [x] Output protection: reject the source, existing output, and link aliases; save only after validation passes.
- [x] Existing regressions retained and expanded to 79 tests covering complex triggers, text/images/shapes/groups, paths, navigation, and output protection.
- [x] Generic demonstration deck, complex animation examples authored in WPS, trigger/repetition examples, a click-order example, Chinese and English README and supporting documents, support conditions, known limitations, and an issue-report template.
- [x] Credit to the original author, a link to the original project, and a permanent link to the author's licensing clarification.
- [x] Ignore rules excluding real course decks, office documents, environment files, caches, and local artifacts.
- [x] Chinese and English issue-report templates, with repository and issue-report URLs in installation metadata.
- [x] A manually triggered GitHub test workflow with official checkout/setup-python v7 commits pinned, custom-route and text-inspection steps, and a 10-minute timeout per job. It has not been run remotely.
- [x] Re-ran 79 local tests, isolated offline installation, and default/custom-route checks for the three examples on November 11, 2026. Reviewed history and examples for common sensitive patterns, with no matches. See the validation record for details and scope.

See [VALIDATION.en.md](VALIDATION.en.md) for actual results. Object triggers remain experimental, and comparison of trigger input against playback in Mac WPS is incomplete. Infinite loops produce a representative state, and small pixel differences in text scaling remain. These results do not establish that every application and platform has passed validation.

## Checks required before making the repository public

- [x] **Confirm this project's license.** On November 9, 2026, the maintainer confirmed MIT with attribution to `ZGY949`. The root `LICENSE`, installation metadata, and attribution document have been updated. MIT permits use, modification, distribution, and commercial use, requires retention of the copyright and license notice, and does not require publishing modified source code.
- [x] **Review existing provenance records.** Retained the migrated scripts' checksums, acknowledgment of the original project, and the author's licensing reply. The original scripts did not retain a line-by-line upstream mapping. This gap is documented in the attribution; no audited, fully independent origin is claimed. If other code sources are identified later, add their applicable requirements.
- [x] **Manually check key visual results.** Source slides 7 and 8 of the real deck were played step by step in macOS WPS Office 12.1.29182 and compared with all 14 static states on output slides 37–50. The corrected demonstration deck's 3 states and corresponding static output were also checked. No differences were found in equation visibility, paragraph positions, the red box, or the first appearance of answers. All 13 states of the native WPS complex example were also compared. Small pixel differences remain in text scaling and shape edges; see the validation record. Conclusions are limited to those slides and the local environment and do not establish acceptance of all decks or PowerPoint playback.
- [x] **Review platform claims.** The README and validation record explicitly state the scope checked on local macOS, Python 3.12, and WPS 12.1.29182. Windows, other Python versions, and PowerPoint remain unvalidated; no cross-platform success is claimed from these local checks.
- [x] **Confirm upload scope and repository name.** The maintainer confirmed uploading first to the private repository `ZGY949/pptx-animation-split`. Only standalone project files are included; teaching materials in the parent directory are excluded. The GitHub connection selects only this repository and no other private repositories.
- [x] **Review the source package for this upload.** It contains only source code, documentation, configuration, the MIT License, and generic demonstration decks. Checks for common credentials, private keys, notification-link tokens, and personal absolute paths found no matches. Real decks, temporary WPS lock files, caches, and validation artifacts are excluded. Review the actual files before each future commit or upload; `.gitignore` is not a substitute for that review.

## Follow-up before the first public release (historical record)

1. Review the private repository's files, MIT License, attribution, and README rendering. At publication, confirm the tag targets the audited commit and check the downloads and their SHA-256 checksums.
2. If further cross-platform validation is needed, manually run Tests from the Actions page after confirming the account's available allowance and costs. The workflow does not run automatically on push and does not publish automatically.
3. Before making the repository public or publishing the `v0.1.0a3` preview release, obtain the maintainer's confirmation and explain the known limitations. Continue marking checks that have not been performed as incomplete. The current upload authorization covers only the private repository.
4. After the repository is public, obtain the user's instruction before sharing a link in the [original discussion](https://github.com/maxonthegit/PPspliT/issues/29).

Publishing a PyPI package, creating an installer, registering a domain, and deploying a website are not currently required. The GitHub source project can serve as the initial way to share the tool.
