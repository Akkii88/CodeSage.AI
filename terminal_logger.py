import time
import streamlit as st
from datetime import datetime

class TerminalLogger:
    def __init__(self):
        if "terminal_logs" not in st.session_state:
            st.session_state.terminal_logs = []
    
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        st.session_state.terminal_logs.append(log_entry)
    
    def clear(self):
        st.session_state.terminal_logs = []
    
    def get_logs(self):
        return st.session_state.terminal_logs
    
    def success(self, message):
        self.log(message, "SUCCESS")
    
    def warning(self, message):
        self.log(message, "WARNING")
    
    def error(self, message):
        self.log(message, "ERROR")