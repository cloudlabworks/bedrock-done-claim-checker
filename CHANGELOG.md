# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
