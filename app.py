import streamlit as st
import google.generativeai as genai

# --- ページ設定とデザイン ---
st.set_page_config(page_title="ゼロから始める！キャリアの棚卸しアシスタント", layout="wide")

st.markdown("""
<style>
h1, h2, h3 { color: #2C3E50 !important; }
label p, [data-testid="stWidgetLabel"] p { font-size: 16px !important; color: #34495E !important; font-weight: bold !important; }
.stButton button { background-color: #3498DB !important; color: white !important; font-size: 18px !important; font-weight: bold !important; padding: 10px 30px !important; border-radius: 8px !important; border: none !important; width: 100%; }
.stButton button:hover { background-color: #2980B9 !important; }
.step-box { background-color: #EBF5FB; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

st.title("🌱 ゼロから始める！キャリアの棚卸しアシスタント")
st.markdown("""
<div class="step-box">
    <b>自己PR作成ステップ1：素材を集めよう</b><br>
    ここでは，自己PRの「素材」となるあなたの経験を整理します。<br>
    ジョブカード（様式2）の内容をそのまま貼り付けるだけでOKです！AIと一緒に，あなたの中に眠っている強みを発掘しましょう。
</div>
""", unsafe_allow_html=True)

# --- セッション状態（アプリの記憶）の初期化 ---
if "step" not in st.session_state:
    st.session_state.step = 1
if "ai_first_response" not in st.session_state:
    st.session_state.ai_first_response = ""
if "final_sheet" not in st.session_state:
    st.session_state.final_sheet = ""
if "user_initial_input" not in st.session_state:
    st.session_state.user_initial_input = ""

# --- サイドバー：APIキー設定 ---
st.sidebar.header("🔑 セキュリティ設定")
api_key = st.sidebar.text_input("Gemini APIキー", type="password")

# ==========================================
# 【ステップ1】経歴の入力画面
# ==========================================
if st.session_state.step == 1:
    st.subheader("1. これまでの経験を入力してください")
    st.write("※最大3つまで入力できます。1つだけでも大丈夫です。")
    
    # 複数入力用のレイアウト（タブ機能でスッキリ見せます）
    tab1, tab2, tab3 = st.tabs(["🏢 1社目（または1つ目の業務）", "🏢 2社目", "🏢 3社目"])
    
    with tab1:
        period_1 = st.text_input("在籍期間（例：約3年，半年など）", key="p1")
        job_card_1 = st.text_area("ジョブカードの「職務内容」「学んだこと・知識技術等」を貼り付けてください", height=150, key="j1")
        hardship_1 = st.text_area("一番苦労したこと・工夫したこと（任意）", placeholder="失敗から立て直した経験なども立派な素材になります！", key="h1")
    with tab2:
        period_2 = st.text_input("在籍期間（例：約2年など）", key="p2")
        job_card_2 = st.text_area("ジョブカードの内容", height=150, key="j2")
        hardship_2 = st.text_area("一番苦労したこと・工夫したこと（任意）", key="h2")
    with tab3:
        period_3 = st.text_input("在籍期間", key="p3")
        job_card_3 = st.text_area("ジョブカードの内容", height=150, key="j3")
        hardship_3 = st.text_area("一番苦労したこと・工夫したこと（任意）", key="h3")

    st.markdown("---")
    
    if st.button("AIに強みを発掘してもらう ✨"):
        if not api_key:
            st.error("⚠️ 左側のメニューにAPIキーを入力してください。")
        elif not job_card_1:
            st.warning("⚠️ 最低でも「1社目」のジョブカード内容は入力してください。")
        else:
            # 入力内容をまとめる
            combined_input = f"""
            【1社目】期間: {period_1} / 職務内容等: {job_card_1} / 苦労・工夫: {hardship_1}
            【2社目】期間: {period_2} / 職務内容等: {job_card_2} / 苦労・工夫: {hardship_2}
            【3社目】期間: {period_3} / 職務内容等: {job_card_3} / 苦労・工夫: {hardship_3}
            """
            st.session_state.user_initial_input = combined_input

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            prompt1 = f"""
            あなたは温かく寄り添うキャリアコンサルタントです。求職者の経歴情報から、自己PRの素材を発掘してください。
            【求職者の入力情報】
            {combined_input}

            【出力要件（以下の3点を含めて温かいトーンで出力）】
            1. 事実の整理：入力内容を「役割」「行動」「結果」の3要素に分かりやすく整理してください。
            2. 強みの発見と称賛：この経験に隠れている「ポータブルスキル（強み・技術）」を3つ提示し、なぜそう言えるのかを褒めながら解説してください。
            3. 深掘りの質問：自己PRの素材としてさらに磨きをかけるため、具体的な「行動」や「工夫」について、求職者が答えやすい深掘り質問を2〜3個だけ提示してください。
            """
            
            with st.spinner('AIがあなたの経験を分析し、強みを探しています...'):
                try:
                    response = model.generate_content(prompt1)
                    st.session_state.ai_first_response = response.text
                    st.session_state.step = 2 # 次のステップへ進む
                    st.rerun() # 画面を更新
                except Exception as e:
                    st.error(f"エラーが発生しました。詳細: {e}")


# ==========================================
# 【ステップ2】AIとの対話＆最終整理画面
# ==========================================
elif st.session_state.step == 2:
    st.success("分析が完了しました！以下のAIからのメッセージを確認し、質問に答えてみましょう。")
    st.markdown("---")
    st.markdown(st.session_state.ai_first_response)
    st.markdown("---")
    
    st.subheader("💬 AIからの質問に答えてみましょう")
    st.write("※箇条書きでも、思いつくままの短い言葉でも大丈夫です。難しければ「特になし」でも構いません。")
    
    user_answer = st.text_area("ここへ回答を入力してください", height=150)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("⬅️ 最初からやり直す"):
            st.session_state.step = 1
            st.rerun()
    with col2:
        if st.button("最終整理シートを作成する 📝"):
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            prompt2 = f"""
            あなたはキャリアコンサルタントです。先ほどの分析結果と、求職者の追加回答を統合し、「キャリアの棚卸し完了シート」を作成してください。
            
            【初期入力情報】{st.session_state.user_initial_input}
            【AIの一次分析】{st.session_state.ai_first_response}
            【求職者の追加回答】{user_answer}
            
            【出力要件（このシートがそのまま「資料1」になります）】
            以下の項目を見出しとして、分かりやすく整理されたレポート形式で出力してください。
            ・これまでの経験のサマリー（役割・行動・結果）
            ・発掘された3つの強み・ポータブルスキル
            ・追加回答から見えた、あなたならではの「具体的なエピソード（STAR法の種）」
            ・キャリアコンサルタントからの応援メッセージ
            """
            
            with st.spinner('最終整理シートを作成しています...'):
                try:
                    response = model.generate_content(prompt2)
                    st.session_state.final_sheet = response.text
                    st.session_state.step = 3 # 最後のステップへ進む
                    st.rerun()
                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")


# ==========================================
# 【ステップ3】完成・ダウンロード画面
# ==========================================
elif st.session_state.step == 3:
    st.success("🎉 キャリアの棚卸しシート（資料1）が完成しました！")
    st.markdown("---")
    st.markdown(st.session_state.final_sheet)
    st.markdown("---")
    
    st.warning("⚠️ 次の「ステップ2：キャリア・アンカー診断」でこの資料を使用します。必ず下のボタンからダウンロードして保存してください。")
    
    st.download_button(
        label="📝 この棚卸しシート（資料1）をダウンロードする",
        data=st.session_state.final_sheet,
        file_name="career_inventory_sheet1.txt",
        mime="text/plain"
    )
    
    st.write("")
    if st.button("⬅️ 最初からやり直す（データはリセットされます）"):
        st.session_state.step = 1
        st.session_state.ai_first_response = ""
        st.session_state.final_sheet = ""
        st.session_state.user_initial_input = ""
        st.rerun()

# --- ポータルサイトへ戻るボタン ---
st.markdown("---")
st.link_button("🏠 C.HARIGOMA キャリア支援ポータルへ戻る", "https://harigoma-career.streamlit.app/")
