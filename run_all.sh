#!/bin/bash
# Run the full BI pipeline: load -> analyse -> report


SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python3"
VENV_STREAMLIT="$SCRIPT_DIR/.venv/bin/streamlit"

echo "============================================="
echo "Starting Enterprise Observability Pipeline"
echo "============================================="

# Step 1: Load data
echo -e "\n[Step 1/3] Loading and cleaning raw Excel data..."
$VENV_PYTHON "$SCRIPT_DIR/db_loader.py"
if [ $? -ne 0 ]; then
    echo "ERROR: Data loading failed. Pipeline aborted."
    exit 1
fi

# Step 2: Analyse and visualise
echo -e "\n[Step 2/3] Running SQL analysis and generating visual dashboard..."
$VENV_PYTHON "$SCRIPT_DIR/analyzer.py"
if [ $? -ne 0 ]; then
    echo "ERROR: SQL analysis and visualization failed. Pipeline aborted."
    exit 1
fi

# Step 3: Compile and send report
echo -e "\n[Step 3/3] Compiling executive report and executing email reporting..."
$VENV_PYTHON "$SCRIPT_DIR/send_report.py"
if [ $? -ne 0 ]; then
    echo "ERROR: Report compilation or email delivery failed."
    exit 1
fi

echo -e "\n============================================="
echo "Pipeline completed successfully!"
echo "Database location: $SCRIPT_DIR/breaches.duckdb"
echo "Dashboard image:   $SCRIPT_DIR/breach_dashboard.png"
echo "Simulated email:   $SCRIPT_DIR/simulated_email.html"
echo -e "\nLaunching the interactive local web dashboard portal..."
echo "============================================="

# Launch Streamlit automatically (file watcher disabled to prevent inotify limits)
$VENV_STREAMLIT run "$SCRIPT_DIR/app.py" --server.fileWatcherType none
