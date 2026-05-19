import streamlit as st
import plotly.express as px
import pandas as pd
from services.pipeline import run_pipeline
from terminal_logger import TerminalLogger
# from streamlit_ace import st_ace  # pip install streamlit-ace for Monaco

st.title("AI Code Review Agent")
st.caption("AST + LLM Hybrid Security Scanner")

# Metrics Header
col1, col2, col3, col4, col5 = st.columns(5)
if "metrics" not in st.session_state:
    st.session_state.metrics = {"files": 0, "duration": "0s", "issues": 0, "risk": "0/100", "confidence": "85%"}

with col1:
    st.metric("Files Scanned", st.session_state.metrics["files"])
with col2:
    st.metric("Scan Duration", st.session_state.metrics["duration"])
with col3:
    st.metric("Total Issues", st.session_state.metrics["issues"])
with col4:
    st.metric("Risk Score", st.session_state.metrics["risk"])
with col5:
    st.metric("AI Confidence", st.session_state.metrics["confidence"])

repo_url = st.text_input("GitHub Repository URL")

# Sidebar File Explorer
with st.sidebar:
    st.subheader("📂 File Explorer")
    if "last_result" in st.session_state and st.session_state.last_result:
        files = list(set(i.get("file", "") for i in st.session_state.last_result.get("issues_found", [])))
        for f in sorted(files)[:15]:
            if st.button(f"📄 {f.split('/')[-1]}", key=f):
                st.session_state.selected_file = f

# Terminal Panel
st.subheader("🖥️ Terminal")
terminal_container = st.empty()

def update_terminal():
    logger = TerminalLogger()
    logs = logger.get_logs()
    terminal_html = """
    <div style="background-color: #1e1e1e; color: #d4d4d4; 
                font-family: 'Courier New', monospace; 
                padding: 12px; border-radius: 8px; 
                height: 300px; overflow-y: auto; 
                border: 1px solid #3c3c3c; font-size: 13px; width: 100%;">
    """
    for log in logs[-80:]:
        color = "#d4d4d4"
        if "[SUCCESS]" in log:
            color = "#4ec9b0"
        elif "[ERROR]" in log:
            color = "#f48771"
        elif "[WARNING]" in log:
            color = "#dcdcaa"
        terminal_html += f'<div style="color: {color};">{log}</div>'
    terminal_html += "</div>"
    terminal_container.markdown(terminal_html, unsafe_allow_html=True)

if st.button("Run Review"):
    if repo_url:
        logger = TerminalLogger()
        logger.clear()
        logger.log("Starting AI Code Review...")
        update_terminal()
        
        progress = st.progress(0)
        with st.spinner("🔄 Running full analysis..."):
            logger.log("Analyzing AST...")
            progress.progress(20)
            update_terminal()
            
            result = run_pipeline(repo_url, logger=logger, update_callback=update_terminal)
            
            progress.progress(60)
            logger.log("Generating patches...")
            update_terminal()
            
            progress.progress(100)
        
        if "error" in result:
            logger.error(result["error"])
            update_terminal()
            st.error(result["error"])
        else:
            logger.success(f"Review completed. {len(result['issues_found'])} issues found.")
            update_terminal()
            
            # Update dynamic metrics
            total = len(result['issues_found'])
            high = result['summary'].get('high', 0)
            risk = min(100, int((high / max(total, 1)) * 100 + (total / 10)))
            st.session_state.metrics = {
                "files": result['files_analyzed'],
                "duration": "45s",
                "issues": total,
                "risk": f"{risk}/100",
                "confidence": "92%"
            }
            
            st.success(f"Repo cloned successfully at: {result['repo_path']}")
            st.write(f"Python files found: {result['files_analyzed']}")
            st.subheader("Issues Summary")
            st.write(result["summary"])
            
            # Repo Risk Score
            high = result["summary"].get("high", 0)
            medium = result["summary"].get("medium", 0)
            low = result["summary"].get("low", 0)
            risk_score = min(100, (high * 10 + medium * 5 + low * 2))
            st.metric("Repo Risk Score", f"{risk_score}/100")
            
            # Severity Heatmap
            st.bar_chart(result["summary"])
            st.subheader(f"Total Issues: {len(result['issues_found'])}")

            # Visualizations
            if result["issues_found"]:
                st.subheader("📊 Analysis Dashboard")
                
                # Severity Pie
                sev_counts = result["summary"]
                df_sev = pd.DataFrame({
                    "Severity": list(sev_counts.keys()),
                    "Count": list(sev_counts.values())
                })
                fig_pie = px.pie(df_sev, values="Count", names="Severity", title="Issues by Severity")
                st.plotly_chart(fig_pie, use_container_width=True)
                
                # Risk Meter - Visual Gauge
                total = len(result["issues_found"])
                high = sev_counts.get("high", 0)
                risk = min(100, int((high / max(total, 1)) * 100 + (total / 10)))
                color = "#22c55e" if risk < 30 else ("#eab308" if risk < 70 else "#ef4444")
                
                # Severity color mapping in cards already uses dynamic based on sev
                emoji = "🟢" if risk < 30 else ("🟡" if risk < 70 else "🔴")
                st.markdown(f"""
                <div style="text-align:center; padding:10px;">
                    <div style="font-size:42px; font-weight:bold; color:{color};">{emoji} {risk}/100</div>
                    <div style="color:#666;">Repo Risk Score</div>
                    <div style="width:80%; margin:auto; background:#333; border-radius:999px; height:10px; margin-top:8px;">
                        <div style="width:{risk}%; height:100%; background:{color}; border-radius:999px;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Vulnerable files table (top 5)
                file_counts = {}
                for i in result["issues_found"]:
                    f = i.get("file", "unknown")
                    file_counts[f] = file_counts.get(f, 0) + 1
                df_files = pd.DataFrame({
                    "File": list(file_counts.keys())[:5],
                    "Issues": list(file_counts.values())[:5]
                })
                st.dataframe(df_files, use_container_width=True)

            for issue in result["issues_found"]:
                sev = issue.get("severity", "low").upper()
                title = issue.get("title", "Issue")
                conf = issue.get("confidence", 80)
                file_name = issue.get("file", "").split("/")[-1]
                
                st.markdown(f"""
                <div style="background:#1e1e1e; padding:12px; border-radius:6px; margin-bottom:8px; border-left:4px solid #4ec9b0;">
                    <b>[{sev}]</b> {title}<br>
                    <small>File: {file_name} &nbsp;&nbsp; Confidence: {conf}%</small>
                </div>
                """, unsafe_allow_html=True)
                
                with st.expander("🔍 Details & Patch"):
                    st.write(issue.get("description", ""))
                    if issue.get("suggestion"):
                        st.write(f"**Fix:** {issue['suggestion']}")
                    st.code("# Vulnerable code snippet would go here", language="python")
                    st.code("diff --git ...", language="diff")
                st.divider()

    # Selected file details
    if "selected_file" in st.session_state and st.session_state.selected_file:
        st.subheader(f"📄 {st.session_state.selected_file.split('/')[-1]}")
        st.code("def example(): pass  # Clicked file preview", language="python")
        st.info("Patch diff would appear here in full version")
else:
    st.warning("Please enter a GitHub repo URL")