MAIN_CSS = """
<style>
/* 脱离系统/浏览器深色模式与 Streamlit 暗色主题，统一浅色渲染 */
html {
    color-scheme: light !important;
}
.stApp {
    color-scheme: light !important;
    --text-color: #111827 !important;
    --background-color: #ffffff !important;
    --secondary-background-color: #f8fafc !important;
}
/* 保留您原版优秀的沉浸式 UI 设定 */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMainBlockContainer"] {
    background: #ffffff !important;
}
section[data-testid="stSidebar"] {
    background: #f8fafc !important;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] h4,
section[data-testid="stSidebar"] h5,
section[data-testid="stSidebar"] h6,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"],
section[data-testid="stSidebar"] div[data-testid="stCaptionContainer"] {
    color: #111827 !important;
}
section[data-testid="stSidebar"] [data-baseweb="input"] input {
    background: #eef2f7 !important;
    color: #111827 !important;
}
section[data-testid="stSidebar"] [data-baseweb="base-input"] {
    background: #eef2f7 !important;
    border-color: #d1d5db !important;
}
section[data-testid="stSidebar"] [data-baseweb="input"] input::placeholder {
    color: #6b7280 !important;
    opacity: 1 !important;
}
/* Disabled text_input（API Base URL 只读）：暗色主题下否则会透明/看不见 */
section[data-testid="stSidebar"] [data-baseweb="input"] input:disabled,
section[data-testid="stSidebar"] [data-baseweb="input"] input[disabled] {
    background: #eef2f7 !important;
    color: #111827 !important;
    -webkit-text-fill-color: #111827 !important;
    opacity: 1 !important;
    caret-color: #111827 !important;
}
section[data-testid="stSidebar"] [data-baseweb="input"]:has(input:disabled),
section[data-testid="stSidebar"] [data-baseweb="input"]:has(input[disabled]) {
    background: #eef2f7 !important;
    border-color: #d1d5db !important;
}
section[data-testid="stSidebar"] [data-baseweb="input"] button,
section[data-testid="stSidebar"] [data-baseweb="input"] button svg,
section[data-testid="stSidebar"] [data-baseweb="input"] button path {
    color: #111827 !important;
    fill: #111827 !important;
    stroke: #111827 !important;
}
section[data-testid="stSidebar"] [data-baseweb="input"] button:hover,
section[data-testid="stSidebar"] [data-baseweb="input"] button:hover svg,
section[data-testid="stSidebar"] [data-baseweb="input"] button:hover path {
    color: #111827 !important;
    fill: #111827 !important;
    stroke: #111827 !important;
}
section[data-testid="stSidebar"] div[data-testid="stButton"] button {
    background: #ff4b4b !important;
    color: #ffffff !important;
    border: 1px solid #ff4b4b !important;
    font-weight: 700 !important;
}
section[data-testid="stSidebar"] div[data-testid="stButton"] button *,
section[data-testid="stSidebar"] div[data-testid="stButton"] button span,
section[data-testid="stSidebar"] div[data-testid="stButton"] button p {
    color: #ffffff !important;
}
section[data-testid="stSidebar"] div[data-testid="stButton"] button:hover {
    background: #ff2b2b !important;
    color: #ffffff !important;
    border: 1px solid #ff2b2b !important;
}
section[data-testid="stSidebar"] div[data-testid="stButton"] button:hover *,
section[data-testid="stSidebar"] div[data-testid="stButton"] button:hover span,
section[data-testid="stSidebar"] div[data-testid="stButton"] button:hover p {
    color: #ffffff !important;
}
/* Sidebar reboot button: keep inside sidebar, stick near bottom */
section[data-testid="stSidebar"] div[data-testid="stButton"] {
    position: sticky !important;
    bottom: 14px !important;
    z-index: 20 !important;
}
section[data-testid="stSidebar"] div[data-testid="stButton"] > button {
    width: 100% !important;
}
.stApp header { background: transparent !important; }
/* Main content text: enforce readable dark tone (incl. AC-OS about page) */
.main .block-container h1,
.main .block-container h2,
.main .block-container h3,
.main .block-container h4,
.main .block-container h5,
.main .block-container h6,
.main .block-container p,
.main .block-container li,
.main .block-container label,
.main .block-container span,
.main .block-container div[data-testid="stMarkdownContainer"],
.main .block-container div[data-testid="stCaptionContainer"] {
    color: #111827 !important;
}
header [data-testid="stDeployButton"] button,
header [data-testid="stDeployButton"] button span,
header [data-testid="stToolbar"] button,
header [data-testid="stToolbar"] button span {
    color: #111827 !important;
}
.main .block-container,
[data-testid="stMainBlockContainer"] {
    overflow: visible !important;
    padding-top: 1rem !important;
    padding-bottom: 3rem !important; /* 留出底部输入框空间（原值一半） */
    padding-left: 2.5rem !important;
    padding-right: 2.5rem !important;
}
@media (max-width: 1200px) {
    .main .block-container,
    [data-testid="stMainBlockContainer"] {
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
}
:root {
    --acos-content-pad: 2.5rem;
    /* Align dashboard metrics with chat body / input (Streamlit default body ≈ 1rem) */
    --acos-chat-font-size: 1rem;
}
@media (max-width: 1200px) {
    :root { --acos-content-pad: 0.5rem; }
}
[data-testid="stVerticalBlock"] { overflow: visible !important; }
[data-testid="stColumn"] { overflow: visible !important; }
/* Dashboard metrics: same size as chat message / input text */
.main .block-container [data-testid="stMetricValue"] {
    font-size: var(--acos-chat-font-size) !important;
}
/* 为终端输出增加极客感 */
.os-log-box {
    background-color: #1e1e1e;
    color: #00ff00;
    font-family: 'Courier New', Courier, monospace;
    padding: 10px;
    border-radius: 5px;
    margin-bottom: 10px;
}
/* 右上角链接灰色风格 */
.ac-os-link a {
    color: #9aa0a6 !important;
    text-decoration: none !important;
    font-weight: 500 !important;
    display: inline-flex !important;
    align-items: center !important;
    gap: 0.35rem !important;
}
.ac-os-link a:hover {
    color: #b0b6bc !important;
    text-decoration: none !important;
}
.ac-os-link a:visited,
.ac-os-link a:active {
    color: #9aa0a6 !important;
}
.ac-os-link .ac-os-icon {
    opacity: 0.9;
    font-size: 0.9rem;
}
/* Chat 区域文本和链接颜色兜底（避免被主题渲染为白色） */
[data-testid="stChatMessageContent"],
[data-testid="stChatMessageContent"] p,
[data-testid="stChatMessageContent"] div,
[data-testid="stChatMessageContent"] span,
[data-testid="stChatMessageContent"] li {
    color: #111827 !important;
    font-size: var(--acos-chat-font-size) !important;
}
[data-testid="stChatMessageContent"] a,
.main .block-container a {
    color: #2563eb !important;
}
[data-testid="stChatMessageContent"] a:hover,
.main .block-container a:hover {
    color: #1d4ed8 !important;
}
/* Chat 气泡背景改为极淡灰，去除默认偏深灰底 */
[data-testid="stChatMessage"] {
    background: #fafafa !important;
    border: 1px solid #f3f4f6 !important;
    border-radius: 0.65rem !important;
}
/* Execution Audit Log uses native st.dataframe; avoid overriding Glide internals. */
/* 固定顶栏（保证 title + tabs + link 始终在顶部） */
.os-topbar {
    position: sticky;
    top: 0;
    z-index: 1100;
    padding: 0.6rem 0 4px 0;
    background: #ffffff;
    border-bottom: none;
}
.os-topbar-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.8rem;
}
.os-topbar-title {
    font-size: 24px !important;
    font-weight: 700;
    color: #111827;
    margin: 0;
    line-height: 1.15;
}
/* 压缩 tabs 默认顶部空隙 */
div[data-testid="stTabs"] {
    margin-top: 0 !important;
    padding-top: 0 !important;
}
div[data-testid="stTabs"] > div[data-baseweb="tabs"] {
    margin-top: 0 !important;
    padding-top: 0 !important;
    min-height: 60px !important;
}
div[data-testid="stTabs"] > div[data-baseweb="tabs"] > div:first-child {
    min-height: 60px !important;
    height: 60px !important;
    align-items: center !important;
}
div[data-testid="stTabs"] button[role="tab"] {
    height: 60px !important;
    min-height: 60px !important;
    line-height: 60px !important;
    color: #6b7280 !important;
    font-weight: 600 !important;
}
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    color: #111827 !important;
    font-weight: 800 !important;
}
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] p {
    color: #111827 !important;
    font-weight: 800 !important;
}
/* 输入框固定在页面底部（仅 I/O 终端 tab 需要；见下方「Telemetry」时隐藏） */
div[data-testid="stChatInput"] {
    position: fixed !important;
    left: 1rem !important;
    right: 1.5rem !important;
    bottom: 14px !important;
    width: auto !important;
    max-width: 960px !important;
    margin-left: auto !important;
    margin-right: auto !important;
    z-index: 1000 !important;
}
/* 选中第二个 tab（System Telemetry）时隐藏底部 chat：固定层否则会盖住审计表 */
body:has(div[data-testid="stTabs"] [role="tab"][aria-selected="true"]:last-of-type:not(:first-of-type)) div[data-testid="stChatInput"] {
    display: none !important;
}
div[data-testid="stChatInput"] > div {
    background: #ffffff !important;
    border: 1px solid #d0d7de !important;
    border-radius: 0.75rem !important;
    overflow: hidden !important;
}
div[data-testid="stChatInput"] textarea,
div[data-testid="stChatInput"] input {
    background: #ffffff !important;
    color: #111827 !important;
    font-size: var(--acos-chat-font-size) !important;
}
div[data-testid="stChatInput"] textarea::placeholder,
div[data-testid="stChatInput"] input::placeholder {
    color: #6b7280 !important;
    opacity: 1 !important;
}
div[data-testid="stChatInput"] button {
    background: #ffffff !important;
    color: #111827 !important;
    border: none !important;
    border-left: 1px solid #d0d7de !important;
    border-radius: 0 !important;
    box-shadow: none !important;
}
/* 侧边栏展开时，输入框向右避让 */
body:has(section[data-testid="stSidebar"][aria-expanded="true"]) div[data-testid="stChatInput"] {
    left: calc(21rem + 1rem) !important;
    right: 1.5rem !important;
}
/* Dashboard 吸附顶部 */
/* 通过锚点把右侧 dashboard 容器吸附在 title/tab 下方 */
div[data-testid="stVerticalBlock"]:has(#dashboard-sticky-anchor) {
    position: sticky !important;
    top: 6.2rem !important;
    z-index: 1000 !important;
}
div[data-testid="stVerticalBlock"]:has(#dashboard-sticky-anchor) h3,
div[data-testid="stVerticalBlock"]:has(#dashboard-sticky-anchor) [data-testid="stMetricLabel"] p {
    color: #374151 !important;
    font-weight: 600 !important;
    font-size: var(--acos-chat-font-size) !important;
}
div[data-testid="stVerticalBlock"]:has(#dashboard-sticky-anchor) [data-testid="stMetricValue"] {
    color: #111827 !important;
    font-weight: 700 !important;
    font-size: var(--acos-chat-font-size) !important;
}
div[data-testid="stVerticalBlock"]:has(#dashboard-sticky-anchor) [data-testid="stCaptionContainer"] {
    color: #4b5563 !important;
}
div[data-testid="stVerticalBlock"]:has(#dashboard-sticky-anchor) .stMarkdown,
div[data-testid="stVerticalBlock"]:has(#dashboard-sticky-anchor) .stMarkdown p,
div[data-testid="stVerticalBlock"]:has(#dashboard-sticky-anchor) .stMarkdown span,
div[data-testid="stVerticalBlock"]:has(#dashboard-sticky-anchor) [data-testid="stCaptionContainer"] p {
    color: #111827 !important;
}
</style>
"""

ABOUT_PAGE_CSS = """
<style>
/* About page dedicated contrast fallback */
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] {
    background: #ffffff !important;
}
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] h1,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] h2,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] h3,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] h4,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] p,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] li,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] span,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] div {
    color: #111827 !important;
}
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] a {
    color: #2563eb !important;
}
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] a:hover {
    color: #1d4ed8 !important;
}
</style>
"""

TOPBAR_HTML = """
<div class="os-topbar">
  <div class="os-topbar-row">
    <p class="os-topbar-title">Aegis Cortex OS</p>
    <div class="ac-os-link"><a href="?view=about"><span class="ac-os-icon">◉</span><span>AC-OS</span></a></div>
  </div>
</div>
"""
