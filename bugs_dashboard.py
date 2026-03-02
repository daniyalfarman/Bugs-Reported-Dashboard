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

def format_github_link(github_url):
    """Format GitHub link for display"""
    if pd.notna(github_url) and github_url and github_url != '':
        return github_url
    return None  # Return None for missing links

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
    df['client'] = df['host'].map(host_mapping).fillna('Unknown')
    
    # Add school names to dataframe using hardcoded mapping
    df['school_name'] = df['host'].map(host_mapping).fillna('Unknown')
    
        # Create multi-select dropdown with ONLY school names
    st.subheader("Filter by School (Multiple Selection)")
    
    # Get unique school names
    unique_schools = sorted(df['school_name'].unique().tolist())
    
    # Add "Select All" checkbox
    col1, col2 = st.columns([1, 3])
    with col1:
        select_all = st.checkbox("Select All", value=True)
    
    with col2:
        if select_all:
            # If Select All is checked, show all schools
            selected_schools = unique_schools
            st.success(f"✅ All {len(unique_schools)} schools selected")
        else:
            # Show multiselect for individual selection
            selected_schools = st.multiselect(
                "Select Schools",
                options=unique_schools,
                default=[]
            )
    
    # Apply filter based on selected schools
    if selected_schools and not select_all:
        df = df[df['school_name'].isin(selected_schools)]
        if len(selected_schools) == 1:
            st.info(f"📌 Currently viewing: **{selected_schools[0]}**")
        else:
            st.info(f"📌 Currently viewing: **{len(selected_schools)} schools**")
    elif select_all:
        # Keep all data when Select All is checked
        st.info(f"📌 Currently viewing: **All {len(unique_schools)} schools**")
    
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

    # Add this after your existing charts (around line 120-140)

    # Resolution Time Analysis
    st.subheader("⏱️ Bug Resolution Time Analysis")
    
    # Filter for resolved issues only
    resolved_issues = df[df['status'] == 'resolved'].copy()
    
    if not resolved_issues.empty:
        # Calculate resolution time in days
        resolved_issues['resolution_time_days'] = resolved_issues['days_open']
        
        # Create resolution time bins
        resolved_issues['resolution_category'] = pd.cut(
            resolved_issues['resolution_time_days'],
            bins=[0, 1, 3, 7, 14, 30, 60, float('inf')],
            labels=['<1 day', '1-3 days', '3-7 days', '1-2 weeks', '2-4 weeks', '1-2 months', '>2 months']
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Distribution of resolution times
            fig_res_dist = px.histogram(
                resolved_issues, 
                x='resolution_time_days',
                title='Distribution of Bug Resolution Times',
                labels={'resolution_time_days': 'Days to Resolve', 'count': 'Number of Bugs'},
                nbins=30,
                color_discrete_sequence=['#00CC96']
            )
            fig_res_dist.add_vline(
                x=resolved_issues['resolution_time_days'].median(), 
                line_dash="dash", 
                line_color="red",
                annotation_text=f"Median: {resolved_issues['resolution_time_days'].median():.1f} days"
            )
            st.plotly_chart(fig_res_dist, use_container_width=True)
        
        with col2:
            # Resolution time by module
            module_res_time = resolved_issues.groupby('module_name')['resolution_time_days'].agg(['mean', 'median', 'count']).round(1).reset_index()
            module_res_time.columns = ['Module', 'Avg Days', 'Median Days', 'Count']
            module_res_time = module_res_time.sort_values('Avg Days', ascending=True)
            
            fig_res_module = px.bar(
                module_res_time.head(10),
                x='Avg Days',
                y='Module',
                title='Average Resolution Time by Module (Top 10)',
                color='Avg Days',
                color_continuous_scale='RdYlGn_r',
                text='Avg Days'
            )
            fig_res_module.update_traces(textposition='outside')
            st.plotly_chart(fig_res_module, use_container_width=True)
        
        # Resolution time by client
        st.subheader("📊 Resolution Time by Client")
        client_res_time = resolved_issues.groupby('client').agg(
            Avg_Resolution_Days=('resolution_time_days', 'mean'),
            Median_Resolution_Days=('resolution_time_days', 'median'),
            Resolved_Count=('id', 'count'),
            Min_Days=('resolution_time_days', 'min'),
            Max_Days=('resolution_time_days', 'max')
        ).round(1).reset_index()
        
        client_res_time.columns = ['Client', 'Avg Days', 'Median Days', 'Resolved Count', 'Fastest', 'Slowest']
        client_res_time = client_res_time.sort_values('Avg Days')
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            fig_res_client = px.bar(
                client_res_time,
                x='Client',
                y='Avg Days',
                title='Average Resolution Time by Client',
                color='Avg Days',
                color_continuous_scale='Viridis',
                text='Avg Days'
            )
            fig_res_client.update_traces(textposition='outside')
            st.plotly_chart(fig_res_client, use_container_width=True)
        
        with col2:
            # Resolution time trend over time
            resolved_issues['resolution_month'] = resolved_issues['reported_date'].dt.to_period('M').astype(str)
            monthly_res_time = resolved_issues.groupby('resolution_month').agg(
                Avg_Resolution=('resolution_time_days', 'mean'),
                Count=('id', 'count')
            ).reset_index()
            
            fig_res_trend = px.line(
                monthly_res_time,
                x='resolution_month',
                y='Avg_Resolution',
                title='Resolution Time Trend Over Time',
                markers=True,
                labels={'resolution_month': 'Month', 'Avg_Resolution': 'Avg Days to Resolve'}
            )
            st.plotly_chart(fig_res_trend, use_container_width=True)
        
        # Summary metrics
        st.subheader("📈 Resolution Speed Metrics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Average Resolution", f"{resolved_issues['resolution_time_days'].mean():.1f} days")
        
        with col2:
            st.metric("Median Resolution", f"{resolved_issues['resolution_time_days'].median():.1f} days")
        
        with col3:
            p90 = resolved_issues['resolution_time_days'].quantile(0.9)
            st.metric("90% Resolved Within", f"{p90:.1f} days")
        
        with col4:
            fastest = resolved_issues['resolution_time_days'].min()
            st.metric("Fastest Resolution", f"{fastest:.1f} days")
        
        # Resolution efficiency table
        with st.expander("📋 Detailed Resolution Metrics by Module"):
            module_detailed = resolved_issues.groupby('module_name').agg(
                Total_Resolved=('id', 'count'),
                Avg_Days=('resolution_time_days', 'mean'),
                Median_Days=('resolution_time_days', 'median'),
                Min_Days=('resolution_time_days', 'min'),
                Max_Days=('resolution_time_days', 'max'),
                Std_Dev=('resolution_time_days', 'std')
            ).round(1).reset_index()
            
            module_detailed.columns = ['Module', 'Resolved', 'Avg Days', 'Median Days', 'Fastest', 'Slowest', 'Std Dev']
            st.dataframe(module_detailed.sort_values('Avg Days'), use_container_width=True)
    
    else:
        st.info("No resolved issues to analyze resolution time")
    
        # Key Tables - Updated for status
    st.subheader("🔴 Issues Needing Attention (In Progress + Unassigned)")
    attention_issues = df[df['status'].isin(['inprogress', 'unassigned'])].nlargest(10, 'days_open')
    if not attention_issues.empty:
        display_df = attention_issues[['id', 'client', 'module_name', 'status', 'reported_by', 'days_open', 'assigned_to', 'comments', 'reported_page','github_issue_link']].copy()
        
        # Add emojis to status
        display_df['status'] = display_df['status'].map({
            'resolved': '✅ Resolved',
            'inprogress': '🔄 In Progress',
            'unassigned': '⏳ Unassigned'
        })
        
        # Display with clickable link
        st.dataframe(
            display_df,
            column_config={
                "id": "Issue ID",
                "reported_page": st.column_config.LinkColumn(
                    "Issue Link",
                    display_text="🔗 View Issue"
                ),
                "github_issue_link": st.column_config.LinkColumn(
                    "GitHub Ticket",
                    display_text="🐙 Open Ticket"
                ),
                "client": "Client",
                "module_name": "Module",
                "status": "Status",
                "reported_by": "Reported By",
                "days_open": "Days Open",
                "assigned_to": "Assigned To",
                "comments": "Comments"
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("No unresolved issues! 🎉")
    
    st.subheader("📋 Client & Module Performance Summary")

    # Group by both client and module
    module_summary = df.groupby(['client', 'module_name']).agg(
        Total_Issues=('id', 'count'),
        Resolved=('status', lambda x: (x == 'resolved').sum()),
        In_Progress=('status', lambda x: (x == 'inprogress').sum()),
        Unassigned=('status', lambda x: (x == 'unassigned').sum()),
        Assigned=('assigned_to', lambda x: x.notna().sum()),
        Avg_Days_Open=('days_open', 'mean')
    ).round(1).reset_index()

    # Rename columns for display
    module_summary.columns = ['Client', 'Module', 'Total Issues', 'Resolved', 'In Progress', 'Unassigned', 'Assigned', 'Avg Days Open']

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