import streamlit as st
import plotly.graph_objects as go
import json
import requests  # 使用 requests 库来调用 DeepSeek API
from io import BytesIO

# 页面配置
st.set_page_config(
    page_title="WAIC AI潜力画像生成器 (DeepSeek版)",
    page_icon="🧠",
    layout="wide"
)

# 自定义CSS样式 (与之前版本保持一致)
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
</style>
""", unsafe_allow_html=True)

def create_radar_chart(scores, user_name):
    """创建雷达图 (与之前版本保持一致)"""
    categories = ['创新指数', '协作潜力', '领导特质', '技术敏感度']
    values = [
        scores.get('innovation', 0),
        scores.get('collaboration', 0),
        scores.get('leadership', 0),
        scores.get('tech_acumen', 0)
    ]
    
    # 闭合雷达图
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
        width=600,
        height=500,
        margin=dict(t=80, b=40, l=40, r=40)
    )
    
    return fig

def call_deepseek_api(user_inputs, user_name):
    """【已修改】调用DeepSeek API进行分析"""
    try:
        # 获取DeepSeek API密钥
        api_key = st.secrets.get("DEEPSEEK_API_KEY", "")
        if not api_key:
            st.error("❌ DeepSeek API密钥未配置，请联系管理员")
            return None
            
        # DeepSeek API的URL和请求头
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建与Claude版本完全一致的Prompt
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
        }"""
        
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

        # 构建请求体
        payload = {
            "model": "deepseek-chat",  # 使用deepseek-chat模型
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": 1000,
            "temperature": 0.7,
            "response_format": {"type": "json_object"} # 请求JSON格式输出
        }

        # 发送请求
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status() # 如果请求失败则抛出异常

        # 解析返回结果
        result = response.json()
        response_text = result['choices'][0]['message']['content']
        
        # Deepseek在json_object模式下会直接返回一个可解析的JSON字符串
        parsed_result = json.loads(response_text)
        return parsed_result
            
    except requests.exceptions.RequestException as e:
        st.error(f"❌ API网络请求失败：{str(e)}")
        return None
    except json.JSONDecodeError:
        st.error("❌ API返回格式错误，无法解析JSON。")
        return None
    except Exception as e:
        st.error(f"❌ API调用出现未知问题：{str(e)}")
        return None

def convert_plotly_to_bytes(fig):
    """将Plotly图表转换为字节流用于下载 (与之前版本保持一致)"""
    try:
        img_bytes = fig.to_image(format="png", width=800, height=600, scale=2)
        return img_bytes
    except Exception as e:
        st.error(f"图片生成失败：{str(e)}")
        return None

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
    
    # 获取用户昵称
    user_name = st.text_input("👤 请输入您的昵称", placeholder="例如：小王、Alex、技术达人...")
    
    if user_name:
        st.markdown(f"### 👋 Hi {user_name}，请回答以下四个问题：")
        
        # 创建表单
        with st.form("profile_form"):
            st.markdown("#### 📝 请详细回答以下问题，这将帮助AI更准确地分析你的潜力：")
            
            # 四个维度的问题
            innovation_input = st.text_area(
                "🧠 **创新指数**：请描述一个你近期主导或参与的最有创意的项目或想法，你是如何贡献原创思路的？",
                height=120,
                placeholder="请详细描述你的创新经历..."
            )
            
            collaboration_input = st.text_area(
                "🤝 **协作潜力**：请描述一次重要的团队合作经历。你的角色是什么？你如何促进沟通和团队效率？",
                height=120,
                placeholder="请分享你的团队协作经验..."
            )
            
            leadership_input = st.text_area(
                "👑 **领导特质**：想象你领导的项目严重落后，你会采取哪三个关键步骤来扭转局面？",
                height=120,
                placeholder="请描述你的领导策略..."
            )
            
            tech_acumen_input = st.text_area(
                "⚡ **技术敏感度**：哪一项新兴 AI 技术（如：多模态、AI Agent、生成式视频）最让你感到兴奋？为什么？你认为它会如何改变你所在的行业？",
                height=120,
                placeholder="请分享你对AI技术的见解..."
            )
            
            # 提交按钮
            submitted = st.form_submit_button("🚀 开始生成我的 AI 画像", use_container_width=True)
        
        # 处理表单提交
        if submitted:
            # 验证输入
            if not all([innovation_input.strip(), collaboration_input.strip(), 
                        leadership_input.strip(), tech_acumen_input.strip()]):
                st.warning("⚠️ 请完整回答所有四个问题，这样AI才能给出更准确的分析哦！")
                return
            
            # 准备用户输入数据
            user_inputs = {
                'innovation': innovation_input,
                'collaboration': collaboration_input,
                'leadership': leadership_input,
                'tech_acumen': tech_acumen_input
            }
            
            # 显示加载状态
            with st.spinner("✨ AI 大模型(DeepSeek)正在为您深度分析，请稍候..."):
                # 【已修改】调用DeepSeek API
                analysis_result = call_deepseek_api(user_inputs, user_name)
            
            if analysis_result:
                # 显示结果
                st.markdown("---")
                st.header(f"🎉 Hey, {user_name}！这是你的 AI 潜力画像：")
                
                # 显示专属Slogan
                st.markdown(f"""
                <div class="golden-sentence">
                    ✨ {analysis_result.get('golden_sentence', '你是一位充满潜力的探索者！')} ✨
                </div>
                """, unsafe_allow_html=True)
                
                # 创建两列布局
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    # 显示雷达图
                    fig = create_radar_chart(analysis_result.get('scores', {}), user_name)
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    # 显示各维度得分
                    st.markdown("### 📊 详细得分")
                    
                    scores = analysis_result.get('scores', {})
                    st.metric("🧠 创新指数", f"{scores.get('innovation', 'N/A')}/100")
                    st.metric("🤝 协作潜力", f"{scores.get('collaboration', 'N/A')}/100") 
                    st.metric("👑 领导特质", f"{scores.get('leadership', 'N/A')}/100")
                    st.metric("⚡ 技术敏感度", f"{scores.get('tech_acumen', 'N/A')}/100")
                
                # 显示综合分析
                st.markdown(f"""
                <div class="analysis-box">
                    <h3>🔍 AI 综合分析</h3>
                    <p style="font-size: 1.1rem; line-height: 1.6;">{analysis_result.get('analysis', '分析内容生成失败，请重试。')}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # 下载功能
                st.markdown("### 📥 保存与分享")
                
                # 生成下载按钮
                img_bytes = convert_plotly_to_bytes(fig)
                if img_bytes:
                    st.download_button(
                        label="📱 下载结果图，分享你的 AI 潜力",
                        data=img_bytes,
                        file_name=f"{user_name}_AI潜力画像_DeepSeek.png",
                        mime="image/png",
                        use_container_width=True
                    )
                
                # 重新分析按钮
                if st.button("🔄 重新分析", use_container_width=True):
                    st.experimental_rerun()
                    
            else:
                st.error("😅 分析出了一点小问题，请您调整一下输入内容再试试。确保每个问题都有详细的回答哦！")

# 侧边栏信息 (与之前版本保持一致)
with st.sidebar:
    st.markdown("### 🎪 WAIC 2024")
    st.markdown("**世界人工智能大会现场专享**")
    st.markdown("---")
    st.markdown("### 💻 技术栈")
    st.markdown("- **后端:** Python, Streamlit")
    st.markdown("- **AI模型:** DeepSeek API")
    st.markdown("- **可视化:** Plotly")
    st.markdown("---")
    st.markdown("### 💡 小贴士")
    st.markdown("""
    - 回答越详细，分析越准确
    - 可以结合具体案例和数据
    - 真实回答比完美回答更有价值
    """)

if __name__ == "__main__":
    main()

