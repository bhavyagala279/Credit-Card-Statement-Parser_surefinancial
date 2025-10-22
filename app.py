import streamlit as st
import pdfplumber
import json
import re
from datetime import datetime
from typing import Dict, List, Optional
import google.generativeai as genai
import pandas as pd
from io import BytesIO
import time

# PAGE CONFIGURATION
st.set_page_config(
    page_title="Credit Card Parser",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        text-align: center;
        color: #666;
        font-size: 1.2rem;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .stDownloadButton button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# CORE FUNCTIONALITY
class PDFExtractor:
    """Extracts text and tables from PDF statements"""
    
    @staticmethod
    def extract_from_pdf(pdf_file) -> Dict:
        """Extract text and tables from uploaded PDF file"""
        extracted_data = {
            "text": "",
            "tables": [],
            "page_count": 0
        }
        
        try:
            with pdfplumber.open(pdf_file) as pdf:
                extracted_data["page_count"] = len(pdf.pages)
                
                all_text = []
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        all_text.append(f"--- Page {page_num} ---\n{page_text}")
                    
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            extracted_data["tables"].append({
                                "page": page_num,
                                "data": table
                            })
                
                extracted_data["text"] = "\n\n".join(all_text)
                
        except Exception as e:
            raise Exception(f"Error reading PDF: {str(e)}")
        
        return extracted_data


class GeminiParser:
    """Uses Gemini API to extract structured data"""
    
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        try:
            self.model = genai.GenerativeModel('gemini-2.5-flash')
        except:
            # Fallback to standard model name
            self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def parse_statement(self, extracted_data: Dict) -> Dict:
        """Parse credit card statement using Gemini"""
        
        prompt = self._build_prompt(extracted_data["text"])
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean response
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            parsed_data = json.loads(response_text)
            return parsed_data
            
        except json.JSONDecodeError as e:
            raise Exception(f"Could not parse AI response: {str(e)}")
        except Exception as e:
            raise Exception(f"AI parsing error: {str(e)}")
    
    def _build_prompt(self, text: str) -> str:
        """Build structured prompt for Gemini"""
        
        return f"""
Analyze this credit card statement and extract key information.

Return ONLY a valid JSON object with these fields (use null if not found):

{{
  "card_issuer": "Bank/issuer name (Chase, Amex, Citi, etc.)",
  "card_variant": "Card type (Platinum, Gold, Rewards, etc.)",
  "card_last_4": "Last 4 digits",
  "billing_cycle_start": "Start date",
  "billing_cycle_end": "End date",
  "payment_due_date": "Due date in YYYY-MM-DD",
  "total_balance": "Total amount due (number only)",
  "minimum_payment": "Minimum payment (number only)",
  "previous_balance": "Previous balance (number only)",
  "new_charges": "New charges amount (number only)",
  "credit_limit": "Credit limit (number only)",
  "available_credit": "Available credit (number only)",
  "transactions": [
    {{
      "date": "MM/DD/YYYY",
      "description": "Transaction description",
      "amount": "Amount (number, negative for credits)"
    }}
  ]
}}

Instructions:
- Extract ALL transactions you can find
- Convert amounts to numbers (remove $ and commas)
- Use null for missing data
- Return ONLY valid JSON

STATEMENT TEXT:
{text[:20000]}
"""


class DataValidator:
    """Validates and cleans extracted data"""
    
    @staticmethod
    def validate(data: Dict) -> Dict:
        """Validate and clean data"""
        
        result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "data": data.copy()
        }
        
        # Validate card_last_4
        if data.get("card_last_4"):
            digits = re.sub(r'\D', '', str(data["card_last_4"]))
            if len(digits) == 4:
                result["data"]["card_last_4"] = digits
            else:
                result["warnings"].append("Card last 4 digits format issue")
        
        # Validate dates
        for date_field in ["payment_due_date", "billing_cycle_start", "billing_cycle_end"]:
            if data.get(date_field):
                cleaned_date = DataValidator._clean_date(data[date_field])
                if cleaned_date:
                    result["data"][date_field] = cleaned_date
        
        # Validate amounts
        amount_fields = ["total_balance", "minimum_payment", "previous_balance", 
                        "new_charges", "credit_limit", "available_credit"]
        
        for field in amount_fields:
            if data.get(field) is not None:
                cleaned = DataValidator._clean_amount(data[field])
                if cleaned is not None:
                    result["data"][field] = cleaned
        
        # Validate transactions
        if data.get("transactions"):
            cleaned_txns = []
            for txn in data["transactions"]:
                if isinstance(txn, dict) and txn.get("description"):
                    cleaned_txn = txn.copy()
                    if "amount" in txn:
                        amount = DataValidator._clean_amount(txn["amount"])
                        if amount is not None:
                            cleaned_txn["amount"] = amount
                    cleaned_txns.append(cleaned_txn)
            result["data"]["transactions"] = cleaned_txns
        
        # Check critical fields
        if not data.get("card_issuer"):
            result["warnings"].append("Could not identify card issuer")
        if not data.get("total_balance"):
            result["warnings"].append("Could not find total balance")
        
        return result
    
    @staticmethod
    def _clean_date(date_str: str) -> Optional[str]:
        """Clean and normalize date"""
        if not date_str:
            return None
        
        formats = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y", 
                   "%B %d, %Y", "%b %d, %Y", "%Y/%m/%d"]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(str(date_str).strip(), fmt)
                return dt.strftime("%Y-%m-%d")
            except:
                continue
        return str(date_str)
    
    @staticmethod
    def _clean_amount(amount) -> Optional[float]:
        """Clean and convert amount to float"""
        if amount is None:
            return None
        
        try:
            if isinstance(amount, (int, float)):
                return float(amount)
            
            if isinstance(amount, str):
                cleaned = re.sub(r'[$,\s]', '', amount.strip())
                # Handle negative amounts
                if '(' in cleaned and ')' in cleaned:
                    cleaned = '-' + cleaned.replace('(', '').replace(')', '')
                return float(cleaned)
        except:
            return None

#Configuration
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"

# STREAMLIT UI

def main():
    """Main Streamlit application"""
    
    # Check if API key is configured
    if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        st.error("⚠️ **Configuration Required**")
        st.warning("""
        Please add your Gemini API key to the code:
        
        1. Open this file in a text editor
        2. Find the line: `GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"`
        3. Replace with your actual key: `GEMINI_API_KEY = "your-actual-api-key"`
        4. Save and restart the app
        
        Get your API key from: https://aistudio.google.com/app/apikey
        """)
        return
    
    # Header
    st.markdown('<div class="main-header">💳 Credit Card Statement Parser</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Extract key information from your credit card statements instantly</div>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("ℹ️ Information")
        
        st.markdown("""
        ### 📋 What This Extracts:
        - **Card Info**: Issuer, variant, last 4 digits
        - **Billing**: Cycle dates, due date
        - **Amounts**: Balance, minimum payment, limits
        - **Transactions**: All purchases and credits
        
        ### 🔒 Privacy & Security:
        - Your PDFs are processed locally
        - Only text content is sent to AI
        - No data is stored permanently
        - Secure API connection
        
        ### 🎯 Supported Cards:
        Works with most major issuers:
        - Chase, Amex, Citi, HDFC
        - ICICI, Bank of America
        - And many more!
        
        ### 🤖 Powered by:
        - **Gemini 2.5 Flash** - Latest AI model
        - Fast and accurate extraction
        """)
        
        st.markdown("---")
        st.caption("Made for easy statement parsing")
    
    # File uploader
    st.header("📤 Upload Statement")
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=['pdf'],
        help="Upload your credit card statement PDF (max 200MB)"
    )
    
    if uploaded_file:
        # Display file info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("File Name", uploaded_file.name)
        with col2:
            st.metric("File Size", f"{uploaded_file.size / 1024:.1f} KB")
        with col3:
            st.metric("Type", "PDF")
        
        st.markdown("---")
        
        # Process button
        if st.button("🚀 Parse Statement", type="primary", use_container_width=True):
            process_statement(uploaded_file, GEMINI_API_KEY)


def process_statement(uploaded_file, api_key: str):
    """Process uploaded statement"""
    
    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Step 1: Extract PDF
        status_text.text("📄 Extracting text from PDF...")
        progress_bar.progress(25)
        
        extractor = PDFExtractor()
        extracted_data = extractor.extract_from_pdf(uploaded_file)
        
        time.sleep(0.5)  # Brief pause for UX
        
        # Step 2: Parse with AI
        status_text.text("🤖 Analyzing with AI...")
        progress_bar.progress(50)
        
        parser = GeminiParser(api_key)
        parsed_data = parser.parse_statement(extracted_data)
        
        time.sleep(0.5)
        
        # Step 3: Validate
        status_text.text("✓ Validating data...")
        progress_bar.progress(75)
        
        validator = DataValidator()
        result = validator.validate(parsed_data)
        
        progress_bar.progress(100)
        status_text.text("✅ Processing complete!")
        time.sleep(0.5)
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
        # Display results
        display_results(result, extracted_data)
        
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"❌ Error: {str(e)}")


def display_results(result: Dict, extracted_data: Dict):
    """Display parsed results in beautiful format"""
    
    data = result["data"]
    
    # Success message
    st.success("✅ Statement parsed successfully!")
    
    # Warnings and errors
    if result["warnings"]:
        with st.expander("⚠️ Warnings", expanded=False):
            for warning in result["warnings"]:
                st.warning(warning)
    
    if result["errors"]:
        with st.expander("❌ Errors", expanded=True):
            for error in result["errors"]:
                st.error(error)
    
    st.markdown("---")
    
    # Card Information
    st.header("📇 Card Information")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Card Issuer",
            data.get("card_issuer", "Unknown"),
            help="Credit card bank or company"
        )
    
    with col2:
        st.metric(
            "Card Type",
            data.get("card_variant", "Unknown"),
            help="Card tier or rewards program"
        )
    
    with col3:
        card_last_4 = data.get("card_last_4", "N/A")
        st.metric(
            "Card Number",
            f"**** {card_last_4}" if card_last_4 != "N/A" else "N/A",
            help="Last 4 digits of card"
        )
    
    st.markdown("---")
    
    # Billing Summary
    st.header("💰 Billing Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        balance = data.get("total_balance")
        st.metric(
            "Total Balance",
            f"${balance:,.2f}" if balance else "N/A",
            help="Total amount due"
        )
    
    with col2:
        min_pay = data.get("minimum_payment")
        st.metric(
            "Minimum Payment",
            f"${min_pay:,.2f}" if min_pay else "N/A",
            help="Minimum amount to avoid late fees"
        )
    
    with col3:
        due_date = data.get("payment_due_date")
        st.metric(
            "Payment Due",
            due_date if due_date else "N/A",
            help="Payment deadline"
        )
    
    with col4:
        new_charges = data.get("new_charges")
        st.metric(
            "New Charges",
            f"${new_charges:,.2f}" if new_charges else "N/A",
            help="Charges this billing cycle"
        )
    
    # Credit Info
    col1, col2, col3 = st.columns(3)
    
    with col1:
        credit_limit = data.get("credit_limit")
        if credit_limit:
            st.metric("Credit Limit", f"${credit_limit:,.2f}")
    
    with col2:
        available = data.get("available_credit")
        if available:
            st.metric("Available Credit", f"${available:,.2f}")
    
    with col3:
        if credit_limit and available:
            utilization = ((credit_limit - available) / credit_limit) * 100
            st.metric("Credit Utilization", f"{utilization:.1f}%")
    
    st.markdown("---")
    
    # Billing Period
    st.header("📅 Billing Period")
    col1, col2 = st.columns(2)
    
    with col1:
        cycle_start = data.get("billing_cycle_start", "N/A")
        st.info(f"**Start Date:** {cycle_start}")
    
    with col2:
        cycle_end = data.get("billing_cycle_end", "N/A")
        st.info(f"**End Date:** {cycle_end}")
    
    st.markdown("---")
    
    # Transactions
    transactions = data.get("transactions", [])
    if transactions:
        st.header(f"📊 Transactions ({len(transactions)} found)")
        
        # Create DataFrame
        df = pd.DataFrame(transactions)
        
        # Format amounts
        if "amount" in df.columns:
            df["amount_formatted"] = df["amount"].apply(
                lambda x: f"${x:,.2f}" if pd.notnull(x) else "N/A"
            )
        
        # Display table
        st.dataframe(
            df[["date", "description", "amount_formatted"]].rename(
                columns={
                    "date": "Date",
                    "description": "Description",
                    "amount_formatted": "Amount"
                }
            ),
            use_container_width=True,
            height=400
        )
        
        # Transaction insights
        if "amount" in df.columns:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_spent = df[df["amount"] > 0]["amount"].sum()
                st.metric("Total Spent", f"${total_spent:,.2f}")
            
            with col2:
                total_credits = abs(df[df["amount"] < 0]["amount"].sum())
                st.metric("Total Credits", f"${total_credits:,.2f}")
            
            with col3:
                avg_transaction = df[df["amount"] > 0]["amount"].mean()
                st.metric("Avg Transaction", f"${avg_transaction:,.2f}" if not pd.isna(avg_transaction) else "N/A")
    
    else:
        st.info("No transactions found in the statement")
    
    st.markdown("---")
    
    # Download options
    st.header("💾 Export Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # JSON download
        json_str = json.dumps(data, indent=2)
        st.download_button(
            label="📥 Download as JSON",
            data=json_str,
            file_name="statement_data.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col2:
        # CSV download (transactions)
        if transactions:
            df_download = pd.DataFrame(transactions)
            csv = df_download.to_csv(index=False)
            st.download_button(
                label="📥 Download Transactions CSV",
                data=csv,
                file_name="transactions.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    # Raw data expander
    with st.expander("🔍 View Raw Extracted Data", expanded=False):
        st.json(data)


if __name__ == "__main__":
    main()