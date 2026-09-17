"""House chart style for macro time-series charts.

An annotated style: series are labelled where they run rather than in a legend
box, so the reader never has to look away from the data to find out what a line
is. Gill Sans throughout, a pale horizontal grid, an open frame with only a
bottom rule, and no tick marks.

Colour carries meaning: the model estimate is the dark green accent, actual
data is grey, and any further series takes the next colour in the palette.

There is no source line: attribution is given verbally when presenting.

Typical use
-----------
    import chartstyle as cs

    fig, ax = cs.figure(title="US: the policy stance since 1985")
    ax.plot(x, policy, **cs.line(1))
    ax.plot(x, neutral, **cs.line(0))
    cs.label(ax, x[-1], policy[-1], "Policy rate", 1, dy=-22)
    cs.label(ax, x[-1], neutral[-1], "Neutral rate", 0, dy=18)
    cs.finish(fig, ax, ylabel="Per cent")
    fig.savefig("chart.png", dpi=200)
"""

# %% Imports
# Load date formatting, plotting, and tick-location helpers.
from __future__ import annotations

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import MultipleLocator

# The model estimate carries the accent colour; everything actual is grey, so
# the estimate is what the eye lands on first.
# %% Colour and typography palette
# Define the consistent colours and font used by the inflation charts.
ACCENT = "#0B6E4F"     # dark green - the model estimate
GREY = "#9A9A9A"       # actual data
BLACK = "#1A1A1A"      # titles and rules
FAINT = "#EFEFEF"      # gridlines
NOTE = "#5A5A5A"       # annotation text

# Further series, where a chart carries more than two lines.
DESERT = "#B5651D"     # dark desert orange
BLUE = "#2A6F97"       # slate blue
RED = "#A6242B"        # brick red

GREEN = ACCENT         # kept so older scripts importing GREEN still work

FONT = "Gill Sans MT"          # falls back automatically if unavailable

#: Line styles in the order they should be used, most prominent first.
#: Slot 0 is the model estimate; slot 1 the actual series it is compared with.
# %% Series line styles
# Associate each plotted series with a reusable colour and line width.
STYLES = [
    dict(color=ACCENT, lw=2.6, ls="-"),    # 0 model estimate
    dict(color=GREY,   lw=2.0, ls="-"),    # 1 actual data
    dict(color=DESERT, lw=2.0, ls="-"),    # 2
    dict(color=BLUE,   lw=2.0, ls="-"),    # 3
    dict(color=RED,    lw=2.0, ls="-"),    # 4
]


# %% Series styling helpers
# Return line properties and colours for plots and endpoint labels.
def line(i: int = 0, **overrides):
    """Keyword arguments for the i-th line style.

    Pass straight into ``ax.plot``:  ``ax.plot(x, y, **cs.line(1))``.
    Any keyword given here overrides the preset, e.g. ``cs.line(0, lw=2.0)``.
    """
    kw = dict(STYLES[i % len(STYLES)])
    kw.update(overrides)
    return kw


def colour(i: int = 0):
    """Just the colour of the i-th style, for annotations and fills."""
    return STYLES[i % len(STYLES)]["color"]


# %% On-chart annotations
# Name each line directly and provide a helper for concise notes.
def label(ax, x, y, text, i=0, dx=-10, dy=14, ha="right", bold=None):
    """Name a series where it runs, in its own colour, instead of in a legend.

    x, y : the point to label - normally the last observation of the series.
    i    : which line style the series used, so the label matches its colour.
    dx, dy : offset in points; nudge these when two labels would collide.
    bold : emphasise the label. Defaults to True for the model estimate.
    """
    if bold is None:
        bold = (i % len(STYLES)) == 0
    ax.annotate(text, xy=(x, y), xytext=(dx, dy), textcoords="offset points",
                fontsize=13, color=colour(i), ha=ha,
                weight="bold" if bold else "normal")


def note(ax, x, y, text, dy=55, ha="center", tick=True):
    """A short comment on the chart, optionally with a leader line to a point.

    Use sparingly - one per chart at most. The point of this style is that the
    chart carries its own reading, not that it is covered in text.
    """
    kw = dict(fontsize=11, color=NOTE, ha=ha)
    if tick:
        kw["arrowprops"] = dict(arrowstyle="-", color="#B0B0B0", lw=0.9)
    ax.annotate(text, xy=(x, y), xytext=(0, dy), textcoords="offset points", **kw)


# %% Figure setup
# Create a canvas with the shared type, title, and axis defaults.
def figure(title: str = "", ylabel: str = "", figsize=(11, 6.6)):
    """Create a figure and axes carrying the house style.

    ``title`` is set left-aligned above the plot, where a reader starts.
    """
    plt.rcParams.update({
        "font.family": FONT,
        "font.size": 13,
        "axes.linewidth": 1.0,
        "axes.edgecolor": BLACK,
        # Gill Sans has no U+2212 MINUS SIGN, so negative tick labels would
        # come out blank. Fall back to the ASCII hyphen for minus signs.
        "axes.unicode_minus": False,
    })

    fig, ax = plt.subplots(figsize=figsize)

    if title:
        ax.set_title(title, fontsize=17, loc="left", pad=18, color=BLACK)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=12, color=NOTE)

    return fig, ax


# %% Axes finishing
# Apply ticks, grid, zero rule, frame, and optional legend.
def finish(fig, ax, *, ylabel: str = "", ylim=None, ystep=None,
           yfmt="{x:,.0f}", legend=False, legend_loc="upper right",
           year_step: int = 5, rotate_years: int = 0, zero_line: bool = False,
           years: bool = True):
    """Apply the finishing touches once the series have been plotted.

    Parameters
    ----------
    ylabel      : axis label, set quietly beside the y axis.
    ylim, ystep : y-axis range and tick spacing.
    yfmt        : format string for y tick labels.
    legend      : off by default - series are named on the chart with
                  ``label()``. Turn it on where a chart has too many series
                  to label in place.
    year_step   : label every Nth year on the x axis.
    zero_line   : draw a rule at y=0, for series that change sign.
    years       : treat the x axis as dates. Set False where x is something
                  else - a strike, a maturity - and leave its ticks alone.
    """
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=12, color=NOTE)

    # --- y axis ------------------------------------------------------------
    if ylim is not None:
        ax.set_ylim(*ylim)
    if ystep is not None:
        ax.yaxis.set_major_locator(MultipleLocator(ystep))
    ax.yaxis.set_major_formatter(
        yfmt.format if callable(yfmt)
        else plt.matplotlib.ticker.StrMethodFormatter(yfmt))

    # a pale horizontal grid, sitting behind the data
    ax.grid(axis="y", color=FAINT, lw=1.0)
    ax.set_axisbelow(True)

    # a zero rule is darker than the grid but still lighter than any series
    if zero_line:
        ax.axhline(0, color="#C8C8C8", lw=1.0, zorder=0)

    # --- x axis: a tick every `year_step` years ----------------------------
    ax.margins(x=0.01)
    if years:
        ax.xaxis.set_major_locator(mdates.YearLocator(year_step))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        plt.setp(ax.get_xticklabels(), rotation=rotate_years,
                 ha="center" if rotate_years == 0 else "right")

    # --- frame: only a bottom rule, and no tick marks anywhere -------------
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#C8C8C8")
    ax.tick_params(length=0, colors="#6A6A6A")

    # --- legend: normally off, since series are labelled in place ----------
    if legend and ax.get_legend_handles_labels()[0]:
        kwargs = dict(frameon=False, fontsize=12, handlelength=2.4,
                      labelspacing=0.6)
        if isinstance(legend_loc, (tuple, list)):
            ax.legend(loc="upper left", bbox_to_anchor=legend_loc, **kwargs)
        else:
            ax.legend(loc=legend_loc, **kwargs)

    fig.tight_layout()
    return fig, ax
