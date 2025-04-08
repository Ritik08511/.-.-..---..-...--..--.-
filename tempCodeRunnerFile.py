from flask import Flask, render_template, request
import logging
from datetime import datetime
from route_finder import find_routes, print_routes  
from train_availability_scraper import scrape_train_data
from train_route_scraper import scrape_train_routes
import os
import sys
from delay_prediction_module import TrainDelayPredictor, enhance_routes_with_predictions

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Set up the credentials path
CREDENTIALS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "keys",
    "fast-tensor-455801-h0-7c50fd901145.json"
)

# Set the environment variable for Google Cloud credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_PATH

# Verify credentials file exists
if not os.path.exists(CREDENTIALS_PATH):
    raise FileNotFoundError(f"Credentials file not found at: {CREDENTIALS_PATH}")
else:
    logger.debug(f"Credentials file found at: {CREDENTIALS_PATH}")

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
            
            logger.debug(f"Found {len(filtered_routes)} valid routes after filtering")
            
            prediction_error = None
            try:
                # Use the correct project ID format
                # Vertex AI expects a project number (without prefix) for initialization
                predictor = TrainDelayPredictor(
                    project_id="16925727262",
                    endpoint_id="1776921841160421376",
                    location="us-central1"
                )
                
                # Ensure the predictor is available before proceeding
                if not predictor.is_available:
                    logger.warning("Predictor is not available, using fallback predictions")
                    prediction_error = "ML endpoint not available, using fallback predictions"
                
                # Enhance routes with predictions
                filtered_routes = enhance_routes_with_predictions(filtered_routes, predictor)
                logger.debug("Successfully enhanced routes with predictions")
                
                # Log the first prediction to verify it's working
                if filtered_routes and filtered_routes[0]['segments']:
                    first_segment = filtered_routes[0]['segments'][0]
                    if 'delay_prediction' in first_segment:
                        logger.debug(f"First prediction: {first_segment['delay_prediction']}")
                    else:
                        logger.warning("No prediction found in first segment")
                        
            except Exception as e:
                logger.error(f"Error in prediction: {str(e)}", exc_info=True)
                prediction_error = f"Error in prediction service: {str(e)}"
            
            return render_template('results.html', 
                                routes=filtered_routes, 
                                connection_time=min_connection_time,
                                prediction_error=prediction_error)
                                
        except Exception as e:
            logger.error(f"Route processing error: {str(e)}", exc_info=True)
            return render_template('error.html', error=str(e))
    
    return render_template('index.html')

if __name__ == '__main__':
    # Determine if we're in a production environment
    is_production = os.environ.get('FLASK_ENV') == 'production'
    
    # Configure host and port based on environment
    host = '0.0.0.0' if is_production else '127.0.0.1'
    port = int(os.environ.get('PORT', 5000))
    
    # Log the environment and settings
    logger.info(f"Starting Flask app in {'production' if is_production else 'development'} mode")
    logger.info(f"Listening on {host}:{port}")
    
    # Run the Flask app
    app.run(host=host, port=port, debug=not is_production)