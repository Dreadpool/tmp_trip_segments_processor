# trip_processor.py

import csv
import logging
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler("trip_processor.log"),
        logging.StreamHandler()
    ]
)

input_file = 'input.csv'      # Replace with your input file name
output_file = 'output.csv'    # Replace with your desired output file name

# Read the CSV file
with open(input_file, mode='r', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    records = list(reader)

# Group trip segments by Order # and Passenger
orders = defaultdict(list)

for record in records:
    order_number = record['Order #']
    passenger = record['Passenger']
    key = (order_number, passenger)
    orders[key].append(record)

def determine_trip_origin_destination(trip_segments, order_number, passenger):
    graph = {}
    nodes = set()
    in_degree = {}

    # Build the graph and compute in-degrees
    for segment in trip_segments:
        origin = segment['BP Origin']
        destination = segment['BP Destination']

        # Skip if origin or destination is missing
        if not origin or not destination:
            logging.warning(f"Order {order_number}, Passenger {passenger}: Missing origin or destination in segment.")
            continue

        # Add the edge to the graph
        graph.setdefault(origin, []).append(destination)

        # Update nodes set
        nodes.update([origin, destination])

        # Update in-degree counts
        in_degree[destination] = in_degree.get(destination, 0) + 1
        in_degree.setdefault(origin, in_degree.get(origin, 0))

    # Compute out-degrees
    out_degree = {node: len(graph.get(node, [])) for node in nodes}

    # Identify trip origins and destinations
    trip_origins = [node for node in nodes if in_degree.get(node, 0) == 0]
    trip_destinations = [node for node in nodes if out_degree.get(node, 0) == 0]

    # Initialize trip origin and destination
    trip_origin = trip_destination = None

    # Handle anomalies
    if len(trip_origins) == 0:
        logging.error(f"Order {order_number}, Passenger {passenger}: No trip origin found.")
    elif len(trip_origins) > 1:
        logging.warning(f"Order {order_number}, Passenger {passenger}: Multiple trip origins found: {trip_origins}")
        trip_origin = trip_origins[0]  # You may choose to handle this differently
    else:
        trip_origin = trip_origins[0]

    if len(trip_destinations) == 0:
        logging.error(f"Order {order_number}, Passenger {passenger}: No trip destination found.")
    elif len(trip_destinations) > 1:
        logging.warning(f"Order {order_number}, Passenger {passenger}: Multiple trip destinations found: {trip_destinations}")
        trip_destination = trip_destinations[0]  # You may choose to handle this differently
    else:
        trip_destination = trip_destinations[0]

    return trip_origin, trip_destination

# Process each (Order #, Passenger) group
for key, trip_segments in orders.items():
    order_number, passenger = key
    # Determine trip origin and destination
    trip_origin, trip_destination = determine_trip_origin_destination(trip_segments, order_number, passenger)

    # Append to each segment record
    for segment in trip_segments:
        segment['Trip Origin'] = trip_origin if trip_origin else 'Unknown'
        segment['Trip Destination'] = trip_destination if trip_destination else 'Unknown'

# Get fieldnames, including the new ones
fieldnames = records[0].keys()

# Write the updated records to the output CSV file
with open(output_file, mode='w', newline='', encoding='utf-8') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(records)

print(f"Processing complete. Output written to '{output_file}'.")
print("Check 'trip_processor.log' for any warnings or errors.")
