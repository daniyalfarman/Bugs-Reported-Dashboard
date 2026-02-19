import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timezone
import json
import plotly.express as px

# Page config
st.set_page_config(page_title="Issue Dashboard", layout="wide")
st.title("📊 Schoolgram Issues Tracking Dashboard")

# Auto-refresh button
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()

@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_issues():
    """Fetch data from API"""
    try:
        # Replace with your actual API endpoint
        response = requests.get("https://analytics.schoolgram.io/issues/report-bug/")
        data = response.json()
        return pd.DataFrame(data['issues'])
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

# Load data
df = fetch_issues()

if not df.empty:
    # Data Cleaning
    df['reported_date'] = pd.to_datetime(df['reported_date'])
    df['days_open'] = (datetime.now(timezone.utc) - df['reported_date']).dt.days
    df['is_assigned'] = df['assigned_to'].notna() & (df['assigned_to'] != '')
    
    # Parse additional_data to get more info
    df['user_id'] = df['additional_data'].apply(
        lambda x: json.loads(x).get('user_id') if pd.notna(x) else None
    )
    
    # Status mappings for better display
    status_colors = {
        'resolved': '✅',
        'inprogress': '🔄',
        'unassigned': '⏳'
    }
    
        # Import re for hostname extraction
        # Hardcoded host mapping
    host_mapping = {
        2: 'test',
        3: 'demo',
        4: 'excellenceacademy',
        5: 'hhrd',
        7: 'scholastic',
        9: 'test',
        None: 'localhost'
    }
    
    # Add school names to dataframe using hardcoded mapping
    df['school_name'] = df['host'].map(host_mapping).fillna('Unknown')
    
    # Create dropdown with ONLY school names
    st.subheader("Filter by School")
    
    # Get unique school names (deduplicated)
    unique_schools = ['All'] + sorted(df['school_name'].unique().tolist())
    
    # Show only school names in dropdown
    selected_school_display = st.selectbox(
        "Select School",
        options=unique_schools
    )
    
    # Apply filter based on selected school
    if selected_school_display != 'All':
        df = df[df['school_name'] == selected_school_display]
        st.info(f"📌 Currently viewing: **{selected_school_display}**")
    
    # Create KPIs - Updated for new status field
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Issues", len(df))
    
    with col2:
        resolved = len(df[df['status'] == 'resolved'])
        st.metric("✅ Resolved", resolved)
    
    with col3:
        inprogress = len(df[df['status'] == 'inprogress'])
        st.metric("🔄 In Progress", inprogress)
    
    with col4:
        unassigned = len(df[df['status'] == 'unassigned'])
        st.metric("⏳ Unassigned", unassigned)
    
    with col5:
        # Calculate average days open for unresolved issues (inprogress + unassigned)
        unresolved_df = df[df['status'].isin(['inprogress', 'unassigned'])]
        avg_days = round(unresolved_df['days_open'].mean(), 1) if not unresolved_df.empty else 0
        st.metric("Avg Days Open (Unresolved)", avg_days)
    
    # Status distribution pie chart
    col1, col2 = st.columns(2)
    
    with col1:
        # Status Distribution
        status_counts = df['status'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Count']
        # Map status to display names with emojis
        status_counts['Status'] = status_counts['Status'].map({
            'resolved': '✅ Resolved',
            'inprogress': '🔄 In Progress',
            'unassigned': '⏳ Unassigned'
        })
        
        fig_pie = px.pie(status_counts, values='Count', names='Status',
                         title='Issues by Status',
                         color_discrete_sequence=['#00CC96', '#FFA15A', '#AB63FA'])
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # Issues by Module
        module_counts = df['module_name'].value_counts().reset_index()
        module_counts.columns = ['Module', 'Count']
        fig = px.bar(module_counts, x='Module', y='Count', 
                     title='Issues by Module',
                     color='Count',
                     color_continuous_scale='Viridis')
        st.plotly_chart(fig, use_container_width=True)
    
    # Second row charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Unresolved issues by days open (inprogress + unassigned)
        unresolved_df = df[df['status'].isin(['inprogress', 'unassigned'])].copy()
        if not unresolved_df.empty:
            # Add status color to histogram
            fig2 = px.histogram(unresolved_df, x='days_open', 
                               color='status',
                               title='Unresolved Issues - Days Open Distribution',
                               nbins=20,
                               labels={'days_open': 'Days Open', 'status': 'Status'},
                               color_discrete_map={'inprogress': '#FFA15A', 'unassigned': '#AB63FA'})
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No unresolved issues to display")
    
    with col2:
        # Status by Module (stacked bar chart)
        status_by_module = pd.crosstab(df['module_name'], df['status'])
        if not status_by_module.empty:
            fig3 = px.bar(status_by_module, 
                         title='Status Distribution by Module',
                         barmode='stack',
                         color_discrete_map={'resolved': '#00CC96', 
                                           'inprogress': '#FFA15A', 
                                           'unassigned': '#AB63FA'})
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("No data for module status breakdown")
    
    # Key Tables - Updated for status
    st.subheader("🔴 Issues Needing Attention (In Progress + Unassigned)")
    attention_issues = df[df['status'].isin(['inprogress', 'unassigned'])].nlargest(10, 'days_open')
    if not attention_issues.empty:
        display_df = attention_issues[['id', 'module_name', 'status', 'reported_by', 'days_open', 'assigned_to', 'comments']].copy()
        # Add emojis to status for better visualization
        display_df['status'] = display_df['status'].map({
            'resolved': '✅ Resolved',
            'inprogress': '🔄 In Progress',
            'unassigned': '⏳ Unassigned'
        })
        st.dataframe(display_df, use_container_width=True)
    else:
        st.success("No unresolved issues! 🎉")
    
    st.subheader("📋 Module Performance Summary")

    # Fix the module summary aggregation
    module_summary = df.groupby('module_name').agg(
        Total_Issues=('id', 'count'),
        Resolved=('status', lambda x: (x == 'resolved').sum()),
        In_Progress=('status', lambda x: (x == 'inprogress').sum()),
        Unassigned=('status', lambda x: (x == 'unassigned').sum()),
        Assigned=('assigned_to', lambda x: x.notna().sum()),
        Avg_Days_Open=('days_open', 'mean')
    ).round(1).reset_index()

    # Rename columns for display
    module_summary.columns = ['Module', 'Total Issues', 'Resolved', 'In Progress', 'Unassigned', 'Assigned', 'Avg Days Open']

    # Add resolution rate
    module_summary['Resolution Rate'] = (module_summary['Resolved'] / module_summary['Total Issues'] * 100).round(1).astype(str) + '%'

    st.dataframe(module_summary, use_container_width=True)
    
    # All issues table with status
    with st.expander("View All Issues"):
        display_all = df[[
            'id', 'module_name', 'status', 'reported_by', 'reported_date', 
            'days_open', 'assigned_to', 'comments'
        ]].copy()
        # Add emojis to status
        display_all['status'] = display_all['status'].map({
            'resolved': '✅ Resolved',
            'inprogress': '🔄 In Progress',
            'unassigned': '⏳ Unassigned'
        })
        st.dataframe(display_all.sort_values('reported_date', ascending=False), use_container_width=True)

else:
    st.warning("No data available")