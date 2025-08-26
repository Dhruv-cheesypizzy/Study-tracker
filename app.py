import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
try:
    from streamlit_gsheets import GSheetsConnection
    GSHEETS_AVAILABLE = True
except ImportError:
    GSHEETS_AVAILABLE = False

# Page config
st.set_page_config(
    page_title="Study Tracker",
    page_icon="📚",
    layout="wide"
)

# Initialize session state for fallback storage
if 'study_data' not in st.session_state:
    st.session_state.study_data = pd.DataFrame(columns=['date', 'hours'])

# Initialize Google Sheets connection if available
@st.cache_resource
def init_connection():
    if GSHEETS_AVAILABLE:
        try:
            return st.connection("gsheets", type=GSheetsConnection)
        except Exception as e:
            st.warning(f"Google Sheets connection failed: {str(e)}")
            return None
    return None

def get_study_data(force_refresh=False):
    """Retrieve study data from Google Sheets or session state fallback"""
    conn = init_connection()
    
    # Try Google Sheets first
    if conn is not None:
        try:
            # Use ttl=0 for no caching when force_refresh is True
            cache_time = 0 if force_refresh else 1  # Very short cache
            
            # Try different possible sheet names
            sheet_names = ["sheet1", "Sheet1", "Sheet 1", 0]
            df = None
            
            for sheet_name in sheet_names:
                try:
                    df = conn.read(worksheet=sheet_name, usecols=[0, 1], ttl=cache_time)
                    break
                except Exception:
                    continue
            
            if df is None:
                raise Exception("Could not find a valid worksheet")
            
            # Clean the dataframe
            if not df.empty:
                # Remove any completely empty rows
                df = df.dropna(how='all')
                # Ensure we have the right columns
                if len(df.columns) >= 2:
                    df.columns = ['date', 'hours']
                    # Remove header row if it exists
                    df = df[df['date'].astype(str).str.lower() != 'date']
                    # Convert types
                    df['hours'] = pd.to_numeric(df['hours'], errors='coerce')
                    df = df.dropna()
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.sort_values('date')
                else:
                    df = pd.DataFrame(columns=['date', 'hours'])
            else:
                df = pd.DataFrame(columns=['date', 'hours'])
                
            return df
        except Exception as e:
            st.warning(f"Using local storage - Google Sheets error: {str(e)}")
    
    # Fallback to session state
    return st.session_state.study_data.copy()

def add_study_session(study_date, hours):
    """Add or update a study session"""
    try:
        conn = init_connection()
        
        # Convert study_date to datetime
        if isinstance(study_date, str):
            study_datetime = pd.to_datetime(study_date)
        else:
            study_datetime = pd.to_datetime(str(study_date))
        
        # Try Google Sheets first
        if conn is not None:
            try:
                # Get existing data (force refresh to get latest)
                df = get_study_data(force_refresh=True)
                
                # Check if entry exists
                date_str = study_datetime.strftime('%Y-%m-%d')
                existing_entry = False
                
                if not df.empty:
                    df['date'] = pd.to_datetime(df['date'])
                    existing_entry = any(df['date'].dt.strftime('%Y-%m-%d') == date_str)
                
                if existing_entry:
                    # Update existing entry
                    df.loc[df['date'].dt.strftime('%Y-%m-%d') == date_str, 'hours'] = hours
                    result = "updated"
                else:
                    # Add new entry
                    new_row = pd.DataFrame({'date': [study_datetime], 'hours': [hours]})
                    if df.empty:
                        df = new_row
                    else:
                        df = pd.concat([df, new_row], ignore_index=True)
                    result = "added"
                
                # Sort by date
                df = df.sort_values('date')
                
                # Prepare data for sheets (convert date to string)
                df_to_write = df.copy()
                df_to_write['date'] = df_to_write['date'].dt.strftime('%Y-%m-%d')
                
                # Try different sheet names for writing
                sheet_names = ["sheet1", "Sheet1", "Sheet 1", 0]
                write_success = False
                
                for sheet_name in sheet_names:
                    try:
                        conn.update(worksheet=sheet_name, data=df_to_write)
                        write_success = True
                        break
                    except Exception:
                        continue
                
                if not write_success:
                    raise Exception("Could not write to any worksheet")
                
                # Clear any cached data to force refresh on next read
                st.cache_data.clear()
                
                return result
                
            except Exception as e:
                st.warning(f"Google Sheets failed, using local storage: {str(e)}")
        
        # Fallback to session state
        df = st.session_state.study_data.copy()
        date_str = study_datetime.strftime('%Y-%m-%d')
        
        # Check if entry exists
        existing_entry = False
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            existing_entry = any(df['date'].dt.strftime('%Y-%m-%d') == date_str)
        
        if existing_entry:
            # Update existing entry
            df.loc[df['date'].dt.strftime('%Y-%m-%d') == date_str, 'hours'] = hours
            result = "updated"
        else:
            # Add new entry
            new_row = pd.DataFrame({'date': [study_datetime], 'hours': [hours]})
            if df.empty:
                df = new_row
            else:
                df = pd.concat([df, new_row], ignore_index=True)
            result = "added"
        
        # Sort by date and update session state
        df = df.sort_values('date')
        st.session_state.study_data = df
        
        return result
        
    except Exception as e:
        st.error(f"Error adding study session: {str(e)}")
        return "error"

def delete_study_session(study_date):
    """Delete a study session"""
    try:
        conn = init_connection()
        
        # Convert study_date to datetime
        if isinstance(study_date, str):
            study_datetime = pd.to_datetime(study_date)
        else:
            study_datetime = pd.to_datetime(str(study_date))
        
        date_str = study_datetime.strftime('%Y-%m-%d')
        
        # Try Google Sheets first
        if conn is not None:
            try:
                # Get existing data (force refresh)
                df = get_study_data(force_refresh=True)
                
                if not df.empty:
                    # Remove the entry
                    df['date'] = pd.to_datetime(df['date'])
                    df = df[df['date'].dt.strftime('%Y-%m-%d') != date_str]
                    
                    # Prepare data for sheets
                    if not df.empty:
                        df_to_write = df.copy()
                        df_to_write['date'] = df_to_write['date'].dt.strftime('%Y-%m-%d')
                    else:
                        # If no data left, create empty dataframe with headers
                        df_to_write = pd.DataFrame(columns=['date', 'hours'])
                    
                    # Try different sheet names for writing
                    sheet_names = ["sheet1", "Sheet1", "Sheet 1", 0]
                    for sheet_name in sheet_names:
                        try:
                            conn.update(worksheet=sheet_name, data=df_to_write)
                            break
                        except Exception:
                            continue
                
                # Clear cache after deletion
                st.cache_data.clear()
                
                return True
                
            except Exception as e:
                st.warning(f"Google Sheets failed, using local storage: {str(e)}")
        
        # Fallback to session state
        df = st.session_state.study_data.copy()
        
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df = df[df['date'].dt.strftime('%Y-%m-%d') != date_str]
            st.session_state.study_data = df
        
        return True
        
    except Exception as e:
        st.error(f"Error deleting study session: {str(e)}")
        return False

# Main app
st.title("📚 Study Tracker")
st.markdown("Track your daily study hours and visualize your progress!")

# Display connection status
conn = init_connection()
if conn is not None:
    st.success("✅ Connected to Google Sheets")
else:
    st.info("ℹ️ Using local storage - data will be lost when session ends.")

# Add refresh button
if st.button("🔄 Refresh Data", help="Click to refresh data from Google Sheets"):
    st.cache_data.clear()
    st.rerun()

# Sidebar for input
with st.sidebar:
    st.header("📝 Log Study Session")
    
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
            result = add_study_session(study_date, hours_studied)
            if result == "added":
                st.success(f"✅ Added {hours_studied} hours for {study_date}")
                # Force immediate refresh
                st.rerun()
            elif result == "updated":
                st.success(f"✅ Updated {study_date} to {hours_studied} hours")
                # Force immediate refresh
                st.rerun()
            elif result == "error":
                st.error("❌ Failed to save study session")
        else:
            st.error("⚠️ Please enter hours greater than 0")
    
    st.divider()
    
    # Delete section
    st.header("🗑️ Delete Entry")
    delete_date = st.date_input("Select date to delete", key="delete_date")
    if st.button("🗑️ Delete Entry", type="secondary"):
        if delete_study_session(delete_date):
            st.success(f"✅ Deleted entry for {delete_date}")
            st.rerun()
        else:
            st.error("❌ Failed to delete entry")

# Main content area
col1, col2 = st.columns([1, 2])

with col1:
    st.header("📊 Statistics")
    
    # Get data (force refresh to show latest)
    df = get_study_data(force_refresh=True)
    
    if not df.empty and len(df) > 0:
        # Ensure date column is datetime
        df['date'] = pd.to_datetime(df['date'])
        
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
    
    if not df.empty and len(df) > 0:
        # Ensure date column is datetime
        df['date'] = pd.to_datetime(df['date'])
        
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
st.markdown("**💡 Tips:**")
st.markdown("- Log your study sessions daily for best tracking")
st.markdown("- Use the 🔄 Refresh button if data doesn't appear immediately")
st.markdown("- You can update existing entries by selecting the same date")
st.markdown("- Use the delete function to remove incorrect entries")
st.markdown("- Data updates in real-time with Google Sheets!")
