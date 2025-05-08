import streamlit as st
from PIL import Image
import google.generativeai as genai
import os

# st.copy_buttonが利用可能かどうかのフラグを設定
CAN_USE_COPY_BUTTON = hasattr(st, "copy_button")

# --- Streamlit ページ設定 ---
st.set_page_config(page_title="Image to Text プロンプトジェネレーター", layout="wide")

# --- APIキー設定 ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    LOCAL_DEV_API_KEY = "YOUR_LOCAL_API_KEY_HERE_IF_NEEDED"
    if LOCAL_DEV_API_KEY != "YOUR_LOCAL_API_KEY_HERE_IF_NEEDED":
        st.warning("Render環境変数のGOOGLE_API_KEYが見つかりません。ローカルのAPIキーを使用します（非推奨）。", icon="⚠️")
        GOOGLE_API_KEY = LOCAL_DEV_API_KEY
    else:
        st.error("Google APIキーがRenderの環境変数に設定されていません。Renderのサービス設定で 'GOOGLE_API_KEY' を設定してください。")
        st.stop()

try:
    genai.configure(api_key=GOOGLE_API_KEY)
except Exception as e:
    st.error(f"Google APIキーの設定またはGeminiライブラリの初期化に失敗しました: {e}")
    st.stop()

# --- Gemini API ラッパー関数 (変更なし) ---
def get_image_description(image_data, prompt_text):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content([prompt_text, image_data])
        return response.text
    except Exception as e:
        st.error(f"画像解析中にエラーが発生しました: {e}", icon="🔥")
        return None

def generate_sdxl_prompts(description_text, prompt_text_template):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        full_prompt = f"{prompt_text_template}\n\n説明文:\n{description_text}"
        response = model.generate_content(full_prompt)
        text_response = response.text
        prompts = {"positive": "生成失敗。応答確認を。", "negative": "生成失敗。応答確認を。"}
        positive_keyword_jp = "ポジティブプロンプト:"
        negative_keyword_jp = "ネガティブプロンプト:"
        positive_keyword_en = "Positive Prompt:"
        negative_keyword_en = "Negative Prompt:"
        positive_prompt = ""
        negative_prompt = ""
        if positive_keyword_jp in text_response:
            parts = text_response.split(positive_keyword_jp, 1)
            if len(parts) > 1:
                if negative_keyword_jp in parts[1]:
                    sub_parts = parts[1].split(negative_keyword_jp, 1)
                    positive_prompt = sub_parts[0].strip()
                    if len(sub_parts) > 1:
                        negative_prompt = sub_parts[1].strip()
                else:
                    positive_prompt = parts[1].strip()
        elif positive_keyword_en in text_response:
            parts = text_response.split(positive_keyword_en, 1)
            if len(parts) > 1:
                if negative_keyword_en in parts[1]:
                    sub_parts = parts[1].split(negative_keyword_en, 1)
                    positive_prompt = sub_parts[0].strip()
                    if len(sub_parts) > 1:
                        negative_prompt = sub_parts[1].strip()
                else:
                    positive_prompt = parts[1].strip()
        if positive_prompt: prompts["positive"] = positive_prompt
        if negative_prompt: prompts["negative"] = negative_prompt
        elif not positive_prompt and not negative_prompt and text_response:
            st.warning("プロンプト形式が期待通りではありません。応答全文をポジティブとして扱います。", icon="⚠️")
            prompts["positive"] = text_response
        return prompts
    except Exception as e:
        st.error(f"プロンプト生成中にエラー: {e}", icon="🔥")
        return {"positive": "エラー発生", "negative": "エラー発生"}

# --- Streamlit UI メイン部分 ---
st.title("🖼️ Image to Text プロンプトジェネレーター (Gemini API)")
st.caption("画像をアップロードすると、Geminiが画像を解析し、SDXL用のプロンプトを生成します。")

# --- サイドバー: プロンプト設定 (変更なし) ---
st.sidebar.header("⚙️ プロンプト詳細設定")
image_analysis_prompt_default = """この画像を非常に詳細に、客観的に説明してください。
以下の要素を含めて、具体的に記述してください。
- **構図:** (例: クローズアップ、ロングショット、三人称視点、俯瞰など)
- **被写体:** (例: 若い女性、猫、未来的な都市、古い本など。特徴も詳細に)
- **背景:** (例: ぼやけた森、賑やかな市場、宇宙空間など)
- **色調:** (例: 暖色系、寒色系、モノクロ、セピア調、鮮やか、パステルカラーなど)
- **光の当たり方:** (例: 日中の強い光、夕暮れの柔らかい光、逆光、スタジオ照明など)
- **画風/スタイル:** (例: 写実的、アニメ風、水彩画風、油絵風、ピクセルアート、サイバーパンクなど)
- **感情/雰囲気:** (例: 喜び、悲しみ、神秘的、穏やか、緊張感、ノスタルジックなど)
"""
image_analysis_prompt = st.sidebar.text_area(
    "1. 画像解析用プロンプト (Gemini Visionへ):",
    image_analysis_prompt_default,
    height=300,
    key="iap_sidebar"
)
sdxl_generation_prompt_template_default = """以下の説明文に基づいて、Stable Diffusion XL (SDXL) で高品質な画像を生成するための、非常に詳細で効果的なプロンプトを作成してください。\n\n最終的な出力は、以下の形式で「ポジティブプロンプト:」と「ネガティブプロンプト:」の行を必ず含めてください。\n\nポジティブプロンプト: [ここに生成されたポジティブプロンプト]\nネガティブプロンプト: [ここに生成されたネガティブプロンプト]\n\n考慮事項:\n- ポジティブプロンプトには、画質を高めるキーワード (例: masterpiece, best quality, ultra-detailed, photorealistic, 8k, high resolution, sharp focus, intricate details など) を適切に含めてください。\n- 説明文の主要な要素（被写体、背景、スタイル、雰囲気など）を網羅し、SDXLが理解しやすいように具体的に記述してください。\n- 必要に応じて、特定のアーティストのスタイル (例: by Greg Rutkowski, style of Makoto Shinkai など) やカメラ設定 (例: wide-angle lens, shallow depth of field など) も含めることができます。\n- ネガティブプロンプトには、低品質な結果や望ましくない要素を避けるためのキーワード (例: worst quality, low quality, normal quality, blurry, jpeg artifacts, watermark, signature, text, deformed, mutated, ugly, disfigured, extra limbs, missing limbs, bad anatomy など) を含めてください。\n- 説明文の内容を忠実に再現しつつ、芸術的で魅力的な画像を生成できるようなプロンプトを目指してください。"""
sdxl_generation_prompt_template = st.sidebar.text_area(
    "2. SDXLプロンプト生成用指示 (Gemini Textへ):",
    sdxl_generation_prompt_template_default,
    height=350,
    key="sgpt_sidebar"
)

# --- UI改善のための定数とセッションステート初期化 (変更なし) ---
DESCRIPTION_PLACEHOLDER = "画像をアップロードし、「生成する」ボタンを押すと、ここに画像の説明が表示されます。"
POSITIVE_PLACEHOLDER = "画像をアップロードし、「生成する」ボタンを押すと、ここにポジティブプロンプトが表示されます。"
NEGATIVE_PLACEHOLDER = "画像をアップロードし、「生成する」ボタンを押すと、ここにネガティブプロンプトが表示されます。"
if "description" not in st.session_state: st.session_state.description = DESCRIPTION_PLACEHOLDER
if "positive_prompt" not in st.session_state: st.session_state.positive_prompt = POSITIVE_PLACEHOLDER
if "negative_prompt" not in st.session_state: st.session_state.negative_prompt = NEGATIVE_PLACEHOLDER
if "image_processed_once" not in st.session_state: st.session_state.image_processed_once = False

# --- メインコンテンツ レイアウト ---
col1, col2 = st.columns([2, 3])

with col1:
    uploaded_file = st.file_uploader(
        "ここに画像をドラッグ＆ドロップ または ブラウズ",
        type=["jpg", "jpeg", "png"],
        key="main_uploader"
    )

    # ボタンを画像の上に配置
    if uploaded_file is not None:
        if st.button("✨ 解析してプロンプトを生成する", type="primary", use_container_width=True, key="generate_button_main"):
            st.session_state.image_processed_once = True
            try: # 画像処理とAPI呼び出しをtry-exceptで囲む
                image_for_processing = Image.open(uploaded_file) # ボタンが押された後に画像を開く
                with st.spinner("画像を解析中... (Gemini Vision)"):
                    description_raw = get_image_description(image_for_processing, image_analysis_prompt)

                if description_raw:
                    cleaned_description = description_raw.replace(' сопротивленияnew', '')
                    st.session_state.description = cleaned_description
                    with st.spinner("SDXLプロンプトを生成中... (Gemini)"):
                        sdxl_prompts = generate_sdxl_prompts(cleaned_description, sdxl_generation_prompt_template)

                    if sdxl_prompts:
                        st.session_state.positive_prompt = sdxl_prompts.get("positive", "エラーまたは未生成")
                        st.session_state.negative_prompt = sdxl_prompts.get("negative", "エラーまたは未生成")
                        st.toast("プロンプトの生成が完了しました！ 🎉", icon="✅")
                    else:
                        st.session_state.positive_prompt = "プロンプト生成に失敗。"
                        st.session_state.negative_prompt = "プロンプト生成に失敗。"
                        st.error("SDXLプロンプトの生成に失敗。", icon="🔥")
                else:
                    st.session_state.description = "画像の説明を取得できませんでした。"
                    st.session_state.positive_prompt = POSITIVE_PLACEHOLDER
                    st.session_state.negative_prompt = NEGATIVE_PLACEHOLDER
                    st.error("画像の説明を取得できませんでした。API等を確認してください。", icon="🔥")
            except Exception as e: # 画像ファイル関連のエラーもここでキャッチ
                st.error(f"画像の処理またはAPI呼び出し中に予期せぬエラー: {e}", icon="🔥")
                st.session_state.image_processed_once = True
                st.session_state.description = f"エラー発生: {e}"
                st.session_state.positive_prompt = "エラー発生"
                st.session_state.negative_prompt = "エラー発生"

        # 画像表示はボタンの下
        image = Image.open(uploaded_file)
        st.image(image, caption="アップロードされた画像", width=300)

    else: # uploaded_file is None
        if not st.session_state.image_processed_once:
            st.markdown(
                "<div style='height: 300px; display: flex; align-items: center; justify-content: center; border: 2px dashed #ccc; border-radius: 7px; background-color: #f9f9f9;'>"
                "<span style='color: #777; text-align: center;'>画像をアップロードすると<br>ここにプレビューが表示されます</span>"
                "</div>",
                unsafe_allow_html=True
            )

with col2:
    # --- 生成されたSDXLプロンプト ---
    st.subheader("📝 生成されたSDXLプロンプト")

    # ポジティブプロンプト
    st.markdown("**ポジティブプロンプト 👍**")
    if st.session_state.positive_prompt not in [POSITIVE_PLACEHOLDER, "エラーまたは未生成", "プロンプト生成に失敗。", "エラー発生"] and "失敗" not in st.session_state.positive_prompt:
        if CAN_USE_COPY_BUTTON:
            st.copy_button("コピー", st.session_state.positive_prompt, key="copy_pos_btn_main_above")
        else:
            st.code(st.session_state.positive_prompt, language=None)
            st.caption("テキストをコピーできます (右上のアイコン)。")
    st.text_area(
        "ポジティブプロンプト編集エリア", # ラベル変更
        value=st.session_state.positive_prompt,
        height=150, # 少し高さを調整
        key="positive_prompt_edit_area_main",
        label_visibility="collapsed", # ラベルを非表示 (st.markdownで表示しているため)
        help="生成されたポジティブプロンプトです。ここで編集も可能です。"
    )

    st.markdown("---")

    # ネガティブプロンプト
    st.markdown("**ネガティブプロンプト 👎**")
    if st.session_state.negative_prompt not in [NEGATIVE_PLACEHOLDER, "エラーまたは未生成", "プロンプト生成に失敗。", "エラー発生"] and "失敗" not in st.session_state.negative_prompt:
        if CAN_USE_COPY_BUTTON:
            st.copy_button("コピー", st.session_state.negative_prompt, key="copy_neg_btn_main_above")
        else:
            st.code(st.session_state.negative_prompt, language=None)
            st.caption("テキストをコピーできます (右上のアイコン)。")
    st.text_area(
        "ネガティブプロンプト編集エリア", # ラベル変更
        value=st.session_state.negative_prompt,
        height=100,
        key="negative_prompt_edit_area_main",
        label_visibility="collapsed", # ラベルを非表示
        help="生成されたネガティブプロンプトです。ここで編集も可能です。"
    )

    st.markdown("---")

    # --- 画像の詳細説明 ---
    st.subheader("🖼️ 画像の詳細説明 (生成元)")
    if st.session_state.description not in [DESCRIPTION_PLACEHOLDER, "画像の説明を取得できませんでした。"] and "エラー発生" not in st.session_state.description:
        if CAN_USE_COPY_BUTTON:
            st.copy_button("コピー", st.session_state.description, key="copy_desc_btn_main_above")
        else:
            st.code(st.session_state.description, language=None)
            st.caption("テキストをコピーできます (右上のアイコン)。")
    st.text_area(
        "画像の説明表示エリア", # ラベル変更
        value=st.session_state.description,
        height=120, # 高さを調整
        key="desc_display_area_main",
        disabled=True,
        label_visibility="collapsed", # ラベルを非表示
        help="Geminiによって生成された画像の説明です。"
    )


st.markdown("---")
st.markdown("© 2025 Matsui Naoki/sdxl_i2t_project  (Powered by Gemini & Streamlit)")