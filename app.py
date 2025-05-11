import streamlit as st
import pandas as pd
import requests
import datetime
from io import BytesIO
from dotenv import load_dotenv
import os

# Load environment variables (optional fallback if used locally)
load_dotenv()

# -----------------------------
# Page Config & Title
# -----------------------------
st.set_page_config(page_title="Google Ads Tracker", layout="wide")
st.title("📊 Google Ads Tracker")
st.caption("Track paid search ad rankings for your keywords using your own SerpApi key.")

# -----------------------------
# User Input: SerpApi Key
# -----------------------------
api_key = st.sidebar.text_input("🔑 Enter your SerpApi API Key", type="password")

# -----------------------------
# Keyword Input Section
# -----------------------------
st.header("🔍 Enter Keywords")

uploaded_file = st.file_uploader("Upload Excel file with keywords (column A)", type=["xlsx"])
manual_keywords = st.text_input("Or enter keywords separated by commas")

keyword_list = []

if uploaded_file:
    df_keywords = pd.read_excel(uploaded_file)
    keyword_list = df_keywords.iloc[:, 0].dropna().astype(str).tolist()
    st.success(f"✅ {len(keyword_list)} keywords loaded from uploaded file.")
elif manual_keywords:
    keyword_list = [kw.strip() for kw in manual_keywords.split(",") if kw.strip()]
    st.success(f"✅ {len(keyword_list)} keywords entered manually.")

# -----------------------------
# Helper to Call SerpApi
# -----------------------------
def fetch_ad_results(keyword, api_key):
    params = {
        "engine": "google",
        "q": keyword,
        "api_key": api_key,
        "gl": "us",
        "hl": "en",
        "google_domain": "google.com"
    }
    response = requests.get("https://serpapi.com/search", params=params)
    data = response.json()
    results = []

    for i, ad in enumerate(data.get("ads", []), 1):
        results.append({
            "Keyword": keyword,
            "Ad Position": i,
            "Title": ad.get("title"),
            "Displayed Link": ad.get("displayed_link"),
            "Domain": ad.get("displayed_link", "").split("/")[0],
            "Timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    return results

# -----------------------------
# Execute Button
# -----------------------------
if keyword_list and api_key:
    if st.button("🚀 Run Tracker"):
        all_results = []
        with st.spinner("Fetching ad rankings..."):
            for kw in keyword_list:
                try:
                    all_results.extend(fetch_ad_results(kw, api_key))
                except Exception as e:
                    st.error(f"Error fetching results for '{kw}': {e}")

        if all_results:
            result_df = pd.DataFrame(all_results)
            st.subheader("📋 Ad Rankings Table")
            st.dataframe(result_df, use_container_width=True)

            # Download button
            buffer = BytesIO()
            result_df.to_excel(buffer, index=False)
            st.download_button(
                label="💾 Download Results as Excel",
                data=buffer.getvalue(),
                file_name="ad_rankings.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # Chart: Top Domains
            st.subheader("🏆 Top Domains by Frequency")
            top_domains = result_df["Domain"].value_counts().head(10)
            st.bar_chart(top_domains)
        else:
            st.warning("No ads found for the entered keywords.")

elif not api_key:
    st.info("Please enter your SerpApi key in the sidebar to begin.")
elif not keyword_list:
    st.info("Please upload a keyword file or enter keywords manually.")
