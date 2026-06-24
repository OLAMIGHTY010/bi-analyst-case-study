import duckdb
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import os

_script_dir = os.path.dirname(os.path.abspath(__file__))
db_file = os.path.join(_script_dir, "breaches.duckdb")
output_img = os.path.join(_script_dir, "breach_dashboard.png")

def run_analysis():
    print("Running analysis queries using DuckDB...")
    conn = duckdb.connect(db_file, read_only=True)
    
    # Overall weekly breach counts
    df_weekly_raw = conn.execute("""
    SELECT week, SUM(breach_count) AS total_breaches
    FROM weekly_breaches_raw
    GROUP BY week
    ORDER BY week
    """).df()
    
    # Tier 1 & 2 weekly breach counts
    df_weekly_t12 = conn.execute("""
    SELECT week, SUM(breach_count) AS total_breaches
    FROM tier_1_2_breaches
    GROUP BY week
    ORDER BY week
    """).df()
    
    # Top 10 microservices in weekly raw
    df_top_services_raw = conn.execute("""
    SELECT microservice, SUM(breach_count) AS total_breaches
    FROM weekly_breaches_raw
    GROUP BY microservice
    ORDER BY total_breaches DESC
    LIMIT 10
    """).df()
    
    # Top 10 microservices in Tier 1 & 2
    df_top_services_t12 = conn.execute("""
    SELECT microservice, SUM(breach_count) AS total_breaches
    FROM tier_1_2_breaches
    GROUP BY microservice
    ORDER BY total_breaches DESC
    LIMIT 10
    """).df()
    
    # Breach type breakdown by week
    df_types_raw = conn.execute("""
    SELECT 
        week,
        CASE 
            WHEN breach_type IN ('Error rate', 'Availability', 'Health Check', 'Failed Count', 'Failure Rate & Failed Count') THEN 'Error rate'
            WHEN breach_type IN ('Latency', 'Consumer Lag', 'Pending Count', 'Pending Rate & Pending Count', 'Frozen Jobs', 'Unsynced Count', 'High Disk Usage on D:') THEN 'Latency'
            ELSE 'Unknown'
        END AS core_breach_type,
        SUM(breach_count) AS total_breaches
    FROM weekly_breaches_raw
    GROUP BY week, core_breach_type
    ORDER BY week, core_breach_type
    """).df()
    
    # Breach type totals for KPIs
    df_kpi_types = conn.execute("""
    SELECT 
        CASE 
            WHEN breach_type IN ('Error rate', 'Availability', 'Health Check', 'Failed Count', 'Failure Rate & Failed Count') THEN 'Error rate'
            WHEN breach_type IN ('Latency', 'Consumer Lag', 'Pending Count', 'Pending Rate & Pending Count', 'Frozen Jobs', 'Unsynced Count', 'High Disk Usage on D:') THEN 'Latency'
            ELSE 'Unknown'
        END AS core_breach_type,
        SUM(breach_count) AS total_breaches
    FROM weekly_breaches_raw
    GROUP BY core_breach_type
    """).df()
    
    conn.close()
    
    # KPI figures
    total_ecosystem_breaches = df_weekly_raw['total_breaches'].sum()
    total_t12_breaches = df_weekly_t12['total_breaches'].sum()
    t12_percent = (total_t12_breaches / total_ecosystem_breaches) * 100
    
    error_breaches = df_kpi_types.loc[df_kpi_types['core_breach_type'] == 'Error rate', 'total_breaches'].values
    error_breaches = error_breaches[0] if len(error_breaches) > 0 else 0
    error_percent = (error_breaches / total_ecosystem_breaches) * 100
    
    latency_breaches = df_kpi_types.loc[df_kpi_types['core_breach_type'] == 'Latency', 'total_breaches'].values
    latency_breaches = latency_breaches[0] if len(latency_breaches) > 0 else 0
    latency_percent = (latency_breaches / total_ecosystem_breaches) * 100
    
    # WoW change for latest week
    w3_val = df_weekly_raw.loc[df_weekly_raw['week'] == 'Week 3', 'total_breaches'].values[0]
    w4_val = df_weekly_raw.loc[df_weekly_raw['week'] == 'Week 4', 'total_breaches'].values[0]
    wow_change_w4 = ((w4_val - w3_val) / w3_val) * 100
    
    print("\n--- Summary Statistics (Overall) ---")
    print(df_weekly_raw)
    print("\n--- KPI Summary Metrics ---")
    print(f"Total Breaches: {total_ecosystem_breaches:,.0f}")
    print(f"Error Breaches: {error_breaches:,.0f} ({error_percent:.1f}%)")
    print(f"Latency Breaches: {latency_breaches:,.0f} ({latency_percent:.1f}%)")
    print(f"Tier 1 & 2 Breaches: {total_t12_breaches:,.0f} ({t12_percent:.1f}%)")
    print(f"Week 4 WoW Change: {wow_change_w4:+.1f}%")
    
    print("\nCreating visual dashboard...")
    
    # Chart style
    sns.set_theme(style="whitegrid")
    plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
    plt.rcParams['font.family'] = 'sans-serif'
    
    # Layout
    fig = plt.figure(figsize=(18, 15))
    gs = gridspec.GridSpec(3, 4, height_ratios=[1, 4, 4])
    
    fig.suptitle('Enterprise Observability - Service Breach Dashboard', fontsize=24, fontweight='bold', color='#2c3e50', y=0.98)
    
    # KPI cards
    ax_kpi1 = fig.add_subplot(gs[0, 0])
    ax_kpi1.axis('off')
    ax_kpi1.add_patch(plt.Rectangle((0.02, 0.02), 0.96, 0.96, color='#2c3e50', alpha=0.1, transform=ax_kpi1.transAxes))
    ax_kpi1.text(0.5, 0.7, 'TOTAL SLA BREACHES', ha='center', va='center', fontsize=10, fontweight='bold', color='#57606f')
    ax_kpi1.text(0.5, 0.4, f"{total_ecosystem_breaches:,.0f}", ha='center', va='center', fontsize=24, fontweight='bold', color='#2c3e50')
    ax_kpi1.text(0.5, 0.15, 'All system microservices', ha='center', va='center', fontsize=8.5, style='italic', color='#7f8c8d')


    ax_kpi2 = fig.add_subplot(gs[0, 1])
    ax_kpi2.axis('off')
    ax_kpi2.add_patch(plt.Rectangle((0.02, 0.02), 0.96, 0.96, color='#ff4757', alpha=0.1, transform=ax_kpi2.transAxes))
    ax_kpi2.text(0.5, 0.7, 'ERROR BREACH RATIO', ha='center', va='center', fontsize=10, fontweight='bold', color='#ff4757')
    ax_kpi2.text(0.5, 0.4, f"{error_percent:.1f}%", ha='center', va='center', fontsize=24, fontweight='bold', color='#ff4757')
    ax_kpi2.text(0.5, 0.15, f"{error_breaches:,.0f} incidents", ha='center', va='center', fontsize=8.5, color='#7f8c8d')


    ax_kpi3 = fig.add_subplot(gs[0, 2])
    ax_kpi3.axis('off')
    ax_kpi3.add_patch(plt.Rectangle((0.02, 0.02), 0.96, 0.96, color='#1e90ff', alpha=0.1, transform=ax_kpi3.transAxes))
    ax_kpi3.text(0.5, 0.7, 'LATENCY BREACH RATIO', ha='center', va='center', fontsize=10, fontweight='bold', color='#1e90ff')
    ax_kpi3.text(0.5, 0.4, f"{latency_percent:.1f}%", ha='center', va='center', fontsize=24, fontweight='bold', color='#1e90ff')
    ax_kpi3.text(0.5, 0.15, f"{latency_breaches:,.0f} incidents", ha='center', va='center', fontsize=8.5, color='#7f8c8d')


    ax_kpi4 = fig.add_subplot(gs[0, 3])
    ax_kpi4.axis('off')
    ax_kpi4.add_patch(plt.Rectangle((0.02, 0.02), 0.96, 0.96, color='#ff9f43', alpha=0.1, transform=ax_kpi4.transAxes))
    ax_kpi4.text(0.5, 0.7, 'TIER 1 & 2 CHANNELS', ha='center', va='center', fontsize=10, fontweight='bold', color='#e67e22')
    ax_kpi4.text(0.5, 0.4, f"{t12_percent:.1f}%", ha='center', va='center', fontsize=24, fontweight='bold', color='#e67e22')
    ax_kpi4.text(0.5, 0.15, f"{total_t12_breaches:,.0f} core breaches", ha='center', va='center', fontsize=8.5, color='#7f8c8d')

    # Chart 1: Weekly trends
    ax1 = fig.add_subplot(gs[1, 0:2])
    ax1.plot(df_weekly_raw['week'], df_weekly_raw['total_breaches'], marker='o', linewidth=3, markersize=8, color='#2f3542', label='Overall Ecosystem')
    ax1.plot(df_weekly_t12['week'], df_weekly_t12['total_breaches'], marker='s', linewidth=3, markersize=8, color='#ff9f43', label='Tier 1 & 2 Channels')
    ax1.set_title('Weekly Breach Trends', fontsize=14, fontweight='semibold', color='#2c3e50', pad=15)
    ax1.set_ylabel('Number of Breaches', fontsize=12)
    ax1.legend(frameon=True, facecolor='#f1f2f6', edgecolor='none')
    # Data labels
    for i, txt in enumerate(df_weekly_raw['total_breaches']):
        ax1.annotate(f"{txt:,.0f}", (df_weekly_raw['week'][i], df_weekly_raw['total_breaches'][i]), textcoords="offset points", xytext=(0,10), ha='center', fontweight='bold', color='#2f3542')
    for i, txt in enumerate(df_weekly_t12['total_breaches']):
        ax1.annotate(f"{txt:,.0f}", (df_weekly_t12['week'][i], df_weekly_t12['total_breaches'][i]), textcoords="offset points", xytext=(0,-15), ha='center', fontweight='bold', color='#e67e22')

    # Chart 2: Breach type breakdown
    ax2 = fig.add_subplot(gs[1, 2:4])

    df_pivot_raw = df_types_raw.pivot(index='week', columns='core_breach_type', values='total_breaches').fillna(0)

    cols_order = [c for c in ['Error rate', 'Latency', 'Unknown'] if c in df_pivot_raw.columns]
    df_pivot_raw = df_pivot_raw[cols_order]
    
    color_palette = {
        'Error rate': '#ff4757',  # Coral red
        'Latency': '#1e90ff',     # Dodger blue
        'Unknown': '#747d8c'      # Slate grey
    }
    
    df_pivot_raw.plot(kind='bar', stacked=True, ax=ax2, color=[color_palette.get(c, '#747d8c') for c in df_pivot_raw.columns], width=0.5)
    ax2.set_title('Overall Breach Classification by Week', fontsize=14, fontweight='semibold', color='#2c3e50', pad=15)
    ax2.set_ylabel('Number of Breaches', fontsize=12)
    ax2.set_xlabel('')
    ax2.set_xticklabels(df_pivot_raw.index, rotation=0)
    ax2.legend(title='Breach Type', frameon=True, facecolor='#f1f2f6')

    for idx, (week, row) in enumerate(df_pivot_raw.iterrows()):
        cumulative = 0
        for col in df_pivot_raw.columns:
            val = row[col]
            if val > 0:
                ax2.text(idx, cumulative + val/2, f"{int(val):,}", ha='center', va='center', color='white', fontweight='bold')
                cumulative += val

    # Chart 3: Top 10 overall
    ax3 = fig.add_subplot(gs[2, 0:2])
    df_top_services_raw_sorted = df_top_services_raw.sort_values(by='total_breaches', ascending=True)
    bars_raw = ax3.barh(df_top_services_raw_sorted['microservice'], df_top_services_raw_sorted['total_breaches'], color='#57606f', height=0.6)
    ax3.set_title('Top 10 Incidents - Overall Ecosystem', fontsize=14, fontweight='semibold', color='#2c3e50', pad=15)
    ax3.set_xlabel('Cumulative Breach Count', fontsize=12)

    for bar in bars_raw:
        width = bar.get_width()
        ax3.text(width + 10, bar.get_y() + bar.get_height()/2, f"{int(width):,}", ha='left', va='center', fontweight='bold', color='#2f3542')

    # Chart 4: Top 10 Tier 1 & 2
    ax4 = fig.add_subplot(gs[2, 2:4])
    df_top_services_t12_sorted = df_top_services_t12.sort_values(by='total_breaches', ascending=True)
    bars_t12 = ax4.barh(df_top_services_t12_sorted['microservice'], df_top_services_t12_sorted['total_breaches'], color='#f0932b', height=0.6)
    ax4.set_title('Top 10 Incidents - Tier 1 & 2 Channels', fontsize=14, fontweight='semibold', color='#2c3e50', pad=15)
    ax4.set_xlabel('Cumulative Breach Count', fontsize=12)

    for bar in bars_t12:
        width = bar.get_width()
        ax4.text(width + 5, bar.get_y() + bar.get_height()/2, f"{int(width):,}", ha='left', va='center', fontweight='bold', color='#2f3542')

    plt.tight_layout()
    
    # Save
    os.makedirs(os.path.dirname(output_img), exist_ok=True)
    plt.savefig(output_img, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Dashboard saved to: {output_img}")

if __name__ == "__main__":
    run_analysis()
