# Citing ALTEA

If you use ALTEA in your research, please cite the archived software:

> Bravo-Abad, J. (2026). *ALTEA: Autonomous Learning for Tomographic Ensembles
> and Attributes* (v0.1.0). Zenodo. <https://doi.org/10.5281/zenodo.21442516>

## BibTeX

```bibtex
@software{bravoabad_altea_2026,
  author    = {Bravo-Abad, Jorge},
  title     = {{ALTEA: Autonomous Learning for Tomographic Ensembles
               and Attributes}},
  year      = {2026},
  version   = {0.1.0},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.21442516},
  url       = {https://doi.org/10.5281/zenodo.21442516}
}
```

Machine-readable metadata is in
[`CITATION.cff`](https://github.com/jorgebravoabad/altea/blob/main/CITATION.cff),
which GitHub renders as a "Cite this repository" button.

## Which DOI to use

Zenodo mints two identifiers:

- a **concept DOI**, which always resolves to the most recent release — use this
  in papers, so citations stay current as ALTEA evolves;
- a **version DOI**, specific to one release — use this when reproducibility
  requires pinning the exact code that was run.

## Reproducibility

If you report results produced with ALTEA, consider archiving the
`provenance.json` from each run alongside your data. It records the exact
versions, configuration and input hashes, which makes your analysis auditable.
See {doc}`provenance`.
