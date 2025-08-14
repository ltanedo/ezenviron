# %%
# Workbench for testing ezenviron module
# This is a Hydrogen-compatible file for interactive testing

# Re-import the entire ezenviron module
import importlib
import sys
if 'ezenviron' in sys.modules:
    importlib.reload(sys.modules['ezenviron'])
import ezenviron

print("ezenviron module loaded successfully!")
print(f"Available functions: {ezenviron.__all__}")

# %%
# Test getting an existing environment variable
import importlib
import sys
if 'ezenviron' in sys.modules:
    importlib.reload(sys.modules['ezenviron'])
import ezenviron

# Test getting PATH environment variable
path_value = ezenviron.get("PATH")
print(f"PATH length: {len(path_value) if path_value else 0}")
print(f"PATH starts with: {path_value[:100] if path_value else 'None'}...")

# %%
# Test getting a non-existent environment variable
import importlib
import sys
if 'ezenviron' in sys.modules:
    importlib.reload(sys.modules['ezenviron'])
import ezenviron

non_existent = ezenviron.get("NONEXISTENT_VAR_12345")
print(f"Non-existent variable result: {non_existent}")

# %%
# Test setting a new environment variable
import importlib
import sys
if 'ezenviron' in sys.modules:
    importlib.reload(sys.modules['ezenviron'])
import ezenviron

# Set a test variable
test_key = "EZENVIRON_TEST_VAR"
test_value = "test_value_123"

try:
    success = ezenviron.set(test_key, test_value)
    print(f"Setting {test_key}={test_value}: {'Success' if success else 'Failed'}")
    
    # Verify it was set
    retrieved_value = ezenviron.get(test_key)
    print(f"Retrieved value: {retrieved_value}")
    print(f"Values match: {retrieved_value == test_value}")
except Exception as e:
    print(f"Error during set operation: {e}")

# %%
# Test reload functionality
import importlib
import sys
if 'ezenviron' in sys.modules:
    importlib.reload(sys.modules['ezenviron'])
import ezenviron

try:
    updated_vars = ezenviron.reload()
    print(f"Reload completed. Updated {len(updated_vars)} variables:")
    
    # Show first few updated variables (if any)
    for i, (key, value) in enumerate(updated_vars.items()):
        if i >= 5:  # Limit output
            print(f"  ... and {len(updated_vars) - 5} more")
            break
        print(f"  {key}={value[:50]}{'...' if len(value) > 50 else ''}")
        
except Exception as e:
    print(f"Error during reload: {e}")

# %%
# Test load_dotenv functionality (create a test .env file first)
import importlib
import sys
if 'ezenviron' in sys.modules:
    importlib.reload(sys.modules['ezenviron'])
import ezenviron
import os

# Create a test .env file
test_env_content = """# Test .env file
TEST_VAR1=value1
TEST_VAR2="quoted value"
TEST_VAR3='single quoted'
export TEST_VAR4=exported_value
# This is a comment
TEST_VAR5=value with spaces
"""

test_env_path = "test.env"
with open(test_env_path, "w") as f:
    f.write(test_env_content)

try:
    results = ezenviron.load_dotenv(test_env_path)
    print(f"load_dotenv results: {results}")
    
    # Verify some of the loaded variables
    for key in ["TEST_VAR1", "TEST_VAR2", "TEST_VAR3", "TEST_VAR4", "TEST_VAR5"]:
        value = ezenviron.get(key)
        print(f"  {key}={value}")
        
except Exception as e:
    print(f"Error during load_dotenv: {e}")
finally:
    # Clean up test file
    if os.path.exists(test_env_path):
        os.remove(test_env_path)

# %%
# Test error handling - try to use on non-Windows (if applicable)
import importlib
import sys
if 'ezenviron' in sys.modules:
    importlib.reload(sys.modules['ezenviron'])
import ezenviron
import platform

print(f"Current platform: {platform.system()}")

if platform.system() != "Windows":
    print("Testing error handling on non-Windows platform...")
    try:
        ezenviron.set("TEST_VAR", "test_value")
    except RuntimeError as e:
        print(f"Expected error caught: {e}")
else:
    print("Running on Windows - full functionality available")

# %%
# Module information and cleanup
import importlib
import sys
if 'ezenviron' in sys.modules:
    importlib.reload(sys.modules['ezenviron'])
import ezenviron

print(f"ezenviron version: {ezenviron.__version__}")
print(f"ezenviron author: {ezenviron.__author__}")
print(f"ezenviron email: {ezenviron.__email__}")

# Clean up test variables if they exist
test_vars = ["EZENVIRON_TEST_VAR", "TEST_VAR1", "TEST_VAR2", "TEST_VAR3", "TEST_VAR4", "TEST_VAR5"]
for var in test_vars:
    if var in os.environ:
        print(f"Test variable {var} is still in environment")
