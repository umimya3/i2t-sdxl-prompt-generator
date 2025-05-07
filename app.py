import streamlit as st

#st.set_option('browser.gatherUsageStats', False) # 念のため
st.set_page_config(page_title="Test App")

st.title("Test App")
st.write("Hello from Streamlit on Hugging Face Spaces!")

# APIキーを読み込もうとする部分だけテスト
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    if api_key:
        st.success("GOOGLE_API_KEY loaded successfully from secrets!")
        # st.write(f"API Key: {api_key[:5]}...") # デバッグ用にキーの一部を表示 (注意して扱う)
    else:
        st.error("GOOGLE_API_KEY is empty in secrets.")
except KeyError:
    st.error("GOOGLE_API_KEY not found in st.secrets.")
except Exception as e:
    st.error(f"Error loading API key: {e}")

# Geminiライブラリの初期化だけテスト
try:
    import google.generativeai as genai
    if "api_key" in locals() and api_key: # api_keyが取得できていれば
         genai.configure(api_key=api_key)
         st.success("Gemini configured successfully!")
    else:
        st.warning("Skipping Gemini configuration as API key was not loaded.")
except Exception as e:
    st.error(f"Error configuring Gemini: {e}")