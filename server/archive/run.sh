cleanup() {
    echo "Ctrl+C received. Cleaning up..."
    # Kill the first Python script
    pkill -f backend.py
    # Kill the second Python script
    pkill -f app.py
    exit 1
}

# Trap Ctrl+C and call the cleanup function
trap cleanup INT

sudo python3 app.py &

# Wait for the Flask app to start by checking a specific endpoint or log message
while ! curl -s http://localhost:5000/health >/dev/null; do
    echo "Waiting for Flask app to start..."
    sleep 1
done

# Run the second Python script
sudo python3 backend.py

cleanup()