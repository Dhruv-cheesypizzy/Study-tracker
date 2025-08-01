import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import os

# Page config
st.set_page_config(
    page_title="Study Tracker",
    page_icon="📚",
    layout="wide"
)

# Database setup
def init_database():
    """Initialize the SQLite database"""
    conn = sqlite3.connect('study_data.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS study_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            hours REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def add_study_session(study_date, hours):
    """Add a new study session to the database"""
    conn = sqlite3.connect('study_data.db')
    cursor = conn.cursor()
    
    # Check if entry for this date already exists
    cursor.execute('SELECT id, hours FROM study_sessions WHERE date = ?', (study_date,))
    existing = cursor.fetchone()
    
    if existing:
        # Update existing entry
        cursor.execute('UPDATE study_sessions SET hours = ? WHERE date = ?', (hours, study_date))
        conn.commit()
        conn.close()
        return "updated"
    else:
        # Insert new entry
        cursor.execute('INSERT INTO study_sessions (date, hours) VALUES (?, ?)', (study_date, hours))
        conn.commit()
        conn.close()
        return "added"

def get_study_data():
    """Retrieve all study data from database"""
    conn = sqlite3.connect('study_data.db')
    df = pd.read_sql_query('SELECT date, hours FROM study_sessions ORDER BY date', conn)
    conn.close()
    
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
    
    return df

def delete_study_session(study_date):
    """Delete a study session from the database"""
    conn = sqlite3.connect('study_data.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM study_sessions WHERE date = ?', (study_date,))
    conn.commit()
    conn.close()

# Initialize database
init_database()

# Authentication
ADMIN_PASSWORD = "study2025"  # Change this to your preferred password

def check_admin_access():
    """Check if user has admin access"""
    if 'admin_mode' not in st.session_state:
        st.session_state.admin_mode = False
    return st.session_state.admin_mode

def show_login():
    """Show login form for admin access"""
    st.sidebar.header("🔐 Admin Access")
    password = st.sidebar.text_input("Enter admin password:", type="password")
    
    if st.sidebar.button("Login"):
        if password == ADMIN_PASSWORD:
            st.session_state.admin_mode = True
            st.sidebar.success("✅ Admin access granted!")
            st.rerun()
        else:
            st.sidebar.error("❌ Incorrect password")
    
    st.sidebar.info("👀 You're in **VIEW-ONLY** mode")
    st.sidebar.markdown("Enter admin password to add/edit data")

# Main app
st.title("📚 Study Tracker")
st.markdown("Track your daily study hours and visualize your progress!")

# Check admin access
is_admin = check_admin_access()

# Sidebar for input (only for admin)
if is_admin:
    with st.sidebar:
        st.header("📝 Log Study Session")
        st.success("🔓 Admin Mode Active")
        
        if st.button("🚪 Logout", type="secondary"):
            st.session_state.admin_mode = False
            st.rerun()
        
        st.divider()
else:
    show_login()

# Admin-only input section
if is_admin:
    with st.sidebar:
        # Date input
        study_date = st.date_input(
            "Date",
            value=date.today(),
            max_value=date.today()
        )
        
        # Hours input
        hours_studied = st.number_input(
            "Hours Studied",
            min_value=0.0,
            max_value=24.0,
            value=0.0,
            step=0.5,
            format="%.1f"
        )
        
        # Submit button
        if st.button("💾 Save Study Session", type="primary"):
            if hours_studied > 0:
                result = add_study_session(str(study_date), hours_studied)
                if result == "added":
                    st.success(f"✅ Added {hours_studied} hours for {study_date}")
                else:
                    st.success(f"✅ Updated {study_date} to {hours_studied} hours")
                st.rerun()
            else:
                st.error("⚠️ Please enter hours greater than 0")
        
        st.divider()
        
        # Delete section
        st.header("🗑️ Delete Entry")
        delete_date = st.date_input("Select date to delete", key="delete_date")
        if st.button("🗑️ Delete Entry", type="secondary"):
            delete_study_session(str(delete_date))
            st.success(f"✅ Deleted entry for {delete_date}")
            st.rerun()

# Main content area
col1, col2 = st.columns([1, 2])

with col1:
    st.header("📊 Statistics")
    
    # Get data
    df = get_study_data()
    
    if not df.empty:
        total_hours = df['hours'].sum()
        avg_hours = df['hours'].mean()
        total_days = len(df)
        max_hours = df['hours'].max()
        
        # Display metrics
        st.metric("Total Hours Studied", f"{total_hours:.1f} hrs")
        st.metric("Average Hours/Day", f"{avg_hours:.1f} hrs")
        st.metric("Total Study Days", f"{total_days} days")
        st.metric("Best Day", f"{max_hours:.1f} hrs")
        
        # Recent sessions
        st.subheader("📅 Recent Sessions")
        recent_df = df.tail(10).sort_values('date', ascending=False)
        for _, row in recent_df.iterrows():
            st.write(f"**{row['date'].strftime('%Y-%m-%d')}**: {row['hours']:.1f} hours")
    else:
        st.info("🎯 Start tracking your study sessions!")
        st.write("Add your first study session using the form on the left.")

with col2:
    st.header("📈 Progress Chart")
    
    if not df.empty:
        # Create line chart
        fig = px.line(
            df, 
            x='date', 
            y='hours',
            title='Daily Study Hours Over Time',
            labels={'date': 'Date', 'hours': 'Hours Studied'},
            markers=True,
            line_shape='linear'
        )
        
        # Customize the chart
        fig.update_traces(
            line=dict(color='#1f77b4', width=3),
            marker=dict(size=8, color='#ff7f0e')
        )
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(size=12),
            title_font_size=16,
            xaxis=dict(showgrid=True, gridcolor='lightgray'),
            yaxis=dict(showgrid=True, gridcolor='lightgray'),
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Additional charts
        if len(df) > 7:
            st.subheader("📊 Weekly Average")
            
            # Calculate 7-day rolling average
            df_sorted = df.sort_values('date')
            df_sorted['rolling_avg'] = df_sorted['hours'].rolling(window=7, min_periods=1).mean()
            
            fig2 = px.line(
                df_sorted,
                x='date',
                y='rolling_avg',
                title='7-Day Rolling Average',
                labels={'date': 'Date', 'rolling_avg': 'Average Hours'},
                line_shape='spline'
            )
            
            fig2.update_traces(line=dict(color='green', width=2))
            fig2.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(size=12),
                title_font_size=14
            )
            
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("📊 Your study progress chart will appear here once you log some sessions!")

# Footer
st.divider()
st.markdown("---")
st.markdown("**💡 Tips:**")
st.markdown("- Log your study sessions daily for best tracking")
st.markdown("- You can update existing entries by selecting the same date")
st.markdown("- Use the delete function to remove incorrect entries")
st.markdown("- Track consistently to see meaningful progress patterns!")
