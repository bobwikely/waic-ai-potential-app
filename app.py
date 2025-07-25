import streamlit as st
import plotly.graph_objects as go
import json
import requests
from io import BytesIO
import uuid
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import qrcode
from PIL import Image

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
    """
    使用Streamlit Secrets中配置的服务账户凭据连接Google Sheets API。
    """
    try:
        # 从Streamlit Secrets中获取GCP服务账户密钥
        creds_json = st.secrets["GCP_SERVICE_ACCOUNT_KEY"]
        creds_dict = json.loads(creds_json) # 将JSON字符串解析为字典
        
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except KeyError:
        st.error("❌ Google Cloud Service Account 凭据未在 Streamlit Secrets 中配置 (GCP_SERVICE_ACCOUNT_KEY)。")
        st.stop() # 停止应用运行，因为核心凭据缺失
        return None
    except json.JSONDecodeError:
        st.error("❌ Google Cloud Service Account 凭据 JSON 格式错误。请检查 Streamlit Secrets 中的内容是否为有效的JSON。")
        st.stop() # 停止应用运行
        return None
    except Exception as e:
        st.error(f"❌ 无法连接 Google Sheets：{str(e)}。请检查凭据和API启用情况。")
        st.stop() # 停止应用运行
        return None

# 获取工作表
@st.cache_data(ttl=600)
def get_worksheet():
    """
    获取指定Google Sheet和工作表。
    """
    client = get_gspread_client()
    if client:
        try:
            # 您的Google Sheet名称
            spreadsheet_name = "WAIC_AI_Potentials_Data"
            # 您在Google Sheet中的工作表名称（根据您提供的图片是User_Profiles）
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
    """
    将一行数据追加到Google Sheet中。
    """
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
    """
    根据分享ID从Google Sheet中查找对应的用户画像记录。
    """
    sheet = get_worksheet()
    if sheet:
        try:
            all_records = sheet.get_all_records()
            for record in all_records:
                if record.get('share_id') == share_id:
                    return record
            return None # 如果没有找到匹配的记录
        except Exception as e:
            st.error(f"❌ 无法根据分享ID查找数据：{str(e)}")
            return None
    return None

def create_radar_chart(scores, user_name):
    """
    创建用户的AI潜力雷达图。
    """
    categories = ['创新指数', '协作潜力', '领导特质', '技术敏感度']
    values = [
        scores.get('innovation', 0),
        scores.get('collaboration', 0),
        scores.get('leadership', 0),
        scores.get('tech_acumen', 0)
    ]
    
    # 为了闭合雷达图，将第一个值追加到末尾
    values_closed = values + [values[0]]
    categories_closed = categories + [categories[0]]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=values_closed,
        theta=categories_closed,
        fill='toself',
        fillcolor='rgba(31, 119, 180, 0.3)', # 填充颜色
        line=dict(color='rgba(31, 119, 180, 1)', width=3), # 线条颜色和宽度
        marker=dict(size=8, color='rgba(31, 119, 180, 1)'), # 标记点样式
        name=f'{user_name}的AI潜力画像'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100], # 分数范围0-100
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
            text=f"📊 {user_name} 的 AI 潜力雷达图",
            x=0.5, # 标题居中
            font=dict(size=20, color='#2c3e50')
        ),
        font=dict(family="Arial, sans-serif"),
        margin=dict(t=80, b=40, l=60, r=60) # 调整图表边距
    )
    
    return fig

def call_deepseek_api(user_inputs):
    """
    调用DeepSeek API，根据用户输入获取AI潜力分析结果。
    """
    try:
        # 从Streamlit Secrets中获取DeepSeek API密钥
        api_key = st.secrets.get("DEEPSEEK_API_KEY", "")
        if not api_key:
            st.error("❌ DeepSeek API密钥未配置，请联系管理员")
            return None
            
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 系统提示词，定义AI的角色和输出格式
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
}
"""
        
        # 用户提示词，包含用户的具体输入
        user_prompt = f"""请分析以下信息：

创新指数相关信息：
{user_inputs['innovation']}

协作潜力相关信息：
{user_inputs['collaboration']}

领导特质相关信息：
{user_inputs['leadership']}

技术敏感度相关信息：
{user_inputs['tech_acumen']}

请基于以上信息进行专业分析，并严格按照JSON格式输出，确保分析和评语中使用“您”来称呼。
"""

        # API请求的payload
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": 1000,
            "temperature": 0.7,
            "response_format": {"type": "json_object"} # 明确要求返回JSON格式
        }

        # 发送API请求
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status() # 检查HTTP请求是否成功

        result = response.json()
        response_text = result['choices'][0]['message']['content']
        
        # 解析API返回的JSON字符串
        parsed_result = json.loads(response_text)
        return parsed_result
            
    except requests.exceptions.RequestException as e:
        st.error(f"❌ API网络请求失败：{str(e)}")
        return None
    except json.JSONDecodeError:
        st.error("❌ API返回格式错误，无法解析JSON。请尝试更具体的输入或联系支持。")
        st.info(f"API原始返回内容（供调试）：{response_text}") # 显示原始返回以便调试
        return None
    except Exception as e:
        st.error(f"❌ API调用出现未知问题：{str(e)}")
        return None

def convert_plotly_to_bytes(fig):
    """
    将Plotly图表转换为PNG格式的字节流，用于下载。
    """
    try:
        # 使用kaleido将Plotly图表导出为图片
        img_bytes = fig.to_image(format="png", width=1000, height=800, scale=2) 
        return img_bytes
    except Exception as e:
        st.error(f"图片生成失败：{str(e)}")
        st.warning("提示：如果图片无法下载，请确保您的环境中已安装 'kaleido' 库。")
        return None

# 封装显示画像结果的逻辑，方便复用
def display_portrait_results(current_user_name, analysis_result_data, current_share_id=None):
    """
    显示AI潜力画像结果，包括雷达图、分析文本和分享选项。
    """
    st.markdown("---")
    st.header(f"🎉 Hey, {current_user_name}！这是您的 AI 潜力画像：")
    
    golden_sentence = analysis_result_data.get('golden_sentence', '您是一位充满潜力的探索者！')
    st.markdown(f"""
    <div class="golden-sentence">
        ✨ {golden_sentence} ✨
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([0.6, 0.4]) # 分列布局
    
    with col1:
        scores = {}
        # 兼容API返回的不同分数结构
        if 'scores' in analysis_result_data and isinstance(analysis_result_data['scores'], dict):
            scores = analysis_result_data['scores']
        else: # 如果是直接从Google Sheet加载的扁平化数据
            scores['innovation'] = analysis_result_data.get('innovation_score', 0)
            scores['collaboration'] = analysis_result_data.get('collaboration_score', 0)
            scores['leadership'] = analysis_result_data.get('leadership_score', 0)
            scores['tech_acumen'] = analysis_result_data.get('tech_acumen_score', 0)

        # 确保所有分数都是整数
        for k in scores:
            try:
                scores[k] = int(scores[k])
            except (ValueError, TypeError):
                scores[k] = 0 # 转换失败则设为0
        
        fig = create_radar_chart(scores, current_user_name)
        st.plotly_chart(fig, use_container_width=True) # 使用容器宽度，自适应布局
    
    with col2:
        st.markdown("### 📊 详细得分")
        st.metric("🧠 创新指数", f"{scores.get('innovation', 'N/A')}/100")
        st.metric("🤝 协作潜力", f"{scores.get('collaboration', 'N/A')}/100")  
        st.metric("👑 领导特质", f"{scores.get('leadership', 'N/A')}/100")
        st.metric("⚡ 技术敏感度", f"{scores.get('tech_acumen', 'N/A')}/100")
            
    # 获取分析文本，兼容不同字段名
    analysis_text = analysis_result_data.get('analysis', analysis_result_data.get('analysis_text', '分析内容生成失败，请重试。'))
    st.markdown(f"""
    <div class="analysis-box">
        <h3>🔍 AI 综合分析</h3>
        <p style="font-size: 1.1rem; line-height: 1.6;">{analysis_text}</p>
    </div>
    """, unsafe_allow_html=True)
            
    st.markdown("### 📥 保存与分享")
            
    # 下载图片按钮
    img_bytes = convert_plotly_to_bytes(fig)
    if img_bytes:
        st.download_button(
            label="📱 下载结果图，分享您的 AI 潜力",
            data=img_bytes,
            file_name=f"{current_user_name}_AI潜力画像_DeepSeek.png",
            mime="image/png",
            use_container_width=True
        )
    
    # 分享链接和二维码
    if current_share_id:
        # 部署后请将此URL替换为您的Streamlit应用的实际部署URL
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
            # 生成二维码并显示
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
        st.query_params.clear() # 清除URL参数
        st.experimental_rerun() # 重新运行应用，回到初始状态


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
    
    # 检查URL中是否有分享ID
    share_id = st.query_params.get("share_id")

    # 如果有分享ID，则加载并显示保存的画像
    if share_id:
        with st.spinner(f"正在加载分享ID为 '{share_id}' 的AI潜力画像..."):
            portrait_data = get_record_by_share_id(share_id)
            if portrait_data:
                display_portrait_results(
                    portrait_data.get('user_name', '匿名用户'), # 从加载的数据中获取昵称
                    portrait_data, # 传入整个数据字典
                    share_id # 传入分享ID
                )
                st.stop() # 显示结果后停止后续表单渲染
            else:
                st.warning(f"🤔 未找到分享ID为 '{share_id}' 的画像数据。请检查链接是否正确或已过期。")
                if st.button("返回主页重新生成", use_container_width=True):
                    st.query_params.clear()
                    st.experimental_rerun()
                st.stop() # 停止应用运行，等待用户操作

    # 使用st.session_state存储输入组件的值，确保跨重新运行保持值
    # 在应用生命周期开始时初始化所有session_state键
    if 'user_name_input' not in st.session_state:
        st.session_state.user_name_input = ""
    if 'innovation_input' not in st.session_state:
        st.session_state.innovation_input = ""
    if 'collaboration_input' not in st.session_state:
        st.session_state.collaboration_input = ""
    if 'leadership_input' not in st.session_state:
        st.session_state.leadership_input = ""
    if 'tech_acumen_input' not in st.session_state:
        st.session_state.tech_acumen_input = ""

    # 用户昵称输入框
    user_name_input = st.text_input(
        "👤 请输入您的昵称", 
        placeholder="例如：小王、Alex、技术达人...", 
        key="user_name_input", # 唯一的widget key
        value=st.session_state.user_name_input, # 从session_state读取当前值
        # on_change lambda 确保当组件值改变时，session_state也同步更新
        on_change=lambda: setattr(st.session_state, 'user_name_input', st.session_state.user_name_input) 
    )
    # 确保session_state.user_name_input始终与最新的输入框值同步
    if st.session_state.user_name_input != user_name_input:
        st.session_state.user_name_input = user_name_input

    
    # 只有当昵称输入框有内容时才显示下面的表单
    if st.session_state.user_name_input: 
        st.markdown(f"### 👋 Hi {st.session_state.user_name_input}，请回答以下四个问题：")
        
        with st.form("profile_form", clear_on_submit=False): # 设置 clear_on_submit=False 以便在验证失败时保留输入
            st.markdown("#### 📝 请详细回答以下问题，这将帮助AI更准确地分析您的潜力：")
            
            # 各个维度的输入框，绑定到session_state
            innovation_input = st.text_area(
                "🧠 **创新指数**：请描述一个您近期主导或参与的最有创意的项目或想法，您是如何贡献原创思路的？",
                height=120,
                placeholder="请详细描述您的创新经历...",
                key="innovation_input",
                value=st.session_state.innovation_input,
                on_change=lambda: setattr(st.session_state, 'innovation_input', st.session_state.innovation_input)
            )
            
            collaboration_input = st.text_area(
                "🤝 **协作潜力**：请描述一次重要的团队合作经历。您的角色是什么？您如何促进沟通和团队效率？",
                height=120,
                placeholder="请分享您的团队协作经验...",
                key="collaboration_input",
                value=st.session_state.collaboration_input,
                on_change=lambda: setattr(st.session_state, 'collaboration_input', st.session_state.collaboration_input)
            )
            
            leadership_input = st.text_area(
                "👑 **领导特质**：想象您领导的项目严重落后，您会采取哪三个关键步骤来扭转局面？",
                height=120,
                placeholder="请描述您的领导策略...",
                key="leadership_input",
                value=st.session_state.leadership_input,
                on_change=lambda: setattr(st.session_state, 'leadership_input', st.session_state.leadership_input)
            )
            
            tech_acumen_input = st.text_area(
                "⚡ **技术敏感度**：哪一项新兴 AI 技术（如：多模态、AI Agent、生成式视频）最让您感到兴奋？为什么？您认为它会如何改变您所在的行业？",
                height=120,
                placeholder="请分享您对AI技术的见解...",
                key="tech_acumen_input",
                value=st.session_state.tech_acumen_input,
                on_change=lambda: setattr(st.session_state, 'tech_acumen_input', st.session_state.tech_acumen_input)
            )
            
            submitted = st.form_submit_button("🚀 开始生成我的 AI 画像", use_container_width=True)
        
        if submitted:
            # 获取当前最新的输入值
            current_user_name_value = st.session_state.user_name_input
            current_innovation_value = st.session_state.innovation_input
            current_collaboration_value = st.session_state.collaboration_input
            current_leadership_value = st.session_state.leadership_input
            current_tech_acumen_value = st.session_state.tech_acumen_input

            # 检查所有输入是否都已填写
            if not all([current_innovation_value.strip(), current_collaboration_value.strip(), 
                            current_leadership_value.strip(), current_tech_acumen_value.strip()]):
                st.warning("⚠️ 请完整回答所有四个问题，这样AI才能给出更准确的分析哦！")
                # 不再使用return，让警告信息显示出来，用户可以继续填写
            else: 
                user_inputs = {
                    'innovation': current_innovation_value,
                    'collaboration': current_collaboration_value,
                    'leadership': current_leadership_value,
                    'tech_acumen': current_tech_acumen_value
                }
                
                with st.spinner("✨ AI 大模型(DeepSeek)正在为您深度分析，请稍候..."):
                    analysis_result = call_deepseek_api(user_inputs)
                
                if analysis_result:
                    current_share_id = str(uuid.uuid4()) # 生成唯一的分享ID
                    
                    # 准备要写入Google Sheet的数据行
                    data_row = [
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"), # 时间戳
                        current_share_id, # 分享ID
                        current_user_name_value, # 用户昵称
                        current_innovation_value, # 创新输入
                        current_collaboration_value, # 协作输入
                        current_leadership_value, # 领导输入
                        current_tech_acumen_value, # 技术敏感度输入
                        analysis_result['scores'].get('innovation', ''), # 创新得分
                        analysis_result['scores'].get('collaboration', ''), # 协作得分
                        analysis_result['scores'].get('leadership', ''), # 领导得分
                        analysis_result['scores'].get('tech_acumen', ''), # 技术敏感度得分
                        analysis_result.get('analysis', ''), # 综合分析
                        analysis_result.get('golden_sentence', '') # 专属评语
                    ]
                    
                    # 将数据写入Google Sheet
                    if append_to_sheet(data_row):
                        st.success("✅ 您的画像数据已成功保存！")
                        display_portrait_results(current_user_name_value, analysis_result, current_share_id)
                        # 清空表单输入框的session_state值，让下次显示时为空
                        st.session_state.innovation_input = ""
                        st.session_state.collaboration_input = ""
                        st.session_state.leadership_input = ""
                        st.session_state.tech_acumen_input = ""
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
    st.markdown("扫描您名片上的微信二维码，或联系我获取更多信息！") # 请替换为实际的二维码图片或提示

if __name__ == "__main__":
    main()
