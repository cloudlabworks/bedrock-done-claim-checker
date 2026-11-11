# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0]

First PyPI release. Status unchanged: one live two-claim smoke test (2026-10-27) and offline unit tests; not an accuracy benchmark.

### Added

- `pip install bedrock-done-claim-checker` installs the `bedrock_done_claim_checker` package (`bedrock_done_claim_checker.handler`). Standard library only; `lambda_handler` also needs `boto3`, which the Lambda Python runtime provides.
- Release workflow: builds the sdist and wheel from hash-pinned build tools (`requirements/release.txt`), attests build provenance, publishes to PyPI by trusted publishing and creates a GitHub release with the provenance bundle.
- CI workflow: offline unit tests on Python 3.10 and 3.13, and a build that installs and imports the wheel.

### Changed

- Minimum Python is 3.10. The Lambda function still runs on `python3.12`; `src/handler.py`, `deploy.sh` and the scripts are unchanged.

## 2026-11-03

No versioned release yet. This section records the repository as of 2026-11-03.

### Added

- Bedrock done-claim checker: a Lambda function and one Bedrock model behind a capped harness, with the CloudFormation template (`bedrock-harness-demo.yaml`), deploy, invoke, preflight and teardown scripts, and offline tests (40a461c).
- README: results of the first live run (a667fd8).
- `CONTRIBUTING.md`: contributions are released under the repository's MIT licence, and commits carry a DCO sign-off (#1).

### Changed

- The concurrency pin is optional (`ReservedConcurrency`, off by default): new AWS accounts reject `ReservedConcurrentExecutions` (2bf1df3).

### Fixed

- Claim words are stemmed before the evidence check, so a well-evidenced claim ("deployed", "tests" against "deploy", "pytest") is no longer downgraded; regression test added (247760f).

[Unreleased]: https://github.com/cloudlabworks/bedrock-done-claim-checker/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/cloudlabworks/bedrock-done-claim-checker/releases/tag/v0.1.0
