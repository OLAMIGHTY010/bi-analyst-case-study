import streamlit as st
import duckdb
import pandas as pd
import os

db_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "breaches.duckdb")

# Page config
st.set_page_config(
    page_title="Enterprise Observability Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Styles
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        .main-title {
            font-size: 32px;
            font-weight: 800;
            color: var(--text-color) !important;
            margin-bottom: 2px;
        }
        .subtitle {
            font-size: 16px;
            color: var(--text-color) !important;
            opacity: 0.6;
            margin-bottom: 25px;
        }

        /* Storytelling tab */
        .story-hero {
            background: linear-gradient(135deg, var(--primary-color), #2b5876);
            padding: 45px 40px;
            border-radius: 16px;
            margin-bottom: 30px;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0,0,0,0.15);
        }
        .story-hero h1 {
            font-size: 38px;
            font-weight: 800;
            margin-bottom: 10px;
            color: #ffffff !important;
            background: none !important;
            -webkit-text-fill-color: #ffffff !important;
        }
        .story-hero p {
            font-size: 16px;
            color: rgba(255,255,255,0.85) !important;
            max-width: 720px;
            margin: 0 auto;
            line-height: 1.7;
        }
        .story-hero strong {
            color: #ffffff !important;
        }

        .story-chapter {
            background: var(--secondary-background-color);
            border-left: 5px solid;
            padding: 22px 28px;
            border-radius: 0 12px 12px 0;
            margin-bottom: 24px;
        }
        .story-chapter.landscape { border-color: #667eea; }
        .story-chapter.villains { border-color: #e84363; }
        .story-chapter.forward { border-color: #10b981; }
        .story-chapter h2 {
            font-size: 22px;
            font-weight: 700;
            margin-bottom: 4px;
            color: var(--text-color) !important;
        }
        .story-chapter .chapter-label {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 2px;
            font-weight: 700;
            margin-bottom: 6px;
        }
        .story-chapter.landscape .chapter-label { color: #667eea !important; }
        .story-chapter.villains .chapter-label { color: #e84363 !important; }
        .story-chapter.forward .chapter-label { color: #10b981 !important; }

        .story-stat-row {
            display: flex;
            gap: 16px;
            margin: 20px 0;
            flex-wrap: wrap;
        }
        .story-stat {
            flex: 1;
            min-width: 180px;
            background: var(--background-color);
            border-radius: 12px;
            padding: 22px 16px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            border: 1px solid var(--secondary-background-color);
        }
        .story-stat .stat-value {
            font-size: 34px;
            font-weight: 800;
            line-height: 1.1;
        }
        .story-stat .stat-label {
            font-size: 12px;
            color: var(--text-color) !important;
            opacity: 0.7;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 8px;
            font-weight: 600;
        }

        .story-insight {
            background: var(--secondary-background-color);
            border-radius: 12px;
            padding: 22px 26px;
            margin: 16px 0;
            box-shadow: 0 1px 8px rgba(0,0,0,0.06);
            border-left: 5px solid #667eea;
        }
        .story-insight.danger { border-left-color: #e84363; }
        .story-insight.warning { border-left-color: #f59e0b; }
        .story-insight.success { border-left-color: #10b981; }
        .story-insight h4 {
            margin: 0 0 10px 0;
            font-size: 16px;
            font-weight: 700;
            color: var(--text-color) !important;
        }
        .story-insight p {
            margin: 0;
            color: var(--text-color) !important;
            opacity: 0.85;
            font-size: 14.5px;
            line-height: 1.8;
        }
        .story-insight strong {
            color: var(--text-color) !important;
            opacity: 1;
        }
        .story-insight em {
            color: var(--text-color) !important;
            opacity: 0.6;
        }
        .story-insight code {
            background: var(--background-color) !important;
            color: #e84363 !important;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 13px;
            font-weight: 600;
        }

        .story-verdict {
            background: linear-gradient(135deg, #f5576c, #f093fb);
            padding: 35px 40px;
            border-radius: 16px;
            margin-top: 28px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .story-verdict h3 {
            font-size: 22px;
            font-weight: 800;
            margin-bottom: 14px;
            color: #ffffff !important;
        }
        .story-verdict p {
            color: rgba(255,255,255,0.95) !important;
            font-size: 15px;
            max-width: 760px;
            margin: 0 auto;
            line-height: 1.8;
        }
        .story-verdict strong {
            color: #ffffff !important;
        }
        .story-verdict em {
            color: rgba(255,255,255,0.8) !important;
        }
    </style>
""", unsafe_allow_html=True)


st.markdown('<div class="main-title">Enterprise Observability - Service Breach Portal</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Interactive Real-time Observability Analytics & Business Intelligence Dashboard</div>', unsafe_allow_html=True)

# Sidebar
st.sidebar.header("Navigation & Filters")
dataset_choice = st.sidebar.selectbox(
    "Select Target Dataset",
    ["Overall System Raw Data", "Tier 1 & Tier 2 Channels"]
)

# DB connection
if not os.path.exists(db_file):
    st.error(f"DuckDB database not found at {db_file}. Please run the pipeline script first to generate the database.")
    st.stop()

conn = duckdb.connect(db_file, read_only=True)


table_name = "weekly_breaches_raw" if dataset_choice == "Overall System Raw Data" else "tier_1_2_breaches"
df_all = conn.execute(f"SELECT * FROM {table_name}").df()


other_table = "tier_1_2_breaches" if dataset_choice == "Overall System Raw Data" else "weekly_breaches_raw"
df_other = conn.execute(f"SELECT * FROM {other_table}").df()

# Full datasets for the chronicles tab
df_raw_full = conn.execute("SELECT * FROM weekly_breaches_raw").df()
df_tier_full = conn.execute("SELECT * FROM tier_1_2_breaches").df()

# Breach type classification
if dataset_choice == "Overall System Raw Data":
    df_all['core_breach_type'] = df_all['breach_type'].map(lambda x: 
        'Error rate' if x in ['Error rate', 'Availability', 'Health Check', 'Failed Count', 'Failure Rate & Failed Count']
        else 'Latency' if x in ['Latency', 'Consumer Lag', 'Pending Count', 'Pending Rate & Pending Count', 'Frozen Jobs', 'Unsynced Count', 'High Disk Usage on D:']
        else 'Unknown'
    )
else:
    df_all['core_breach_type'] = df_all['breach_type']


df_raw_full['core_breach_type'] = df_raw_full['breach_type'].map(lambda x: 
    'Error rate' if x in ['Error rate', 'Availability', 'Health Check', 'Failed Count', 'Failure Rate & Failed Count']
    else 'Latency' if x in ['Latency', 'Consumer Lag', 'Pending Count', 'Pending Rate & Pending Count', 'Frozen Jobs', 'Unsynced Count', 'High Disk Usage on D:']
    else 'Unknown'
)
df_tier_full['core_breach_type'] = df_tier_full['breach_type']

# Sidebar filters
weeks_available = sorted(df_all['week'].unique())
selected_weeks = st.sidebar.multiselect("Filter by Week", weeks_available, default=weeks_available)

types_available = sorted(df_all['core_breach_type'].unique())
selected_types = st.sidebar.multiselect("Filter by Core Breach Type", types_available, default=types_available)


df_filtered = df_all[
    (df_all['week'].isin(selected_weeks)) & 
    (df_all['core_breach_type'].isin(selected_types))
]

# KPIs
total_breaches = df_filtered['breach_count'].sum() if len(df_filtered) > 0 else 0
unique_services = df_filtered['microservice'].nunique() if len(df_filtered) > 0 else 0

if len(df_filtered) > 0:
    err_count = df_filtered[df_filtered['core_breach_type'] == 'Error rate']['breach_count'].sum()
    err_percent = (err_count / total_breaches) * 100 if total_breaches > 0 else 0
    
    lat_count = df_filtered[df_filtered['core_breach_type'] == 'Latency']['breach_count'].sum()
    lat_percent = (lat_count / total_breaches) * 100 if total_breaches > 0 else 0
else:
    err_count, err_percent, lat_count, lat_percent = 0, 0, 0, 0


col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total SLA Breaches", f"{total_breaches:,}")
with col2:
    st.metric("Active Services Affected", f"{unique_services}")
with col3:
    st.metric("Error Breach Ratio", f"{err_percent:.1f}%", f"{err_count:,} breaches", delta_color="inverse")
with col4:
    st.metric("Latency Breach Ratio", f"{lat_percent:.1f}%", f"{lat_count:,} breaches", delta_color="inverse")

st.markdown("---")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["Interactive Analytics", "Raw Data Explorer", "Executive Insights", "🔥 The Breach Chronicles"])

with tab1:
    st.subheader("Visual Analytics Trends")
    
    if len(df_filtered) == 0:
        st.warning("No data matches the selected filters.")
    else:
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.markdown("#### Weekly Breach Distribution")
            df_weekly = df_filtered.groupby(['week', 'core_breach_type'])['breach_count'].sum().reset_index()

            df_pivot = df_weekly.pivot(index='week', columns='core_breach_type', values='breach_count').fillna(0)
            st.bar_chart(df_pivot)
            
        with col_chart2:
            st.markdown("#### Top 10 Microservices by SLA Breaches")
            df_top = df_filtered.groupby('microservice')['breach_count'].sum().sort_values(ascending=False).head(10).reset_index()
            st.bar_chart(data=df_top, x="microservice", y="breach_count", color="#ff4757")

        st.markdown("---")
        with st.expander("Show Static Matplotlib Observability Dashboard"):
            _dashboard_img = os.path.join(os.path.dirname(os.path.abspath(__file__)), "breach_dashboard.png")
            if os.path.exists(_dashboard_img):
                st.image(_dashboard_img, width="stretch")
            else:
                st.info("Dashboard image not found. Run the analysis pipeline (e.g. `analyzer.py`) to generate `breach_dashboard.png`.")

with tab2:
    st.subheader("Searchable Data Table")
    st.markdown("Use the filters on the left sidebar to change this table's output.")
    
    search_query = st.text_input("Quick Search Microservice Name", "")
    df_table = df_filtered
    if search_query:
        df_table = df_filtered[df_filtered['microservice'].str.lower().str.contains(search_query.lower())]
        
    st.dataframe(
        df_table.sort_values(by='breach_count', ascending=False),
        column_config={
            "week": "Week",
            "microservice": "Microservice Name",
            "breach_count": st.column_config.NumberColumn("SLA Breach Count", format="%d"),
            "breach_type": "Raw Breach Type",
            "core_breach_type": "Standardized Breach Type"
        },
        width="stretch",
        hide_index=True
    )

with tab3:
    st.subheader("Executive Insights & SRE Action Plan")
    
    col_ins1, col_ins2 = st.columns([2, 1])
    
    with col_ins1:
        st.markdown("""
        ### Strategic Recommendations
        
        * **Audit the Xplorer Core Case API (`xplorer-case-api`)**:
          This microservice is responsible for **3,641 breaches (10.0% of the entire ecosystem)**. Since these are mostly error rate incidents, SRE teams should prioritize code profiling and exceptions checks on its database query locks.
        * **API Gateway Scaling**:
          `OneBank.APIGateWay` accounts for **1,898 breaches** (mostly latency). We recommend increasing resources (CPU/Memory) or horizontally scaling instances to manage connection pooling bottlenecks.
        * **Introduce Downstream Safeguards**:
          Critical consumer portals (e.g. USSD, SMS, and OTP) show high vulnerability to failures in backend dependencies. Implementing automated client-side rate-limiting and connection queue cutoffs will prevent cascade outages.
        """)
    
    with col_ins2:
        st.markdown("""
        ### Data Quality Advisory
        
        > ⚠️ **Tier 1 & 2 Sheet Anomaly**:
        > The breach counts for all 16 microservices in `Week 2` and `Week 3` are *exactly identical* in the provided Tier 1 & 2 summary sheet. 
        > This suggests a duplicate record entry error in the source Excel file.
        > Operational decisions should account for this duplicate when analyzing channel trends.
        """)


with tab4:

    # Metrics for the narrative
    story_total = df_raw_full['breach_count'].sum()
    story_services = df_raw_full['microservice'].nunique()
    story_weeks = sorted(df_raw_full['week'].unique())


    weekly_totals = df_raw_full.groupby('week')['breach_count'].sum().sort_index()
    peak_week = weekly_totals.idxmax()
    peak_val = weekly_totals.max()
    low_week = weekly_totals.idxmin()
    low_val = weekly_totals.min()


    weekly_list = weekly_totals.reset_index()
    weekly_list.columns = ['week', 'total']
    weekly_list['wow_change'] = weekly_list['total'].pct_change() * 100


    error_total = df_raw_full[df_raw_full['core_breach_type'] == 'Error rate']['breach_count'].sum()
    latency_total = df_raw_full[df_raw_full['core_breach_type'] == 'Latency']['breach_count'].sum()
    error_pct = (error_total / story_total) * 100 if story_total > 0 else 0
    latency_pct = (latency_total / story_total) * 100 if story_total > 0 else 0


    top_services = df_raw_full.groupby('microservice')['breach_count'].sum().sort_values(ascending=False)
    top1_name = top_services.index[0] if len(top_services) > 0 else "N/A"
    top1_count = top_services.iloc[0] if len(top_services) > 0 else 0
    top1_pct = (top1_count / story_total) * 100 if story_total > 0 else 0
    top3 = top_services.head(3)
    top3_combined = top3.sum()
    top3_pct = (top3_combined / story_total) * 100 if story_total > 0 else 0

    # Tier 1 & 2 analysis
    tier_total = df_tier_full['breach_count'].sum()
    tier_pct = (tier_total / story_total) * 100 if story_total > 0 else 0
    tier_top = df_tier_full.groupby('microservice')['breach_count'].sum().sort_values(ascending=False)
    tier_top1_name = tier_top.index[0] if len(tier_top) > 0 else "N/A"
    tier_top1_count = tier_top.iloc[0] if len(tier_top) > 0 else 0


    if len(weekly_list) >= 2:
        last_wow = weekly_list.iloc[-1]['wow_change']
        trend_direction = "improving" if last_wow < 0 else "worsening"
        trend_emoji = "📉" if last_wow < 0 else "📈"
    else:
        last_wow = 0
        trend_direction = "stable"
        trend_emoji = "➡️"

    # Persistent offenders (present every week)
    service_week_counts = df_raw_full.groupby('microservice')['week'].nunique()
    persistent_offenders = service_week_counts[service_week_counts == len(story_weeks)]
    num_persistent = len(persistent_offenders)


    st.markdown(f"""
    <div class="story-hero">
        <h1>The Breach Chronicles</h1>
        <p>
            A data-driven investigation into <strong>{story_total:,.0f} SLA breaches</strong> across 
            <strong>{story_services} microservices</strong> over <strong>{len(story_weeks)} weeks</strong> — 
            uncovering hidden patterns, systemic risks, and the path to operational resilience.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Act I
    st.markdown(f"""
    <div class="story-chapter landscape">
        <div class="chapter-label">Act I</div>
        <h2>The Landscape — A System Under Siege</h2>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="story-stat-row">
        <div class="story-stat">
            <div class="stat-value" style="color: #2c3e50;">{story_total:,.0f}</div>
            <div class="stat-label">Total SLA Breaches</div>
        </div>
        <div class="story-stat">
            <div class="stat-value" style="color: #667eea;">{story_services}</div>
            <div class="stat-label">Services Affected</div>
        </div>
        <div class="story-stat">
            <div class="stat-value" style="color: #f5576c;">{error_pct:.0f}%</div>
            <div class="stat-label">Error-Driven</div>
        </div>
        <div class="story-stat">
            <div class="stat-value" style="color: #1e90ff;">{latency_pct:.0f}%</div>
            <div class="stat-label">Latency-Driven</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="story-insight">
        <h4>📊 The Numbers Tell a Story</h4>
        <p>
            Over the observation window, the enterprise ecosystem recorded <strong>{story_total:,.0f} SLA breaches</strong> — 
            an average of <strong>{story_total / len(story_weeks):,.0f} breaches per week</strong>. 
            The split isn't random: <strong>{error_pct:.1f}% are error-rate incidents</strong> (failed requests, health check failures, availability drops), 
            while <strong>{latency_pct:.1f}% are latency-related</strong> (slow responses, consumer lag, pending queues).
            This near 60/40 split reveals a system where <em>things don't just break — they also crawl</em>.
        </p>
    </div>
    """, unsafe_allow_html=True)


    st.markdown("#### 📈 The Weekly Pulse")
    df_story_weekly = df_raw_full.groupby(['week', 'core_breach_type'])['breach_count'].sum().reset_index()
    df_story_pivot = df_story_weekly.pivot(index='week', columns='core_breach_type', values='breach_count').fillna(0)
    st.bar_chart(df_story_pivot)

    wow_narratives = []
    for _, row in weekly_list.iterrows():
        if pd.notna(row['wow_change']):
            direction = "🔺" if row['wow_change'] > 0 else "🔽"
            wow_narratives.append(f"**{row['week']}**: {row['total']:,.0f} breaches ({direction} {abs(row['wow_change']):.1f}% WoW)")
        else:
            wow_narratives.append(f"**{row['week']}**: {row['total']:,.0f} breaches (baseline)")

    st.markdown(" → ".join(wow_narratives))

    st.markdown(f"""
    <div class="story-insight {'danger' if trend_direction == 'worsening' else 'success'}">
        <h4>{trend_emoji} Momentum Check</h4>
        <p>
            The breach trajectory is <strong>{trend_direction}</strong>. 
            {'The most recent week shows a <strong>' + f'{abs(last_wow):.1f}%' + ' decline</strong> — a signal that remediation efforts may be taking hold, but the absolute numbers remain dangerously high.' if trend_direction == 'improving' else 'The most recent week shows a <strong>' + f'{abs(last_wow):.1f}%' + ' increase</strong> — the problem is compounding, and without intervention, the next reporting cycle could be significantly worse.'}
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Act II
    st.markdown(f"""
    <div class="story-chapter villains">
        <div class="chapter-label">Act II</div>
        <h2>The Villains — Unmasking the Worst Offenders</h2>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="story-insight danger">
        <h4>🎯 The #1 Offender: <code>{top1_name}</code></h4>
        <p>
            This single microservice is responsible for <strong>{top1_count:,.0f} breaches</strong> — 
            a staggering <strong>{top1_pct:.1f}%</strong> of the entire ecosystem's SLA violations.
            If this service were a patient, it would be in the ICU. Every SRE cycle, operations teams are 
            forced to firefight incidents originating from this one dependency.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### 🏆 Top 10 Most Breaching Services")
    df_story_top = top_services.head(10).reset_index()
    df_story_top.columns = ['microservice', 'breach_count']
    st.bar_chart(data=df_story_top, x="microservice", y="breach_count", color="#f5576c")

    st.markdown(f"""
    <div class="story-insight warning">
        <h4>⚡ The Concentration Problem</h4>
        <p>
            The top 3 services alone — <strong>{', '.join(f'<code>{n}</code>' for n in top3.index)}</strong> — 
            account for <strong>{top3_combined:,.0f} breaches ({top3_pct:.1f}%)</strong> of the total.
            Meanwhile, <strong>{num_persistent} services</strong> appear as offenders in <em>every single week</em> 
            of the observation period. These aren't flaky failures — they're <strong>chronic, systemic issues</strong> 
            baked into the architecture.
        </p>
    </div>
    """, unsafe_allow_html=True)


    st.markdown(f"""
    <div class="story-insight">
        <h4>🏦 Tier 1 & 2 Channels — The Customer Frontline</h4>
        <p>
            The customer-facing Tier 1 & 2 channels registered <strong>{tier_total:,.0f} breaches</strong>, 
            representing <strong>{tier_pct:.1f}%</strong> of the ecosystem total. 
            The worst offender in this critical tier is <strong><code>{tier_top1_name}</code></strong> 
            with <strong>{tier_top1_count:,.0f} breaches</strong>. 
            These aren't backend noise — each one represents a moment where a real customer experienced 
            a degraded or failed banking interaction.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Act III
    st.markdown(f"""
    <div class="story-chapter forward">
        <div class="chapter-label">Act III</div>
        <h2>The Path Forward — From Chaos to Control</h2>
    </div>
    """, unsafe_allow_html=True)

    col_act1, col_act2 = st.columns(2)

    with col_act1:
        st.markdown(f"""
        <div class="story-insight success">
            <h4>🔧 Immediate Actions (This Sprint)</h4>
            <p>
                <strong>1. Triage <code>{top1_name}</code></strong> — Deploy dedicated observability 
                (distributed tracing + error budget alerts) on this service immediately. Its {top1_pct:.1f}% 
                contribution means fixing it alone would eliminate ~{top1_count:,.0f} breaches.<br><br>
                <strong>2. Error-Rate Deep Dive</strong> — With {error_pct:.0f}% of breaches being error-driven, 
                prioritize exception analysis, retry-storm detection, and circuit breaker audits across the top 5 services.<br><br>
                <strong>3. Tier 1 & 2 War Room</strong> — Establish a daily breach review for customer-facing channels 
                until the {tier_total:,.0f} Tier 1 & 2 breach count drops below a target threshold.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col_act2:
        st.markdown(f"""
        <div class="story-insight">
            <h4>🏗️ Structural Improvements (Next Quarter)</h4>
            <p>
                <strong>1. SLA Budget Framework</strong> — Implement per-service error budgets. Services exceeding 
                their budget lose deployment privileges until stability improves.<br><br>
                <strong>2. Latency Guardrails</strong> — The {latency_pct:.0f}% latency breach share points to 
                missing timeout policies and backpressure mechanisms. Deploy adaptive rate limiting 
                at the API gateway layer.<br><br>
                <strong>3. Decouple Chronic Offenders</strong> — The {num_persistent} services breaching every week 
                need architectural review. Consider bulkhead isolation, async failover queues, 
                or service mesh sidecar proxies to contain blast radius.
            </p>
        </div>
        """, unsafe_allow_html=True)


    breaches_per_day = story_total / (len(story_weeks) * 7)
    st.markdown(f"""
    <div class="story-verdict">
        <h3>The Bottom Line</h3>
        <p>
            At <strong>{breaches_per_day:,.0f} SLA breaches per day</strong>, this ecosystem is bleeding reliability. 
            But the data also reveals a silver lining: the problem is <strong>concentrated, not diffuse</strong>. 
            Just <strong>3 services drive {top3_pct:.0f}%</strong> of all incidents. 
            This means targeted investment in a handful of critical services can yield outsized improvements 
            in system-wide stability. The question isn't <em>whether</em> to act — it's <em>how fast</em>.
        </p>
    </div>
    """, unsafe_allow_html=True)

conn.close()

