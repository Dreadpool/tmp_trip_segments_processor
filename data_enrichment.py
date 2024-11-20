import pandas as pd
import streamlit as st

def load_customer_data(file_path='customer_data.csv'):
    """Loads the backend customer data from a CSV file."""
    try:
        customer_df = pd.read_csv(
            file_path,
            encoding='latin1',
            sep=',',
            usecols=[
                'Has Acct', 'Name', 'E-mail Address', 'Created', 'Sales Amt.',
                'Address 1', 'Address2', 'City', 'State', 'ZIP', 'Phone', 'Cell Phone'
            ]
        )
        
        if 'E-mail Address' not in customer_df.columns:
            st.error("The customer data file must contain an 'E-mail Address' column.")
            st.stop()
            
        customer_df['E-mail Address'] = customer_df['E-mail Address'].str.lower().str.strip()
        customer_df.drop_duplicates(subset='E-mail Address', inplace=True)
        return customer_df
    except Exception as e:
        st.error(f"Error loading customer data: {e}")
        st.stop()

def enrich_uploaded_data(uploaded_df, customer_df):
    """Enriches the uploaded data with customer information."""
    try:
        # Store original Barcode format if it exists
        barcode_series = None
        if 'Barcode' in uploaded_df.columns:
            barcode_series = uploaded_df['Barcode'].astype(str)
        
        # Normalize email columns
        uploaded_df['Customer Email'] = uploaded_df['Customer Email'].str.lower().str.strip()
        
        # Merge the dataframes
        enriched_df = pd.merge(
            uploaded_df,
            customer_df,
            left_on='Customer Email',
            right_on='E-mail Address',
            how='left',
            validate='many_to_one'
        )
        
        # Restore Barcode format if it existed
        if barcode_series is not None:
            enriched_df['Barcode'] = barcode_series
        
        # Drop the redundant email column
        enriched_df.drop(columns=['E-mail Address'], inplace=True)
        
        return enriched_df
    except Exception as e:
        st.error(f"Error enriching the uploaded data: {e}")
        st.stop()