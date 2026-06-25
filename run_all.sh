#!/bin/bash
# Run the full BI pipeline: load -> analyse -> report


SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

if [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
elif [ -f "$SCRIPT_DIR/.venv/bin/python3" ]; then
    VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python3"
else
    VENV_PYTHON="python"
fi

if [ -f "$SCRIPT_DIR/.venv/bin/streamlit" ]; then
    VENV_STREAMLIT="$SCRIPT_DIR/.venv/bin/streamlit"
else
    VENV_STREAMLIT="streamlit"
fi

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
echo -e "\nTo launch the interactive local web dashboard portal, run:"
echo "  source .venv/bin/activate && streamlit run app.py"
echo "============================================="
exit 0
