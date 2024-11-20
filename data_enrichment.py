# data_enrichment.py

import pandas as pd
import streamlit as st

def load_customer_data(file_path='customer_data.csv'):
    """Loads the backend customer data from a CSV file."""
    try:
        # Read the CSV file from the specified file path
        customer_df = pd.read_csv(
            file_path,
            encoding='latin1',  # Adjust encoding if necessary
            sep=',',
            usecols=[
                'Has Acct', 'Name', 'E-mail Address', 'Created', 'Sales Amt.',
                'Address 1', 'Address2', 'City', 'State', 'ZIP', 'Phone', 'Cell Phone'
            ]
        )

        # Ensure 'E-mail Address' column exists
        if 'E-mail Address' not in customer_df.columns:
            st.error("The customer data file must contain an 'E-mail Address' column.")
            st.stop()

        # Normalize 'E-mail Address' column
        customer_df['E-mail Address'] = customer_df['E-mail Address'].str.lower().str.strip()

        # Drop duplicate email addresses
        customer_df.drop_duplicates(subset='E-mail Address', inplace=True)

        return customer_df
    except Exception as e:
        st.error(f"Error loading customer data: {e}")
        st.stop()

def enrich_uploaded_data(uploaded_df, customer_df):
    """Enriches the uploaded data with customer information."""
    try:
        # Normalize email columns to lowercase and strip whitespace for matching
        uploaded_df['Customer Email'] = uploaded_df['Customer Email'].str.lower().str.strip()

        # Merge the dataframes on the email address using all columns from customer_df
        enriched_df = pd.merge(
            uploaded_df,
            customer_df,
            left_on='Customer Email',
            right_on='E-mail Address',
            how='left',
            validate='many_to_one'  # Ensures uniqueness in customer data
        )

        # Drop the redundant 'E-mail Address' column from the customer data
        enriched_df.drop(columns=['E-mail Address'], inplace=True)

        return enriched_df
    except Exception as e:
        st.error(f"Error enriching the uploaded data: {e}")
        st.stop()
