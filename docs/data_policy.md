# Data Policy

## Purpose

This repository is intended to distribute the AAT IEF gel ROI/lane review tool, not the underlying real research dataset.

## Default Rule

Do not commit real gel images, patient data, sample identifiers, reviewed clinical annotations, or exported training datasets unless the responsible institution has explicitly approved sharing.

## Ignored Data Locations

The `.gitignore` file excludes these data-bearing paths by default:

```text
dataset/Originial/*
outputs/*
Web/review_exports/*
```

Only placeholder files are kept so the expected folder structure exists after cloning.

## Allowed in the Repository

The following are normally safe to commit:

- source code
- configuration files
- non-sensitive documentation
- empty folder placeholders
- synthetic or fully anonymized example images, if clearly labelled and approved
- small test fixtures that do not contain real patient or sample data

## Restricted Data

Treat the following as restricted:

- raw gel image files from real research or clinical workflows
- manually reviewed ROI/lane geometry derived from real images
- lane-level category labels if they can be linked to real samples
- exported training CSV/JSONL files
- filenames or metadata that identify a patient, sample, site, clinician, or institution

## Recommended Collaboration Model

Use one of these models:

1. Private GitHub repository for code only, with data shared through the institution's approved secure channel.
2. Public code repository plus separate private data storage.
3. Public code repository plus synthetic/demo images only.

## Before Public Release

Before making the repository public:

1. confirm data-sharing permissions with the research owner or institution
2. remove all real image files and generated outputs
3. inspect CSV files for sample identifiers or labels
4. run a secret scan and large-file audit
5. add a license and citation policy

## Clinical Disclaimer

This tool supports research review of gel image segmentation. It is not validated for clinical diagnosis and must not be used as a standalone diagnostic system.
