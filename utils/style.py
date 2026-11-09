import streamlit as st


def apply_custom_css():
    """
    Applies high-end 3D styling across the application.
    Features:
    - 3D layered elevation and perspective
    - Glassmorphism with deep ambient shadows
    - Embossed 3D button and card borders
    - Smooth interactive transitions
    - Strict zero-icon / zero-emoji clean professional typography
    """
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap');

        :root {
            --bg-base: #090d16;
            --bg-surface: #111827;
            --bg-card: rgba(17, 24, 39, 0.78);
            --border-3d-top: rgba(255, 255, 255, 0.18);
            --border-3d-bottom: rgba(0, 0, 0, 0.6);
            --accent-primary: #3b82f6;
            --accent-secondary: #6366f1;
            --accent-cyan: #06b6d4;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --glow-3d: 0 16px 36px -10px rgba(0, 0, 0, 0.8), 0 0 24px rgba(59, 130, 246, 0.18);
        }

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            color: var(--text-main);
        }

        /* 3D App Background Canvas */
        .stApp {
            background:
                radial-gradient(circle at 18% 12%, rgba(59, 130, 246, 0.15) 0%, transparent 40%),
                radial-gradient(circle at 82% 88%, rgba(99, 102, 241, 0.18) 0%, transparent 45%),
                radial-gradient(circle at 50% 50%, rgba(6, 182, 212, 0.08) 0%, transparent 60%),
                linear-gradient(180deg, #070a12 0%, #0d1322 50%, #080c16 100%);
            background-attachment: fixed;
            color: var(--text-main);
        }

        /* Main Container */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3.5rem;
            max-width: 1360px;
            perspective: 1200px;
        }

        /* Headings with 3D Emboss */
        h1, h2, h3, h4 {
            font-family: 'Space Grotesk', sans-serif !important;
            letter-spacing: -0.02em;
            text-shadow: 0 3px 8px rgba(0, 0, 0, 0.7);
        }

        h1 {
            color: #ffffff !important;
            font-size: 2.3rem !important;
            font-weight: 700 !important;
            border-left: 4px solid var(--accent-primary);
            padding-left: 14px;
        }

        h2 {
            color: #e2e8f0 !important;
            font-weight: 600 !important;
            margin-top: 1.5rem !important;
        }

        h3 {
            color: #cbd5e1 !important;
            font-weight: 600 !important;
        }

        /* 3D Isometric Sidebar */
        [data-testid="stSidebar"] {
            background: linear-gradient(195deg, #090e1a 0%, #0f172a 60%, #060912 100%) !important;
            border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
            box-shadow: 12px 0 30px rgba(0, 0, 0, 0.6) !important;
        }

        [data-testid="stSidebar"] * {
            color: #e2e8f0 !important;
        }

        /* 3D Elevated Metric Cards */
        [data-testid="stMetric"] {
            background: var(--bg-card) !important;
            backdrop-filter: blur(14px) !important;
            -webkit-backdrop-filter: blur(14px) !important;
            border-top: 1px solid var(--border-3d-top) !important;
            border-left: 1px solid var(--border-3d-top) !important;
            border-bottom: 2px solid var(--border-3d-bottom) !important;
            border-right: 2px solid var(--border-3d-bottom) !important;
            border-radius: 14px !important;
            padding: 20px 22px !important;
            box-shadow:
                0 18px 36px -12px rgba(0, 0, 0, 0.85),
                0 4px 12px rgba(0, 0, 0, 0.5),
                inset 0 1px 0 rgba(255, 255, 255, 0.15) !important;
            transform: translateZ(10px);
            transition: all 0.28s cubic-bezier(0.2, 0.8, 0.2, 1) !important;
        }

        [data-testid="stMetric"]:hover {
            transform: translateY(-4px) scale(1.015) !important;
            box-shadow:
                0 24px 44px -10px rgba(0, 0, 0, 0.9),
                0 0 24px rgba(59, 130, 246, 0.25),
                inset 0 1px 0 rgba(255, 255, 255, 0.25) !important;
        }

        [data-testid="stMetricLabel"] {
            color: var(--text-muted) !important;
            font-size: 0.84rem !important;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-weight: 600;
        }

        [data-testid="stMetricValue"] {
            color: #60a5fa !important;
            font-family: 'Space Grotesk', sans-serif !important;
            font-weight: 700 !important;
            font-size: 2rem !important;
            text-shadow: 0 4px 12px rgba(96, 165, 250, 0.35);
        }

        /* 3D Pushable Buttons */
        .stButton > button,
        .stDownloadButton > button {
            background: linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%) !important;
            color: #ffffff !important;
            font-family: 'Space Grotesk', sans-serif !important;
            font-weight: 600 !important;
            font-size: 0.95rem !important;
            letter-spacing: 0.03em;
            border-top: 1px solid rgba(255, 255, 255, 0.3) !important;
            border-left: 1px solid rgba(255, 255, 255, 0.2) !important;
            border-right: 1px solid rgba(0, 0, 0, 0.4) !important;
            border-bottom: 3px solid #111827 !important;
            border-radius: 10px !important;
            padding: 10px 22px !important;
            box-shadow:
                0 10px 22px -6px rgba(29, 78, 216, 0.6),
                0 4px 8px rgba(0, 0, 0, 0.4),
                inset 0 1px 0 rgba(255, 255, 255, 0.3) !important;
            transition: all 0.16s ease-in-out !important;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow:
                0 14px 28px -4px rgba(37, 99, 235, 0.75),
                0 6px 12px rgba(0, 0, 0, 0.5),
                inset 0 1px 0 rgba(255, 255, 255, 0.4) !important;
            color: #ffffff !important;
        }

        .stButton > button:active,
        .stDownloadButton > button:active {
            transform: translateY(2px) !important;
            border-bottom: 1px solid #111827 !important;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.5) !important;
        }

        /* 3D Input Fields */
        .stTextInput input,
        .stNumberInput input,
        .stSelectbox div[data-baseweb="select"] {
            background-color: rgba(15, 23, 42, 0.85) !important;
            color: #f1f5f9 !important;
            border-top: 1px solid rgba(0, 0, 0, 0.6) !important;
            border-left: 1px solid rgba(0, 0, 0, 0.5) !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.12) !important;
            border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 9px !important;
            box-shadow: inset 0 2px 6px rgba(0, 0, 0, 0.6) !important;
        }

        /* 3D Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            background: rgba(15, 23, 42, 0.6);
            padding: 6px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.07);
        }

        .stTabs [data-baseweb="tab"] {
            background: transparent !important;
            border-radius: 8px !important;
            padding: 9px 18px !important;
            font-weight: 500 !important;
            color: #94a3b8 !important;
            border: none !important;
            transition: all 0.2s ease !important;
        }

        .stTabs [aria-selected="true"] {
            background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%) !important;
            color: #ffffff !important;
            border-top: 1px solid rgba(255, 255, 255, 0.2) !important;
            border-bottom: 2px solid #0284c7 !important;
            box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4) !important;
        }

        /* DataTables */
        [data-testid="stDataFrame"] {
            background: rgba(15, 23, 42, 0.75) !important;
            border-radius: 12px !important;
            border: 1px solid rgba(255, 255, 255, 0.09) !important;
            box-shadow: 0 16px 32px -10px rgba(0, 0, 0, 0.75) !important;
            overflow: hidden !important;
        }

        /* Custom 3D Card Class */
        .card-3d {
            background: linear-gradient(145deg, rgba(30, 41, 59, 0.65), rgba(15, 23, 42, 0.85));
            border-top: 1px solid rgba(255, 255, 255, 0.16);
            border-left: 1px solid rgba(255, 255, 255, 0.12);
            border-right: 2px solid rgba(0, 0, 0, 0.5);
            border-bottom: 3px solid rgba(0, 0, 0, 0.7);
            border-radius: 14px;
            padding: 22px 24px;
            margin-bottom: 18px;
            box-shadow: 0 16px 36px -10px rgba(0, 0, 0, 0.85);
            transition: all 0.24s ease;
        }

        .card-3d:hover {
            transform: translateY(-3px);
            box-shadow: 0 22px 42px -8px rgba(0, 0, 0, 0.9), 0 0 18px rgba(59, 130, 246, 0.2);
        }

        /* Dividers */
        hr {
            border-color: rgba(255, 255, 255, 0.08) !important;
            margin: 1.8rem 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def add_sidebar_branding():
    """
    Renders clean, high-tech sidebar navigation branding without icons or emojis.
    """
    with st.sidebar:
        st.markdown(
            """
            <div style="padding: 12px 4px 6px 4px; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 14px;">
                <div style="font-family: 'Space Grotesk', sans-serif; font-size: 1.25rem; font-weight: 700; letter-spacing: -0.01em; color: #ffffff;">
                    STUDENT PERFORMANCE SYSTEM
                </div>
                <div style="font-size: 0.76rem; letter-spacing: 0.12em; text-transform: uppercase; color: #94a3b8; margin-top: 4px;">
                    Academic Intelligence Engine
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("Version 3.0 | 3D Analytics Suite")
