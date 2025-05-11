import streamlit as st
import pandas as pd
import requests
import os
from dotenv import load_dotenv
from io import StringIO
from urllib.parse import urlparse
from datetime import datetime
from st_aggrid import AgGrid, GridOptionsBuilder
from streamlit_tags import st_tags

# Page setup
st.set_page_config(page_title="Google Ads Tracker", layout="wide")
st.title("🔍 Google Ads Tracker")
st.markdown("**Track the appearance and ranking of ads across Google search results. Upload or enter keywords, analyze top advertisers, view rank history, and download results.**")
st.markdown("---")

# Allow users to input their SERP API Key
SERP_API_KEY = st.text_input("Enter your free SERP API Key:", type="password")

# Persistent data store
HISTORY_FILE = "rank_history.csv"

@st.cache_data(show_spinner=False)
def fetch_ads_for_keyword(keyword, api_key, check_date):
    try:
        params = {"q": keyword, "hl": "en", "api_key": api_key}
        response = requests.get("https://serpapi.com/search", params=params)
        data = response.json()
        ads = data.get("ads", [])
        return [{
            "Keyword": keyword,
            "Position": ad.get("position", "N/A"),
            "Title": ad.get("title", ""),
            "Link": ad.get("link", ""),
            "Domain": urlparse(ad.get("link", "")).netloc,
            "Date Checked": check_date
        } for ad in ads]
    except Exception as e:
        return [{
            "Keyword": keyword,
            "Position": "Error",
            "Title": str(e),
            "Link": "",
            "Domain": "",
            "Date Checked": check_date
        }]

# ---- Keyword Input Section ----
with st.expander("📄 Input Panel: Upload or Enter Keywords", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        uploaded_file = st.file_uploader("📂 Upload Excel with 'keyword' column", type=["xlsx"])
    with col2:
        typed_keywords = st_tags(
            label="Enter keywords manually:",
            text="Press enter to add more",
            value=[],
            maxtags=50,
            key="1"
        )

keyword_list = []

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        if "keyword" in df.columns:
            keyword_list = df["keyword"].dropna().astype(str).tolist()
            st.success(f"✅ Loaded {len(keyword_list)} keywords from file.")
        else:
            st.error("Excel must have a 'keyword' column.")
    except Exception as e:
        st.error(f"Upload error: {e}")
elif typed_keywords:
    keyword_list = typed_keywords
    st.success(f"✅ {len(keyword_list)} keyword(s) entered.")

# ---- Results Processing ----
if keyword_list:
    if st.button("🚀 Run Ad Position Check"):
        results = []
        progress = st.progress(0, text="Fetching ad data...")
        today_str = datetime.today().strftime("%Y-%m-%d")

        for i, keyword in enumerate(keyword_list):
            ads = fetch_ads_for_keyword(keyword, SERP_API_KEY, today_str)
            results.extend(ads)
            progress.progress((i + 1) / len(keyword_list), text=f"{keyword} ({i+1}/{len(keyword_list)})")

        progress.empty()
        results_df = pd.DataFrame(results)

        # Save results to history file
        if os.path.exists(HISTORY_FILE):
            history_df = pd.read_csv(HISTORY_FILE)
            history_df = pd.concat([history_df, results_df], ignore_index=True)
        else:
            history_df = results_df
        history_df.to_csv(HISTORY_FILE, index=False)

        # Display with AgGrid
        st.subheader("📊 Ad Results")
        gb = GridOptionsBuilder.from_dataframe(results_df)
        gb.configure_pagination(paginationAutoPageSize=True)
        gb.configure_default_column(editable=False, groupable=True)
        gb.configure_side_bar()
        gridOptions = gb.build()
        AgGrid(results_df, gridOptions=gridOptions, height=400)

        # Download
        st.download_button("⬇️ Download CSV", data=results_df.to_csv(index=False), file_name=f"ads_results_{today_str}.csv", mime="text/csv")

        # Bar Chart
        st.subheader("🏆 Top Domains by Frequency")
        domain_counts = results_df["Domain"].value_counts().head(10)
        st.bar_chart(domain_counts)

        # Line Chart
        st.subheader("📈 Historical Ranking (Line Chart)")
        history_df["Date Checked"] = pd.to_datetime(history_df["Date Checked"])
        history_df = history_df[history_df["Position"].apply(lambda x: str(x).isdigit())]
        history_df["Position"] = history_df["Position"].astype(int)

        selected_keyword = st.selectbox("Select a keyword to view rank history:", history_df["Keyword"].unique())
        keyword_data = history_df[history_df["Keyword"] == selected_keyword].sort_values("Date Checked")
        chart_data = keyword_data.pivot_table(index="Date Checked", columns="Domain", values="Position", aggfunc="min")
        st.line_chart(chart_data)

else:
    st.info("👋 Upload or enter keywords to start.")
