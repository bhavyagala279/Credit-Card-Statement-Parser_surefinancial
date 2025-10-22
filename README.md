# **Credit Card Statement Parser**

An AI-powered tool to extract key information from credit card statements. Built with Streamlit and powered by Google's Gemini AI.

## **Overview**

This application automatically parses credit card statements and extracts important information including card details, billing information, transaction history, and spending insights. It uses Google's Gemini AI model to intelligently understand different statement formats across various credit card issuers.

## **Features**

* Extracts card information, billing details, and complete transaction history  
* Validates and cleans extracted data automatically  
* Provides spending insights and transaction summaries  
* Export data in JSON or CSV format  
* Clean, intuitive web interface  
* Works with statements from major credit card issuers

## **Installation**

**Requirements:**

* Python 3.8 or higher  
* Google Gemini API key

**Install dependencies:**

bash

pip install streamlit pdfplumber google-generativeai pandas

Or use the requirements file:

bash

pip install \-r requirements.txt

## **Configuration**

Get your Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey).

**Option 1: Direct configuration**

Open `app.py` and add your API key:

python

GEMINI\_API\_KEY \= "your-actual-api-key-here"

**Option 2: Environment variable (recommended)**

Create a `.env` file:

GEMINI\_API\_KEY=your-actual-api-key-here

Then install python-dotenv and update the code:

bash

pip install python-dotenv

python  
from dotenv import load\_dotenv  
import os

load\_dotenv()

GEMINI\_API\_KEY \= os.getenv("GEMINI\_API\_KEY")

## **Usage**

Run the application:

bash

streamlit run app.py

The app will open in your browser at `http://localhost:8501`.

**Steps:**

1. Upload your credit card statement PDF  
2. Click "Parse Statement"  
3. Review extracted information  
4. Download results as JSON or CSV

## 

## 

## **What Gets Extracted**

**Card Information:**

* Issuer name  
* Card type/variant  
* Last 4 digits

**Billing Details:**

* Billing cycle dates  
* Payment due date  
* Total balance and minimum payment  
* Credit limit and available credit  
* Previous balance and new charges

**Transactions:**

* Date, description, and amount for all transactions  
* Automatic calculation of total spent, credits, and averages

## **Supported Cards**

This parser works with most major credit card issuers including Chase, American Express, Citi, Capital One, Discover, Bank of America, Wells Fargo, and others. The AI model adapts to different statement formats automatically.

## **Technical Details**

**Dependencies:**

* `streamlit` \- Web interface  
* `pdfplumber` \- PDF text extraction  
* `google-generativeai` \- Gemini AI API  
* `pandas` \- Data processing

**AI Model:** Gemini 2.5 Flash

**Processing:** Text is extracted locally from PDFs, then sent to the Gemini API for structured data extraction. Results are validated and cleaned before display.

## **Troubleshooting**

**"API key not configured"**

* Check that your API key is properly set in the code or environment variable

**"Model not found" error**

* Try changing the model name to `gemini-pro` in the GeminiParser class

**PDF extraction fails**

* Ensure the PDF is not password protected  
* Check that the file is a valid PDF

**No transactions found**

* Some statement formats may not be fully supported  
* Try with a different statement to verify functionality

## **Project Structure**

surefinancial/    
├── Sample CCS             \# Sample Credit Card Statements
├── Output.pdf             \# Final Results
├── app.py                 \# Main application  
├── README.md              \# Documentation  
├── Project Description    \# Documentation

## **Contributing**

Contributions are welcome. Please open an issue to discuss proposed changes before submitting a pull request.

## **License**

MIT License \- see LICENSE file for details.

## **Acknowledgments**

Built with Google Gemini AI, Streamlit, and pdfplumber.

---

For questions or issues, please open an issue on GitHub.

## 

