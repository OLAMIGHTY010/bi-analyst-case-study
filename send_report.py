import os
import sys
import json
import smtplib
import duckdb
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import config

logger = config.setup_logging("send_report")

def get_insights() -> dict:
    """Query DuckDB for email metrics."""
    logger.info("Querying DuckDB insights...")
    if not os.path.exists(config.DB_FILE):
        logger.critical(f"DuckDB file not found at {config.DB_FILE}.")
        raise FileNotFoundError(f"Database file not found: {config.DB_FILE}")
        
    conn = None
    try:
        conn = duckdb.connect(config.DB_FILE, read_only=True)
        
        total_raw = conn.execute("SELECT SUM(breach_count) FROM weekly_breaches_raw").fetchone()[0] or 0
        total_t12 = conn.execute("SELECT SUM(breach_count) FROM tier_1_2_breaches").fetchone()[0] or 0
        
        top_overall = conn.execute("""
            SELECT microservice, SUM(breach_count) AS total
            FROM weekly_breaches_raw
            GROUP BY microservice
            ORDER BY total DESC
            LIMIT 3
        """).fetchall()
        
        top_t12 = conn.execute("""
            SELECT microservice, SUM(breach_count) AS total
            FROM tier_1_2_breaches
            GROUP BY microservice
            ORDER BY total DESC
            LIMIT 3
        """).fetchall()
        
        types = dict(conn.execute("""
            SELECT core_breach_type, SUM(breach_count)
            FROM weekly_breaches_raw
            GROUP BY core_breach_type
        """).fetchall())
        
        conn.close()
        conn = None
        
        return {
            'total_raw': total_raw,
            'total_t12': total_t12,
            'top_overall': top_overall,
            'top_t12': top_t12,
            'error_rate_count': types.get('Error rate', 0),
            'latency_count': types.get('Latency', 0),
            'unknown_count': types.get('Unknown', 0)
        }
    except Exception as e:
        logger.exception("Failed to query database insights.")
        raise
    finally:
        if conn:
            conn.close()


def generate_recommendations(insights: dict) -> list:
    """Generate SRE recommendations."""
    recommendations = []
    
    top_overall = insights['top_overall']
    top_t12 = insights['top_t12']
    
    if top_overall:
        top_service, breaches = top_overall[0]
        recommendations.append(
            f"<strong>Audit {top_service}:</strong> This microservice is the system's worst offender, "
            f"accumulating <strong>{breaches:,} SLA breaches</strong>. Immediate database query profiling, "
            f"connection pool size validation, and exception handling reviews are highly recommended."
        )
        
    if len(top_overall) >= 2:
        sec_service, breaches = top_overall[1]
        recommendations.append(
            f"<strong>Scale {sec_service}:</strong> With <strong>{breaches:,} SLA breaches</strong>, "
            f"this service exhibits symptoms of capacity limits. SRE recommends scaling container instances "
            f"and tuning cache eviction intervals to mitigate the latency blast radius."
        )
        
    if top_t12:
        t12_service, breaches = top_t12[0]
        recommendations.append(
            f"<strong>Contain Blast Radius for {t12_service}:</strong> The critical customer-facing channel "
            f"exceeded SLA targets with <strong>{breaches:,} breaches</strong>. Implement API Gateway circuit "
            f"breakers and graceful degradation fallbacks to isolate downstream outages."
        )
        
    if not recommendations:
        recommendations.append("All service metrics are within baseline limits. Continue standard infrastructure health monitoring.")
        
    return recommendations


def build_html_body(insights: dict) -> str:
    """Create HTML body."""
    total_raw = insights['total_raw']
    error_percent = (insights['error_rate_count'] / total_raw) * 100 if total_raw > 0 else 0
    latency_percent = (insights['latency_count'] / total_raw) * 100 if total_raw > 0 else 0
    t12_percent = (insights['total_t12'] / total_raw) * 100 if total_raw > 0 else 0
    
    top_overall_html = "".join([f"<li><strong>{svc}</strong>: {count:,} breaches</li>" for svc, count in insights['top_overall']])
    top_t12_html = "".join([f"<li><strong>{svc}</strong>: {count:,} breaches</li>" for svc, count in insights['top_t12']])
    
    recs = generate_recommendations(insights)
    recommendations_html = "".join([f"<li>{r}</li>" for r in recs])
    
    sla = config.SLA_THRESHOLDS
    
    total_status = "CRITICAL" if total_raw >= sla["total_breaches"] else "OPTIMAL"
    total_color = "#ff4757" if total_status == "CRITICAL" else "#2ed573"
    
    error_status = "HIGH RISK" if error_percent >= sla["error_breach_ratio"] else "OPTIMAL"
    error_color = "#ff4757" if error_status == "HIGH RISK" else "#2ed573"
    
    latency_status = "HIGH RISK" if latency_percent >= sla["latency_breach_ratio"] else "OPTIMAL"
    latency_color = "#ff4757" if latency_status == "HIGH RISK" else "#2ed573"
    
    t12_status = "HIGH RISK" if t12_percent >= sla["tier_1_2_contribution"] else "OPTIMAL"
    t12_color = "#ff4757" if t12_status == "HIGH RISK" else "#2ed573"
    
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
                    This report presents a comprehensive review of service-level breach occurrences across our microservice ecosystem. 
                    In total, the ecosystem recorded <strong>{total_raw:,} breaches</strong>, primarily driven by 
                    <strong>Error Rate</strong> incidents ({insights['error_rate_count']:,} breaches, {error_percent:.1f}%) and 
                    <strong>Latency</strong> issues ({insights['latency_count']:,} breaches, {latency_percent:.1f}%). 
                    Critical channels (Tier 1 & 2 services) experienced <strong>{insights['total_t12']:,} breaches</strong> ({t12_percent:.1f}% of total), representing a vital area for operational stability.
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
                            <td>&lt; {sla['total_breaches']:,}</td>
                            <td style="color: {total_color}; font-weight: bold;">{total_status}</td>
                        </tr>
                        <tr>
                            <td><strong>Error Breach Ratio</strong></td>
                            <td>{error_percent:.1f}%</td>
                            <td>&lt; {sla['error_breach_ratio']:.1f}%</td>
                            <td style="color: {error_color}; font-weight: bold;">{error_status}</td>
                        </tr>
                        <tr>
                            <td><strong>Latency Breach Ratio</strong></td>
                            <td>{latency_percent:.1f}%</td>
                            <td>&lt; {sla['latency_breach_ratio']:.1f}%</td>
                            <td style="color: {latency_color}; font-weight: bold;">{latency_status}</td>
                        </tr>
                        <tr>
                            <td><strong>Tier 1 & 2 Contribution</strong></td>
                            <td>{t12_percent:.1f}%</td>
                            <td>&lt; {sla['tier_1_2_contribution']:.1f}%</td>
                            <td style="color: {t12_color}; font-weight: bold;">{t12_status}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <div class="section">
                <h2>3. Key Quality Alerts & Anomalies</h2>
                <div class="alert">
                    <strong>Critical Data Quality Warning:</strong> Data analysis detected duplicate weekly breach counts across all 16 microservices between multiple weeks in the Tier 1 & 2 sheets. This strongly points to a copy-paste clerical duplication error in the source Excel file. Although database integrity and table indexing have been preserved, weekly trends and KPI status reports for critical channels should be evaluated with awareness of this duplicate record.
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
                    {recommendations_html}
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


def parse_email_list(value) -> list:
    """Helper to parse a string, comma-separated string, or list of strings into a list of cleaned email addresses."""
    if not value:
        return []
    if isinstance(value, list):
        return [email.strip() for email in value if isinstance(email, str) and email.strip()]
    if isinstance(value, str):
        return [email.strip() for email in value.split(',') if email.strip()]
    return []


def send_report() -> None:
    """Generates executive summary from DuckDB, formats HTML, and dispatches via SMTP or Simulation."""
    logger.info("Initializing report dispatcher...")
    
    if not os.path.exists(config.EMAIL_CONFIG_FILE):
        logger.critical(f"Email configuration file not found at: {config.EMAIL_CONFIG_FILE}")
        return
        
    try:
        with open(config.EMAIL_CONFIG_FILE, 'r') as f:
            email_config = json.load(f)
    except Exception as e:
        logger.exception("Failed to parse email configuration JSON.")
        return
        
    is_simulation = email_config.get('is_simulation', True)
    smtp_host = email_config.get('smtp_host', 'localhost')
    smtp_port = email_config.get('smtp_port', 587)
    use_tls = email_config.get('use_tls', True)
    username = email_config.get('username', '')
    password = email_config.get('password', '')
    sender = email_config.get('sender', '')
    
    # parse recipients
    to_list = parse_email_list(email_config.get('recipient', ''))
    cc_list = parse_email_list(email_config.get('cc', ''))
    bcc_list = parse_email_list(email_config.get('bcc', ''))
    
    if not to_list:
        logger.error("No primary email recipient specified.")
        return
        
    logger.info("Building HTML report...")
    try:
        insights = get_insights()
        html_content = build_html_body(insights)
    except Exception as e:
        logger.exception("Failed to build HTML email report.")
        sys.exit(1)
        
    # save copy locally
    try:
        with open(config.SIMULATED_HTML_OUTPUT, 'w') as f:
            f.write(html_content)
        logger.info(f"Simulated email written to: {config.SIMULATED_HTML_OUTPUT}")
    except Exception as e:
        logger.error(f"Failed to save local simulated email: {e}")
        
    if is_simulation:
        logger.info("=== EMAIL TRANSMISSION SIMULATION (SUCCESS) ===")
        logger.info(f"Sender: {sender}")
        logger.info(f"To: {', '.join(to_list)}")
        if cc_list:
            logger.info(f"Cc: {', '.join(cc_list)}")
        if bcc_list:
            logger.info(f"Bcc: {', '.join(bcc_list)}")
        logger.info("Subject: Executive Observability Report: Weekly Microservice Breach Analysis")
        logger.info(f"Status: Local report saved at {config.SIMULATED_HTML_OUTPUT}")
        logger.info("================================================")
        return
        
    # send email
    logger.info("Constructing message structure...")
    msg = MIMEMultipart('related')
    msg['Subject'] = "Executive Observability Report: Weekly Microservice Breach Analysis"
    msg['From'] = sender
    msg['To'] = ", ".join(to_list)
    if cc_list:
        msg['Cc'] = ", ".join(cc_list)
    
    msg_alternative = MIMEMultipart('alternative')
    msg.attach(msg_alternative)
    msg_html = MIMEText(html_content, 'html')
    msg_alternative.attach(msg_html)
    
    # attach dashboard image
    if os.path.exists(config.OUTPUT_IMAGE):
        try:
            with open(config.OUTPUT_IMAGE, 'rb') as img_f:
                msg_image = MIMEImage(img_f.read())
                msg_image.add_header('Content-ID', '<breach_dashboard>')
                msg_image.add_header('Content-Disposition', 'inline', filename='breach_dashboard.png')
                msg.attach(msg_image)
        except Exception as e:
            logger.error(f"Failed to attach image: {e}")
    else:
        logger.warning(f"Dashboard image {config.OUTPUT_IMAGE} not found.")
        
    try:
        logger.info(f"Connecting to SMTP server at {smtp_host}:{smtp_port}...")
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            if use_tls:
                server.starttls()
            if username and password:
                server.login(username, password)
            
            all_recipients = to_list + cc_list + bcc_list
            logger.info(f"Sending to: {all_recipients}...")
            server.sendmail(sender, all_recipients, msg.as_string())
            
        logger.info("Email report dispatched successfully!")
    except Exception as e:
        logger.exception("SMTP transmission failed.")
        sys.exit(1)

if __name__ == "__main__":
    send_report()
