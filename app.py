import streamlit as st
import plotly.graph_objects as go
import json
import requests  # 使用requests库用于调用DeepSeek API
# from io import BytesIO # 图片下载功能已移除，不再需要
# import qrcode # 二维码直接加载图片文件，不再需要动态生成
# from PIL import Image # Pillow（PIL）用于qrcode，现在也无需导入

# 页面配置
st.set_page_config(
    page_title="WAIC AI潜力画像生成器 (DeepSeek版)",  # 标题更新以反映模型变化
    page_icon="🤖",
    layout="wide"
)

# 自定义CSS样式，用于美化页面元素
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

def create_radar_chart(scores, user_name):
    """
    创建用户的AI潜力雷达图。
    参数:
        scores (dict): 包含 'innovation', 'collaboration', 'leadership', 'tech_acumen' 分数的字典。
        user_name (str): 用户昵称，用于图表标题和图例。
    返回:
        plotly.graph_objects.Figure: 生成的雷达图对象。
    """
    categories = ['创新指数', '协作潜力', '领导特质', '技术敏感度']
    values = [
        scores.get('innovation', 0),    # 使用.get()确保即使键不存在也不会报错，并提供默认值
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
        fill='toself', # 填充形状内部
        fillcolor='rgba(31, 119, 180, 0.3)', # 填充颜色和透明度
        line=dict(color='rgba(31, 119, 180, 1)', width=3), # 线条颜色和宽度
        marker=dict(size=8, color='rgba(31, 119, 180, 1)'), # 标记点样式
        name=f'{user_name}的AI潜力画像' # 图例名称
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100], # 分数范围0-100
                tickfont=dict(size=12),
                gridcolor='rgba(0,0,0,0.1)' # 网格线颜色
            ),
            angularaxis=dict(
                tickfont=dict(size=14, color='#2c3e50'), # 角度轴字体样式
                gridcolor='rgba(0,0,0,0.1)' # 网格线颜色
            )
        ),
        showlegend=True, # 显示图例
        title=dict(
            text=f"📊 {user_name} 的 AI 潜力雷达图", # 图表主标题
            x=0.5, # 标题居中
            font=dict(size=20, color='#2c3e50')
        ),
        font=dict(family="Arial, sans-serif"), # 整体字体
        margin=dict(t=80, b=40, l=40, r=40) # 调整图表边距
    )
    
    return fig

def call_deepseek_api(user_inputs, user_name):
    """
    调用DeepSeek API，根据用户输入获取AI潜力分析结果。
    参数:
        user_inputs (dict): 包含用户对四个维度描述的字典。
        user_name (str): 用户昵称。
    返回:
        dict: 包含 'scores', 'analysis', 'golden_sentence' 的字典，如果API调用失败则返回 None。
    """
    try:
        # 从Streamlit Secrets中获取DeepSeek API密钥
        api_key = st.secrets.get("DEEPSEEK_API_KEY", "")
        if not api_key:
            st.error("❌ API密钥未配置 (DEEPSEEK_API_KEY)，请联系管理员。")
            return None
            
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建系统提示词，定义AI的角色和输出格式
        system_prompt = """你是一位资深的技术招聘官和职业发展顾问，具有丰富的人才评估经验。
请基于用户提供的信息，从四个维度进行专业分析：创新指数、协作潜力、领导特质、技术敏感度。

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
  "analysis": "<约100-150字的综合分析，语言积极鼓励，突出闪光点>",
  "golden_sentence": "<一句精炼的专属评语，作为用户的AI Slogan>"
}
"""
        
        # 用户提示词，包含用户的具体输入和昵称
        user_prompt = f"""请分析以下用户信息：

用户昵称：{user_name}

创新指数相关信息：
{user_inputs['innovation']}

协作潜力相关信息：
{user_inputs['collaboration']}

领导特质相关信息：
{user_inputs['leadership']}

技术敏感度相关信息：
{user_inputs['tech_acumen']}

请基于以上信息进行专业分析并按JSON格式输出。"""
        
        # DeepSeek API 请求的 payload
        payload = {
            "model": "deepseek-chat", # DeepSeek模型名称
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
        # 确保这里 message['content'] 存在且是字符串
        if 'choices' in result and len(result['choices']) > 0 and \
           'message' in result['choices'][0] and 'content' in result['choices'][0]['message']:
            response_text = result['choices'][0]['message']['content']
        else:
            st.error("API返回结构异常，未找到预期内容。")
            st.info(f"API原始返回（供调试）：{result}")
            return None
        
        # 尝试解析JSON
        try:
            parsed_result = json.loads(response_text)
            return parsed_result
        except json.JSONDecodeError:
            # 如果直接解析失败，尝试提取JSON部分 (DeepSeek通常会直接返回JSON，但仍保留此健壮性处理)
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                st.warning("API返回内容包含非JSON文本，已尝试提取JSON。")
                parsed_result = json.loads(json_match.group())
                return parsed_result
            else:
                st.error("API返回格式错误，无法解析JSON。请尝试更具体的输入或联系支持。")
                st.info(f"API原始返回内容（供调试）：{response_text}") # 显示原始返回以便调试
                return None
                
    except requests.exceptions.RequestException as e: # 捕获网络请求相关错误
        st.error(f"❌ API网络请求失败：{str(e)}")
        return None
    except Exception as e:
        st.error(f"❌ API调用出现未知问题：{str(e)}")
        return None

# `convert_plotly_to_bytes` 函数已移除，因为它不再需要

# 封装显示画像结果的逻辑，方便复用
def display_portrait_results(current_user_name, analysis_result_data):
    """
    显示AI潜力画像结果，包括雷达图、分析文本、下载提示和底部的微信推广。
    参数:
        current_user_name (str): 当前用户昵称。
        analysis_result_data (dict): 包含AI分析结果的字典。
    """
    st.markdown("---")
    st.header(f"🎉 Hey, {current_user_name}！这是你的 AI 潜力画像：")
    
    golden_sentence = analysis_result_data.get('golden_sentence', '你是一位充满潜力的探索者！')
    st.markdown(f"""
    <div class="golden-sentence">
        ✨ {golden_sentence} ✨
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([0.6, 0.4]) # 分列布局，雷达图占60%，分数占40%
    
    with col1:
        scores = analysis_result_data.get('scores', {})
        # 确保所有分数都是整数，避免类型错误
        for k in ['innovation', 'collaboration', 'leadership', 'tech_acumen']:
            try:
                scores[k] = int(scores.get(k, 0))
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
            
    # 获取分析文本
    analysis_text = analysis_result_data.get('analysis', '分析内容生成失败，请重试。')
    st.markdown(f"""
    <div class="analysis-box">
        <h3>🔍 AI 综合分析</h3>
        <p style="font-size: 1.1rem; line-height: 1.6;">{analysis_text}</p>
    </div>
    """, unsafe_allow_html=True)
            
    st.markdown("### 📥 保存与分享")
            
    # 图片下载功能已移除，替换为开发中提示
    st.info("💡 图片下载功能正在开发中，敬请期待！您可以手动截图保存此画像。")
    
    # 推广区域：继续你的AI学习之旅 (放置在主内容区域底部)
    st.markdown("---")
    st.markdown("### 🌟 继续你的AI学习之旅") # 调整标题措辞
            
    col_promo1, col_promo2 = st.columns([1, 1])
            
    with col_promo1:
        st.markdown("""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 20px; border-radius: 10px; color: white; text-align: center;'>
            <h4>🎓 想深入学习AI？</h4>
            <p>获取更多WAIC独家资源<br>
            职业发展机会等你来！</p>
        </div>
        """, unsafe_allow_html=True)
            
    with col_promo2:
        # 在这里放置微信二维码，直接加载图片文件
        # 请确保 qr_code.png 文件存在于应用根目录
        try:
            st.image("qr_code.png", width=180, caption="扫码加微信，获取更多资源")
        except Exception: # 捕获无法找到图片文件的情况
            st.markdown("""
            <div style='border: 2px dashed #667eea; padding: 20px; 
                        border-radius: 10px; text-align: center; height: 180px;
                        display: flex; align-items: center; justify-content: center;'>
                <div>
                    <p>📱 微信二维码</p>
                    <small>请将二维码图片保存为 qr_code.png</small>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    st.markdown("""
    <div style='text-align: center; font-size: 12px; color: #666; margin-top: 10px;'>
        扫描你名片上的微信二维码，<br>
        或联系我获取更多信息！
    </div>
    """, unsafe_allow_html=True)

    # 重新分析按钮
    if st.button("🔄 重新分析", use_container_width=True):
        st.query_params.clear() # 清除URL参数，如果存在 (Streamlit 1.10.0+支持)
        st.experimental_rerun() # 强制应用重新运行 (Streamlit 1.10.0+支持)

# 主应用界面
def main():
    # 主标题
    st.markdown('<h1 class="main-title">🤖 WAIC 现场专享：免费 AI 潜力画像生成</h1>', 
                unsafe_allow_html=True)
    
    # 简介
    st.markdown("""
    ### 🎯 发现你的AI时代潜力
    通过AI深度分析，生成你的专属潜力雷达图。只需几分钟，获得专业的职业发展洞察！
    """)
    
    # 强制初始化所有 session_state 变量在脚本的顶层，无论执行路径如何
    # 这是解决 KeyError 的关键
    if 'stored_user_name' not in st.session_state:
        st.session_state.stored_user_name = ""
    if 'stored_innovation_input' not in st.session_state:
        st.session_state.stored_innovation_input = ""
    if 'stored_collaboration_input' not in st.session_state:
        st.session_state.stored_collaboration_input = ""
    if 'stored_leadership_input' not in st.session_state:
        st.session_state.stored_leadership_input = ""
    if 'stored_tech_acumen_input' not in st.session_state:
        st.session_state.stored_tech_acumen_input = ""

    # 用户昵称输入框，直接从 session_state 获取和更新值
    user_name_input_widget = st.text_input(
        "👤 请输入你的昵称", 
        placeholder="例如：小王、Alex、技术达人...", 
        key="user_name_widget", # 确保 widget key 唯一
        value=st.session_state.stored_user_name # 初始化值从session_state获取
    )
    # 立即将 widget 的最新值同步到 session_state，以确保后续逻辑使用最新值
    st.session_state.stored_user_name = user_name_input_widget
    
    # 只有当昵称输入框有内容时才显示下面的表单
    if st.session_state.stored_user_name: 
        st.markdown(f"### 👋 Hi {st.session_state.stored_user_name}，请回答以下四个问题：")
        
        # 创建表单
        with st.form("profile_form", clear_on_submit=False): # clear_on_submit=False 以便在验证失败时保留输入
            st.markdown("#### 📝 请详细回答以下问题，这将帮助AI更准确地分析你的潜力：")
            
            # 四个维度的问题，直接从session_state初始化值
            innovation_input = st.text_area(
                "🧠 **创新指数**：请描述一个你近期主导或参与的最有创意的项目或想法，你是如何贡献原创思路的？",
                height=120,
                placeholder="请详细描述你的创新经历...",
                key="innovation_widget_form",
                value=st.session_state.stored_innovation_input # 初始化值
            )
            
            collaboration_input = st.text_area(
                "🤝 **协作潜力**：请描述一次重要的团队合作经历。你的角色是什么？你如何促进沟通和团队效率？",
                height=120,
                placeholder="请分享你的团队协作经验...",
                key="collaboration_widget_form",
                value=st.session_state.stored_collaboration_input # 初始化值
            )
            
            leadership_input = st.text_area(
                "👑 **领导特质**：想象你领导的项目严重落后，你会采取哪三个关键步骤来扭转局面？",
                height=120,
                placeholder="请描述你的领导策略...",
                key="leadership_widget_form",
                value=st.session_state.stored_leadership_input # 初始化值
            )
            
            tech_acumen_input = st.text_area(
                "⚡ **技术敏感度**：哪一项新兴 AI 技术（如：多模态、AI Agent、生成式视频）最让你感到兴奋？为什么？你认为它会如何改变你所在的行业？",
                height=120,
                placeholder="请分享你对AI技术的见解...",
                key="tech_acumen_widget_form",
                value=st.session_state.stored_tech_acumen_input # 初始化值
            )
            
            # 提交按钮
            submitted = st.form_submit_button("🚀 开始生成我的 AI 画像", use_container_width=True)
        
        # 处理表单提交
        if submitted:
            # 获取当前提交的值
            current_user_name_value = st.session_state.stored_user_name # 昵称从session_state获取
            # 表单内的输入框的值，在提交后可以直接从它们的返回值中获取
            current_innovation_value = innovation_input
            current_collaboration_value = collaboration_input
            current_leadership_value = leadership_input
            current_tech_acumen_value = tech_acumen_input
            
            # 提交后，将表单的当前输入值保存到 session_state，以便在下次刷新时保留
            st.session_state.stored_innovation_input = current_innovation_value
            st.session_state.stored_collaboration_input = current_collaboration_value
            st.session_state.stored_leadership_input = current_leadership_value
            st.session_state.stored_tech_acumen_input = current_tech_acumen_value


            # 验证所有输入是否都已填写
            if not all([current_innovation_value.strip(), current_collaboration_value.strip(), 
                            current_leadership_value.strip(), current_tech_acumen_value.strip()]):
                st.warning("⚠️ 请完整回答所有四个问题，这样AI才能给出更准确的分析哦！")
            else: 
                user_inputs = {
                    'innovation': current_innovation_value,
                    'collaboration': current_collaboration_value,
                    'leadership': current_leadership_value,
                    'tech_acumen': current_tech_acumen_value
                }
                
                # 显示加载状态，并调用DeepSeek API
                with st.spinner("✨ AI 大模型(DeepSeek)正在为你深度分析，请稍候..."):
                    analysis_result = call_deepseek_api(user_inputs, current_user_name_value)
                
                if analysis_result:
                    # 显示结果
                    display_portrait_results(current_user_name_value, analysis_result)
                    
                    # 提交成功并显示结果后，清空除昵称外的所有输入框的session_state值
                    # 这样下次显示表单时，除了昵称，其他输入框会是空的
                    # 这里的清空操作是针对 stored_input 变量，因为它们是初始化表单的值来源
                    st.session_state.stored_innovation_input = ""
                    st.session_state.stored_collaboration_input = ""
                    st.session_state.stored_leadership_input = ""
                    st.session_state.stored_tech_acumen_input = ""
                else:
                    st.error("😅 分析出了一点小问题，请你调整一下输入内容再试试。确保每个问题都有详细的回答哦！")

# 侧边栏信息
with st.sidebar:
    st.markdown("### 🎪 WAIC 2025") # 更新年份
    st.markdown("**世界人工智能大会现场专享**")
    st.markdown("---")
    st.markdown("### 📋 使用说明")
    st.markdown("""
    1. 输入你的昵称
    2. 详细回答四个维度的问题
    3. 等待AI分析（约30秒）
    4. 获得专属潜力雷达图
    5. （图片下载功能正在开发中）
    """) # 更新说明，移除下载图片，加上提示
    st.markdown("---")
    st.markdown("### 💡 小贴士")
    st.markdown("""
    - 回答越详细，分析越准确
    - 可以结合具体案例和数据
    - 真实回答比完美回答更有价值
    """)
    st.markdown("---")
    st.markdown("### 💫 拓展你的 AI 视野")
    st.markdown("""
    <div style='text-align: center; padding: 10px; background-color: #f0f8ff; border-radius: 8px;'>
        <p style='font-size: 14px; margin-bottom: 10px;'>
        如果你想深入了解 AI 培训、<br>
        职业发展机会或参与我们的<br>
        社群，欢迎扫描下方二维码<br>
        或添加我的微信，获取更多<br>
        WAIC 独家资源！
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # 这里放置二维码图片
    # 请将微信二维码图片保存为 qr_code.png 并放在同目录下
    try:
        # 注意：这里需要你实际提供一个名为 'qr_code.png' 的图片文件
        st.image("qr_code.png", width=200, caption="扫码获取更多AI资源")
    except Exception: # 捕获更通用的异常
        st.markdown("""
        <div style='text-align: center; padding: 20px; border: 2px dashed #ccc; border-radius: 8px;'>
            <p>📱 微信二维码</p>
            <small>请将二维码图片保存为 qr_code.png</small>
        </div>
        """, unsafe_allow_html=True)
            
    st.markdown("""
    <div style='text-align: center; font-size: 12px; color: #666; margin-top: 10px;'>
        扫描你名片上的微信二维码，<br>
        或联系我获取更多信息！
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
