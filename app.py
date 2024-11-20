import streamlit as st
import pandas as pd
from collections import defaultdict

# Import the data enrichment functions
from data_enrichment import load_customer_data, enrich_uploaded_data

def main():
    # Streamlit app title and description
    st.title("Trip Origin and Destination Processor with Data Enrichment")
    st.write("""
    Upload a CSV or Excel file containing trip segments. This app will determine the overall trip origin and destination for each trip
    and enrich the data using customer information.

    **Required columns in the uploaded file**:
    - **Order #**
    - **Passenger** or **Pax**
    - **BP Origin**
    - **BP Destination**
    - **Schedule Date**
    - **Customer Email** or **Cust Email**

    The app groups records by **Order #**, **Schedule Date**, and **Passenger**.
    """)

    # Instructions in an expander
    with st.expander("Instructions"):
        st.write("""
        - Ensure your data file includes all the required columns.
        - The **Customer Email** column (or **Cust Email**) is used to match records with the backend customer data.
        - Dates should be in a consistent format (e.g., **MM/DD/YYYY**).
        - If your data includes a column indicating the sequence of segments (e.g., 'Barcode', 'Segment Number', 'Departure Time'), it will improve accuracy.
        """)

    # Sidebar for Customer Data Management
    st.sidebar.header("Customer Data Management")

    if 'customer_data' not in st.session_state:
        st.session_state['customer_data'] = None

    # Option to upload a new customer data file
    upload_new_customer_file = st.sidebar.checkbox("Upload new customer data file")

    if upload_new_customer_file or st.session_state['customer_data'] is None:
        # File uploader for customer data file
        customer_file = st.sidebar.file_uploader("Upload Customer Data File", type=["csv"])
        if customer_file is not None:
            # Read customer data file content
            customer_file_content = customer_file.getvalue()
            customer_file_name = customer_file.name

            # Load and cache the customer data
            customer_data = load_customer_data(customer_file_content, customer_file_name)
            st.session_state['customer_data'] = customer_data

            st.sidebar.success("Customer data loaded and cached successfully.")
        else:
            st.sidebar.info("Please upload a customer data file.")
            st.stop()
    else:
        customer_data = st.session_state['customer_data']
        st.sidebar.success("Using cached customer data.")

    # Main file uploader for trip segments
    uploaded_file = st.file_uploader("Upload Trip Segments File", type=["csv", "xlsx"])

    # Main processing logic
    if uploaded_file is not None:
        try:
            # Read the uploaded trip segments file
            df = read_uploaded_file(uploaded_file)

            # Check if required columns are present
            required_columns = ['Order #', 'BP Origin', 'BP Destination', 'Schedule Date']
            if 'Passenger' in df.columns:
                passenger_column = 'Passenger'
            elif 'Pax' in df.columns:
                df.rename(columns={'Pax': 'Passenger'}, inplace=True)
                passenger_column = 'Passenger'
            else:
                st.error("The uploaded file must contain a 'Passenger' or 'Pax' column.")
                return
            required_columns.append('Passenger')

            # Check for 'Customer Email' or 'Cust Email' column
            if 'Customer Email' in df.columns:
                email_column = 'Customer Email'
            elif 'Cust Email' in df.columns:
                df.rename(columns={'Cust Email': 'Customer Email'}, inplace=True)
                email_column = 'Customer Email'
            else:
                st.error("The uploaded file must contain a 'Customer Email' or 'Cust Email' column.")
                return
            required_columns.append(email_column)

            if not all(col in df.columns for col in required_columns):
                st.error(f"The uploaded file must contain the following columns: {', '.join(required_columns)}")
                return

            # Convert 'Schedule Date' to datetime.date
            df = convert_schedule_date(df)

            # Identify sequence column if available
            sequence_column = identify_sequence_column(df)

            # Sort the DataFrame to ensure segments are in chronological order
            df = sort_dataframe(df, sequence_column)

            # Enrich the uploaded data with customer data
            df = enrich_uploaded_data(df, customer_data)

            # Proceed with the existing logic
            # Convert DataFrame to list of dictionaries
            records = df.to_dict(orient='records')

            # Group trip segments by Order #, Schedule Date, and Passenger
            orders = group_trip_segments(records)

            # Initialize a list to collect all anomalies
            all_anomalies = []

            # Process each trip group
            processed_records = []
            for key, trip_segments in orders.items():
                order_number, schedule_date, passenger = key

                # Determine trip origin and destination
                trip_origin, trip_destination, anomalies = determine_trip_origin_destination(
                    trip_segments, order_number, schedule_date, passenger
                )

                # Collect anomalies
                all_anomalies.extend(anomalies)

                # Append Trip Origin and Trip Destination to each segment record
                for segment in trip_segments:
                    segment['Trip Origin'] = trip_origin if trip_origin else 'Unknown'
                    segment['Trip Destination'] = trip_destination if trip_destination else 'Unknown'
                    processed_records.append(segment)

            # Convert updated records back to a DataFrame
            result_df = pd.DataFrame(processed_records)

            # Display anomalies if any were found
            display_anomalies(all_anomalies)

            # Display the processed data
            st.write("Processed and Enriched Data:")
            st.dataframe(result_df)

            # Allow users to download the processed data as a CSV file
            download_processed_data(result_df)

        except Exception as e:
            st.error(f"An unexpected error occurred while processing the file: {e}")
            st.stop()
    else:
        st.info("Please upload a trip segments file to start processing.")

# Helper functions

def read_uploaded_file(uploaded_file):
    """Reads the uploaded CSV or Excel file and returns a DataFrame."""
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        else:
            st.error("Unsupported file type. Please upload a CSV or Excel file.")
            st.stop()
        return df
    except Exception as e:
        st.error(f"Error reading the uploaded file: {e}")
        st.stop()

def convert_schedule_date(df):
    """Converts the 'Schedule Date' column to datetime.date."""
    try:
        df['Schedule Date'] = pd.to_datetime(df['Schedule Date']).dt.date
        return df
    except Exception as e:
        st.error(f"Error converting 'Schedule Date' to date: {e}")
        st.stop()

def identify_sequence_column(df):
    """Identifies a sequence column if available."""
    sequence_column = None
    possible_sequence_columns = ['Barcode', 'Boarding Pass', 'Segment ID', 'Segment Number', 'Sequence', 'Departure Time']
    for col in possible_sequence_columns:
        if col in df.columns:
            sequence_column = col
            break
    return sequence_column

def sort_dataframe(df, sequence_column):
    """Sorts the DataFrame based on grouping columns and sequence."""
    try:
        if sequence_column:
            df = df.sort_values(by=['Order #', 'Passenger', 'Schedule Date', sequence_column])
        else:
            df = df.sort_values(by=['Order #', 'Passenger', 'Schedule Date'])
            st.warning("No sequence column found. Sorting by 'Order #', 'Passenger', and 'Schedule Date' only. Ensure your data is in the correct order.")
        return df
    except Exception as e:
        st.error(f"Error sorting the DataFrame: {e}")
        st.stop()

def group_trip_segments(records):
    """Groups trip segments by Order #, Schedule Date, and Passenger."""
    orders = defaultdict(list)
    for record in records:
        order_number = record['Order #']
        schedule_date = record['Schedule Date']
        passenger = record['Passenger']
        key = (order_number, schedule_date, passenger)
        orders[key].append(record)
    return orders

def determine_trip_origin_destination(trip_segments, order_number, schedule_date, passenger):
    """Determines the trip origin and destination using traversal logic."""
    anomalies = []

    if not trip_segments:
        anomalies.append(
            f"Order {order_number}, Passenger {passenger}, Date {schedule_date}: No segments found."
        )
        return None, None, anomalies

    # Initialize trip origin and destination
    trip_origin = trip_segments[0]['BP Origin']
    trip_destination = None

    if not trip_origin:
        anomalies.append(
            f"Order {order_number}, Passenger {passenger}, Date {schedule_date}: Missing BP Origin in the first segment."
        )
        return None, None, anomalies

    # Set to keep track of visited nodes
    visited_nodes = set()
    visited_nodes.add(trip_origin)

    # Traverse segments starting from the second segment
    for i in range(1, len(trip_segments)):
        current_segment = trip_segments[i]
        bp_origin = current_segment.get('BP Origin')
        bp_destination = current_segment.get('BP Destination')

        if not bp_origin or not bp_destination:
            anomalies.append(
                f"Order {order_number}, Passenger {passenger}, Date {schedule_date}: Missing BP Origin or BP Destination in segment {i + 1}."
            )
            continue

        # Check if BP Origin has been visited before
        if bp_origin in visited_nodes:
            # Trip destination is BP Origin of the previous segment
            trip_destination = trip_segments[i - 1]['BP Origin']
            break
        else:
            # Add BP Origin to visited_nodes
            visited_nodes.add(bp_origin)

    # If destination not found during traversal
    if trip_destination is None:
        # Trip destination is BP Destination of the last segment
        trip_destination = trip_segments[-1]['BP Destination']

    # Anomaly Detection
    if trip_destination is None:
        anomalies.append(
            f"Order {order_number}, Passenger {passenger}, Date {schedule_date}: Could not determine trip destination."
        )

    return trip_origin, trip_destination, anomalies

def display_anomalies(all_anomalies):
    """Displays anomalies if any were found."""
    if all_anomalies:
        st.warning("Data anomalies detected during processing:")
        with st.expander("Click to view anomalies"):
            for anomaly in all_anomalies:
                st.write(f"- {anomaly}")
        # Option to download anomalies
        anomalies_df = pd.DataFrame({'Anomalies': all_anomalies})
        anomalies_csv = anomalies_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Anomalies as CSV",
            data=anomalies_csv,
            file_name='anomalies.csv',
            mime='text/csv'
        )
    else:
        st.success("Processing complete without anomalies!")

def download_processed_data(result_df):
    """Allows users to download the processed data as a CSV file."""
    csv = result_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Processed Data as CSV",
        data=csv,
        file_name='processed_trips.csv',
        mime='text/csv'
    )

if __name__ == "__main__":
    main()
