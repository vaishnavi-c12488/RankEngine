
"""RankEngine: Streamlit product search dashboard."""
import html
import os
import re

import requests
import streamlit as st

API_URL = os.getenv("RANKENGINE_API_URL", "http://127.0.0.1:8000")

st.set_page_config(
    page_title="RankEngine | Product Search",
    page_icon="🔎",
    layout="wide",
)

st.title("🔎 RankEngine")
st.subheader("AI-powered product search")
st.caption("Dense vector retrieval + LightGBM LambdaMART reranking")

with st.sidebar:
    st.header("Search settings")
    locale = st.selectbox(
        "Product marketplace",
        options=["us", "jp", "es"],
        format_func=lambda value: {
            "us": "United States (US)",
            "jp": "Japan (JP)",
            "es": "Spain (ES)",
        }[value],
    )
    candidate_k = st.slider(
        "Candidates retrieved",
        min_value=10,
        max_value=100,
        value=50,
        step=10,
    )
    result_count = st.slider(
        "Products to display",
        min_value=1,
        max_value=20,
        value=10,
    )
    st.divider()
    st.caption("Retrieval: Qdrant + bi-encoder")
    st.caption("Reranking: LightGBM LambdaMART")

with st.form("product_search_form"):
    query = st.text_input(
        "What are you looking for?",
        placeholder="e.g. wireless headphones",
    )
    submitted = st.form_submit_button(
        "Search products",
        type="primary",
        use_container_width=True,
    )

def clean_description(value: str) -> str:
    """Remove HTML tags and normalize whitespace for display."""
    value = re.sub(r"<[^>]*>", " ", value or "")
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


if submitted:
    query = query.strip()

    if not query:
        st.warning("Enter a product search query.")
    elif result_count > candidate_k:
        st.warning("Displayed products cannot exceed retrieved candidates.")
    else:
        with st.spinner("Retrieving and ranking products..."):
            try:
                response = requests.post(
                    f"{API_URL}/search",
                    json={
                        "query": query,
                        "locale": locale,
                        "top_k": result_count,
                        "candidate_k": candidate_k,
                    },
                    timeout=120,
                )
                response.raise_for_status()
                data = response.json()

                st.success(
                    f"Retrieved {data['candidates_retrieved']} candidates "
                    f"for marketplace {data['locale'].upper()}."
                )

                results = data.get("results", [])
                if not results:
                    st.info("No products were returned for this search.")
                else:
                    st.markdown(f"### Search results for “{query}”")
                    st.caption(
                        "Ranked by LambdaMART after dense vector retrieval."
                    )

                    for item in results:
                        with st.container(border=True):
                            left, right = st.columns([5, 1])

                            with left:
                                st.markdown(
                                    f"**{item['rank']}. "
                                    f"{item.get('title') or 'Untitled product'}**"
                                )
                                brand = item.get("brand", "")
                                if brand:
                                    st.caption(f"Brand: {brand}")

                                description = clean_description(
                                    item.get("description", "")
                                )
                                if description:
                                    st.write(description[:450])

                                st.caption(
                                    f"Product ID: {item['product_id']} "
                                    f"| Locale: {item['locale'].upper()}"
                                )

                            with right:
                                st.metric(
                                    "Rerank score",
                                    f"{item['rerank_score']:.4f}",
                                )
                                st.caption(
                                    f"Retrieval: "
                                    f"{item['retrieval_score']:.4f}"
                                )

            except requests.exceptions.ConnectionError:
                st.error(
                    "Cannot connect to the RankEngine API. "
                    "Start the API in another terminal with: "
                    "python -m uvicorn api.main:app --reload"
                )
            except requests.exceptions.Timeout:
                st.error("The search timed out. Please try again.")
            except requests.exceptions.HTTPError as exc:
                detail = ""
                try:
                    detail = response.json().get("detail", "")
                except ValueError:
                    pass
                st.error(f"API error ({response.status_code}): {detail or exc}")
            except (requests.exceptions.RequestException, ValueError) as exc:
                st.error(f"Could not complete the search: {exc}")
