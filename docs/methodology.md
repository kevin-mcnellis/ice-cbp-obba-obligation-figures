# Methodology Notes

## Scope

This package reproduces four figures from the public post:

<https://www.kevinmcnellis.com/posts/ice-cbp-obba-obligation/>

The figures summarize calendar-year 2025 ICE and CBP funding and obligations
after enactment of the One Big Beautiful Bill Act, P.L. 119-21.

## Source Layers

The figures use two distinct source layers:

| Source layer | Used for | Limits |
| --- | --- | --- |
| USAspending File A / Account Balances | Account-level budgetary-resources context for annual appropriations, OBBA appropriations, obligations, and unobligated balances | Does not decompose every dollar by object class or program activity |
| USAspending File B / Object Class Program Activity | Object-class and program-activity decomposition in the Sankey and OBBA object-class figures | Does not by itself separate internal agency spending from external awards |

The object-class figures are decomposition graphics. They should not be read as
replacements for File A account-balance totals.

## Calendar-Year 2025 File B Calculation

The public File B rows are cumulative within fiscal year. For calendar-year 2025
object-class figures, the scripts compute:

```text
(FY2025 Q2 / Mar. 31 - FY2025 Q1 / Dec. 31)
+ (FY2025 Q3 / Jun. 30 - FY2025 Q2 / Mar. 31)
+ (FY2025 Q4 / Sep. 30 - FY2025 Q3 / Jun. 30)
+ FY2026 Q1 / Dec. 31
```

This produces calendar-year 2025 obligations while respecting the fiscal-year
boundary between September and October.

## Funding-Source Buckets

The Sankey figures use these funding-source buckets:

- `Annual appropriations - current year BA`
- `Annual appropriations - carryover BA`
- `Fee revenue`
- `OBBA`

The bucket logic is implemented in `special_graphics_tafs.py`, with publication
display labels handled in `object_class_bridge.py`.

## Section 90002 Special Row

The raw panel can identify `070-X-0532-000` as an `X` / no-year account. For the
published graphics, only rows meeting both conditions below are classified with
CBP OBBA:

1. `tafs = 070-X-0532-000`
2. `program_activity_name = FACILITIES (PL 119-21, TITLE IX, SUBTITLE A, SEC. 90002)`

This rule is intentionally narrow and lives in `special_graphics_tafs.py`.

## Object-Class Labels

Object-class labels come from USAspending File B. `object_class_bridge.py` maps
those labels to OMB Section 83 object-class concepts and to shorter publication
labels. Personnel compensation and benefit classes are rolled into the published
`Personnel expenses` category.

## Rebuild Command

```sh
python3 scripts/build_publication_graphics.py
```

That wrapper runs all three figure builders and verifies the expected output
files are present and non-empty.
