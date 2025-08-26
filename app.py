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
            conn = st.connection("gsheets", type=GSheetsConnection)
            # Test the connection by trying to read
            test_df = conn.read(worksheet=0, ttl=5)  # Try reading first sheet
            st.success("✅ Google Sheets connection successful!")
            return conn
        except Exception as e:
            st.error(f"❌ Google Sheets connection failed: {str(e)}")
            st.info("🔍 Debug info - Check your secrets configuration")
            return None
    else:
        st.warning("⚠️ streamlit_gsheets not installed")
    return None

def debug_connection():
    """Debug function to test Google Sheets connection"""
    st.subheader("🔍 Connection Debug Info")
    
    conn = init_connection()
    if conn is not None:
        try:
            # Try to read the sheet with different methods
            st.write("Testing different ways to read your sheet...")
            
            # Method 1: Try reading by index
            try:
                df1 = conn.read(worksheet=0, ttl=5)
                st.success(f"✅ Method 1 (worksheet=0): Found {len(df1)} rows, {len(df1.columns)} columns")
                st.write("First few rows:", df1.head())
            except Exception as e:
                st.error(f"❌ Method 1 failed: {str(e)}")
            
            # Method 2: Try reading by name "sheet1"
            try:
                df2 = conn.read(worksheet="sheet1", ttl=5)
                st.success(f"✅ Method 2 (worksheet='sheet1'): Found {len(df2)} rows, {len(df2.columns)} columns")
                st.write("First few rows:", df2.head())
            except Exception as e:
                st.error(f"❌ Method 2 failed: {str(e)}")
            
            # Method 3: Try reading by name "Sheet1"
            try:
                df3 = conn.read(worksheet="Sheet1", ttl=5)
                st.success(f"✅ Method 3 (worksheet='Sheet1'): Found {len(df3)} rows, {len(df3.columns)} columns")
                st.write("First few rows:", df3.head())
            except Exception as e:
                st.error(f"❌ Method 3 failed: {str(e)}")
                
        except Exception as e:
            st.error(f"❌ General connection error: {str(e)}")
    else:
        st.error("❌ No connection established")

def get_study_data():
    """Retrieve study data from Google Sheets or session state fallback"""
    conn = init_connection()
    
    # Try Google Sheets first
    if conn is not None:
        try:
            # Try different possible sheet names/indices
            methods = [
                ("worksheet=0", 0),
                ("worksheet='sheet1'", "sheet1"),
                ("worksheet='Sheet1'", "Sheet1"),
            ]
            
            df = None
            successful_method = None
            
            for method_name, sheet_identifier in methods:
                try:
                    df = conn.read(worksheet=sheet_identifier, usecols=[0, 1], ttl=5)
                    successful_method = method_name
                    break
                except Exception as e:
                    continue
            
            if df is None:
                raise Exception("Could not read from any worksheet")
            
            st.info(f"📊 Successfully read data using {successful_method}")
            
            # Clean the dataframe
            if not df.empty:
                st.write(f"Raw data shape: {df.shape}")
                st.write("Raw data preview:", df.head())
                
                # Remove any completely empty rows
                df = df.dropna(how='all')
                
                # Ensure we have the right columns
                if len(df.columns) >= 2:
                    df.columns = ['date', 'hours']
                    
                    # Remove header row if it exists (case insensitive)
                    df = df[~df['date'].astype(str).str.lower().isin(['date', 'Date', 'DATE'])]
                    
                    # Convert types
                    df['hours'] = pd.to_numeric(df['hours'], errors='coerce')
                    df = df.dropna()
                    
                    if not df.empty:
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
                # Get existing data
                df = get_study_data()
                
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
                
                # Try different methods to write
                methods = [0, "sheet1", "Sheet1"]
                write_success = False
                
                for method in methods:
                    try:
                        conn.update(worksheet=method, data=df_to_write)
                        st.success(f"✅ Successfully wrote to worksheet using: {method}")
                        write_success = True
                        break
                    except Exception as e:
                        st.warning(f"Failed to write using {method}: {str(e)}")
                        continue
                
                if not write_success:
                    raise Exception("Could not write to any worksheet")
                
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

# Main app
st.title("📚 Study Tracker (Debug Version)")
st.markdown("Track your daily study hours and visualize your progress!")

# Add debug section
with st.expander("🔍 Debug Connection (Click to test your Google Sheets setup)"):
    debug_connection()

# Display connection status
conn = init_connection()
if conn is not None:
    st.success("✅ Connected to Google Sheets")
else:
    st.info("ℹ️ Using local storage - data will be lost when session ends.")

# Instructions for first-time setup
with st.expander("📋 Setup Instructions for Google Sheets"):
    st.markdown("""
    **To connect your Google Sheets:**
    
    1. Create a new Google Sheet with 2 columns: `date` and `hours`
    2. Make sure the sheet tab is named `sheet1` (lowercase)
    3. Add a header row: A1="date", B1="hours"
    4. Create a Google Cloud Project and enable Google Sheets API
    5. Create a Service Account and download the JSON key file
    6. Share your sheet with the service account email (give Editor permissions)
    7. Add the connection details to your Streamlit secrets
    
    **Current sheet structure should be:**
    ```
    A1: date     B1: hours
    A2: 2024-08-26  B2: 2.5
    A3: 2024-08-27  B3: 3.0
    ```
    
    **In your Streamlit app settings, add these secrets:**
    ```toml
    [connections.gsheets]
    spreadsheet = "your_google_sheet_url_here"
    type = "service_account"
    project_id = "your_project_id"
    private_key_id = "your_private_key_id"
    private_key = "-----BEGIN PRIVATE KEY-----\\nyour_private_key_here\\n-----END PRIVATE KEY-----\\n"
    client_email = "your_service_account_email@project.iam.gserviceaccount.com"
    client_id = "your_client_id"
    auth_uri = "https://accounts.google.com/o/oauth2/auth"
    token_uri = "https://oauth2.googleapis.com/token"
    auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
    client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/your_service_account_email%40project.iam.gserviceaccount.com"
    ```
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
            result = add_study_session(study_date, hours_studied)
            if result == "added":
                st.success(f"✅ Added {hours_studied} hours for {study_date}")
                st.rerun()
            elif result == "updated":
                st.success(f"✅ Updated {study_date} to {hours_studied} hours")
                st.rerun()
            elif result == "error":
                st.error("❌ Failed to save study session")
        else:
            st.error("⚠️ Please enter hours greater than 0")

# Main content area
col1, col2 = st.columns([1, 2])

with col1:
    st.header("📊 Statistics")
    
    # Get data
    df = get_study_data()
    
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
    else:
        st.info("📊 Your study progress chart will appear here once you log some sessions!")
