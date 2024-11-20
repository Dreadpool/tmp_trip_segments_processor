# customer_summary.py

import pandas as pd
import streamlit as st

def generate_customer_summary(df):
    """
    Generates a summary of unique customers based on 'Customer Email',
    including all customer-related information and a count of unique order numbers (# of transactions).

    Parameters:
        df (pd.DataFrame): The processed and enriched DataFrame containing trip segments.

    Returns:
        pd.DataFrame: A DataFrame with unique customers, their information, and transaction counts.
    """
    try:
        # Ensure 'Customer Email' column exists
        if 'Customer Email' not in df.columns:
            st.error("The data must contain a 'Customer Email' column.")
            st.stop()

        # Normalize 'Customer Email' column
        df['Customer Email'] = df['Customer Email'].str.lower().str.strip()

        # Define customer-related columns to include
        customer_columns = [
            'Customer Email',
            'Name',
            'Has Acct',
            'Created',
            'Sales Amt.',
            'Address 1',
            'Address2',
            'City',
            'State',
            'ZIP',
            'Phone',
            'Cell Phone'
        ]

        # Ensure all customer columns are present in the DataFrame
        missing_columns = [col for col in customer_columns if col not in df.columns]
        if missing_columns:
            st.error(f"The following customer data columns are missing: {', '.join(missing_columns)}")
            st.stop()

        # Group by 'Customer Email' and aggregate customer information
        customer_summary = df.groupby('Customer Email').agg({
            'Name': 'first',
            'Has Acct': 'first',
            'Created': 'first',
            'Sales Amt.': 'first',
            'Address 1': 'first',
            'Address2': 'first',
            'City': 'first',
            'State': 'first',
            'ZIP': 'first',
            'Phone': 'first',
            'Cell Phone': 'first',
            'Order #': pd.Series.nunique  # Count unique order numbers
        }).reset_index()

        # Rename columns for clarity
        customer_summary.rename(columns={'Order #': '# of transactions'}, inplace=True)

        return customer_summary

    except Exception as e:
        st.error(f"Error generating customer summary: {e}")
        st.stop()
