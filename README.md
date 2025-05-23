# Train Route Finder

A comprehensive application for finding optimal train routes across India. The system integrates with Google Cloud Vertex AI to predict train delays and improve journey planning.

## Features

- Search for train routes between any two stations in India
- View multiple route options with connections
- Real-time delay predictions using machine learning
- Voice command support with natural language processing
- Mobile-friendly responsive design

## Voice Commands

You can find trains using natural language voice commands. Simply click the microphone button and say phrases like:
- "Book a train from Delhi to Patna for tomorrow"
- "Find a train from Ahmedabad to Jaipur on 30 June"
- "Find a train from Chennai to Mumbai for this Friday"

The system uses natural language processing to extract the origin, destination, and travel date from your command.

## Technologies Used

- Python Flask backend
- Google Cloud Vertex AI for delay predictions
- Azure Speech Services for voice commands
- Azure Language Service for natural language processing
- Ngrok for secure tunneling

## Getting Started

1. Clone this repository
2. Install requirements: `pip install -r requirements.txt`
3. Add your API keys to the `keys` directory
4. Run the application: `python app.py`

## API Integration

The application integrates with:
- Google Cloud Vertex AI for delay predictions
- Azure Speech Services for voice recognition
- Azure Language Services for intent recognition

## Contributors

- Developed by Ritvik
