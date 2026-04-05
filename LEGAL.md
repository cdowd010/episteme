# Legal And Source-Handling Policy

This file is an operational compliance guide for the repository. It is not legal advice.

Primary author: Chris Dowd

## 1. Outbound Licensing

- Repo-authored source code is released under the Apache License 2.0 in `LICENSE`.
- Repo-authored code attribution notices are carried in `NOTICE`.
- `ATTRIBUTION.md` is a human-readable summary only. It does not replace or modify the underlying licenses.

## 2. Third-Party Material Is Not Relicensed

- Third-party papers, articles, preprints, journal layouts, figures, tables, images, trademarks, and database records cited from this repository remain under their original terms.
- Bibliographic metadata stored in `data/papers.json`, `data/literature_watch.json`, and rendered views is not a relicense of the underlying source material.
- The repository must not imply endorsement by any cited author, publisher, collaboration, laboratory, or database provider.

## 3. Literature-Watch Storage Rule

- Store bibliographic metadata, source URLs, identifiers, scoring metadata, review decisions, and short repo-authored relevance notes only.
- Do not commit publisher PDFs, downloaded article files, copied full text, copied abstracts, reconstructed abstract text, copied figures, copied tables, or large third-party dataset exports unless the upstream license or written permission clearly allows it and that permission is documented next to the material.
- OpenAlex metadata may be used for discovery and ranking. Any abstract-derived text used during ranking must stay transient in memory and must not be written to repository data files.
- Physics-news ingestion must remain primary-source only, with a stored primary-source URL on an allowed domain before the item enters review.

## 4. Citation And Attribution Rules

- Cite the primary source whenever a theorem, empirical value, or prior result is relied on.
- Keep citation metadata accurate to the best available evidence: authors, title, venue, year, DOI/arXiv, and a short `used_for` note.
- If quoted text is ever used, keep it minimal, use quotation marks, and identify the source clearly.
- Reuse of third-party figures or tables requires a documented open license, written permission, or separate human review of whether a legal exception applies.

## 5. Practical Compliance Boundary

- This repository is designed to stay on the safer side of U.S. copyright practice by storing factual citation metadata and original notes rather than expressive source content.
- If future work needs to include substantial third-party text, images, tables, or PDFs, do not commit it until the license or permission basis is recorded explicitly.
- `python src/desitter.py validate` treats tracked image/document asset extensions as policy-gated inputs. A committed `.pdf`, office document, or image asset must either stay out of the repository or be explicitly allowlisted with a documented permission basis.

## 6. Third-Party Software And Tooling

- Direct runtime or development dependencies must not materially change the repository's outbound licensing obligations. In practice, unreviewed direct dependencies are blocked by default.
- New direct dependencies under strong-copyleft, network-copyleft, source-available-restrictive, or unclear terms should not be added unless Chris explicitly approves the legal tradeoff.
- Vendored third-party code must not be copied into the repository unless the upstream license is recorded and compatible with the outbound license of the destination files.
- Stronger-copyleft tools may be used only as bounded exceptions when they are separate executables or local runtimes, are not vendored into the repository, are not redistributed by the repository, and their review basis is recorded.
- The current reviewed software inventory lives in `data/third_party_software.json` and is rendered to `views/third_party_software.md`. `python src/desitter.py validate` blocks unreviewed declared dependencies and current-use tools classified as having a high legal impact.
- Hosted code-generation or coding-assistant tools with unclear, restrictive, or output-encumbering terms should be treated as prohibited until explicitly reviewed.

## 7. Directory License Boundary Map

| Path | Primary contents | Outbound license or rule |
| --- | --- | --- |
| `src/**/*.py` | Repo-authored executable code | Apache License 2.0 (`LICENSE`) with attribution notices in `NOTICE` |
// ...existing code...
| `src/integrity/*.json` | Repo-authored integrity configuration and reference data | Apache License 2.0 (`LICENSE`) |
| `data/*.json` | Repo-authored structured research data, citation metadata, and watch state | Apache License 2.0 (`LICENSE`); cited third-party works remain under their original terms |
| `views/*.md` | Generated markdown views rendered from repo-authored data | Apache License 2.0 (`LICENSE`); cited third-party works remain under their original terms |
| `session/`, `knowledge/`, `logs/`, `protocols/`, `templates/`, `workstreams/`, `archive/` | Repo-authored prose, notes, audits, and drafts | Apache License 2.0 (`LICENSE`) |
| `readme.md`, `LEGAL.md`, `ATTRIBUTION.md`, `SYSTEM_BRIEFING.md`, `CLAUDE.md`, `.cursorrules`, `.github/copilot-instructions.md` | Repo-authored documentation and tool-adapter instructions | Apache License 2.0 (`LICENSE`) |
| `LICENSE`, `NOTICE` | License and attribution texts | Distributed as their respective legal/attribution texts |

If a specific file states a narrower or different rule, that file-specific rule controls for that file.