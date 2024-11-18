import streamlit as st
import pandas as pd
from collections import defaultdict

# Streamlit app title and description
st.title("Trip Origin and Destination Processor")
st.write("""
Upload a CSV or Excel file (.xlsx) containing trip segments. This app will determine the overall trip origin and destination for each trip
based on the data provided. The required columns are:
- **Order #**
- **Passenger**
- **BP Origin**
- **BP Destination**
""")

# File uploader widget for users to upload CSV or Excel files
uploaded_file = st.file_uploader("Choose a file", type=["csv", "xlsx"])

# Function to determine trip origin and destination using a graph-based approach
def determine_trip_origin_destination(trip_segments, order_number, passenger):
    graph = {}
    nodes = set()
    in_degree = {}
    anomalies = []

    # Build the graph and compute in-degrees
    for segment in trip_segments:
        origin = segment['BP Origin']
        destination = segment['BP Destination']

        # Skip if origin or destination is missing
        if not origin or not destination:
            anomalies.append(f"Order {order_number}, Passenger {passenger}: Missing origin or destination in a segment.")
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
        anomalies.append(f"Order {order_number}, Passenger {passenger}: No trip origin found.")
    elif len(trip_origins) > 1:
        anomalies.append(f"Order {order_number}, Passenger {passenger}: Multiple trip origins found: {trip_origins}")
        trip_origin = trip_origins[0]
    else:
        trip_origin = trip_origins[0]

    if len(trip_destinations) == 0:
        anomalies.append(f"Order {order_number}, Passenger {passenger}: No trip destination found.")
    elif len(trip_destinations) > 1:
        anomalies.append(f"Order {order_number}, Passenger {passenger}: Multiple trip destinations found: {trip_destinations}")
        trip_destination = trip_destinations[0]
    else:
        trip_destination = trip_destinations[0]

    return trip_origin, trip_destination, anomalies

# Main processing logic
if uploaded_file is not None:
    try:
        # Determine the file type and read the file accordingly
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        else:
            st.error("Unsupported file type. Please upload a CSV or Excel file.")
            st.stop()

        # Check if required columns are present
        required_columns = ['Order #', 'Passenger', 'BP Origin', 'BP Destination']
        if not all(col in df.columns for col in required_columns):
            st.error(f"The uploaded file must contain the following columns: {', '.join(required_columns)}")
        else:
            # Convert DataFrame to list of dictionaries
            records = df.to_dict(orient='records')

            # Group trip segments by Order # and Passenger
            orders = defaultdict(list)
            for record in records:
                order_number = record['Order #']
                passenger = record['Passenger']
                key = (order_number, passenger)
                orders[key].append(record)

            # Initialize a list to collect all anomalies
            all_anomalies = []

            # Process each (Order #, Passenger) group
            for key, trip_segments in orders.items():
                order_number, passenger = key
                trip_origin, trip_destination, anomalies = determine_trip_origin_destination(trip_segments, order_number, passenger)

                # Collect anomalies
                all_anomalies.extend(anomalies)

                # Append Trip Origin and Trip Destination to each segment record
                for segment in trip_segments:
                    segment['Trip Origin'] = trip_origin if trip_origin else 'Unknown'
                    segment['Trip Destination'] = trip_destination if trip_destination else 'Unknown'

            # Convert updated records back to a DataFrame
            result_df = pd.DataFrame(records)

            # Display anomalies if any were found
            if all_anomalies:
                st.warning("Data anomalies detected during processing:")
                for anomaly in all_anomalies:
                    st.write(f"- {anomaly}")
            else:
                st.success("Processing complete without anomalies!")

            # Display the processed data
            st.write("Processed Data:")
            st.dataframe(result_df)

            # Allow users to download the processed data as a CSV file
            def convert_df(df):
                return df.to_csv(index=False).encode('utf-8')

            csv = convert_df(result_df)
            st.download_button(
                label="Download Processed Data as CSV",
                data=csv,
                file_name='processed_trips.csv',
                mime='text/csv'
            )
    except Exception as e:
        st.error(f"An error occurred while processing the file: {e}")
else:
    st.info("Please upload a CSV or Excel file to start processing.")
