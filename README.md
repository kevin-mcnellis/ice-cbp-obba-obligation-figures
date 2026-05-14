# ICE/CBP OBBA Obligation Figures

This folder documents and reproduces the four figures used in:

<https://www.kevinmcnellis.com/posts/ice-cbp-obba-obligation/>

It is designed to be copied into a public GitHub repository and linked from the
post methodology. The package preserves the exact figure-building scripts used
for the published graphics, the derived input panel needed by the object-class
figures, the rendered outputs, chart-data CSVs, and lightweight verification
checks.

## Figures Covered

| Published figure | Generated file |
| --- | --- |
| Intro comparison of annual appropriations, OBBA appropriations, and obligations | `output/figures/ice_cbp_intro_obligation_vs_appropriation.png` |
| ICE/CBP OBBA obligations by object class | `output/figures/ice_cbp_2025_obba_object_class.png` |
| CBP obligations by funding source and object class | `output/figures/cbp_2025_funding_source_object_class_obligations.png` |
| ICE obligations by funding source and object class | `output/figures/ice_2025_funding_source_object_class_obligations.png` |

## Reproduce The Figures

From this folder:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
python3 scripts/build_publication_graphics.py
python3 verification/verify_publication_package.py
```

The build command writes PNG, SVG, chart-data CSV, and metadata JSON outputs
under `output/`.

## Source Data Included

The object-class figures use this derived File B panel:

`ice_cbp_file_b_program_activity_object_class_monthly_and_quarterly_2024_01_to_2025_12.csv`

That panel is built from public USAspending File B / object-class program
activity downloads. The figure scripts treat File B as a decomposition layer,
not as a complete account-balance layer. Calendar-year 2025 values are derived
from cumulative quarter-end snapshots:

`(Mar. 31, 2025 - Dec. 31, 2024) + (Jun. 30 - Mar. 31) + (Sep. 30 - Jun. 30) + Dec. 31, 2025`

The intro figure uses the published values embedded in
`scripts/build_ice_cbp_intro_obligation_vs_appropriation_figure.py`; its chart
data is written to `output/data/ice_cbp_intro_obligation_vs_appropriation_chart_data.csv`.

## Important Methodology Notes

- File A is the preferred source for account-balance questions such as total
  budgetary resources, obligations, and unobligated balances.
- File B supports object-class and program-activity decomposition. It includes
  award and non-award spending grouped together.
- The two Sankey figures and the OBBA object-class figure use File B because the
  question is how calendar-year 2025 obligations break out by object class and
  funding source.
- `070-X-0532-000` is treated as CBP OBBA only for rows where File B labels the
  program activity as `FACILITIES (PL 119-21, TITLE IX, SUBTITLE A, SEC. 90002)`.
- The scripts preserve this special classification in `special_graphics_tafs.py`.

## Repository Layout

```text
.
├── README.md
├── docs/
│   └── methodology.md
├── scripts/
│   ├── build_publication_graphics.py
│   ├── build_ice_cbp_intro_obligation_vs_appropriation_figure.py
│   ├── build_ice_cbp_funding_source_object_class_sankey.py
│   └── build_ice_cbp_obba_object_class_figure 4.py
├── object_class_bridge.py
├── special_graphics_tafs.py
├── ice_cbp_file_b_program_activity_object_class_monthly_and_quarterly_2024_01_to_2025_12.csv
├── MANIFEST.sha256
├── output/
│   ├── data/
│   └── figures/
└── verification/
    └── verify_publication_package.py
```

## Verification

`verification/verify_publication_package.py` checks that:

- all four published PNGs exist and are non-empty;
- corresponding SVG and metadata sidecars exist;
- chart-data CSVs exist and are non-empty;
- the included File B panel contains the quarterly snapshots needed by the
  2025 object-class calculations;
- the PNG files have valid PNG signatures.

For a full rebuild check, run `python3 scripts/build_publication_graphics.py`
before the verifier.

`MANIFEST.sha256` records file hashes for the package after the verified build.
