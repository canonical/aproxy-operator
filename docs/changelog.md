# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Each revision is versioned by the date of the revision.

## [Unreleased]

Place any unreleased changes here, that are subject to release in coming versions :).

- Added support for base ubuntu@26.04. Aproxy now supports 20.04, 22.04, 24.04, and 26.04.
- Load the netfilter kernel modules required by the nftables rules before applying them.
- Organize the documentation home page by user needs and explain its structure.
- Migrated the `terraform/` module to the CC008 Charm Terraform Standard: renamed `versions.tf` to
  `terraform.tf`, added the mandatory `constraints` variable and the `application`/`provides`/`requires`
  outputs (replacing the deprecated `app_name` and `endpoints` outputs), added a `terraform/MAJOR_VERSION`
  file, and wired the `terraform_modules_compliance`, `terraform_modules_release` and
  `generate_terraform_docs` CI workflows. Note that the `base` variable now defaults to `null` (the
  charm's default base) instead of `ubuntu@24.04`; pass `base = "ubuntu@24.04"` explicitly to keep the
  previous default.

# 2026-05-19
- Add `aproxy-port` charm configuration to allow customizing the port that aproxy listens on.
- Fix a problem in the input chain that blocks forwarded traffic.

## 2026-03-05

- Add landing pages for how-to and reference section.

## 2026-02-19

- Update tutorial and add workflow to test the tutorial using Spread.

## 2025-01-11

- Fixed the model config variable names for HTTP and HTTPS proxy.

## 2025-12-17

- Moved charm-architecture.md from Explanation to Reference category.

## 2025-12-9

- Added support for base ubuntu@20.04. Aproxy now supports 20.04, 22.04, and 24.04.

## 2025-10-9

- Added core functionality and tests to the charm.
