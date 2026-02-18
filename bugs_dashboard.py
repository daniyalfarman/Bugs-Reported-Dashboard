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
    
    # ADD HOST FILTER HERE
    st.subheader("Filter by Host")
    host_options = ['All'] + sorted(df['host'].unique().tolist())
    selected_host = st.selectbox("Select Host", host_options)
    
    # Apply host filter
    if selected_host != 'All':
        df = df[df['host'] == selected_host]
    
    # Create KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Issues", len(df))
    
    with col2:
        unresolved = len(df[df['resolved'] == False])
        st.metric("Unresolved Issues", unresolved)
    
    with col3:
        assigned = len(df[df['is_assigned']])
        st.metric("Assigned Issues", assigned)
    
    with col4:
        avg_days = round(df[df['resolved'] == False]['days_open'].mean(), 1) if len(df[df['resolved'] == False]) > 0 else 0
        st.metric("Avg Days Open (Unresolved)", avg_days)
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Issues by Module
        module_counts = df['module_name'].value_counts().reset_index()
        module_counts.columns = ['Module', 'Count']
        fig = px.bar(module_counts, x='Module', y='Count', 
                     title='Issues by Module',
                     color='Count',
                     color_continuous_scale='Viridis')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Unresolved issues by days open
        unresolved_df = df[df['resolved'] == False].copy()
        if not unresolved_df.empty:
            fig2 = px.histogram(unresolved_df, x='days_open', 
                               title='Unresolved Issues - Days Open Distribution',
                               nbins=20,
                               labels={'days_open': 'Days Open'})
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No unresolved issues to display")
    
    # Key Tables
    st.subheader("🔴 Unresolved Issues (by age)")
    oldest_unresolved = df[df['resolved'] == False].nlargest(10, 'days_open')
    if not oldest_unresolved.empty:
        st.dataframe(oldest_unresolved[['id', 'module_name', 'reported_by', 'days_open', 'assigned_to', 'comments']], use_container_width=True)
    else:
        st.success("No unresolved issues!")
    
    st.subheader("📋 Issues by Module - Detailed")
    module_summary = df.groupby('module_name').agg({
        'id': 'count',
        'resolved': lambda x: (~x).sum(),  # unresolved count
        'assigned_to': lambda x: x.notna().sum(),
        'days_open': 'mean'
    }).round(1).rename(columns={
        'id': 'Total Issues',
        'resolved': 'Unresolved',
        'assigned_to': 'Assigned',
        'days_open': 'Avg Days Open'
    }).reset_index()
    
    st.dataframe(module_summary, use_container_width=True)
    
    # All issues table
    with st.expander("View All Issues"):
        st.dataframe(df[
            ['id', 'module_name', 'reported_by', 'reported_date', 
             'days_open', 'resolved', 'assigned_to', 'comments']
        ].sort_values('reported_date', ascending=False), use_container_width=True)

else:
    st.warning("No data available")