"""app/user_panel.py
Customer-facing app for SamriddhiAI.

Run from SamriddhiAI/ root:
    py -3.11 -m streamlit run app/user_panel.py --server.port 8502
"""

from pathlib import Path
import sys
import pandas as pd
import streamlit as st
import altair as alt

sys.path.insert(0, str(Path.cwd()))

from app.shared.data_loader import (
    load_model_input, load_stress, load_life_stage,
    load_recommender, get_row,
)
from app.shared.formatting import money, pct
from app.shared.style import (
    apply_brand_style, header, viewing_label, metric_card, reco_card,
    info_banner, hr, SHIELD_SVG,
)

CHATBOT_URL = "http://localhost:8503"

import os as _os

def _is_cloud():
    """True when running on Streamlit Community Cloud."""
    return _os.environ.get("HOSTNAME", "").startswith("streamlit-")

st.set_page_config(
    page_title="SamriddhiAI - My Banking",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_brand_style(mode="user")


PRODUCT_NAMES = {
    "personal": "Personal Loan",
    "home":     "Home Loan",
    "auto":     "Auto Loan",
    "mortgage": "Mortgage Top-Up",
}

PRODUCT_WHY = {
    "personal": "Suited for planned expenses such as education, medical needs, "
                "or a wedding, with predictable monthly repayments.",
    "home":     "Designed for a home purchase, spreading the cost over many "
                "years at a rate fixed at the time of sanction.",
    "auto":     "For a new vehicle, with repayment terms typically between "
                "three and seven years.",
    "mortgage": "Lets you borrow against a property you already own, without "
                "selling it.",
}

CATEGORY_LABELS = {
    "salary": "Salary received",
    "business_income": "Business income",
    "emi": "EMI payment",
    "rent": "Rent paid",
    "discretionary": "Everyday spending",
    "bounce": "Payment failed",
    "suspicious": "Unusual transfer",
}


def _chatbot_url_for(customer_id):
    """Return the chatbot URL — cloud in production, localhost in local dev."""
    if _is_cloud():
        base = "https://samriddhiai-ykdcvwhe7sheeghqrdgr5i.streamlit.app"
    else:
        base = "http://localhost:8503"
    return f"{base}/?customer_id={customer_id}"

# ------------------------------------------------------------------
# Altair chart helpers — clean light background, our palette
# ------------------------------------------------------------------
def make_area_chart(df: pd.DataFrame, x: str, y_cols: list, color_map: dict,
                    height: int = 280) -> alt.Chart:
    """Area chart from a wide DataFrame."""
    melted = df.reset_index().melt(id_vars=x, value_vars=y_cols,
                                   var_name="series", value_name="value")
    chart = (
        alt.Chart(melted)
        .mark_area(opacity=0.35, interpolate="monotone", line=True)
        .encode(
            x=alt.X(f"{x}:T", title=None, axis=alt.Axis(format="%b %Y")),
            y=alt.Y("value:Q", title=None),
            color=alt.Color("series:N",
                            scale=alt.Scale(domain=list(color_map.keys()),
                                            range=list(color_map.values())),
                            legend=alt.Legend(title=None, orient="top")),
            tooltip=[alt.Tooltip(f"{x}:T", title="Month"),
                     alt.Tooltip("series:N", title="Series"),
                     alt.Tooltip("value:Q", title="Amount", format=",.0f")],
        )
        .properties(height=height, background="white")
        .configure_view(stroke=None)
        .configure_axis(grid=True, gridColor="#EEF0F3", domain=False, tickColor="#CCCCCC",
                        labelColor="#5B6675", titleColor="#5B6675")
    )
    return chart


def make_bar_chart(df: pd.DataFrame, cat_col: str, val_col: str,
                   color: str = "#2A7F6F", height: int = 260) -> alt.Chart:
    chart = (
        alt.Chart(df)
        .mark_bar(color=color, cornerRadius=2)
        .encode(
            x=alt.X(f"{val_col}:Q", title=None),
            y=alt.Y(f"{cat_col}:N", title=None, sort="-x"),
            tooltip=[alt.Tooltip(f"{cat_col}:N", title="Category"),
                     alt.Tooltip(f"{val_col}:Q", title="Average", format=",.0f")],
        )
        .properties(height=height, background="white")
        .configure_view(stroke=None)
        .configure_axis(grid=True, gridColor="#EEF0F3", domain=False, tickColor="#CCCCCC",
                        labelColor="#5B6675", titleColor="#5B6675")
    )
    return chart


def render_header():
    st.markdown(
        header(
            "SamriddhiAI",
            "Banking made simple",
            "Customer App",
        ),
        unsafe_allow_html=True,
    )


def render_sidebar():
    st.sidebar.markdown("### Welcome")

    quick = st.sidebar.radio(
        "",
        ["Healthy profile", "Stressed profile", "Enter my customer ID"],
        key="user_panel_login_radio",
    )

    if quick == "Healthy profile":
        customer_id = "CUST000005"
    elif quick == "Stressed profile":
        customer_id = "CUST000001"
    else:
        customer_id = st.sidebar.text_input(
            "Customer ID", value="CUST000005",
            placeholder="e.g. CUST000005",
            key="user_panel_id_input",
        )

    st.sidebar.markdown("---")
    st.sidebar.caption("SamriddhiAI · HackOut 2026 · Team Avengers")
    return customer_id


# ------------------------------------------------------------------
# Tab 1 — My account
# ------------------------------------------------------------------
def render_my_account(row, life_row, stress_row):
    st.subheader("My account")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(metric_card("Monthly income",
                                money(row["monthly_declared_income"]),
                                "as you declared to us"), unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card("You save",
                                pct(row["savings_rate_mean_7"]),
                                "share of monthly income"), unsafe_allow_html=True)
    with c3:
        st.markdown(metric_card("EMI payments",
                                pct(row["emi_to_income_mean_7"]),
                                "share of monthly income"), unsafe_allow_html=True)

    c4, c5, c6 = st.columns(3)
    with c4:
        st.markdown(metric_card("Active loans",
                                str(int(row["existing_loan_count"])),
                                "currently open"), unsafe_allow_html=True)
    with c5:
        st.markdown(metric_card("Banking tenure",
                                f"{row['relationship_tenure_years']:.1f} yrs",
                                "years with us"), unsafe_allow_html=True)
    with c6:
        st.markdown(metric_card("Age", str(int(row["age"])),
                                "as on file"), unsafe_allow_html=True)

    if stress_row is not None and stress_row["stress_level"] == "high":
        st.markdown(hr(), unsafe_allow_html=True)
        st.markdown(
            info_banner(
                "We are here if you need support",
                "Some recent months look tighter than usual. If you would like "
                "to talk through repayment options, we can help. No pressure, "
                "no sales.",
                icon=SHIELD_SVG,
            ),
            unsafe_allow_html=True,
        )


# ------------------------------------------------------------------
# Tab 2 — My money
# ------------------------------------------------------------------
def render_my_money(customer_id, row, stress_row):
    st.subheader("My money")
    st.caption("A clear view of how money moves through your account each month.")

    monthly = pd.read_parquet("data/processed/txn_monthly.parquet")
    cust_monthly = monthly[monthly["customer_id"] == customer_id].copy()
    cust_monthly["month"] = pd.to_datetime(cust_monthly["month"])
    cust_monthly = cust_monthly.sort_values("month").set_index("month")

    if len(cust_monthly) == 0:
        st.info("No transaction history available.")
        return

    stressed = stress_row is not None and stress_row["stress_level"] == "high"

    st.markdown("#### Money in and money out")
    money_df = cust_monthly[["credit_sum", "debit_sum"]].rename(
        columns={"credit_sum": "Money in", "debit_sum": "Money out"}
    )
    st.altair_chart(
        make_area_chart(
            money_df,
            x="month",
            y_cols=["Money in", "Money out"],
            color_map={"Money in": "#2A7F6F", "Money out": "#A84434"},
        ),
        use_container_width=True,
    )

    st.markdown("#### Where your money goes")
    cat_cols = {
        "emi_sum": "EMI",
        "rent_sum": "Rent",
        "discretionary_sum": "Everyday spending",
        "business_income_sum": "Business expenses",
    }
    present = {k: v for k, v in cat_cols.items() if k in cust_monthly.columns}
    cat_avgs = {label: float(cust_monthly[col].mean()) for col, label in present.items()}
    cat_avgs["Savings"] = max(0.0, float(cust_monthly["net_flow"].mean()))

    if sum(cat_avgs.values()) > 0:
        cat_df = pd.DataFrame({
            "Category": list(cat_avgs.keys()),
            "Average": list(cat_avgs.values()),
        })
        st.altair_chart(
            make_bar_chart(cat_df, cat_col="Category", val_col="Average",
                           color="#2A7F6F", height=260),
            use_container_width=True,
        )

    st.markdown("#### Savings trend")
    sav_df = cust_monthly[["savings_rate"]].rename(
        columns={"savings_rate": "Savings rate"}
    )
    st.altair_chart(
        make_area_chart(
            sav_df,
            x="month",
            y_cols=["Savings rate"],
            color_map={"Savings rate": "#2A7F6F"},
            height=240,
        ),
        use_container_width=True,
    )

    st.markdown(hr(), unsafe_allow_html=True)

    if stressed:
        st.markdown("#### What these months tell us")
        observations = []
        avg_savings = float(cust_monthly["savings_rate"].mean())
        if avg_savings < 0:
            observations.append(
                "In some months, spending has been higher than income. "
                "This is common, and it can be worked through."
            )
        elif avg_savings < 0.1:
            observations.append(
                "Savings have been thin in recent months. "
                "A small regular amount can help build a buffer."
            )
        emi_burden = float(row["emi_to_income_mean_7"])
        if emi_burden > 0.4:
            observations.append(
                "EMIs currently take up a large share of monthly income. "
                "Restructuring can spread this over a longer period."
            )
        observations.append(
            "Setting aside a fixed amount every month, however small, "
            "builds a buffer over time."
        )
        for obs in observations:
            st.markdown(f"- {obs}")
    else:
        st.markdown("#### What these months tell us")
        observations = []
        avg_savings = float(cust_monthly["savings_rate"].mean())
        if avg_savings > 0.3:
            observations.append(
                "You consistently save more than 30% of your income. "
                "That is a healthy buffer."
            )
        elif avg_savings > 0.1:
            observations.append(
                "You save a steady amount each month. "
                "This puts you in a comfortable position."
            )
        elif avg_savings >= 0:
            observations.append(
                "Savings have been modest. Small regular transfers can "
                "add up over a year."
            )
        emi_burden = float(row["emi_to_income_mean_7"])
        if emi_burden < 0.2:
            observations.append(
                "Your EMI burden is low, which leaves room in your budget "
                "for planned goals."
            )
        elif emi_burden < 0.4:
            observations.append(
                "Your EMIs are a moderate share of income. "
                "Comfortable, and worth watching over time."
            )
        twelve_month = float(cust_monthly["net_flow"].mean()) * 12
        if twelve_month > 0:
            observations.append(
                f"If you keep saving at this pace, you could set aside "
                f"{money(twelve_month)} over the next twelve months."
            )
        for obs in observations:
            st.markdown(f"- {obs}")

    st.markdown(hr(), unsafe_allow_html=True)
    st.markdown("#### Recent transactions")

    ledger = pd.read_parquet("data/interim/transaction_ledger.parquet")
    cust_txns = ledger[ledger["customer_id"] == customer_id].copy()
    cust_txns["date"] = pd.to_datetime(cust_txns["date"])
    cust_txns = cust_txns.sort_values("date", ascending=False).head(10)

    if len(cust_txns) == 0:
        st.caption("No transactions on file.")
    else:
        for _, t in cust_txns.iterrows():
            cat = CATEGORY_LABELS.get(t["true_category"], t["true_category"])
            direction = "in" if t["direction"] == "credit" else "out"
            amount = money(abs(t["amount"]))
            date_str = t["date"].strftime("%d %b %Y")
            st.markdown(f"**{date_str}** · {cat} · {amount} {direction}")


# ------------------------------------------------------------------
# Tab 3 — For you
# ------------------------------------------------------------------
def render_for_you(bundle, row, stress_row):
    st.subheader("For you")
    st.caption("Suggestions based on your profile and recent activity.")

    if stress_row is not None and stress_row["stress_level"] == "high":
        st.markdown(
            info_banner(
                "Let us look at your current commitments first",
                "Before we discuss new products, it may help to review your "
                "existing repayments together.",
                icon=SHIELD_SVG,
            ),
            unsafe_allow_html=True,
        )
        st.markdown("#### Support available now")
        st.markdown("- **Talk to a financial advisor** - free, no obligation")
        st.markdown("- **Restructure your EMIs** - spread repayments over a longer period")
        st.markdown("- **Savings plan review** - a small buffer goes a long way")
        return

    feature_names = bundle["feature_names"]
    x = row[feature_names].to_frame().T.astype(float).fillna(0)
    p_apply = float(bundle["head_a"].predict_proba(x)[0, 1])
    p_product = bundle["head_b"].predict_proba(x)[0]
    products = bundle["head_b"].classes_
    scored = sorted(
        [(p, p_apply * pr) for p, pr in zip(products, p_product)],
        key=lambda t: -t[1],
    )
    scored = [(p, s) for p, s in scored if s > 0.001][:2]

    if not scored:
        st.info("Nothing specific to suggest right now. Check back after your next month.")
        return

    st.markdown("#### Products you may be eligible for")
    for i, (prod, score) in enumerate(scored, 1):
        name = PRODUCT_NAMES.get(prod, prod.title())
        st.markdown(
            reco_card(
                f"{i}. {name}",
                PRODUCT_WHY.get(prod, ""),
            ),
            unsafe_allow_html=True,
        )

    st.markdown(hr(), unsafe_allow_html=True)
    st.markdown("#### Why this might suit you")
    reasons = []
    if row.get("savings_rate_mean_7", 0) > 0.3:
        reasons.append("You save regularly, so repayments would fit comfortably.")
    if row.get("salary_months_present", 0) >= 12:
        reasons.append("You receive a steady salary each month.")
    if row.get("has_any_existing_loan", 0) == 0:
        reasons.append("You have no existing loans, keeping things simple.")
    if not reasons:
        reasons.append("This suggestion is based on your overall profile.")
    for r in reasons[:4]:
        st.markdown(f"- {r}")

    emi_monthly = float(row.get("emi_sum_mean_7", 0))
    if emi_monthly > 0:
        st.markdown(hr(), unsafe_allow_html=True)
        st.markdown("#### Upcoming EMI payments")
        st.caption("Based on your recent EMI pattern, here is what to expect.")
        for i in range(1, 4):
            st.markdown(f"- Month {i}: approximately **{money(emi_monthly)}**")

    st.caption(
        "These suggestions are here to help you plan, not to push a product. "
        "You are always free to say no."
    )

def render_chat_tab(customer_id):
    """Embedded iframe locally; new-tab button on cloud (X-Frame-Options blocks cloud iframe)."""
    st.subheader("Chat with us")
    st.caption(
        "Ask about balance, loans, EMI, KYC, or anything else - in your own language."
    )

    # Cloud chatbot URL (deployed). Local uses 127.0.0.1:8503.
    if _is_cloud():
        url = f"https://samriddhiai-ykdcvwhe7sheeghqrdgr5i.streamlit.app/?customer_id={customer_id}"
    else:
        url = f"http://localhost:8503/?customer_id={customer_id}"

    if _is_cloud():
        # Cloud: iframe is blocked by X-Frame-Options, so use a button.
        st.markdown(
            f'''
            <div style="
                background:#FFFFFF;
                border:1px solid #E6E0D2;
                border-radius:8px;
                padding:32px;
                text-align:center;
                margin-top:20px;
            ">
                <div style="font-size:17px; color:#16202E; margin-bottom:16px;">
                    Our assistant is ready. Click below to start a conversation.
                </div>
                <a href="{url}" target="_blank" rel="noopener noreferrer" style="
                    display:inline-block;
                    padding:14px 32px;
                    background:#2A7F6F;
                    color:#FFFFFF !important;
                    border-radius:6px;
                    font-weight:600;
                    font-size:16px;
                    text-decoration:none;
                    letter-spacing:0.02em;
                ">Open Chatbot</a>
                <div style="font-size:13px; color:#5B6675; margin-top:16px;">
                    Opens in a new tab so this page stays open.
                </div>
            </div>
            ''',
            unsafe_allow_html=True,
        )
    else:
        # Local: embed the iframe. CORS is disabled on the local chatbot, so it works.
        import streamlit.components.v1 as components
        components.html(
            f"""
            <iframe src="{url}"
                    width="100%"
                    height="720"
                    style="border:1px solid #E6E0D2; border-radius:8px; background:#FFFFFF;"
                    allow="microphone">
            </iframe>
            """,
            height=740,
        )

    """Open the multilingual chatbot in a new tab."""
    st.subheader("Chat with us")
    st.caption(
        "Ask about balance, loans, EMI, KYC, or anything else - in your own language."
    )

    url = _chatbot_url_for(customer_id)

    st.markdown(
        f'''
        <div style="
            background:#FFFFFF;
            border:1px solid #E6E0D2;
            border-radius:8px;
            padding:28px;
            text-align:center;
            margin-top:20px;
        ">
            <div style="font-size:17px; color:#16202E; margin-bottom:14px;">
                Our assistant is ready. Click below to start a conversation.
            </div>
            <a href="{url}" target="_blank" rel="noopener noreferrer" style="
                display:inline-block;
                padding:14px 32px;
                background:#2A7F6F;
                color:#FFFFFF !important;
                border-radius:6px;
                font-weight:600;
                font-size:16px;
                text-decoration:none;
                letter-spacing:0.02em;
            ">Open Chatbot</a>
            <div style="font-size:13px; color:#5B6675; margin-top:16px;">
                The chatbot opens in a new tab so you can keep this page open.
            </div>
        </div>
        ''',
        unsafe_allow_html=True,
    )

# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main():
    model_input = load_model_input()
    stress = load_stress()
    life_stage = load_life_stage()
    bundle = load_recommender()

    render_header()
    customer_id = render_sidebar()

    row = get_row(model_input, customer_id)
    if row is None:
        st.error(f"Customer {customer_id} not found.")
        return

    stress_row = get_row(stress, customer_id)
    life_row = get_row(life_stage, customer_id)

    st.markdown(viewing_label(customer_id), unsafe_allow_html=True)

    tabs = st.tabs(["My account", "My money", "For you", "Chat"])

    with tabs[0]:
        render_my_account(row, life_row, stress_row)
    with tabs[1]:
        render_my_money(customer_id, row, stress_row)
    with tabs[2]:
        render_for_you(bundle, row, stress_row)
    with tabs[3]:
        render_chat_tab(customer_id)


if __name__ == "__main__":
    main()
