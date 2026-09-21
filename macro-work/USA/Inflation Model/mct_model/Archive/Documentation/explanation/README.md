# Understanding and fitting MCT

Open `Fitting_the_NY_Fed_MCT.pdf` for the 16-page guide. It is written for a statistically experienced reader learning factor models.

The editable source is `Fitting_the_NY_Fed_MCT.tex`. Keep `factor_illustration.pdf` alongside it. The figure is an explicitly labelled synthetic illustration, not a fitted model result.

Build from this directory, running twice to resolve the contents and references:

```powershell
pdflatex -interaction=nonstopmode -halt-on-error Fitting_the_NY_Fed_MCT.tex
pdflatex -interaction=nonstopmode -halt-on-error Fitting_the_NY_Fed_MCT.tex
```

Validation: compiled successfully without overfull boxes or unresolved references; checked PDF page count, external links, and rendered the illustration and Kalman-equation pages for visual inspection. Sources are linked inside the PDF. It distinguishes the published configuration, the Python implementation, and validation still required for the full fit.
