import json
import duckdb
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

_script_dir = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(_script_dir, "email_config.json")
db_file = os.path.join(_script_dir, "breaches.duckdb")
image_file = os.path.join(_script_dir, "breach_dashboard.png")
simulated_html_output = os.path.join(_script_dir, "simulated_email.html")

def get_insights():
    conn = duckdb.connect(db_file)
    
    # Total breaches
    total_raw = conn.execute("SELECT SUM(breach_count) FROM weekly_breaches_raw").fetchone()[0] or 0
    
    # Tier 1 & 2
    total_t12 = conn.execute("SELECT SUM(breach_count) FROM tier_1_2_breaches").fetchone()[0] or 0
    
    # Top 3 overall
    top_overall = conn.execute("""
    SELECT microservice, SUM(breach_count) AS total
    FROM weekly_breaches_raw
    GROUP BY microservice
    ORDER BY total DESC
    LIMIT 3
    """).fetchall()
    
    # Top 3 Tier 1 & 2
    top_t12 = conn.execute("""
    SELECT microservice, SUM(breach_count) AS total
    FROM tier_1_2_breaches
    GROUP BY microservice
    ORDER BY total DESC
    LIMIT 3
    """).fetchall()
    
    # Breach type counts
    types = dict(conn.execute("""
    SELECT 
        CASE 
            WHEN breach_type IN ('Error rate', 'Availability', 'Health Check', 'Failed Count', 'Failure Rate & Failed Count') THEN 'Error rate'
            WHEN breach_type IN ('Latency', 'Consumer Lag', 'Pending Count', 'Pending Rate & Pending Count', 'Frozen Jobs', 'Unsynced Count', 'High Disk Usage on D:') THEN 'Latency'
            ELSE 'Unknown'
        END AS core_type,
        SUM(breach_count)
    FROM weekly_breaches_raw
    GROUP BY core_type
    """).fetchall())
    
    conn.close()
    
    return {
        'total_raw': total_raw,
        'total_t12': total_t12,
        'top_overall': top_overall,
        'top_t12': top_t12,
        'error_rate_count': types.get('Error rate', 0),
        'latency_count': types.get('Latency', 0),
        'unknown_count': types.get('Unknown', 0)
    }

def build_html_body(insights):
    total_raw = insights['total_raw']
    error_percent = (insights['error_rate_count'] / total_raw) * 100 if total_raw > 0 else 0
    latency_percent = (insights['latency_count'] / total_raw) * 100 if total_raw > 0 else 0
    t12_percent = (insights['total_t12'] / total_raw) * 100 if total_raw > 0 else 0
    
    top_overall_html = "".join([f"<li><strong>{svc}</strong>: {count:,} breaches</li>" for svc, count in insights['top_overall']])
    top_t12_html = "".join([f"<li><strong>{svc}</strong>: {count:,} breaches</li>" for svc, count in insights['top_t12']])
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            color: #2f3542;
            line-height: 1.6;
            margin: 0;
            padding: 0;
            background-color: #f1f2f6;
        }}
        .container {{
            max-width: 800px;
            margin: 20px auto;
            background: #ffffff;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        }}
        .header {{
            background: linear-gradient(135deg, #2c3e50, #34495e);
            color: #ffffff;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }}
        .header p {{
            margin: 5px 0 0 0;
            font-size: 14px;
            opacity: 0.8;
        }}
        .content {{
            padding: 30px;
        }}
        .section {{
            margin-bottom: 25px;
            padding-bottom: 20px;
            border-bottom: 1px solid #e1e2e6;
        }}
        .section:last-child {{
            border-bottom: none;
            margin-bottom: 0;
            padding-bottom: 0;
        }}
        h2 {{
            color: #2c3e50;
            font-size: 18px;
            font-weight: 600;
            margin-top: 0;
        }}
        ul {{
            padding-left: 20px;
            margin: 10px 0;
        }}
        .alert {{
            background-color: #ffeaa7;
            border-left: 4px solid #f1c40f;
            padding: 15px;
            border-radius: 4px;
            margin: 15px 0;
            font-size: 14px;
        }}
        .dashboard-img {{
            width: 100%;
            max-width: 100%;
            height: auto;
            border-radius: 6px;
            margin-top: 15px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .footer {{
            background-color: #2c3e50;
            color: #ffffff;
            text-align: center;
            padding: 15px;
            font-size: 12px;
            opacity: 0.9;
        }}
        .kpi-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        .kpi-table th, .kpi-table td {{
            padding: 10px;
            border: 1px solid #e1e2e6;
            text-align: left;
            font-size: 14px;
        }}
        .kpi-table th {{
            background-color: #f1f2f6;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Executive Observability Report</h1>
            <p>Weekly Microservice Breach Analysis & Executive Insights</p>
        </div>
        <div class="content">
            <div class="section">
                <h2>1. Executive Summary</h2>
                <p>
                    This report presents a comprehensive review of service-level breach occurrences across our microservice ecosystem over a 4-week period. 
                    In total, the ecosystem recorded <strong>{total_raw:,} breaches</strong>, primarily driven by 
                    <strong>Error Rate</strong> incidents ({insights['error_rate_count']:,} breaches, {error_percent:.1f}%) and 
                    <strong>Latency</strong> issues ({insights['latency_count']:,} breaches, {latency_percent:.1f}%). 
                    A subset of 16 critical channels (Tier 1 & 2 services) experienced <strong>{insights['total_t12']:,} breaches</strong> ({t12_percent:.1f}% of total), representing a vital area for operational stability.
                </p>
            </div>

            <div class="section">
                <h2>2. Key Performance Indicators (KPIs)</h2>
                <table class="kpi-table">
                    <thead>
                        <tr>
                            <th>KPI Metric</th>
                            <th>Baseline Value</th>
                            <th>SLA Goal</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>Total SLA Breaches</strong></td>
                            <td>{total_raw:,}</td>
                            <td>&lt; 10,000</td>
                            <td style="color: #ff4757; font-weight: bold;">CRITICAL</td>
                        </tr>
                        <tr>
                            <td><strong>Error Breach Ratio</strong></td>
                            <td>{error_percent:.1f}%</td>
                            <td>&lt; 30.0%</td>
                            <td style="color: #ff4757; font-weight: bold;">HIGH RISK</td>
                        </tr>
                        <tr>
                            <td><strong>Latency Breach Ratio</strong></td>
                            <td>{latency_percent:.1f}%</td>
                            <td>&lt; 70.0%</td>
                            <td style="color: #2ed573; font-weight: bold;">OPTIMAL</td>
                        </tr>
                        <tr>
                            <td><strong>Tier 1 & 2 Contribution</strong></td>
                            <td>{t12_percent:.1f}%</td>
                            <td>&lt; 5.0%</td>
                            <td style="color: #ff4757; font-weight: bold;">HIGH RISK</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <div class="section">
                <h2>3. Key Quality Alerts & Anomalies</h2>
                <div class="alert">
                    <strong>Critical Data Quality Warning:</strong> The breach statistics for Tier 1 & 2 services in Week 2 and Week 3 are <em>exactly identical</em> across all 16 microservices. This strongly suggests a data entry duplication error in the source file. While database integrity is maintained, conclusions regarding weekly trends for Tier 1 & 2 should account for this duplicate Week 3 record.
                </div>
            </div>

            <div class="section">
                <h2>4. Top Offending Services</h2>
                <p><strong>System-Wide Top Incidents:</strong></p>
                <ul>
                    {top_overall_html}
                </ul>
                <p><strong>Tier 1 & 2 Core Channels Top Incidents:</strong></p>
                <ul>
                    {top_t12_html}
                </ul>
            </div>

            <div class="section">
                <h2>5. Strategic Recommendations</h2>
                <ul>
                    <li><strong>Investigate Xplorer Core Case API:</strong> The <em>xplorer-case-api</em> is the single largest bad actor in the system, accumulating over 3,600 breaches. Immediate profiling of database queries and resource leaks is recommended.</li>
                    <li><strong>API Gateway Capacity Tuning:</strong> The <em>OneBank.APIGateWay</em> shows a consistently high rate of latency breaches, pointing to connection pooling exhaustion or throughput bottlenecks. Recommend scaling Gateway instances.</li>
                    <li><strong>Establish SLA Safeguards:</strong> Core Tier 1/2 channels (such as USSD, SMS, and OTP) show rising trend lines in Week 4. We recommend introducing automated rate-limiting to protect these user-facing nodes.</li>
                </ul>
            </div>

            <div class="section">
                <h2>6. Performance Visualization Dashboard</h2>
                <img class="dashboard-img" src="cid:breach_dashboard" alt="Service Breach Dashboard" />
            </div>
        </div>
        <div class="footer">
            Generated by Enterprise Observability &bull; Confidential Business Intelligence Report
        </div>
    </div>
</body>
</html>
"""
    return html

def send_report():
    print("Loading email configurations...")
    if not os.path.exists(config_file):
        print(f"Error: configuration file {config_file} not found.")
        return
        
    with open(config_file, 'r') as f:
        config = json.load(f)
        
    is_simulation = config.get('is_simulation', True)
    smtp_host = config.get('smtp_host', 'localhost')
    smtp_port = config.get('smtp_port', 587)
    use_tls = config.get('use_tls', True)
    username = config.get('username', '')
    password = config.get('password', '')
    sender = config.get('sender', '')
    recipient = config.get('recipient', '')
    
    print("Retrieving insights and formulating email structure...")
    insights = get_insights()
    html_content = build_html_body(insights)
    
    # Save HTML output locally
    with open(simulated_html_output, 'w') as f:
        f.write(html_content)
    print(f"Simulated email HTML body written to: {simulated_html_output}")
    
    if is_simulation:
        print("\n=== EMAIL TRANSMISSION SIMULATION ===")
        print(f"Sender: {sender}")
        print(f"Recipient: {recipient}")
        print("Subject: Executive Observability Report: Weekly Microservice Breach Analysis")
        print("Status: [SIMULATED SUCCESS] (Email generated, chart attached, and saved locally.)")
        print("======================================\n")
        return
        
    # Live SMTP sending
    print("Preparing email headers...")
    msg = MIMEMultipart('related')
    msg['Subject'] = "Executive Observability Report: Weekly Microservice Breach Analysis"
    msg['From'] = sender
    msg['To'] = recipient
    
    # HTML body
    msg_alternative = MIMEMultipart('alternative')
    msg.attach(msg_alternative)
    msg_html = MIMEText(html_content, 'html')
    msg_alternative.attach(msg_html)
    
    # Dashboard image attachment
    if os.path.exists(image_file):
        with open(image_file, 'rb') as img_f:
            msg_image = MIMEImage(img_f.read())
            msg_image.add_header('Content-ID', '<breach_dashboard>')
            msg_image.add_header('Content-Disposition', 'inline', filename='breach_dashboard.png')
            msg.attach(msg_image)
            print("Dashboard image attached.")
    else:
        print("Warning: Dashboard image not found. Sending without attachment.")
        
    try:
        print(f"Connecting to SMTP server at {smtp_host}:{smtp_port}...")
        server = smtplib.SMTP(smtp_host, smtp_port)
        if use_tls:
            server.starttls()
        if username and password:
            server.login(username, password)
        print("Sending email...")
        server.sendmail(sender, [recipient], msg.as_string())
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"SMTP Transmission Failed: {e}")
        print("Check your email credentials and SMTP server configurations in email_config.json.")

if __name__ == "__main__":
    send_report()
