import streamlit as st
import google.generativeai as genai
import json

# --- ページ設定 ---
st.set_page_config(page_title="本音でみつかる！仕事のリアル疑似体験アシスタント", layout="wide")

# --- カスタムCSS ---
st.markdown("""
<style>
h1, h2, h3 { color: #2C3E50 !important; }
.step-header { background-color: #F4F6F7; padding: 15px; border-radius: 8px; border-left: 5px solid #3498DB; margin-bottom: 20px; }
.ai-box { background-color: #EBF5FB; padding: 25px; border-radius: 12px; border-left: 5px solid #2980B9; margin-bottom: 25px; line-height: 1.8; }
.story-box { background-color: #FEF9E7; padding: 25px; border-radius: 12px; border: 2px dashed #F1C40F; margin-bottom: 25px; font-size: 16px; line-height: 1.8; }
.card-box { background-color: #FFFFFF; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 15px; border: 1px solid #E5E7E9; }
[data-testid="stFormSubmitButton"] button { background-color: #E67E22 !important; color: white !important; font-size: 18px !important; font-weight: bold !important; width: 100% !important; border-radius: 8px !important; padding: 10px !important; }
</style>
""", unsafe_allow_html=True)

st.title("🧩 自己理解から仕事理解へ：わたしに合う働き方発見アシスタント")
st.write("「事務職がいい」「あの仕事は嫌だ」といった職種名の先入観を一度外して、あなたが本当に安心できる働き方（環境）をAIと一緒に見つけましょう。")
st.markdown("---")

# --- APIキー設定 ---
st.sidebar.header("🔑 セキュリティ設定")
api_key = st.sidebar.text_input("Gemini APIキー", type="password")

# --- セッション状態（記憶）の初期化 ---
if 'step' not in st.session_state:
    st.session_state.step = 0
if 'profile' not in st.session_state:
    st.session_state.profile = {}
if 'situations' not in st.session_state:
    st.session_state.situations = {"A": [], "B": [], "C": []}
if 'evaluations' not in st.session_state:
    st.session_state.evaluations = {}
if 'absolute_ngs' not in st.session_state:
    st.session_state.absolute_ngs = []
if 'ai_proposal' not in st.session_state:
    st.session_state.ai_proposal = ""
if 'proposed_job_title' not in st.session_state:
    st.session_state.proposed_job_title = ""
if 'ai_reveal' not in st.session_state:
    st.session_state.ai_reveal = ""

# ==================================================
# 【初期画面】プロファイリング（前提条件の取得）
# ==================================================
if st.session_state.step == 0:
    st.markdown("<div class='step-header'><h3>まずは、あなたの現在の状況を教えてください</h3></div>", unsafe_allow_html=True)
    st.write("適切なアドバイスのトーンを決めるための質問です。直感で選んでください。")
    
    with st.form("profile_form"):
        age = st.radio("年代をお教えください", ["20代", "30代", "40代", "50代以上"], horizontal=True)
        status = st.radio("現在の転職への温度感は？", ["限界が近く、今すぐ環境を変えたい", "じっくり次のステップを考えたい", "良いところがあれば検討したい"], horizontal=True)
        
        # 修正箇所：常に自由入力欄を表示させておくことで、文字消えバグを防ぐ
        trigger_choice = st.selectbox("今回の就職活動で「一番変えたいこと（引き金）」は何ですか？", 
                               ["職場の人間関係・対人ストレスを減らしたい", 
                                "仕事内容が自分に合わない（環境を変えたい）", 
                                "体力的な負担を減らしたい", 
                                "勤務時間や休日などの条件を改善したい",
                                "その他（下の欄に自由に入力する）"])
        
        trigger_free = st.text_input("👆上の質問で「その他」を選んだ方は、一番変えたいことを自由に入力してください", placeholder="例：給与を上げたい、正社員になりたい など")

        experiences = st.multiselect("これまでに経験したことのある職種（大まかな分類・複数選択可）", 
                                     ["接客・販売・サービス職", 
                                      "飲食・フード・調理職",
                                      "営業・企画職", 
                                      "一般事務・受付・アシスタント職", 
                                      "総務・経理・人事などのバックオフィス職",
                                      "製造・工場・ライン作業", 
                                      "物流・倉庫・ドライバー",
                                      "清掃・警備・施設管理",
                                      "医療・看護・福祉・介護職", 
                                      "IT・エンジニア・Web・クリエイティブ職",
                                      "その他"])
        
        free_experience = st.text_input("上記にない職種や、より具体的な職種名があれば自由に入力してください", 
                                        placeholder="例：職業訓練の講師、アパレルの店長、コールセンター、など")
        
        submit_profile = st.form_submit_button("次へ進む（業務シチュエーションの準備） 👉")
        
    if submit_profile:
        # trigger（引き金）の決定
        if trigger_choice == "その他（下の欄に自由に入力する）":
            trigger = trigger_free
        else:
            trigger = trigger_choice
            
        # 経験職種の結合処理
        exp_list = experiences.copy()
        if free_experience:
            exp_list.append(free_experience)
        combined_experiences = "、".join(exp_list)

        # エラーチェック
        if not api_key:
            st.error("⚠️ 左側のメニューにAPIキーを入力してください。")
        elif not combined_experiences:
            st.warning("⚠️ 経験職種を選択するか、自由入力欄に入力してください。")
        elif trigger_choice == "その他（下の欄に自由に入力する）" and not trigger:
            st.warning("⚠️ 「その他」を選んだ方は、すぐ下の自由入力欄に一番変えたいことを入力してください。")
        else:
            st.session_state.profile = {"age": age, "status": status, "trigger": trigger, "experiences": combined_experiences}
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            situation_prompt = f"""
            求職者のこれまでの経験職種（{st.session_state.profile['experiences']}）に基づき、その職場でよく発生する、または一般的な職場で起こり得る【具体的な業務シチュエーション】を合計15個生成してください。
            職種名という大きな括りではなく、具体的な「行動」や「環境」レベルの一文にしてください。
            
            以下のJSONフォーマットのみを厳密に出力してください（解説テキストは一切不要です）。
            {{
              "A": ["人と関わる場面のシチュエーション1", "シチュエーション2", "シチュエーション3", "シチュエーション4", "シチュエーション5"],
              "B": ["作業やルールの遵守を求められる場面1", "シチュエーション2", "シチュエーション3", "シチュエーション4", "シチュエーション5"],
              "C": ["働く環境や仕事のペースに関する場面1", "シチュエーション2", "シチュエーション3", "シチュエーション4", "シチュエーション5"]
            }}
            
            ※専門用語は使わず、「不特定多数のクレームに最前線で対応する」「マニュアル通りにデータを正確に入力する」など、初学者が直感的にイメージできるやさしい表現にしてください。
            """
            with st.spinner("あなたの経験に合わせて、シチュエーションカードを作成しています..."):
                try:
                    response = model.generate_content(situation_prompt)
                    clean_text = response.text.replace("```json", "").replace("```", "").strip()
                    st.session_state.situations = json.loads(clean_text)
                    st.session_state.step = 1
                    st.rerun()
                except Exception as e:
                    st.error("カードの生成に失敗しました。もう一度お試しいただくか、APIキーを確認してください。")

# ==================================================
# 【Step 1】業務シチュエーションの直感仕分け（NGカード機能）
# ==================================================
elif st.session_state.step == 1:
    st.progress(0.2)
    st.markdown("<div class='step-header'><h3>Step 1：仕事の場面仕分け（これだけは避けたいこと）</h3></div>", unsafe_allow_html=True)
    st.write("提示されるシチュエーションについて、あなたの本音で仕分けてください。「これが毎日続いたらきついな」と思うものを探します。")
    
    with st.form("sorting_form"):
        st.subheader("👥 A. 人と関わる場面")
        for idx, sit in enumerate(st.session_state.situations.get("A", [])):
            st.markdown(f"<div class='card-box'>📋 {sit}</div>", unsafe_allow_html=True)
            st.session_state.evaluations[f"A_{idx}"] = st.radio("この場面への気持ちは？", ["😊 苦にならない・普通", "😫 正直しんどい・避けたい"], key=f"ans_A_{idx}", horizontal=True)
        
        st.subheader("📊 B. 作業・ルールの場面")
        for idx, sit in enumerate(st.session_state.situations.get("B", [])):
            st.markdown(f"<div class='card-box'>📋 {sit}</div>", unsafe_allow_html=True)
            st.session_state.evaluations[f"B_{idx}"] = st.radio("この場面への気持ちは？", ["😊 苦にならない・普通", "😫 正直しんどい・避けたい"], key=f"ans_B_{idx}", horizontal=True)
            
        st.subheader("⏰ C. 環境・ペースの場面")
        for idx, sit in enumerate(st.session_state.situations.get("C", [])):
            st.markdown(f"<div class='card-box'>📋 {sit}</div>", unsafe_allow_html=True)
            st.session_state.evaluations[f"C_{idx}"] = st.radio("この場面への気持ちは？", ["😊 苦にならない・普通", "😫 正直しんどい・避けたい"], key=f"ans_C_{idx}", horizontal=True)
            
        submit_step1 = st.form_submit_button("仕分けを完了して、絶対NGの選定へ ➔")

    if submit_step1:
        st.session_state.step = 2
        st.rerun()

# ==================================================
# 【Step 1の続き ＆ Step 2】絶対NGの決定 ＆ 自由記述による本音と未来のスキル
# ==================================================
elif st.session_state.step == 2:
    st.progress(0.4)
    st.markdown("<div class='step-header'><h3>Step 2：絶対に避けたい「NG項目」と「未来への希望」</h3></div>", unsafe_allow_html=True)
    
    ng_pool = []
    for key, val in st.session_state.evaluations.items():
        if "😫" in val:
            cat, idx = key.split("_")
            sit_text = st.session_state.situations[cat][int(idx)]
            ng_pool.append(sit_text)
            
    with st.form("ng_and_free_form"):
        st.subheader("🛑 1. 絶対に避けたいNGワースト3")
        if ng_pool:
            absolute_ngs = st.multiselect(
                "先ほど「しんどい」と選んだ中から、次の仕事で【これだけは絶対に避けたい】というものを最大3つ選んでください。",
                options=ng_pool,
                max_selections=3
            )
        else:
            st.write("特に強い拒否感のある項目はありませんでした。このまま次へお進みください。")
            absolute_ngs = []
            
        st.write("---")
        st.subheader("💬 2. あなたの本音を吐き出してください（自由記述）")
        free_text = st.text_area("今一番就職活動で不安なことや、「本当はこういう状態が一番ホッとする、安心できる」と思うことを、まとまらない言葉でも構いませんので素直に教えてください。", 
                                 placeholder="例：前職でお客様からのキツい言葉で心が折れてしまいました。次はあまり最前線に出ず、裏方で誰かを支えるような、静かな環境で働きたいです。")
        
        st.write("---")
        st.subheader("🚀 3. 今後活かしたいスキルや知識（未来への希望）")
        desired_skills = st.text_area("今後、仕事で活かしたい・身につけたいツールや知識、勉強していることはありますか？（日常的なパソコン操作、Excelのデータ入力、簿記の知識、特定の資格など、どんなに小さなことでもOKです）",
                                      placeholder="例：職業訓練でExcelでのデータ集計を学んだので、パソコンを使う仕事に活かしたい。これからはAIツールなども触れるようになりたい。")
        
        submit_step2 = st.form_submit_button("AIコンサルタントに本音を伝えて、働き方の提案を受ける 🔮")

    if submit_step2:
        st.session_state.absolute_ngs = absolute_ngs
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt2 = f"""
        あなたは、求職者の本音を引き出し、現実的で幸せな働き方を提案するキャリアコンサルタントです。
        以下の情報をもとに、求職者へのフィードバックと「職種名を伏せた働き方の提案」を作成してください。
        
        【求職者の情報】
        ・年代：{st.session_state.profile['age']}
        ・一番変えたい引き金：{st.session_state.profile['trigger']}
        ・絶対に避けたいNG項目：{", ".join(absolute_ngs)}
        ・自由記述（本音）：{free_text}
        ・活かしたい・身につけたいスキルや知識：{desired_skills}
        
        【出力構成】
        1. 【本音の翻訳（リフレーミング）】:
        求職者が抱く「人が怖い」「もうあの仕事は嫌だ」という思い込みを否定せず受容し、「〇〇が苦手なのではなく、こういう環境のストレスを避けたいだけなんですよ」と優しく分析して伝えてください。
        ※年代に応じたトーン調整を厳守：
        ・20〜30代なら、明るくポジティブな気づきを与える伴走型。
        ・40代以上なら、これまでの経験に敬意を払い、プライドを傷つけずに「強みの抽象化」として伝えること。
        
        2. 【働き方スタイルの提案】（※注意：具体的な『職種名』は絶対にここに書かないでください！）:
        求職者のNG項目を完全に避けつつ、「活かしたい・身につけたいスキル」が無理なく活きる具体的な仕事を1つ裏で選定し、以下の要素だけを出力してください。
        ・キャッチコピー：（例：自分のペースでコツコツ積み上げる、安心の裏方ワーク）
        ・安心の環境タグ：3つ（例：#電話対応なし #マイカー通勤OK #〇〇のスキルが活きる）
        
        3. 【1日のストーリー】:
        その伏せられた仕事の、朝出社してから夕方退社するまでの業務の流れを、物語のように描写してください。その際、本人が希望するスキルや知識を「どの場面で、どのように使うのか」を具体的にイメージできるように描写に組み込んでください。最後に、必ず「[TARGET_JOB:ここに裏で想定した具体的な職種名を書く]」という形式の一行を【文章の最末尾】にハイドデータとして付与してください。画面には表示させない処理をします。
        
        【超重要：地方の現実に基づくこと】
        提案する仕事は、東京のIT企業やフルリモートワークなどではなく、「新潟市周辺の産業構造」に実際に存在する、マイカー通勤が想定される現実的な仕事（例：食品製造・水産加工の品質チェック・データ管理、地場卸売のバックオフィス、物流倉庫の出荷・配車データ入力アシ最初からタントなど）から選定し、泥臭くても手堅い業務内容を描写してください。
        """
        
        with st.spinner("⏳ AIコンサルタントがあなたの本音を分析し、あなたに一番安心な働き方のストーリーを紡いでいます。10秒ほどお待ちください..."):
            try:
                response = model.generate_content(prompt2)
                res_text = response.text
                
                proposed_job = "一般事務" # デフォルト
                if "[TARGET_JOB:" in res_text:
                    parts = res_text.split("[TARGET_JOB:")
                    res_text = parts[0]
                    proposed_job = parts[1].replace("]", "").strip()
                
                st.session_state.ai_proposal = res_text
                st.session_state.proposed_job_title = proposed_job
                st.session_state.step = 3
                st.rerun()
            except Exception as e:
                st.error(f"分析に失敗しました。エラー: {e}")

# ==================================================
# 【Step 3 & 4】ハイブリッド・フィードバック ＆ 職種名ブラインドの「1日のストーリー」
# ==================================================
elif st.session_state.step == 3:
    st.progress(0.7)
    st.markdown("<div class='step-header'><h3>Step 3 ＆ 4：本音の翻訳 と 働き方の疑似体験ストーリー</h3></div>", unsafe_allow_html=True)
    
    st.markdown("<div class='ai-box'>", unsafe_allow_html=True)
    st.write(st.session_state.ai_proposal)
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.write("---")
    st.markdown("💡 **AIコンサルタントの問いかけ**")
    st.write("この『1日のストーリー』を読んでみて、いかがでしたか？「これなら対人関係で過度に傷つくことなく、自分のやりたいスキルを活かして落ち着いて働けそうだな」と感じられたでしょうか？")
    
    if st.button("🌟 この働き方の本当の名前（職種名）と、事務職とのリアルな比較を見る"):
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt3 = f"""
        求職者は、あなたが提案した「職種名を伏せた働き方のストーリー」を読み、その働き方に魅力を感じています。ここでついに種明かしを行い、現実的な一歩を踏み出す背中を押してください。
        
        【前段で提案した仕事の具体的な職種名】：{st.session_state.proposed_job_title}
        【求職者のNG項目】：{", ".join(st.session_state.absolute_ngs)}
        
        【出力構成】
        1. 【種明かしとポジティブなネーミング】:
        提案した仕事の「職種名」を明かしてください。その際、ネガティブな先入観（例：工場＝暗い、単調など）を持たれないよう、現代的でポジティブな役割としての見出しを添えてください。（例：「工場作業」ではなく「品質と効率を支えるデータ管理オペレーター」など）
        
        2. 【「一般的な事務職」との比較表】:
        Markdownのテーブル形式（| 比較項目 | 一般的な事務職 | 今回提案した職種 |）を用いて、求職者が漠然と希望しがちな「一般的な事務職」と、今回「提案した職種」を分かりやすく比較してください。
        求職者の避けたいストレス（NG項目）の観点から、「事務職＝電話応対が非常に多く、突発的なマルチタスクで人間関係の調整が激しいハブ職であること」の現実を優しく伝え、今回の提案職種のほうがなぜ安全で内定に近く、新潟の市場で現実的なのかを論理的に解説してください。
        
        3. 【次の一歩へのエール】:
        「職種名という色眼鏡を外したことで、本当にあなたが安心して能力を発揮できる働き方が見つかりましたね」と温かく肯定し、ハローワークや求人サイトでこのキーワードを探してみるよう、やさしい言葉で締めくくってください。
        """
        with st.spinner("⏳ ついに種明かしです。一般的な事務職との徹底比較データを生成しています..."):
            try:
                response = model.generate_content(prompt3)
                st.session_state.ai_reveal = response.text
                st.session_state.step = 4
                st.rerun()
            except Exception as e:
                st.error(f"種明かしの生成に失敗しました。エラー: {e}")

# ==================================================
# 【Step 5】種明かし ＆ ギャップ解消（クロージング）
# ==================================================
elif st.session_state.step == 4:
    st.progress(1.0)
    st.markdown("<div class='step-header'><h3>Step 5：種明かしと、これからの現実的な選択肢</h3></div>", unsafe_allow_html=True)
    
    st.markdown("<div class='story-box'>", unsafe_allow_html=True)
    st.write(st.session_state.ai_reveal)
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.success("✨ 先入観から離れたことで、本当に自分が安心できる、かつ新潟で求人のあるリアルな仕事への道が開けましたね！")
    
    final_report = f"【仕事理解・マッチング診断レポート】\n\n{st.session_state.ai_proposal}\n\n--- 種明かしと解説 ---\n\n{st.session_state.ai_reveal}"
    st.download_button(
        label="📝 この仕事理解レポートを保存（ダウンロード）する",
        data=final_report,
        file_name="job_understanding_report.txt",
        mime="text/plain"
    )
    
    st.markdown("---")
    st.write("※もう一度初めから診断を行う場合は、ブラウザを更新してください。")
    st.link_button("🏠 C.HARIGOMA キャリア支援ポータルへ戻る", "https://harigoma-career.streamlit.app/")
