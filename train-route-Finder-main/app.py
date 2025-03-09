from flask import Flask, render_template, request
import logging
from datetime import datetime
from route_finder import find_routes, print_routes  
from train_availability_scraper import scrape_train_data
from train_route_scraper import scrape_train_routes
from pyngrok import ngrok, conf
import os
import atexit
import signal
import sys
from delay_prediction_module import TrainDelayPredictor, enhance_routes_with_predictions

app = Flask(__name__)

# Global variable to store ngrok tunnel
tunnel = None

# Set up the credentials path
CREDENTIALS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "keys",
    "directed-reef-450323-t2-11d3aad6566c.json"
)

# Set the environment variable for Google Cloud credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_PATH

# Verify credentials file exists
if not os.path.exists(CREDENTIALS_PATH):
    raise FileNotFoundError(f"Credentials file not found at: {CREDENTIALS_PATH}")

def cleanup_ngrok():
    """Cleanup function to kill ngrok process"""
    global tunnel
    if tunnel:
        try:
            ngrok.disconnect(tunnel.public_url)
        except:
            pass
    ngrok.kill()

def signal_handler(sig, frame):
    """Handle cleanup on system signals"""
    cleanup_ngrok()
    sys.exit(0)

# Initialize ngrok
def init_ngrok():
    global tunnel
    
    # Get ngrok auth token from environment variable or use a default one
    ngrok_auth_token = os.environ.get("NGROK_AUTH_TOKEN", "2s8AbCxwpLLc5wO0kEKsl1VaXGA_57VcrKmDYQuHdpheaigPJ")
    
    try:
        # Clean up any existing ngrok processes
        cleanup_ngrok()
        
        # Configure ngrok
        conf.get_default().auth_token = ngrok_auth_token
        
        # Set up the tunnel - simplified configuration
        tunnel = ngrok.connect(5000)
        
        print(f"\n * Public URL: {tunnel.public_url}")
        return tunnel
        
    except Exception as e:
        print(f"Error setting up ngrok: {str(e)}")
        return None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            origin = request.form['origin']
            destination = request.form['destination']
            date = request.form['date']
            max_routes = int(request.form['max_routes'])
            min_connection_time = int(request.form['connection_time'])
            
            date = date.replace('-', '')
            
            routes = find_routes(
                origin=origin,
                destination=destination,
                date=date,
                scrape_availability=scrape_train_data,
                scrape_routes=scrape_train_routes,
                max_routes=max_routes
            )
            
            filtered_routes = []
            for route in routes:
                valid_route = True
                if len(route['segments']) > 1:
                    for i in range(len(route['segments']) - 1):
                        current_segment = route['segments'][i]
                        next_segment = route['segments'][i + 1]
                        time_diff = (next_segment['departure_time'] - current_segment['arrival_time']).total_seconds() / 60
                        if time_diff < min_connection_time:
                            valid_route = False
                            break
                if valid_route:
                    filtered_routes.append(route)
            
            print(f"Debug: Using credentials from: {CREDENTIALS_PATH}")
            print(f"Debug: Credentials file exists: {os.path.exists(CREDENTIALS_PATH)}")
            
            try:
                predictor = TrainDelayPredictor(
                    project_id="521902680111",
                    endpoint_id="8318633396381155328",
                    location="us-central1"
                )
                filtered_routes = enhance_routes_with_predictions(filtered_routes, predictor)
                print("Debug: Successfully enhanced routes with predictions")
            except Exception as e:
                print(f"Debug: Error in prediction: {str(e)}")
                # Continue without predictions if there's an error
                return render_template('results.html', 
                                    routes=filtered_routes, 
                                    connection_time=min_connection_time,
                                    error=str(e))

            return render_template('results.html', 
                                routes=filtered_routes, 
                                connection_time=min_connection_time)
                                
        except Exception as e:
            print(f"Debug: Route processing error: {str(e)}")
            return render_template('error.html', error=str(e))
    
    return render_template('index.html')

def run_app():
    """Function to run the Flask app with proper cleanup"""
    # Register cleanup functions
    atexit.register(cleanup_ngrok)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize ngrok
    if init_ngrok():
        # Run the Flask app with reloader disabled
        app.run(debug=True, use_reloader=False)
    else:
        print("Failed to initialize ngrok. Exiting...")
        sys.exit(1)

if __name__ == '__main__':
    run_app()