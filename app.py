"""IS 445 Final Project — public-facing stock/bond data story.

All returns come from the unmodified JST Macrohistory Database R6 workbook.
Run from this project's directory with: streamlit run app.py
"""

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


# -----------------------------------------------------------------------------
# Data and authorship
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "JSTdatasetR6.xlsx"
REPO_URL = "https://github.com/kunyangjiang/is445-final"
SOURCE_URL = "https://www.macrohistory.net/database/"
LICENSE_URL = "https://www.macrohistory.net/database/licence-terms/"
AUTHORS = "Kunyang Jiang · Lucas Zhu · Oliver Lee · Yi-Hsun Kao"
STOCK_COLOR = "#265A76"
BOND_COLOR = "#CA7A42"
UP_COLOR = "#137D74"
DOWN_COLOR = "#BB4F56"
GRID_COLOR = "#E5E8E8"


st.set_page_config(
    page_title="Is Diversification Worth It? | IS 445",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner=False)
def load_returns() -> pd.DataFrame:
    """Read the original XLSX and reproduce the Parts 1–2 U.S. selection."""
    frame = pd.read_excel(DATA_FILE, sheet_name="Sheet1", engine="openpyxl")
    required = {"iso", "year", "eq_tr", "bond_tr"}
    if not required.issubset(frame.columns):
        raise ValueError("The JST workbook is missing required return columns.")

    us = frame.loc[
        frame["iso"].eq("USA") & frame["year"].between(1950, 2020),
        ["year", "eq_tr", "bond_tr"],
    ].copy()
    us = us.sort_values("year").reset_index(drop=True)
    if (
        len(us) != 71
        or us["year"].duplicated().any()
        or us[["eq_tr", "bond_tr"]].isna().any().any()
        or us["year"].tolist() != list(range(1950, 2021))
    ):
        raise ValueError("The expected 71 complete U.S. annual observations are unavailable.")

    us["Stocks"] = us["eq_tr"] * 100
    us["Government bonds"] = us["bond_tr"] * 100
    return us[["year", "Stocks", "Government bonds"]]


def make_boxplot(rows: pd.DataFrame) -> alt.Chart:
    long = rows.melt(
        id_vars="year",
        value_vars=["Stocks", "Government bonds"],
        var_name="asset",
        value_name="annual_return",
    )
    return (
        alt.Chart(long)
        .mark_boxplot(size=35)
        .encode(
            x=alt.X(
                "annual_return:Q",
                title="Annual nominal total return (%)",
                scale=alt.Scale(domain=[-50, 55]),
                axis=alt.Axis(gridColor=GRID_COLOR),
            ),
            y=alt.Y(
                "asset:N",
                sort=["Stocks", "Government bonds"],
                title=None,
                axis=alt.Axis(labelFontSize=13, labelPadding=10),
            ),
            color=alt.Color(
                "asset:N",
                scale=alt.Scale(
                    domain=["Stocks", "Government bonds"],
                    range=[STOCK_COLOR, BOND_COLOR],
                ),
                legend=None,
            ),
        )
        .properties(height=185)
        .configure_view(stroke=None)
    )


def make_linked_charts(rows: pd.DataFrame) -> alt.Chart:
    long = rows.melt(
        id_vars="year",
        value_vars=["Stocks", "Government bonds"],
        var_name="asset",
        value_name="annual_return",
    )
    pick_year = alt.selection_point(
        name="chosen_year",
        fields=["year"],
        on="click",
        clear="dblclick",
        toggle=False,
        empty=False,
    )

    heatmap = (
        alt.Chart(long)
        .mark_rect(stroke="white", strokeWidth=0.75)
        .encode(
            x=alt.X(
                "year:O",
                sort="ascending",
                title="Year (click a cell to select)",
                axis=alt.Axis(
                    values=list(range(1950, 2021, 10)),
                    labelAngle=0,
                    labelOverlap=False,
                    labelFontSize=11,
                ),
            ),
            y=alt.Y(
                "asset:N",
                sort=["Stocks", "Government bonds"],
                title=None,
                axis=alt.Axis(labelFontSize=12, labelPadding=9),
            ),
            color=alt.Color(
                "annual_return:Q",
                scale=alt.Scale(
                    domain=[-50, 0, 50],
                    range=[DOWN_COLOR, "#F6F6F4", UP_COLOR],
                ),
                title="Return (%)",
                legend=alt.Legend(orient="bottom", gradientLength=200),
            ),
            tooltip=[
                alt.Tooltip("year:O", title="Year"),
                alt.Tooltip("asset:N", title="Asset"),
                alt.Tooltip("annual_return:Q", title="Return (%)", format="+.2f"),
            ],
        )
        .add_params(pick_year)
        .properties(height=115, title="Annual returns: select a year")
    )

    scatter_encoding = {
        "x": alt.X(
            "Stocks:Q",
            title="Stock total return (%)",
            scale=alt.Scale(domain=[-50, 55]),
            axis=alt.Axis(gridColor=GRID_COLOR),
        ),
        "y": alt.Y(
            "Government bonds:Q",
            title="Government-bond total return (%)",
            scale=alt.Scale(domain=[-25, 45]),
            axis=alt.Axis(gridColor=GRID_COLOR),
        ),
        "tooltip": [
            alt.Tooltip("year:O", title="Year"),
            alt.Tooltip("Stocks:Q", title="Stocks (%)", format="+.2f"),
            alt.Tooltip("Government bonds:Q", title="Bonds (%)", format="+.2f"),
        ],
    }
    scatter_base = alt.Chart(rows).encode(**scatter_encoding)
    context = scatter_base.mark_circle(size=72, color="#97A9B6", opacity=0.66)
    highlight = (
        scatter_base.transform_filter(pick_year)
        .mark_circle(
            size=290,
            color="#F4A442",
            opacity=1,
            stroke="#824E22",
            strokeWidth=2,
        )
    )

    x_zero = (
        alt.Chart(pd.DataFrame({"zero": [0]}))
        .mark_rule(color="#7D8990", strokeDash=[4, 5])
        .encode(x="zero:Q")
    )
    y_zero = (
        alt.Chart(pd.DataFrame({"zero": [0]}))
        .mark_rule(color="#7D8990", strokeDash=[4, 5])
        .encode(y="zero:Q")
    )
    scatter = alt.layer(x_zero, y_zero, context, highlight).properties(
        height=325, title="Stock and bond returns: the selected year is outlined in amber"
    )

    return (
        alt.vconcat(heatmap, scatter, spacing=24)
        .resolve_scale(color="independent")
        .configure_view(stroke=None)
        .configure_title(anchor="start", fontSize=16, fontWeight=600, color="#263746")
    )


def make_stock_down_chart(rows: pd.DataFrame) -> alt.Chart:
    down_years = rows.loc[rows["Stocks"] < 0].copy()
    down_years["outcome"] = down_years["Government bonds"].gt(0).map(
        {True: "Bonds gained", False: "Bonds did not gain"}
    )
    return (
        alt.Chart(down_years)
        .mark_bar(cornerRadiusEnd=3)
        .encode(
            x=alt.X(
                "year:O",
                title="Year when stocks lost value",
                sort="ascending",
                axis=alt.Axis(labelAngle=0, labelFontSize=12),
            ),
            y=alt.Y(
                "Government bonds:Q",
                title="Government-bond return (%)",
                scale=alt.Scale(domain=[-8, 29]),
                axis=alt.Axis(gridColor=GRID_COLOR),
            ),
            color=alt.Color(
                "outcome:N",
                scale=alt.Scale(
                    domain=["Bonds gained", "Bonds did not gain"],
                    range=[UP_COLOR, DOWN_COLOR],
                ),
                legend=alt.Legend(title=None, orient="bottom"),
            ),
            tooltip=[
                alt.Tooltip("year:O", title="Year"),
                alt.Tooltip("Stocks:Q", title="Stock return (%)", format="+.2f"),
                alt.Tooltip("Government bonds:Q", title="Bond return (%)", format="+.2f"),
            ],
        )
        .properties(height=285)
        .configure_view(stroke=None)
    )


def reset_period() -> None:
    st.session_state["year_range"] = (1950, 2020)


# -----------------------------------------------------------------------------
# Site layout
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp { background: #FAFBF9; color: #233443; }
    .block-container { max-width: 1100px; padding-top: 2.5rem; padding-bottom: 5rem; }
    h1, h2, h3 { color: #1E3140; letter-spacing: -0.025em; }
    h1 { font-size: clamp(2.4rem, 5vw, 4.1rem) !important; line-height: 1.12 !important; }
    h2 { padding-top: 1rem; }
    .story-kicker { color: #366B76; font-size: .8rem; font-weight: 700; letter-spacing: .15em; }
    .story-deck { color: #536573; font-size: 1.14rem; line-height: 1.7; max-width: 790px; }
    .byline { font-size: .92rem; color: #576774; margin: .7rem 0 2.1rem; }
    .editorial-rule { border: 0; border-top: 1px solid #D8E0DE; margin: 1.5rem 0; }
    .chapter-label { font-size: .78rem; font-weight: 700; color: #417D80; letter-spacing: .14em; margin-top: 1.5rem; }
    .figure-note { color: #657684; font-size: .88rem; line-height: 1.55; margin-top: .15rem; }
    [data-testid="stMetricValue"] { color: #243E4C; }
    [data-testid="stSidebar"] { background-color: #F0F4F2; }
    a { color: #176F7A !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

try:
    full = load_returns()
except (FileNotFoundError, ValueError, OSError) as exc:
    st.error(f"The data file could not be loaded: {exc}")
    st.info("Place JSTdatasetR6.xlsx inside the project's data/ directory.")
    st.stop()

with st.sidebar:
    st.markdown("### Explore the record")
    st.caption("The main charts respond to this time window. The opening facts refer to the full 1950–2020 sample.")
    st.slider(
        "Years shown",
        min_value=1950,
        max_value=2020,
        value=(1950, 2020),
        key="year_range",
    )
    st.button("Reset to 1950–2020", on_click=reset_period)
    st.divider()
    st.markdown("**Reading the charts**")
    st.markdown("- Teal: positive return or bond gain\n- Rose: negative return or bond loss\n- Amber dot: the year you select")
    st.caption("This is an educational historical comparison, not an investment recommendation.")

start_year, end_year = st.session_state["year_range"]
current = full.loc[full["year"].between(start_year, end_year)].copy()
full_stock_down = full.loc[full["Stocks"] < 0]
bond_up_when_stocks_down = int((full_stock_down["Government bonds"] > 0).sum())
both_down = int((full_stock_down["Government bonds"] < 0).sum())

st.markdown('<p class="story-kicker">IS 445 · FALL 2026 · FINAL PROJECT</p>', unsafe_allow_html=True)
st.title("Is Diversification Worth It?")
st.markdown(
    '<p class="story-deck">When U.S. stocks lost money, did government bonds offer a way out? '
    'We revisit 71 years of historical returns to examine both the promise and the limits of holding different assets.</p>',
    unsafe_allow_html=True,
)
st.markdown(f'<p class="byline">By {AUTHORS} &nbsp; | &nbsp; United States, 1950–2020</p>', unsafe_allow_html=True)
st.markdown('<hr class="editorial-rule">', unsafe_allow_html=True)

k1, k2, k3 = st.columns(3)
with k1:
    st.metric("Years when stocks fell", f"{len(full_stock_down)} / 71")
with k2:
    st.metric("Bond gains in those years", f"{bond_up_when_stocks_down} / {len(full_stock_down)}")
with k3:
    st.metric("Years both assets fell", f"{both_down}")
st.caption("Headline counts are calculated from the entire 1950–2020 dataset; changing the sidebar updates the charts below.")

st.markdown(
    "In this historical sample, stocks delivered a higher average annual return than government bonds, "
    "but they also moved more sharply from year to year. Bonds sometimes gained when stocks declined, "
    "which is one reason investors use more than one asset class. That protection was not universal: "
    "in three years, both assets posted negative annual returns."
)

st.markdown('<p class="chapter-label">01 / THE TRADE-OFF</p>', unsafe_allow_html=True)
st.header("Higher average returns came with bigger swings")
st.markdown(
    "Across 1950–2020, stocks averaged **12.38%** a year, compared with **6.12%** for government bonds. "
    "These are simple averages of yearly returns, not the growth rate of a long-term investment account. "
    "Stocks also had a higher standard deviation of annual returns—**16.22 percentage points** versus "
    "**10.54** for bonds. The distribution below puts those differences side by side."
)
st.altair_chart(make_boxplot(current), use_container_width=True, theme=None)
st.markdown(
    '<p class="figure-note"><strong>Figure 1.</strong> Each box marks the middle half of annual returns, '
    'the internal line marks the median, and points beyond the whiskers show unusually large moves. '
    'This figure is original, calculated from JST R6 data. The sidebar changes the period displayed.</p>',
    unsafe_allow_html=True,
)

st.markdown('<p class="chapter-label">02 / EXPLORE YEAR BY YEAR</p>', unsafe_allow_html=True)
st.header("Did stocks and bonds move together?")
st.markdown(
    "The upper grid gives each year two cells: one for stocks and one for government bonds. "
    "**Click any colored cell** to find the same year's stock–bond pair in the scatterplot below; "
    "double-click a cell to clear your choice. Years in the upper-left part of the scatterplot "
    "are especially revealing: stocks lost value while bonds gained. Hover for exact figures."
)
st.altair_chart(make_linked_charts(current), use_container_width=True, theme=None)
st.markdown(
    '<p class="figure-note"><strong>Figure 2 · Primary interactive visualization.</strong> '
    'Linked annual-return heatmap and scatterplot adapted from the team’s Part 2 analysis. '
    'The dashed axes divide gains and losses; click-to-highlight is in addition to basic tooltips. '
    'Source: JST R6; authors: project team.</p>',
    unsafe_allow_html=True,
)
st.markdown(
    "Across the full sample, the correlation between annual stock and bond returns was about **−0.049**, "
    "or nearly zero. That means their year-by-year movements showed little *linear* relationship here. "
    "It does not mean one asset always offsets the other, and a relationship observed in this period "
    "need not remain the same in the future."
)

st.markdown('<p class="chapter-label">03 / THE STRESS TEST</p>', unsafe_allow_html=True)
st.header("What happened in the years when stocks fell?")
st.markdown(
    "Rather than averaging across every year, we can focus on the **14 years when stocks had negative returns**. "
    "Bonds gained in **11** of them, including 2008, when the dataset records a stock return of about "
    "**−38.75%** and a bond return of about **+24.68%**. However, both were down in "
    "**1969, 1973, and 1981**. The bars show why diversification can help, without promising that it always will."
)
if (current["Stocks"] < 0).any():
    st.altair_chart(make_stock_down_chart(current), use_container_width=True, theme=None)
else:
    st.info("No years with negative stock returns fall inside the selected range. Expand the sidebar period to see this chart.")
st.markdown(
    '<p class="figure-note"><strong>Figure 3.</strong> Government-bond returns in years when stock returns were negative. '
    'Teal bars represent bond gains; rose bars represent bond losses. The chart uses the same JST R6 data '
    'and was created by the project team. It is filtered by the sidebar.</p>',
    unsafe_allow_html=True,
)

st.markdown('<p class="chapter-label">04 / WHAT WE CAN CONCLUDE</p>', unsafe_allow_html=True)
st.header("A useful cushion, not a guarantee")
st.markdown(
    "The historical pattern gives a practical reason to combine different types of investments: "
    "bonds often behaved differently from stocks during bad stock-market years. But that observation "
    "is **not** a backtest of a 60/40 portfolio, nor does it establish that any particular mix would "
    "have delivered the best results. Portfolio weights, rebalancing, costs, and the investor's time "
    "horizon would all matter."
)
st.markdown(
    "There are also limits to the evidence. We use one country's **annual nominal total returns** for "
    "1950–2020: inflation is not subtracted, and year-end figures cannot capture losses that happened "
    "between observations. The historical series is constructed from several underlying sources; "
    "it is not a direct record of modern exchange-traded funds. The lesson is more modest than "
    "'bonds are safe': the benefits of diversification vary by period and by what happens in markets."
)

st.markdown('<hr class="editorial-rule">', unsafe_allow_html=True)
st.header("Data, methods & credits")
st.markdown(
    "**Data source.** Jordà–Schularick–Taylor (JST) Macrohistory Database, Release 6, "
    f"published by the MacroFinance & MacroHistory Lab. [Official database]({SOURCE_URL}) · "
    f"[Dataset licensing terms]({LICENSE_URL}) (CC BY-NC-SA 4.0). "
    "We use U.S. observations from 1950 through 2020, with `eq_tr` for stock total returns "
    "and `bond_tr` for government-bond total returns. Decimal returns were multiplied by 100 "
    "for percentage displays; no missing values occur in this selected sample."
)
st.markdown(
    "**Reproduce our analysis.** "
    f"[Analysis notebook]({REPO_URL}/blob/main/Analysis.ipynb) · "
    f"[Original XLSX snapshot]({REPO_URL}/blob/main/data/JSTdatasetR6.xlsx) · "
    f"[Application source code]({REPO_URL}/blob/main/app.py). "
    "All three visuals on this page are original charts created for this class project "
    "from the cited JST dataset; the linked interactivity builds on our Part 2 dashboard."
)
st.markdown(
    "**Suggested academic citations.** Jordà, Schularick & Taylor (2017), "
    "*Macrofinancial History and the New Business Cycle Facts*; "
    "Jordà, Knoll, Kuvshinov, Schularick & Taylor (2019), "
    "*The Rate of Return on Everything, 1870–2015*."
)
st.caption(
    "IS 445 Final Project · Kunyang Jiang, Lucas Zhu, Oliver Lee, Yi-Hsun Kao · "
    "Noncommercial academic data use; data and data-derived figures credited under CC BY-NC-SA 4.0."
)
