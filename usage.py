import ezenviron

# Get environment variable
value = ezenviron.get("PATH")

# Set environment variable
success = ezenviron.set("MY_VAR", "my_value")

# Load from .env file
results = ezenviron.load_dotenv(".env")

# Reload all environment variables
updated = ezenviron.reload()