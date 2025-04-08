from google.cloud import aiplatform
from datetime import datetime
import logging
import random
import re

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TrainDelayPredictor:
    def __init__(self, project_id="16925727262", endpoint_id="1776921841160421376", location="us-central1", credentials_path=None):
        logger.debug("Initializing TrainDelayPredictor...")
        logger.debug(f"Project ID: {project_id}")
        logger.debug(f"Endpoint ID: {endpoint_id}")
        logger.debug(f"Location: {location}")
        
        try:
            if credentials_path:
                aiplatform.init(
                    project=project_id,
                    location=location,
                    credentials=aiplatform.Credentials.from_service_account_file(credentials_path)
                )
            else:
                # Initialize without explicit credentials, relying on environment variables
                aiplatform.init(
                    project=project_id,
                    location=location
                )
                
            # Log that we're connecting to the endpoint
            logger.debug(f"Connecting to endpoint: projects/{project_id}/locations/{location}/endpoints/{endpoint_id}")
            
            self.endpoint = aiplatform.Endpoint(
                endpoint_name=f"projects/{project_id}/locations/{location}/endpoints/{endpoint_id}"
            )
            self.is_available = True
            logger.debug("Successfully connected to Vertex AI endpoint")
        except Exception as e:
            logger.error(f"Failed to initialize ML endpoint: {str(e)}")
            print("Running in fallback mode with mock predictions")
            self.is_available = False
    
    def predict_delay(self, train_number: str, source_station: str, destination_station: str) -> dict:
        """
        Predict delay for a train segment
        Args:
            train_number: Train number
            source_station: Source station code (e.g., 'NDLS' from 'NDLS_NewDelhi')
            destination_station: Destination station code (e.g., 'CPR' from 'CPR_Chapra')
        Returns:
            Dictionary with prediction results or fallback prediction if ML endpoint is unavailable
        """
        if not self.is_available:
            logger.debug(f"Using fallback prediction for train {train_number}")
            return self._get_fallback_prediction()
            
        try:
            # Extract only digits from train number (remove any parentheses, spaces, etc.)
            clean_train_number = re.sub(r'[^0-9]', '', str(train_number))
            
            # Extract only station codes from full station names
            source_code = source_station.split('_')[0] if '_' in source_station else source_station
            dest_code = destination_station.split('_')[0] if '_' in destination_station else destination_station
            
            # Ensure we have valid inputs
            if not clean_train_number:
                logger.error(f"Invalid train number format: '{train_number}', cannot extract digits")
                return self._get_fallback_prediction()
                
            logger.debug(f"Making prediction for train {train_number} (cleaned: {clean_train_number}) from {source_code} to {dest_code}")
            
            # The API expects these exact key names with proper case
            instance = {
                'train_number': clean_train_number,
                'origin_station': source_code,
                'destination_station': dest_code
            }
            
            # Log the request being sent
            logger.debug(f"Sending prediction request: {instance}")
            
            response = self.endpoint.predict(instances=[instance])
            
            # Log the raw response for debugging
            logger.debug(f"Raw prediction response: {response}")
            
            # Print full response for debugging
            import json
            print(f"Complete response: {response}")
            print(f"Predictions: {response.predictions}")
            
            prediction = response.predictions[0]
            
            # Adjust based on the actual response structure from Vertex AI
            if isinstance(prediction, (int, float)):
                # Single value returned
                result = {
                    'predicted_delay': float(prediction),
                    'min_delay': max(0, float(prediction) - 5),
                    'max_delay': float(prediction) + 10,
                    'confidence_level': self._calculate_confidence_level(float(prediction))
                }
            elif isinstance(prediction, dict):
                # Dictionary returned
                if 'value' in prediction:
                    result = {
                        'predicted_delay': prediction['value'],
                        'min_delay': prediction.get('lower_bound', max(0, prediction['value'] - 5)),
                        'max_delay': prediction.get('upper_bound', prediction['value'] + 10),
                        'confidence_level': self._calculate_confidence_level(prediction['value'])
                    }
                elif 'predicted_delay' in prediction:
                    result = prediction
                else:
                    # Use the first numeric value found
                    for key, value in prediction.items():
                        if isinstance(value, (int, float)):
                            result = {
                                'predicted_delay': float(value),
                                'min_delay': max(0, float(value) - 5),
                                'max_delay': float(value) + 10,
                                'confidence_level': self._calculate_confidence_level(float(value))
                            }
                            break
                    else:
                        # Fallback if no numeric value found
                        logger.warning(f"Couldn't parse prediction: {prediction}")
                        return self._get_fallback_prediction()
            else:
                # Handling for list or other formats
                logger.warning(f"Unexpected prediction format: {type(prediction)}, value: {prediction}")
                return self._get_fallback_prediction()
            
            logger.debug(f"Prediction result: {result}")
            return result
        except Exception as e:
            logger.error(f"Prediction error for train {train_number}: {str(e)}")
            import traceback
            traceback.print_exc()
            logger.debug("Falling back to default prediction")
            return self._get_fallback_prediction()
    
    def _calculate_confidence_level(self, predicted_delay: float) -> str:
        """Calculate confidence level based on predicted delay"""
        if predicted_delay <= 15:
            return "HIGH"
        elif predicted_delay <= 30:
            return "MEDIUM"
        else:
            return "LOW"

    def _get_fallback_prediction(self) -> dict:
        """Provide a fallback prediction when ML endpoint is unavailable"""
        delay_weights = [0] * 60 + [5] * 20 + [10] * 10 + [15] * 5 + [20] * 3 + [25] * 1 + [30] * 1
        random_delay = random.choice(delay_weights)
        
        return {
            'predicted_delay': random_delay,
            'min_delay': max(0, random_delay - 5),
            'max_delay': random_delay + 10,
            'confidence_level': 'MEDIUM',
            'is_fallback': True
        }

def enhance_routes_with_predictions(routes: list, predictor: TrainDelayPredictor) -> list:
    """
    Add delay predictions to each route segment
    """
    if not predictor or not predictor.is_available:
        logger.warning("Predictor not available, skipping delay predictions")
        return routes
    
    enhanced_count = 0
    failures_count = 0
    
    for route_idx, route in enumerate(routes):
        for segment_idx, segment in enumerate(route['segments']):
            # Process all segments, not just the first one
            try:
                # Extract the required fields with proper cleaning
                train_num = segment.get('train_number', 'Unknown')
                from_station = segment.get('from_station', 'Unknown')
                to_station = segment.get('to_station', 'Unknown')
                
                # Debug the segment data
                logger.debug(f"Segment data: {segment}")
                logger.debug(f"Processing segment {segment_idx} in route {route_idx}: Train {train_num} from {from_station} to {to_station}")
                
                # Clean train number before passing to predict
                clean_train_num = re.sub(r'[^0-9]', '', str(train_num))
                if not clean_train_num:
                    logger.warning(f"Invalid train number: {train_num}, using fallback prediction")
                    segment['delay_prediction'] = predictor._get_fallback_prediction()
                    enhanced_count += 1
                    continue
                
                logger.debug(f"Cleaned train number: {clean_train_num}")
                
                prediction = predictor.predict_delay(
                    clean_train_num,  # Use cleaned train number
                    from_station,
                    to_station
                )
                
                if prediction:
                    # Only store prediction in delay_prediction for consistency
                    segment['delay_prediction'] = prediction
                    enhanced_count += 1
                    
                    # Add a flag to indicate if this is a fallback prediction
                    if prediction.get('is_fallback', False):
                        logger.debug(f"Added fallback prediction to segment: {prediction}")
                    else:
                        logger.debug(f"Added AI prediction to segment: {prediction}")
            except Exception as e:
                failures_count += 1
                logger.error(f"Error enhancing segment {segment_idx} in route {route_idx}: {str(e)}")
                logger.debug(f"Segment data: {segment}")
                # Apply fallback prediction on error
                try:
                    segment['delay_prediction'] = predictor._get_fallback_prediction()
                    logger.debug(f"Applied fallback prediction after error")
                except Exception as fallback_error:
                    logger.error(f"Error applying fallback prediction: {str(fallback_error)}")
    
    logger.debug(f"Enhanced {enhanced_count} segments with delay predictions (failures: {failures_count})")
    return routes