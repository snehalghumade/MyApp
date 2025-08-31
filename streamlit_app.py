# streamlit_app.py
# A simple, mobile-friendly web app for teachers to enter subjects & marks
# and instantly get a copyable/downloadable bar chart.
#
# How to run locally:
#   1) pip install streamlit plotly kaleido pandas
#   2) streamlit run streamlit_app.py
#
# Tip: In the chart's toolbar (top-right), use the camera icon to
#      "Download plot as PNG". There's also a dedicated download button below.

import io
from typing import List
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Marks → Bar Chart",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ---------- Helpers ----------

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Standardize column names
    rename_map = {}
    for c in df.columns:
        cl = str(c).strip().lower()
        if cl in {"subject", "subjects", "name", "topic"}:
            rename_map[c] = "Subject"
        elif cl in {"marks", "score", "scores", "value"}:
            rename_map[c] = "Marks"
    df = df.rename(columns=rename_map)

    # Ensure required columns exist
    if "Subject" not in df.columns or "Marks" not in df.columns:
        # Try to infer from first two columns
        if len(df.columns) >= 2:
            df = df.rename(columns={df.columns[0]: "Subject", df.columns[1]: "Marks"})
        else:
            df["Subject"] = df.get("Subject", [])
            df["Marks"] = df.get("Marks", [])

    # Strip subject strings
    df["Subject"] = df["Subject"].astype(str).str.strip()

    # Coerce marks to numeric
    df["Marks"] = pd.to_numeric(df["Marks"], errors="coerce")

    # Drop empty/NaN rows
    df = df.dropna(subset=["Subject", "Marks"])  # type: ignore[arg-type]
    df = df[df["Subject"] != ""]

    # Deduplicate subjects by keeping the last occurrence
    df = df.drop_duplicates(subset=["Subject"], keep="last")

    return df[["Subject", "Marks"]]


def example_df(n: int = 5) -> pd.DataFrame:
    return pd.DataFrame({
        "Subject": [f"Subject {i+1}" for i in range(n)],
        "Marks": [80, 72, 90, 65, 88][:n],
    })


# ---------- UI ----------

st.title("📊 Marks → Bar Chart")
st.caption("Enter subjects and marks, then download a clean bar chart. Works on mobile & desktop.")

with st.sidebar:
    st.subheader("Data input")
    input_mode = st.radio(
        "Choose how you'll provide the data:",
        ["Edit a table", "Paste list/CSV", "Upload CSV"],
        index=0,
    )

    st.markdown("---")
    st.subheader("Chart options")
    orientation = st.selectbox("Orientation", ["Vertical", "Horizontal"], index=0)
    show_values = st.checkbox("Show values on bars", value=True)
    sort_bars = st.checkbox("Sort by marks (descending)", value=True)
    x_title = st.text_input("X-axis title (optional)", value="")
    y_title = st.text_input("Y-axis title (optional)", value="Marks")

# Collect data based on mode
if input_mode == "Edit a table":
    st.write("### 1) Edit the table")
    st.write("Type subjects and marks directly. Add or remove rows as needed.")

    init_rows = st.number_input("Start with this many rows", min_value=1, max_value=30, value=5)
    df_init = example_df(init_rows)

    try:
        df_edit = st.data_editor(
            df_init,
            num_rows="dynamic",  # available in newer Streamlit versions
            use_container_width=True,
            hide_index=True,
        )
    except TypeError:
        df_edit = st.data_editor(
            df_init,
            use_container_width=True,
            hide_index=True,
        )

    df = clean_dataframe(df_edit)

elif input_mode == "Paste list/CSV":
    st.write("### 1) Paste your data")
    st.write("Paste lines like \n`Math, 78`\n`Science, 85`\n`English, 92`")

    pasted = st.text_area("Paste here", height=180, placeholder="Subject, Marks (one per line)")

    if pasted.strip():
        # Try to parse as CSV with flexible separator (comma/semicolon/tab)
        # Normalize separators to comma
        lines: List[str] = [ln for ln in pasted.splitlines() if ln.strip()]
        norm = "\n".join([ln.replace("\t", ",").replace(";", ",") for ln in lines])
        try:
            temp = pd.read_csv(io.StringIO(norm), header=None, names=["Subject", "Marks"])
        except Exception:
            # Fallback: split by first comma
            rows = []
            for ln in lines:
                if "," in ln:
                    s, m = ln.split(",", 1)
                else:
                    parts = ln.split()
                    s, m = " ".join(parts[:-1]), parts[-1] if len(parts) > 1 else (ln, "")
                rows.append({"Subject": s.strip(), "Marks": m.strip()})
            temp = pd.DataFrame(rows)
        df = clean_dataframe(temp)
    else:
        df = example_df(5)

else:  # Upload CSV
    st.write("### 1) Upload a CSV file")
    st.write("CSV must have two columns: Subject, Marks (headers optional).")
    up = st.file_uploader("Choose a CSV file", type=["csv"])
    if up is not None:
        try:
            temp = pd.read_csv(up)
        except Exception:
            up.seek(0)
            temp = pd.read_csv(up, header=None)
        df = clean_dataframe(temp)
    else:
        df = example_df(5)

# Show the cleaned data back to the user
st.write("### 2) Preview & tidy")
st.dataframe(df, use_container_width=True, hide_index=True)

# Safety checks
if df.empty:
    st.warning("No valid rows found. Please enter at least one subject and a numeric mark.")
    st.stop()

# Optional sorting
if sort_bars:
    df = df.sort_values("Marks", ascending=False)

# ---------- Build the chart ----------

st.write("### 3) Chart")

if orientation == "Vertical":
    fig = px.bar(df, x="Subject", y="Marks", text="Marks" if show_values else None)
    if show_values:
        fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(xaxis_title=x_title or "Subject", yaxis_title=y_title or "Marks")
else:
    fig = px.bar(df, x="Marks", y="Subject", orientation="h", text="Marks" if show_values else None)
    if show_values:
        fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(xaxis_title=y_title or "Marks", yaxis_title=x_title or "Subject")

fig.update_layout(margin=dict(l=20, r=20, t=20, b=20))

# Show interactive chart with Plotly's built-in download button
st.plotly_chart(
    fig,
    use_container_width=True,
    config={"displaylogo": False, "toImageButtonOptions": {"format": "png", "scale": 2}},
)

# Offer a dedicated PNG download too (via Kaleido)
try:
    png_bytes = fig.to_image(format="png", scale=3, engine="kaleido")
    st.download_button(
        label="⬇️ Download chart as PNG",
        data=png_bytes,
        file_name="marks_barchart.png",
        mime="image/png",
        use_container_width=True,
    )
except Exception:
    st.info("Use the camera icon in the chart toolbar to download as PNG.")

# Also let them export the data
csv_bytes = df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="⬇️ Download data (CSV)",
    data=csv_bytes,
    file_name="marks_data.csv",
    mime="text/csv",
    use_container_width=True,
)

st.caption("Pro tip: On mobile, turn the phone sideways for a wider chart. ✨")
