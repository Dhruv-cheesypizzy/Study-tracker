import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

# Page config
st.set_page_config(
    page_title="Study Tracker",
    page_icon="📚",
    layout="wide"
)

# Initialize Google Sheets connection
@st.cache_resource
def init_connection():
    return st.connection("gsheets", type=GSheetsConnection)

def get_study_data():
    """Retrieve all study data from Google Sheets"""
    try:
        conn = init_connection()
        df = conn.read(worksheet="study_tracker", usecols=[0, 1], ttl=5)
        
        # Clean the dataframe
        if not df.empty:
            # Remove any completely empty rows
            df = df.dropna(how='all')
            # Ensure we have the right columns
            if len(df.columns) >= 2:
                df.columns = ['date', 'hours']
                # Remove header row if it exists
                df = df[df['date'] != 'date']
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
        st.error(f"Error reading from Google Sheets: {str(e)}")
        return pd.DataFrame(columns=['date', 'hours'])

def add_study_session(study_date, hours):
    """Add or update a study session in Google Sheets"""
    try:
        conn = init_connection()
        
        # Get existing data
        df = get_study_data()
        
        # Convert study_date to string for comparison
        date_str = str(study_date)
        
        # Check if entry exists
        if not df.empty and date_str in df['date'].dt.strftime('%Y-%m-%d').values:
            # Update existing entry
            df.loc[df['date'].dt.strftime('%Y-%m-%d') == date_str, 'hours'] = hours
            result = "updated"
        else:
            # Add new entry
            new_row = pd.DataFrame({'date': [date_str], 'hours': [hours]})
            if df is None or df.empty:
                df = new_row
            else:
                df = pd.concat([df, new_row], ignore_index=True)

            result = "added"
        
        # Sort by date
        df = df.sort_values('date')
        
        # Prepare data for sheets (convert date to string)
        df_to_write = df.copy()
        df_to_write['date'] = df_to_write['date'].dt.strftime('%Y-%m-%d')
        
        # Write back to sheets
        conn.update(worksheet="study_tracker", data=df_to_write)
        
        return result
        
    except Exception as e:
        st.error(f"Error adding study session: {str(e)}")
        return "error"

def delete_study_session(study_date):
    """Delete a study session from Google Sheets"""
    try:
        conn = init_connection()
        
        # Get existing data
        df = get_study_data()
        
        if not df.empty:
            # Remove the entry
            date_str = str(study_date)
            df = df[df['date'].dt.strftime('%Y-%m-%d') != date_str]
            
            # Prepare data for sheets
            if not df.empty:
                df_to_write = df.copy()
                df_to_write['date'] = df_to_write['date'].dt.strftime('%Y-%m-%d')
            else:
                # If no data left, create empty dataframe with headers
                df_to_write = pd.DataFrame(columns=['date', 'hours'])
            
            # Write back to sheets
            conn.update(worksheet="study_tracker", data=df_to_write)
            
        return True
        
    except Exception as e:
        st.error(f"Error deleting study session: {str(e)}")
        return False

# Main app
st.title("📚 Study Tracker")
st.markdown("Track your daily study hours and visualize your progress!")

# Instructions for first-time setup
with st.expander("📋 Setup Instructions (Click if this is your first time)"):
    st.markdown("""
    **To connect your Google Sheets:**
    
    1. Create a new Google Sheet with 2 columns: `date` and `hours`
    2. Share the sheet with your Streamlit app's service account email
    3. Add the sheet URL to your Streamlit secrets
    
    **In your Streamlit app settings, add these secrets:**
    ```toml
    [connections.gsheets]
    spreadsheet = "your_google_sheet_url_here"
    type = "service_account"
    project_id = "your_project_id"
    private_key_id = "your_private_key_id"
    private_key = "your_private_key"
    client_email = "your_service_account_email"
    client_id = "your_client_id"
    auth_uri = "https://accounts.google.com/o/oauth2/auth"
    token_uri = "https://token.googleapis.com/token"
    auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
    client_x509_cert_url = "your_cert_url"
    ```
    
    **Need help?** Follow the [Streamlit Google Sheets connection guide](https://docs.streamlit.io/knowledge-base/tutorials/databases/gcs-gsheets).
    """)

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
            result = add_study_session(str(study_date), hours_studied)
            if result == "added":
                st.success(f"✅ Added {hours_studied} hours for {study_date}")
            elif result == "updated":
                st.success(f"✅ Updated {study_date} to {hours_studied} hours")
            st.rerun()
        else:
            st.error("⚠️ Please enter hours greater than 0")
    
    st.divider()
    
    # Delete section
    st.header("🗑️ Delete Entry")
    delete_date = st.date_input("Select date to delete", key="delete_date")
    if st.button("🗑️ Delete Entry", type="secondary"):
        if delete_study_session(str(delete_date)):
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
st.markdown("- Your data is automatically saved to Google Sheets!")
st.markdown("- Track consistently to see meaningful progress patterns!")







