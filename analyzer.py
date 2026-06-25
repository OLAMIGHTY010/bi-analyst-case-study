import os
import sys
import duckdb
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import config

logger = config.setup_logging("analyzer")

def get_sorted_weeks(weeks_list: list) -> list:
    """Sort week labels."""
    def week_key(w):
        digits = ''.join(filter(str.isdigit, str(w)))
        return int(digits) if digits else 0
    return sorted(weeks_list, key=week_key)

def generate_system_dashboard(
    df_weekly_raw: pd.DataFrame,
    df_weekly_t12: pd.DataFrame,
    df_top_services_raw: pd.DataFrame,
    df_types_raw: pd.DataFrame,
    df_kpi_types: pd.DataFrame,
    total_ecosystem_breaches: float,
    total_t12_breaches: float,
    t12_percent: float,
    error_breaches: float,
    error_percent: float,
    latency_breaches: float,
    latency_percent: float,
    wow_label: str,
    wow_change: float
) -> None:
    """Generate overall system dashboard."""
    logger.info("Generating system dashboard...")
    sns.set_theme(style="whitegrid")
    plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
    plt.rcParams['font.family'] = 'sans-serif'
    
    fig = plt.figure(figsize=(18, 15))
    gs = gridspec.GridSpec(3, 4, height_ratios=[1, 4, 4])
    
    fig.suptitle('Enterprise Observability - Overall System SLA Dashboard', fontsize=24, fontweight='bold', color='#2c3e50', y=0.98)
    
    # KPI cards
    kpi_configs = [
        {"title": "TOTAL SLA BREACHES", "val": f"{total_ecosystem_breaches:,.0f}", "sub": "All system microservices", "color": "#2c3e50"},
        {"title": "ERROR BREACH RATIO", "val": f"{error_percent:.1f}%", "sub": f"{error_breaches:,.0f} incidents", "color": "#ff4757"},
        {"title": "LATENCY BREACH RATIO", "val": f"{latency_percent:.1f}%", "sub": f"{latency_breaches:,.0f} incidents", "color": "#1e90ff"},
        {"title": "TIER 1 & 2 CHANNELS", "val": f"{t12_percent:.1f}%", "sub": f"{total_t12_breaches:,.0f} core breaches", "color": "#e67e22"}
    ]
    
    for idx, kpi in enumerate(kpi_configs):
        ax = fig.add_subplot(gs[0, idx])
        ax.axis('off')
        ax.add_patch(plt.Rectangle((0.02, 0.02), 0.96, 0.96, color=kpi["color"], alpha=0.1, transform=ax.transAxes))
        ax.text(0.5, 0.7, kpi["title"], ha='center', va='center', fontsize=10, fontweight='bold', color=kpi["color"])
        ax.text(0.5, 0.4, kpi["val"], ha='center', va='center', fontsize=24, fontweight='bold', color=kpi["color"])
        ax.text(0.5, 0.15, kpi["sub"], ha='center', va='center', fontsize=8.5, style='italic', color='#7f8c8d')
        
    # Weekly trends
    ax1 = fig.add_subplot(gs[1, 0:2])
    weekly_raw_sorted = df_weekly_raw.copy()
    weekly_raw_sorted['week_num'] = weekly_raw_sorted['week'].apply(lambda x: int(''.join(filter(str.isdigit, x))) if any(c.isdigit() for c in x) else 0)
    weekly_raw_sorted = weekly_raw_sorted.sort_values('week_num').reset_index(drop=True)
    
    ax1.plot(weekly_raw_sorted['week'], weekly_raw_sorted['total_breaches'], marker='o', linewidth=3, markersize=8, color='#2f3542', label='Overall Ecosystem')
    
    if not df_weekly_t12.empty:
        weekly_t12_sorted = df_weekly_t12.copy()
        weekly_t12_sorted['week_num'] = weekly_t12_sorted['week'].apply(lambda x: int(''.join(filter(str.isdigit, x))) if any(c.isdigit() for c in x) else 0)
        weekly_t12_sorted = weekly_t12_sorted.sort_values('week_num').reset_index(drop=True)
        ax1.plot(weekly_t12_sorted['week'], weekly_t12_sorted['total_breaches'], marker='s', linewidth=3, markersize=8, color='#ff9f43', label='Tier 1 & 2 Channels')
        
    ax1.set_title('Weekly Breach Trends', fontsize=14, fontweight='bold', color='#2c3e50', pad=15)
    ax1.set_ylabel('Number of Breaches', fontsize=12)
    ax1.legend(frameon=True, facecolor='#f1f2f6', edgecolor='none')
    
    for i, row in weekly_raw_sorted.iterrows():
        ax1.annotate(f"{row['total_breaches']:,.0f}", (row['week'], row['total_breaches']), textcoords="offset points", xytext=(0,10), ha='center', fontweight='bold', color='#2f3542')
    if not df_weekly_t12.empty:
        for i, row in weekly_t12_sorted.iterrows():
            ax1.annotate(f"{row['total_breaches']:,.0f}", (row['week'], row['total_breaches']), textcoords="offset points", xytext=(0,-18), ha='center', fontweight='bold', color='#e67e22')
            
    # Breakdown by type
    ax2 = fig.add_subplot(gs[1, 2:4])
    df_types_raw['week_num'] = df_types_raw['week'].apply(lambda x: int(''.join(filter(str.isdigit, x))) if any(c.isdigit() for c in x) else 0)
    df_types_sorted = df_types_raw.sort_values('week_num')
    df_pivot_raw = df_types_sorted.pivot(index='week', columns='core_breach_type', values='total_breaches').fillna(0)
    df_pivot_raw = df_pivot_raw.reindex(get_sorted_weeks(df_pivot_raw.index))
    
    cols_order = [c for c in ['Error rate', 'Latency', 'Unknown'] if c in df_pivot_raw.columns]
    df_pivot_raw = df_pivot_raw[cols_order]
    
    color_palette = {'Error rate': '#ff4757', 'Latency': '#1e90ff', 'Unknown': '#747d8c'}
    df_pivot_raw.plot(kind='bar', stacked=True, ax=ax2, color=[color_palette.get(c, '#747d8c') for c in df_pivot_raw.columns], width=0.5)
    
    ax2.set_title('Overall Breach Classification by Week', fontsize=14, fontweight='bold', color='#2c3e50', pad=15)
    ax2.set_ylabel('Number of Breaches', fontsize=12)
    ax2.set_xlabel('')
    ax2.set_xticklabels(df_pivot_raw.index, rotation=0)
    ax2.legend(title='Breach Type', frameon=True, facecolor='#f1f2f6')
    
    for idx, (week, row) in enumerate(df_pivot_raw.iterrows()):
        cumulative = 0
        for col in df_pivot_raw.columns:
            val = row[col]
            if val > 0:
                ax2.text(idx, cumulative + val/2, f"{int(val):,}", ha='center', va='center', color='white', fontweight='bold', fontsize=9)
                cumulative += val
                
    # Pareto chart
    ax3 = fig.add_subplot(gs[2, 0:2])
    df_pareto = df_top_services_raw.copy()
    df_pareto['cum_sum'] = df_pareto['total_breaches'].cumsum()
    df_pareto['cum_pct'] = (df_pareto['cum_sum'] / total_ecosystem_breaches) * 100 if total_ecosystem_breaches > 0 else 0
    
    bars_p = ax3.bar(df_pareto['microservice'], df_pareto['total_breaches'], color='#57606f', width=0.5, label='Breach Count')
    ax3.set_title('Pareto Analysis - Cumulative System SLA Breaches', fontsize=14, fontweight='bold', color='#2c3e50', pad=15)
    ax3.set_ylabel('Individual SLA Breach Count', fontsize=12, color='#2c3e50')
    ax3.tick_params(axis='y', labelcolor='#2c3e50')
    ax3.set_xticks(range(len(df_pareto)))
    ax3.set_xticklabels(df_pareto['microservice'], rotation=35, ha='right', fontsize=9)
    
    for bar in bars_p:
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height + 50, f"{int(height):,}", ha='center', va='bottom', fontsize=8, fontweight='bold')
        
    ax3_sec = ax3.twinx()
    ax3_sec.plot(df_pareto['microservice'], df_pareto['cum_pct'], color='#ff4757', marker='o', linewidth=2.5, markersize=6, label='Cumulative %')
    ax3_sec.set_ylabel('Cumulative Percentage (%)', fontsize=12, color='#ff4757')
    ax3_sec.tick_params(axis='y', labelcolor='#ff4757')
    ax3_sec.set_ylim(0, 110)
    ax3_sec.grid(False)
    
    ax3_sec.axhline(80, color='#ff4757', linestyle='--', alpha=0.6, linewidth=1.5)
    ax3_sec.text(0, 83, '80% Pareto Cutoff (Vital Few)', color='#ff4757', fontsize=9.5, style='italic', fontweight='bold')
    
    # Top 10 bar
    ax4 = fig.add_subplot(gs[2, 2:4])
    df_top_services_raw_sorted = df_top_services_raw.head(10).sort_values(by='total_breaches', ascending=True)
    bars_top = ax4.barh(df_top_services_raw_sorted['microservice'], df_top_services_raw_sorted['total_breaches'], color='#57606f', height=0.6)
    ax4.set_title('Top 10 Incidents - System-Wide', fontsize=14, fontweight='bold', color='#2c3e50', pad=15)
    ax4.set_xlabel('Cumulative Breach Count', fontsize=12)
    
    for bar in bars_top:
        width = bar.get_width()
        ax4.text(width + 50, bar.get_y() + bar.get_height()/2, f"{int(width):,}", ha='left', va='center', fontweight='bold', color='#2f3542')
        
    plt.tight_layout()
    os.makedirs(os.path.dirname(config.OUTPUT_IMAGE_SYSTEM), exist_ok=True)
    plt.savefig(config.OUTPUT_IMAGE_SYSTEM, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f"System dashboard visualization successfully saved to: {config.OUTPUT_IMAGE_SYSTEM}")
 
def generate_tier_dashboard(
    df_weekly_t12: pd.DataFrame,
    df_top_services_t12: pd.DataFrame,
    df_types_t12: pd.DataFrame,
    df_kpi_types_t12: pd.DataFrame,
    total_t12_breaches: float,
    total_ecosystem_breaches: float,
    t12_percent: float,
    error_breaches_t12: float,
    error_percent_t12: float,
    latency_breaches_t12: float,
    latency_percent_t12: float,
    wow_label_t12: str,
    wow_change_t12: float
) -> None:
    """Generate Tier 1 & 2 dashboard."""
    logger.info("Generating Tier 1 & 2 dashboard...")
    sns.set_theme(style="whitegrid")
    plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
    plt.rcParams['font.family'] = 'sans-serif'
    
    fig = plt.figure(figsize=(18, 15))
    gs = gridspec.GridSpec(3, 4, height_ratios=[1, 4, 4])
    
    fig.suptitle('Enterprise Observability - Tier 1 & 2 Channels Dashboard', fontsize=24, fontweight='bold', color='#2c3e50', y=0.98)
    
    # KPIs
    kpi_configs = [
        {"title": "TIER 1 & 2 BREACHES", "val": f"{total_t12_breaches:,.0f}", "sub": "16 customer-facing channels", "color": "#e67e22"},
        {"title": "ERROR BREACH RATIO", "val": f"{error_percent_t12:.1f}%", "sub": f"{error_breaches_t12:,.0f} incidents", "color": "#ff4757"},
        {"title": "LATENCY BREACH RATIO", "val": f"{latency_percent_t12:.1f}%", "sub": f"{latency_breaches_t12:,.0f} incidents", "color": "#1e90ff"},
        {"title": "ECOSYSTEM SHARE", "val": f"{t12_percent:.1f}%", "sub": f"of total {total_ecosystem_breaches:,.0f} breaches", "color": "#2c3e50"}
    ]
    
    for idx, kpi in enumerate(kpi_configs):
        ax = fig.add_subplot(gs[0, idx])
        ax.axis('off')
        ax.add_patch(plt.Rectangle((0.02, 0.02), 0.96, 0.96, color=kpi["color"], alpha=0.1, transform=ax.transAxes))
        ax.text(0.5, 0.7, kpi["title"], ha='center', va='center', fontsize=10, fontweight='bold', color=kpi["color"])
        ax.text(0.5, 0.4, kpi["val"], ha='center', va='center', fontsize=24, fontweight='bold', color=kpi["color"])
        ax.text(0.5, 0.15, kpi["sub"], ha='center', va='center', fontsize=8.5, style='italic', color='#7f8c8d')
        
    # Weekly trends
    ax1 = fig.add_subplot(gs[1, 0:2])
    weekly_t12_sorted = df_weekly_t12.copy()
    weekly_t12_sorted['week_num'] = weekly_t12_sorted['week'].apply(lambda x: int(''.join(filter(str.isdigit, x))) if any(c.isdigit() for c in x) else 0)
    weekly_t12_sorted = weekly_t12_sorted.sort_values('week_num').reset_index(drop=True)
    
    ax1.plot(weekly_t12_sorted['week'], weekly_t12_sorted['total_breaches'], marker='s', linewidth=3, markersize=8, color='#ff9f43', label='Tier 1 & 2 Channels')
    ax1.set_title('Weekly Breach Trends (Tier 1 & 2)', fontsize=14, fontweight='bold', color='#2c3e50', pad=15)
    ax1.set_ylabel('Number of Breaches', fontsize=12)
    ax1.legend(frameon=True, facecolor='#f1f2f6', edgecolor='none')
    
    for i, row in weekly_t12_sorted.iterrows():
        ax1.annotate(f"{row['total_breaches']:,.0f}", (row['week'], row['total_breaches']), textcoords="offset points", xytext=(0,10), ha='center', fontweight='bold', color='#e67e22')
        
    # Classification
    ax2 = fig.add_subplot(gs[1, 2:4])
    df_types_t12['week_num'] = df_types_t12['week'].apply(lambda x: int(''.join(filter(str.isdigit, x))) if any(c.isdigit() for c in x) else 0)
    df_types_t12_sorted = df_types_t12.sort_values('week_num')
    df_pivot_t12 = df_types_t12_sorted.pivot(index='week', columns='core_breach_type', values='total_breaches').fillna(0)
    df_pivot_t12 = df_pivot_t12.reindex(get_sorted_weeks(df_pivot_t12.index))
    
    cols_order = [c for c in ['Error rate', 'Latency', 'Unknown'] if c in df_pivot_t12.columns]
    df_pivot_t12 = df_pivot_t12[cols_order]
    
    color_palette = {'Error rate': '#ff4757', 'Latency': '#1e90ff', 'Unknown': '#747d8c'}
    df_pivot_t12.plot(kind='bar', stacked=True, ax=ax2, color=[color_palette.get(c, '#747d8c') for c in df_pivot_t12.columns], width=0.5)
    
    ax2.set_title('Tier 1 & 2 Breach Classification by Week', fontsize=14, fontweight='bold', color='#2c3e50', pad=15)
    ax2.set_ylabel('Number of Breaches', fontsize=12)
    ax2.set_xlabel('')
    ax2.set_xticklabels(df_pivot_t12.index, rotation=0)
    ax2.legend(title='Breach Type', frameon=True, facecolor='#f1f2f6')
    
    for idx, (week, row) in enumerate(df_pivot_t12.iterrows()):
        cumulative = 0
        for col in df_pivot_t12.columns:
            val = row[col]
            if val > 0:
                ax2.text(idx, cumulative + val/2, f"{int(val):,}", ha='center', va='center', color='white', fontweight='bold', fontsize=9)
                cumulative += val
                
    # Pareto
    ax3 = fig.add_subplot(gs[2, 0:2])
    df_pareto_t12 = df_top_services_t12.copy()
    df_pareto_t12['cum_sum'] = df_pareto_t12['total_breaches'].cumsum()
    df_pareto_t12['cum_pct'] = (df_pareto_t12['cum_sum'] / total_t12_breaches) * 100 if total_t12_breaches > 0 else 0
    
    bars_p = ax3.bar(df_pareto_t12['microservice'], df_pareto_t12['total_breaches'], color='#e67e22', width=0.5, label='Breach Count')
    ax3.set_title('Pareto Analysis - Tier 1 & 2 Customer Channels', fontsize=14, fontweight='bold', color='#2c3e50', pad=15)
    ax3.set_ylabel('Individual SLA Breach Count', fontsize=12, color='#2c3e50')
    ax3.tick_params(axis='y', labelcolor='#2c3e50')
    ax3.set_xticks(range(len(df_pareto_t12)))
    ax3.set_xticklabels(df_pareto_t12['microservice'], rotation=35, ha='right', fontsize=9)
    
    for bar in bars_p:
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height + 10, f"{int(height):,}", ha='center', va='bottom', fontsize=8, fontweight='bold')
        
    ax3_sec = ax3.twinx()
    ax3_sec.plot(df_pareto_t12['microservice'], df_pareto_t12['cum_pct'], color='#ff4757', marker='o', linewidth=2.5, markersize=6, label='Cumulative %')
    ax3_sec.set_ylabel('Cumulative Percentage (%)', fontsize=12, color='#ff4757')
    ax3_sec.tick_params(axis='y', labelcolor='#ff4757')
    ax3_sec.set_ylim(0, 110)
    ax3_sec.grid(False)
    
    ax3_sec.axhline(80, color='#ff4757', linestyle='--', alpha=0.6, linewidth=1.5)
    ax3_sec.text(0, 83, '80% Pareto Cutoff (Vital Few)', color='#ff4757', fontsize=9.5, style='italic', fontweight='bold')
    
    # Top 10 bar
    ax4 = fig.add_subplot(gs[2, 2:4])
    df_t12_sorted = df_top_services_t12.sort_values(by='total_breaches', ascending=True)
    bars_t12 = ax4.barh(df_t12_sorted['microservice'], df_t12_sorted['total_breaches'], color='#f0932b', height=0.6)
    ax4.set_title('Top Offenders - Tier 1 & 2 Channels', fontsize=14, fontweight='bold', color='#2c3e50', pad=15)
    ax4.set_xlabel('Cumulative Breach Count', fontsize=12)
    
    for bar in bars_t12:
        width = bar.get_width()
        ax4.text(width + 5, bar.get_y() + bar.get_height()/2, f"{int(width):,}", ha='left', va='center', fontweight='bold', color='#2f3542')
        
    plt.tight_layout()
    os.makedirs(os.path.dirname(config.OUTPUT_IMAGE_TIER), exist_ok=True)
    plt.savefig(config.OUTPUT_IMAGE_TIER, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f"Tier 1 & 2 dashboard saved to: {config.OUTPUT_IMAGE_TIER}")

def run_analysis() -> None:
    """Run analytics on DuckDB data."""
    logger.info("Connecting to DuckDB database for analysis...")
    if not os.path.exists(config.DB_FILE):
        logger.critical(f"DuckDB database file not found at: {config.DB_FILE}")
        raise FileNotFoundError(f"Missing analytical database: {config.DB_FILE}")
        
    conn = None
    try:
        conn = duckdb.connect(config.DB_FILE, read_only=True)
        
        # weekly totals
        df_weekly_raw = conn.execute("""
            SELECT week, SUM(breach_count) AS total_breaches
            FROM weekly_breaches_raw
            GROUP BY week
            ORDER BY week
        """).df()
        
        # weekly t12
        df_weekly_t12 = conn.execute("""
            SELECT week, SUM(breach_count) AS total_breaches
            FROM tier_1_2_breaches
            GROUP BY week
            ORDER BY week
        """).df()
        
        # top 10 raw
        df_top_services_raw = conn.execute("""
            SELECT microservice, SUM(breach_count) AS total_breaches
            FROM weekly_breaches_raw
            GROUP BY microservice
            ORDER BY total_breaches DESC
            LIMIT 10
        """).df()
        
        # top 10 t12
        df_top_services_t12 = conn.execute("""
            SELECT microservice, SUM(breach_count) AS total_breaches
            FROM tier_1_2_breaches
            GROUP BY microservice
            ORDER BY total_breaches DESC
            LIMIT 10
        """).df()
        
        # classification raw
        df_types_raw = conn.execute("""
            SELECT week, core_breach_type, SUM(breach_count) AS total_breaches
            FROM weekly_breaches_raw
            GROUP BY week, core_breach_type
            ORDER BY week, core_breach_type
        """).df()
        
        # classification totals
        df_kpi_types = conn.execute("""
            SELECT core_breach_type, SUM(breach_count) AS total_breaches
            FROM weekly_breaches_raw
            GROUP BY core_breach_type
        """).df()
        
        # classification t12
        df_types_t12 = conn.execute("""
            SELECT week, core_breach_type, SUM(breach_count) AS total_breaches
            FROM tier_1_2_breaches
            GROUP BY week, core_breach_type
            ORDER BY week, core_breach_type
        """).df()
        
        # classification t12 totals
        df_kpi_types_t12 = conn.execute("""
            SELECT core_breach_type, SUM(breach_count) AS total_breaches
            FROM tier_1_2_breaches
            GROUP BY core_breach_type
        """).df()
        
        conn.close()
        conn = None
        
        if df_weekly_raw.empty:
            logger.error("No weekly breach data retrieved.")
            return
            
        # KPIs
        total_ecosystem_breaches = df_weekly_raw['total_breaches'].sum()
        total_t12_breaches = df_weekly_t12['total_breaches'].sum() if not df_weekly_t12.empty else 0
        t12_percent = (total_t12_breaches / total_ecosystem_breaches) * 100 if total_ecosystem_breaches > 0 else 0
        
        error_breaches = df_kpi_types.loc[df_kpi_types['core_breach_type'] == 'Error rate', 'total_breaches'].values
        error_breaches = error_breaches[0] if len(error_breaches) > 0 else 0
        error_percent = (error_breaches / total_ecosystem_breaches) * 100 if total_ecosystem_breaches > 0 else 0
        
        latency_breaches = df_kpi_types.loc[df_kpi_types['core_breach_type'] == 'Latency', 'total_breaches'].values
        latency_breaches = latency_breaches[0] if len(latency_breaches) > 0 else 0
        latency_percent = (latency_breaches / total_ecosystem_breaches) * 100 if total_ecosystem_breaches > 0 else 0
        
        # WoW calculations
        sorted_weeks = get_sorted_weeks(df_weekly_raw['week'].unique())
        if len(sorted_weeks) >= 2:
            latest_week = sorted_weeks[-1]
            prev_week = sorted_weeks[-2]
            
            latest_val = df_weekly_raw.loc[df_weekly_raw['week'] == latest_week, 'total_breaches'].values[0]
            prev_val = df_weekly_raw.loc[df_weekly_raw['week'] == prev_week, 'total_breaches'].values[0]
            
            wow_change = ((latest_val - prev_val) / prev_val) * 100 if prev_val > 0 else 0.0
            wow_label = f"{latest_week} vs {prev_week} WoW Change"
        else:
            logger.warning("Fewer than 2 weeks of data available.")
            wow_change = 0.0
            latest_week = sorted_weeks[0] if len(sorted_weeks) > 0 else "N/A"
            prev_week = "N/A"
            wow_label = "WoW Change"
            
        logger.info("--- Executive Statistics Summarized ---")
        logger.info(f"Total Breaches: {total_ecosystem_breaches:,.0f}")
        logger.info(f"Error Breaches: {error_breaches:,.0f} ({error_percent:.1f}%)")
        logger.info(f"Latency Breaches: {latency_breaches:,.0f} ({latency_percent:.1f}%)")
        logger.info(f"Tier 1 & 2 Breaches: {total_t12_breaches:,.0f} ({t12_percent:.1f}%)")
        logger.info(f"{wow_label}: {wow_change:+.1f}%")
        
        # Tier 1 & 2 KPIs
        error_breaches_t12 = df_kpi_types_t12.loc[df_kpi_types_t12['core_breach_type'] == 'Error rate', 'total_breaches'].values
        error_breaches_t12 = error_breaches_t12[0] if len(error_breaches_t12) > 0 else 0
        error_percent_t12 = (error_breaches_t12 / total_t12_breaches) * 100 if total_t12_breaches > 0 else 0
        
        latency_breaches_t12 = df_kpi_types_t12.loc[df_kpi_types_t12['core_breach_type'] == 'Latency', 'total_breaches'].values
        latency_breaches_t12 = latency_breaches_t12[0] if len(latency_breaches_t12) > 0 else 0
        latency_percent_t12 = (latency_breaches_t12 / total_t12_breaches) * 100 if total_t12_breaches > 0 else 0
 
        # Tier 1 & 2 WoW
        sorted_weeks_t12 = get_sorted_weeks(df_weekly_t12['week'].unique())
        if len(sorted_weeks_t12) >= 2:
            latest_week_t12 = sorted_weeks_t12[-1]
            prev_week_t12 = sorted_weeks_t12[-2]
            
            latest_val_t12 = df_weekly_t12.loc[df_weekly_t12['week'] == latest_week_t12, 'total_breaches'].values[0]
            prev_val_t12 = df_weekly_t12.loc[df_weekly_t12['week'] == prev_week_t12, 'total_breaches'].values[0]
            
            wow_change_t12 = ((latest_val_t12 - prev_val_t12) / prev_val_t12) * 100 if prev_val_t12 > 0 else 0.0
            wow_label_t12 = f"{latest_week_t12} vs {prev_week_t12} WoW Change (Tier 1 & 2)"
        else:
            wow_change_t12 = 0.0
            wow_label_t12 = "WoW Change (Tier 1 & 2)"
 
        generate_system_dashboard(
            df_weekly_raw=df_weekly_raw,
            df_weekly_t12=df_weekly_t12,
            df_top_services_raw=df_top_services_raw,
            df_types_raw=df_types_raw,
            df_kpi_types=df_kpi_types,
            total_ecosystem_breaches=total_ecosystem_breaches,
            total_t12_breaches=total_t12_breaches,
            t12_percent=t12_percent,
            error_breaches=error_breaches,
            error_percent=error_percent,
            latency_breaches=latency_breaches,
            latency_percent=latency_percent,
            wow_label=wow_label,
            wow_change=wow_change
        )
        
        generate_tier_dashboard(
            df_weekly_t12=df_weekly_t12,
            df_top_services_t12=df_top_services_t12,
            df_types_t12=df_types_t12,
            df_kpi_types_t12=df_kpi_types_t12,
            total_t12_breaches=total_t12_breaches,
            total_ecosystem_breaches=total_ecosystem_breaches,
            t12_percent=t12_percent,
            error_breaches_t12=error_breaches_t12,
            error_percent_t12=error_percent_t12,
            latency_breaches_t12=latency_breaches_t12,
            latency_percent_t12=latency_percent_t12,
            wow_label_t12=wow_label_t12,
            wow_change_t12=wow_change_t12
        )
        
    except Exception as e:
        logger.exception("An error occurred during dashboard generation.")
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    run_analysis()
