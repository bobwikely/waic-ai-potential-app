import streamlit as st
import plotly.graph_objects as go
import json
import requests
from io import BytesIO
import uuid
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# 页面配置
st.set_page_config(
    page_title="WAIC AI潜力画像生成器 (DeepSeek版)",
    page_icon="🧠",
    layout="wide"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main-title {
        text-align: center;
        color: #1f77b4;
        font-size: 2.5rem;
        margin-bottom: 2rem;
        padding: 1rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .golden-sentence {
        text-align: center;
        font-size: 1.5rem;
        color: #ff6b6b;
        font-weight: bold;
        padding: 1rem;
        background-color: #fff3cd;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .analysis-box {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
    }
    /* 调整雷达图容器的最小高度，防止在小屏幕下过度压缩 */
    .stPlotlyChart {
        min-height: 400px;
    }
</style>
""", unsafe_allow_html=True)

# Gspread 初始化函数
@st.cache_resource(ttl=3600)
def get_gspread_client():
    try:
        creds_json = st.secrets["GCP_SERVICE_ACCOUNT_KEY"]
        creds_dict = json.loads(creds_json) # 尝试解析JSON
        
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except KeyError:
        st.error("❌ Google Cloud Service Account 凭据未在 Streamlit Secrets 中配置 (GCP_SERVICE_ACCOUNT_KEY)。")
        return None
    except json.JSONDecodeError:
        st.error("❌ Google Cloud Service Account 凭据 JSON 格式错误。请检查 Streamlit Secrets 中的内容是否为有效的JSON。")
        st.stop() # 出现JSON解析错误时停止应用，避免后续报错
        return None
    except Exception as e:
        st.error(f"❌ 无法连接 Google Sheets：{str(e)}。请检查凭据和API启用情况。")
        st.stop() # 连接错误时停止应用
        return None

# 获取工作表
@st.cache_data(ttl=600)
def get_worksheet():
    client = get_gspread_client()
    if client:
        try:
            spreadsheet_name = "WAIC_AI_Potentials_Data"
            worksheet_name = "User_Profiles"
            sheet = client.open(spreadsheet_name).worksheet(worksheet_name)
            return sheet
        except gspread.exceptions.SpreadsheetNotFound:
            st.error(f"❌ 找不到名为 '{spreadsheet_name}' 的 Google Sheet。请检查名称或共享权限。")
            st.stop()
            return None
        except gspread.exceptions.WorksheetNotFound:
            st.error(f"❌ 找不到工作表 '{worksheet_name}'。请检查名称。")
            st.stop()
            return None
        except Exception as e:
            st.error(f"❌ 无法获取 Google Sheet 工作表：{str(e)}")
            st.stop()
            return None
    return None

# 写入数据到 Google Sheets
def append_to_sheet(data_row):
    sheet = get_worksheet()
    if sheet:
        try:
            sheet.append_row(data_row)
            return True
        except Exception as e:
            st.error(f"❌ 无法将数据写入 Google Sheet：{str(e)}")
            return False
    return False

# 从 Google Sheets 根据 share_id 查找记录
def get_record_by_share_id(share_id):
    sheet = get_worksheet()
    if sheet:
        try:
            all_records = sheet.get_all_records()
            for record in all_records:
                if record.get('share_id') == share_id:
                    return record
            return None
        except Exception as e:
            st.error(f"❌ 无法根据分享ID查找数据：{str(e)}")
            return None
    return None


def create_radar_chart(scores, user_name):
    """创建雷达图"""
    categories = ['创新指数', '协作潜力', '领导特质', '技术敏感度']
    values = [
        scores.get('innovation', 0),
        scores.get('collaboration', 0),
        scores.get('leadership', 0),
        scores.get('tech_acumen', 0)
    ]
    
    values_closed = values + [values[0]]
    categories_closed = categories + [categories[0]]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=values_closed,
        theta=categories_closed,
        fill='toself',
        fillcolor='rgba(31, 119, 180, 0.3)',
        line=dict(color='rgba(31, 119, 180, 1)', width=3),
        marker=dict(size=8, color='rgba(31, 119, 180, 1)'),
        name=f'{user_name}的AI潜力画像'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(size=12),
                gridcolor='rgba(0,0,0,0.1)'
            ),
            angularaxis=dict(
                tickfont=dict(size=14, color='#2c3e50'),
                gridcolor='rgba(0,0,0,0.1)'
            )
        ),
        showlegend=True,
        title=dict(
            text=f"🎯 {user_name} 的 AI 潜力雷达图",
            x=0.5,
            font=dict(size=20, color='#2c3e50')
        ),
        font=dict(family="Arial, sans-serif"),
        margin=dict(t=80, b=40, l=60, r=60)
    )
    
    return fig

def call_deepseek_api(user_inputs):
    """调用DeepSeek API进行分析"""
    try:
        api_key = st.secrets.get("DEEPSEEK_API_KEY", "")
        if not api_key:
            st.error("❌ DeepSeek API密钥未配置，请联系管理员")
            return None
            
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        system_prompt = """你是一位资深的技术招聘官和职业发展顾问，具有丰富的人才评估经验。
        请基于用户提供的信息，从四个维度进行专业分析：创新指数、协作潜力、领导特质、技术敏感度。

        **在您的分析和评语中，请始终使用“您”来指代用户，保持亲切、积极和鼓励的语气。**
        
        评分标准：
        - 创新指数(innovation)：原创思维、问题解决能力、创意实现
        - 协作潜力(collaboration)：团队合作、沟通能力、集体意识  
        - 领导特质(leadership)：决策能力、责任担当、影响力
        - 技术敏感度(tech_acumen)：技术理解、学习能力、前瞻性

        请严格按照以下JSON格式输出，不要添加任何其他内容：
        {
          "scores": {
            "innovation": <1-100之间的整数>,
            "collaboration": <1-100之间的整数>,
            "leadership": <1-100之间的整数>,  
            "tech_acumen": <1-100之间的整数>
          },
          "analysis": "<约100-150字的综合分析，语言积极鼓励，突出闪光点，请始终使用“您”来称呼用户，而不是直接提及昵称>",
          "golden_sentence": "<一句精炼的专属评语，作为您的AI Slogan，请直接以评语开始，不要提到用户昵称>"
        }"""
        
        user_prompt = f"""请分析以下信息：

        创新指数相关信息：
        {user_inputs['innovation']}

        协作潜力相关信息：
        {user_inputs['collaboration']}

        领导特质相关信息：
        {user_inputs['leadership']}

        技术敏感度相关信息：
        {user_inputs['tech_acumen']}

        请基于以上信息进行专业分析，并严格按照JSON格式输出，确保分析和评语中使用“您”来称呼。"""

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": 1000,
            "temperature": 0.7,
            "response_format": {"type": "json_object"}
        }

        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()

        result = response.json()
        response_text = result['choices'][0']['message']['content']
        
        parsed_result = json.loads(response_text)
        return parsed_result
            
    except requests.exceptions.RequestException as e:
        st.error(f"❌ API网络请求失败：{str(e)}")
        return None
    except json.JSONDecodeError:
        st.error("❌ API返回格式错误，无法解析JSON。请尝试更具体的输入或联系支持。")
        st.info(f"API原始返回内容（供调试）：{response_text}")
        return None
    except Exception as e:
        st.error(f"❌ API调用出现未知问题：{str(e)}")
        return None

def convert_plotly_to_bytes(fig):
    """将Plotly图表转换为字节流用于下载"""
    try:
        img_bytes = fig.to_image(format="png", width=1000, height=800, scale=2) 
        return img_bytes
    except Exception as e:
        st.error(f"图片生成失败：{str(e)}")
        st.warning("提示：如果图片无法下载，请确保您的环境中已安装 'kaleido' 库。")
        return None

# 新增一个函数来封装显示画像结果的逻辑，方便复用
def display_portrait_results(current_user_name, analysis_result_data, current_share_id=None):
    st.markdown("---")
    st.header(f"🎉 Hey, {current_user_name}！这是您的 AI 潜力画像：")
    
    golden_sentence = analysis_result_data.get('golden_sentence', '您是一位充满潜力的探索者！')
    st.markdown(f"""
    <div class="golden-sentence">
        ✨ {golden_sentence} ✨
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([0.6, 0.4])
    
    with col1:
        scores = {}
        if 'scores' in analysis_result_data and isinstance(analysis_result_data['scores'], dict):
            scores = analysis_result_data['scores']
        else:
            scores['innovation'] = analysis_result_data.get('innovation_score', 0)
            scores['collaboration'] = analysis_result_data.get('collaboration_score', 0)
            scores['leadership'] = analysis_result_data.get('leadership_score', 0)
            scores['tech_acumen'] = analysis_result_data.get('tech_acumen_score', 0)

        for k in scores:
            try:
                scores[k] = int(scores[k])
            except (ValueError, TypeError):
                scores[k] = 0
        
        fig = create_radar_chart(scores, current_user_name)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### 📊 详细得分")
        st.metric("🧠 创新指数", f"{scores.get('innovation', 'N/A')}/100")
        st.metric("🤝 协作潜力", f"{scores.get('collaboration', 'N/A')}/100") 
        st.metric("👑 领导特质", f"{scores.get('leadership', 'N/A')}/100")
        st.metric("⚡ 技术敏感度", f"{scores.get('tech_acumen', 'N/A')}/100")
            
    analysis_text = analysis_result_data.get('analysis', analysis_result_data.get('analysis_text', '分析内容生成失败，请重试。'))
    st.markdown(f"""
    <div class="analysis-box">
        <h3>🔍 AI 综合分析</h3>
        <p style="font-size: 1.1rem; line-height: 1.6;">{analysis_text}</p>
    </div>
    """, unsafe_allow_html=True)
        
    st.markdown("### 📥 保存与分享")
        
    img_bytes = convert_plotly_to_bytes(fig)
    if img_bytes:
        st.download_button(
            label="📱 下载结果图，分享您的 AI 潜力",
            data=img_bytes,
            file_name=f"{current_user_name}_AI潜力画像_DeepSeek.png",
            mime="image/png",
            use_container_width=True
        )
    
    if current_share_id:
        base_app_url = "https://waic-ai-potential-app-cmpagnd2gprtttnonquh4w.streamlit.app/"
        share_url = f"{base_app_url}?share_id={current_share_id}"
        st.markdown(f"""
        <div style="background-color: #e6f7ff; padding: 15px; border-radius: 8px; margin-top: 20px;">
            <h4>🔗 您的专属分享链接：</h4>
            <p style="word-break: break-all; font-size: 1rem;">{share_url}</p>
            <p>💡 **小贴士：** 复制此链接，发送给朋友或发布到朋友圈，他们可以直接查看您的画像！</p>
            <p>或者，直接让朋友在微信中扫描下方二维码！</p>
        </div>
        """, unsafe_allow_html=True)

        try:
            import qrcode
            from PIL import Image
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(share_url)
            qr.make(fit=True)
            img_qr = qr.make_image(fill_color="black", back_color="white")
            
            buf = BytesIO()
            img_qr.save(buf, format="PNG")
            st.image(buf.getvalue(), caption="扫描二维码查看您的专属画像", width=200)
        except ImportError:
            st.warning("⚠️ 无法生成二维码。请在终端运行 `pip install qrcode Pillow` 以启用此功能。")
        except Exception as e:
            st.warning(f"⚠️ 生成二维码时出错：{e}")

    # 重新分析按钮
    if st.button("🔄 重新分析", use_container_width=True):
        st.query_params.clear() # 清除所有URL参数，确保回到主页面
        st.experimental_rerun()


# 主应用界面
def main():
    # 主标题
    st.markdown('<h1 class="main-title">🤖 WAIC 现场专享：免费 AI 潜力画像生成</h1>', 
                unsafe_allow_html=True)
    
    # 简介
    st.markdown("""
    ### 🎯 发现您的AI时代潜力
    通过AI深度分析，生成您的专属潜力雷达图。只需几分钟，获得专业的职业发展洞察！
    """)
    
    # 尝试从URL参数获取分享ID
    share_id = st.query_params.get("share_id")

    # 如果URL中带有分享ID，尝试从Google Sheets加载并显示画像
    if share_id:
        with st.spinner(f"正在加载分享ID为 '{share_id}' 的AI潜力画像..."):
            portrait_data = get_record_by_share_id(share_id)
            if portrait_data:
                display_portrait_results(
                    portrait_data.get('user_name', '匿名用户'),
                    portrait_data,
                    share_id
                )
                st.stop()
            else:
                st.warning(f"🤔 未找到分享ID为 '{share_id}' 的画像数据。请检查链接是否正确或已过期。")
                if st.button("返回主页重新生成", use_container_width=True):
                    st.query_params.clear()
                    st.experimental_rerun()
                st.stop() # 确保在未找到数据时也停止，避免渲染主表单


    # 初始化所有输入组件的session_state值，确保它们在任何时候都有默认值
    if 'user_name_value' not in st.session_state:
        st.session_state.user_name_value = ""
    if 'innovation_input_value' not in st.session_state:
        st.session_state.innovation_input_value = ""
    if 'collaboration_input_value' not in st.session_state:
        st.session_state.collaboration_input_value = ""
    if 'leadership_input_value' not in st.session_state:
        st.session_state.leadership_input_value = ""
    if 'tech_acumen_input_value' not in st.session_state:
        st.session_state.tech_acumen_input_value = ""


    # 以下是用户填写表单并生成画像的原始逻辑
    # 为每个输入组件指定一个唯一的key，并将其值绑定到st.session_state
    user_name = st.text_input(
        "👤 请输入您的昵称", 
        placeholder="例如：小王、Alex、技术达人...", 
        key="user_name_input_widget", # 唯一的widget key
        value=st.session_state.user_name_value, # 绑定到session_state值
        on_change=lambda: setattr(st.session_state, 'user_name_value', st.session_state.user_name_input_widget) # 当组件值改变时更新session_state
    )
    
    if user_name: # 只有当user_name不为空时才显示表单
        st.markdown(f"### 👋 Hi {user_name}，请回答以下四个问题：")
        
        with st.form("profile_form", clear_on_submit=True): # 表单提交后清空内容
            st.markdown("#### 📝 请详细回答以下问题，这将帮助AI更准确地分析您的潜力：")
            
            innovation_input = st.text_area(
                "🧠 **创新指数**：请描述一个您近期主导或参与的最有创意的项目或想法，您是如何贡献原创思路的？",
                height=120,
                placeholder="请详细描述您的创新经历...",
                key="innovation_input_area",
                value=st.session_state.innovation_input_value,
                on_change=lambda: setattr(st.session_state, 'innovation_input_value', st.session_state.innovation_input_area)
            )
            
            collaboration_input = st.text_area(
                "🤝 **协作潜力**：请描述一次重要的团队合作经历。您的角色是什么？您如何促进沟通和团队效率？",
                height=120,
                placeholder="请分享您的团队协作经验...",
                key="collaboration_input_area",
                value=st.session_state.collaboration_input_value,
                on_change=lambda: setattr(st.session_state, 'collaboration_input_value', st.session_state.collaboration_input_area)
            )
            
            leadership_input = st.text_area(
                "👑 **领导特质**：想象您领导的项目严重落后，您会采取哪三个关键步骤来扭转局面？",
                height=120,
                placeholder="请描述您的领导策略...",
                key="leadership_input_area",
                value=st.session_state.leadership_input_value,
                on_change=lambda: setattr(st.session_state, 'leadership_input_value', st.session_state.leadership_input_area)
            )
            
            tech_acumen_input = st.text_area(
                "⚡ **技术敏感度**：哪一项新兴 AI 技术（如：多模态、AI Agent、生成式视频）最让您感到兴奋？为什么？您认为它会如何改变您所在的行业？",
                height=120,
                placeholder="请分享您对AI技术的见解...",
                key="tech_acumen_input_area",
                value=st.session_state.tech_acumen_input_value,
                on_change=lambda: setattr(st.session_state, 'tech_acumen_input_value', st.session_state.tech_acumen_input_area)
            )
            
            submitted = st.form_submit_button("🚀 开始生成我的 AI 画像", use_container_width=True)
        
        if submitted:
            # 提交后清空表单输入框
            st.session_state.innovation_input_value = ""
            st.session_state.collaboration_input_value = ""
            st.session_state.leadership_input_value = ""
            st.session_state.tech_acumen_input_value = ""

            if not all([innovation_input.strip(), collaboration_input.strip(), 
                         leadership_input.strip(), tech_acumen_input.strip()]):
                st.warning("⚠️ 请完整回答所有四个问题，这样AI才能给出更准确的分析哦！")
                # 即使警告，也不要直接return，让用户看到警告后可以继续填写
            else: # 只有所有输入都完整时才调用API和保存数据
                user_inputs = {
                    'innovation': innovation_input,
                    'collaboration': collaboration_input,
                    'leadership': leadership_input,
                    'tech_acumen': tech_acumen_input
                }
                
                with st.spinner("✨ AI 大模型(DeepSeek)正在为您深度分析，请稍候..."):
                    analysis_result = call_deepseek_api(user_inputs)
                
                if analysis_result:
                    current_share_id = str(uuid.uuid4())
                    
                    data_row = [
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        current_share_id,
                        user_name,
                        innovation_input,
                        collaboration_input,
                        leadership_input,
                        tech_acumen_input,
                        analysis_result['scores'].get('innovation', ''),
                        analysis_result['scores'].get('collaboration', ''),
                        analysis_result['scores'].get('leadership', ''),
                        analysis_result['scores'].get('tech_acumen', ''),
                        analysis_result.get('analysis', ''),
                        analysis_result.get('golden_sentence', '')
                    ]
                    
                    if append_to_sheet(data_row):
                        st.success("✅ 您的画像数据已成功保存！")
                        display_portrait_results(user_name, analysis_result, current_share_id)
                    else:
                        st.error("❌ 无法保存您的画像数据。请联系管理员或检查Google Sheets配置。")
                else:
                    st.error("😅 分析出了一点小问题，请您调整一下输入内容再试试。确保每个问题都有详细的回答哦！")

# 侧边栏信息
with st.sidebar:
    st.markdown("### 🎪 WAIC 2025")
    st.markdown("**世界人工智能大会现场专享**")
    st.markdown("---")
    st.markdown("### 💻 技术栈")
    st.markdown("- **后端:** Python, Streamlit")
    st.markdown("- **AI模型:** DeepSeek API")
    st.markdown("- **可视化:** Plotly")
    st.markdown("- **数据存储:** Google Sheets")
    st.markdown("---")
    st.markdown("### 💡 小贴士")
    st.markdown("""
    - 回答越详细，分析越准确
    - 可以结合具体案例和数据
    - 真实回答比完美回答更有价值
    """)
    st.markdown("### 🤝 拓展您的 AI 视野")
    st.markdown("""
    如果您想深入了解 AI 培训、职业发展机会或参与我们的社群，
    欢迎扫描下方二维码或添加我的微信，获取更多WAIC独家资源！
    """)
    st.markdown("扫描您名片上的微信二维码，或联系我获取更多信息！")

if __name__ == "__main__":
    main()
