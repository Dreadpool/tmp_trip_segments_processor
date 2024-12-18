import streamlit as st
import pandas as pd
from collections import defaultdict
from io import BytesIO

# Import the data enrichment functions
from data_enrichment import load_customer_data, enrich_uploaded_data

# Import the customer summary function
from customer_summary import generate_customer_summary

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

    # Load customer data from backend file
    customer_data = load_customer_data()

    # Main file uploader for trip segments
    uploaded_file = st.file_uploader("Upload Trip Segments File", type=["csv", "xlsx"])

    # Checkbox to generate unique customer summary
    generate_customer_summary_checkbox = st.checkbox("Generate Unique Customer Summary")

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

            # If the checkbox is selected, generate customer summary
            if generate_customer_summary_checkbox:
                customer_summary_df = generate_customer_summary(df)

                # Display the customer summary
                st.write("Unique Customer Summary:")
                st.dataframe(customer_summary_df)

                # Allow users to download the customer summary
                download_customer_summary(customer_summary_df)
            else:
                # Process the enriched data
                records = df.to_dict(orient='records')
                orders = group_trip_segments(records)
                all_anomalies = []
                processed_records = []

                for key, trip_segments in orders.items():
                    order_number, schedule_date, passenger = key
                    trip_origin, trip_destination, anomalies = determine_trip_origin_destination(
                        trip_segments, order_number, schedule_date, passenger
                    )
                    all_anomalies.extend(anomalies)

                    for segment in trip_segments:
                        segment['Trip Origin'] = trip_origin if trip_origin else 'Unknown'
                        segment['Trip Destination'] = trip_destination if trip_destination else 'Unknown'
                        processed_records.append(segment)

                result_df = pd.DataFrame(processed_records)

                # Display anomalies if any were found
                display_anomalies(all_anomalies)

                # Display the processed data
                st.write("Processed and Enriched Data:")
                st.dataframe(result_df)

                # Allow users to download the processed data
                download_processed_data(result_df)

        except Exception as e:
            st.error(f"An unexpected error occurred while processing the file: {e}")
            st.stop()
    else:
        st.info("Please upload a trip segments file to start processing.")

def read_uploaded_file(uploaded_file):
    """Reads the uploaded CSV or Excel file and returns a DataFrame."""
    try:
        # Define dtype dictionary to force Barcode as string
        dtype_dict = {'Barcode': str}
        
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file, dtype=dtype_dict)
        elif uploaded_file.name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file, engine='openpyxl', dtype=dtype_dict)
        else:
            st.error("Unsupported file type. Please upload a CSV or Excel file.")
            st.stop()
            
        # Additional safeguard to ensure Barcode remains string
        if 'Barcode' in df.columns:
            df['Barcode'] = df['Barcode'].astype(str)
        
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
            st.warning("No sequence column found. Sorting by 'Order #', 'Passenger', and 'Schedule Date' only.")
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

    trip_origin = trip_segments[0]['BP Origin']
    trip_destination = None

    if not trip_origin:
        anomalies.append(
            f"Order {order_number}, Passenger {passenger}, Date {schedule_date}: Missing BP Origin in first segment."
        )
        return None, None, anomalies

    visited_nodes = set()
    visited_nodes.add(trip_origin)

    for i in range(1, len(trip_segments)):
        current_segment = trip_segments[i]
        bp_origin = current_segment.get('BP Origin')
        bp_destination = current_segment.get('BP Destination')

        if not bp_origin or not bp_destination:
            anomalies.append(
                f"Order {order_number}, Passenger {passenger}, Date {schedule_date}: Missing BP Origin or BP Destination in segment {i + 1}."
            )
            continue

        if bp_origin in visited_nodes:
            trip_destination = trip_segments[i - 1]['BP Origin']
            break
        else:
            visited_nodes.add(bp_origin)

    if trip_destination is None:
        trip_destination = trip_segments[-1]['BP Destination']

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
    """Allows users to download the processed data as Excel only to preserve formatting."""
    try:
        # Create Excel file in memory
        output = BytesIO()
        
        # Create a copy of the dataframe for export to avoid modifying the original
        export_df = result_df.copy()
        
        # Handle Barcode column formatting for Excel
        if 'Barcode' in export_df.columns:
            # Make sure Barcode is string type but without visible quotes
            export_df['Barcode'] = export_df['Barcode'].astype(str).str.lstrip("'")
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            export_df.to_excel(writer, index=False)
            workbook = writer.book
            worksheet = writer.sheets['Sheet1']
            
            # Find and format Barcode column
            if 'Barcode' in export_df.columns:
                barcode_col_idx = export_df.columns.get_loc('Barcode')
                barcode_col_letter = chr(65 + barcode_col_idx)
                
                # Set column to text format
                text_format = workbook.add_format({
                    'num_format': '@',
                    'text_wrap': False
                })
                worksheet.set_column(f'{barcode_col_letter}:{barcode_col_letter}', 20, text_format)
        
        output.seek(0)
        
        st.download_button(
            label="Download as Excel",
            data=output,
            file_name='processed_trips.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        st.error(f"Error creating Excel file: {e}")

def download_customer_summary(summary_df):
    """Allows users to download the customer summary as CSV."""
    csv = summary_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Customer Summary as CSV",
        data=csv,
        file_name='customer_summary.csv',
        mime='text/csv'
    )

if __name__ == "__main__":
    main()