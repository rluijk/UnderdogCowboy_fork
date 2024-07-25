import sys
print(sys.path)

print("Attempting to import underdogcowboy")
import underdogcowboy
print("underdogcowboy imported successfully")

print("Attempting to import JSONExtractor")
try:
    from underdogcowboy import JSONExtractor
    print("JSONExtractor imported successfully")
    print(f"JSONExtractor is: {JSONExtractor}")
except ImportError as e:
    print(f"Error importing JSONExtractor: {e}")

print("Contents of underdogcowboy:")
print(dir(underdogcowboy))