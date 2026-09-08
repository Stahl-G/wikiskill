# Deliver the recalculated workbook

## Description
Formula recalculation is useful only if the recalculated file replaces the file handed to the evaluator or user.

## Root cause
`openpyxl` writes formulas but does not populate cached results. A trace converted `output.xlsx` into `recalc/output.xlsx` and inspected that copy, while leaving the original uncached `output.xlsx` as the delivered artifact.

## Evidence
Failure sequence:
```sh
soffice --headless -env:UserInstallation=file:///... --convert-to xlsx --outdir recalc output.xlsx
python3 -c "load_workbook('recalc/output.xlsx', data_only=True)"
```
The validation copy had booleans, but the final output still had null cached values.

Successful traces used:
```sh
soffice --headless -env:UserInstallation=file:///... --convert-to xlsx --outdir recalc output.xlsx
if [ -f recalc/output.xlsx ]; then mv recalc/output.xlsx output.xlsx; fi
```

## Workaround
Set `fullCalcOnLoad`, `forceFullCalc`, and automatic calculation before saving, then convert into a workspace-local directory and `mv`/`cp` the converted file over the final path. Reopen that exact final path with `data_only=False` and `data_only=True` before reporting completion.