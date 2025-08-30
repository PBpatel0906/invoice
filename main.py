import streamlit as st
import PyPDF2
import re
import io
import zipfile
from typing import Dict, List, Tuple
import pandas as pd
from datetime import datetime
import base64
import os
import tempfile
from pathlib import Path
import sqlite3
import hashlib

# Page configuration
st.set_page_config(
    page_title="Invoice Splitter Pro",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-bottom: 2rem;
        border-radius: 10px;
    }
    
    .upload-section {
        background: #f8fafc;
        padding: 2rem;
        border-radius: 10px;
        border: 2px dashed #e2e8f0;
        text-align: center;
        margin: 2rem 0;
    }
    
    .results-section {
        background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
        padding: 2rem;
        border-radius: 10px;
        margin: 2rem 0;
    }
    
    .postal-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin: 1rem 0;
        border-left: 4px solid #667eea;
    }
    
    .feedback-section {
        background: linear-gradient(135deg, #2d3748 0%, #4a5568 100%);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        margin: 2rem 0;
    }
    
    .success-message {
        background: linear-gradient(45deg, #48bb78, #38a169);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        margin: 1rem 0;
    }
    
    .error-message {
        background: linear-gradient(45deg, #f56565, #e53e3e);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        margin: 1rem 0;
    }
    
    .stats-container {
        display: flex;
        justify-content: space-around;
        margin: 2rem 0;
    }
    
    .stat-item {
        text-align: center;
        padding: 1rem;
        background: white;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    .progress-container {
        margin: 1rem 0;
    }
    
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

class InvoiceSplitter:
    def __init__(self):
        self.uk_postal_regex = re.compile(
            r'\b[A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2}\b',
            re.IGNORECASE
        )
        self.processed_files = {}
        
    def extract_text_from_pdf(self, pdf_file) -> List[Tuple[int, str]]:
        """Extract text from each page of the PDF"""
        try:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            pages_text = []
            
            for page_num, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                pages_text.append((page_num, text))
                
            return pages_text
        except Exception as e:
            st.error(f"Error reading PDF: {str(e)}")
            return []
    
    def find_postal_codes(self, text: str) -> List[str]:
        """Find UK postal codes in text"""
        matches = self.uk_postal_regex.findall(text)
        # Clean and standardize postal codes
        cleaned_codes = []
        for match in matches:
            # Remove extra spaces and convert to uppercase
            cleaned = re.sub(r'\s+', ' ', match.strip().upper())
            if cleaned not in cleaned_codes:
                cleaned_codes.append(cleaned)
        return cleaned_codes
    
    def split_pdf_by_postal_codes(self, pdf_file) -> Dict:
        """Split PDF by postal codes found on each page"""
        try:
            pdf_file.seek(0)  # Reset file pointer
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            # Dictionary to store pages by postal code
            postal_code_pages = {}
            unmatched_pages = []
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            total_pages = len(pdf_reader.pages)
            
            for page_num, page in enumerate(pdf_reader.pages):
                status_text.text(f"Processing page {page_num + 1} of {total_pages}...")
                progress_bar.progress((page_num + 1) / total_pages)
                
                text = page.extract_text()
                postal_codes = self.find_postal_codes(text)
                
                if postal_codes:
                    # Use the first postal code found on the page
                    primary_postal_code = postal_codes[0]
                    
                    if primary_postal_code not in postal_code_pages:
                        postal_code_pages[primary_postal_code] = []
                    
                    postal_code_pages[primary_postal_code].append((page_num, page))
                else:
                    unmatched_pages.append((page_num, page))
            
            progress_bar.empty()
            status_text.empty()
            
            return {
                'matched': postal_code_pages,
                'unmatched': unmatched_pages,
                'total_pages': total_pages
            }
            
        except Exception as e:
            st.error(f"Error processing PDF: {str(e)}")
            return {'matched': {}, 'unmatched': [], 'total_pages': 0}
    
    def create_pdf_from_pages(self, pages: List, filename: str) -> bytes:
        """Create a new PDF from selected pages"""
        try:
            pdf_writer = PyPDF2.PdfWriter()
            
            for page_num, page in pages:
                pdf_writer.add_page(page)
            
            output_buffer = io.BytesIO()
            pdf_writer.write(output_buffer)
            output_buffer.seek(0)
            
            return output_buffer.getvalue()
        except Exception as e:
            st.error(f"Error creating PDF for {filename}: {str(e)}")
            return b''
    
    def create_zip_file(self, pdf_files: Dict[str, bytes]) -> bytes:
        """Create a ZIP file containing all split PDFs"""
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filename, pdf_data in pdf_files.items():
                zip_file.writestr(filename, pdf_data)
        
        zip_buffer.seek(0)
        return zip_buffer.getvalue()

class FeedbackManager:
    def __init__(self):
        self.db_path = "feedback.db"
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database for feedback"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                description TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                ip_hash TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def save_feedback(self, name: str, email: str, description: str, ip_address: str = None):
        """Save feedback to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Hash IP address for privacy
            ip_hash = hashlib.sha256(str(ip_address).encode()).hexdigest() if ip_address else None
            
            cursor.execute("""
                INSERT INTO feedback (name, email, description, ip_hash)
                VALUES (?, ?, ?, ?)
            """, (name, email, description, ip_hash))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            st.error(f"Error saving feedback: {str(e)}")
            return False

def main():
    # Initialize classes
    splitter = InvoiceSplitter()
    feedback_manager = FeedbackManager()
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🚚 Invoice Splitter Pro</h1>
        <p>Automatically split PDF invoices by UK postal codes</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Navigation tabs
    tab1, tab2, tab3 = st.tabs(["📄 Upload & Process", "📊 Results", "💬 Feedback"])
    
    with tab1:
        st.markdown("## Upload Your PDF File")
        st.markdown("Upload a PDF file containing multiple invoices. The system will automatically detect UK postal codes and split the document accordingly.")
        
        # File upload
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=['pdf'],
            help="Upload a PDF file up to 200MB"
        )
        
        if uploaded_file is not None:
            # Display file info
            file_size = len(uploaded_file.getvalue()) / (1024 * 1024)  # MB
            st.success(f"✅ File uploaded successfully: **{uploaded_file.name}** ({file_size:.2f} MB)")
            
            # Process button
            if st.button("🚀 Process PDF", type="primary", use_container_width=True):
                with st.spinner("Processing your PDF file..."):
                    # Process the PDF
                    result = splitter.split_pdf_by_postal_codes(uploaded_file)
                    
                    if result['matched'] or result['unmatched']:
                        # Store results in session state
                        st.session_state.processing_result = result
                        st.session_state.uploaded_file = uploaded_file
                        
                        # Show summary
                        matched_pages = sum(len(pages) for pages in result['matched'].values())
                        unmatched_pages = len(result['unmatched'])
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Pages", result['total_pages'])
                        with col2:
                            st.metric("Matched Pages", matched_pages)
                        with col3:
                            st.metric("Postal Codes Found", len(result['matched']))
                        
                        st.success("✅ PDF processed successfully! Check the Results tab to download your split files.")
                        
                        # Auto-switch to results tab (user needs to click)
                        st.info("👉 Click on the **Results** tab to view and download your split PDF files.")
    
    with tab2:
        if 'processing_result' in st.session_state:
            result = st.session_state.processing_result
            uploaded_file = st.session_state.uploaded_file
            
            st.markdown("## 📊 Processing Results")
            
            if result['matched']:
                st.markdown("### Split PDFs by Postal Code")
                
                # Create download files
                pdf_files = {}
                
                for postal_code, pages in result['matched'].items():
                    st.markdown(f"""
                    <div class="postal-card">
                        <h4>📍 {postal_code}</h4>
                        <p><strong>{len(pages)} pages</strong> found with this postal code</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Create PDF for this postal code
                    filename = f"invoices_{postal_code.replace(' ', '_')}.pdf"
                    pdf_data = splitter.create_pdf_from_pages(pages, filename)
                    pdf_files[filename] = pdf_data
                    
                    # Download button for individual PDF
                    st.download_button(
                        label=f"📥 Download {postal_code} PDF",
                        data=pdf_data,
                        file_name=filename,
                        mime="application/pdf",
                        key=f"download_{postal_code}"
                    )
                
                # Handle unmatched pages
                if result['unmatched']:
                    st.markdown("### 📄 Unmatched Pages")
                    st.warning(f"Found {len(result['unmatched'])} pages without valid UK postal codes")
                    
                    unmatched_filename = "unmatched_pages.pdf"
                    unmatched_pdf = splitter.create_pdf_from_pages(result['unmatched'], unmatched_filename)
                    pdf_files[unmatched_filename] = unmatched_pdf
                    
                    st.download_button(
                        label="📥 Download Unmatched Pages",
                        data=unmatched_pdf,
                        file_name=unmatched_filename,
                        mime="application/pdf"
                    )
                
                # Create ZIP file with all PDFs
                st.markdown("### 📦 Download All Files")
                zip_data = splitter.create_zip_file(pdf_files)
                
                st.download_button(
                    label="📦 Download All PDFs (ZIP)",
                    data=zip_data,
                    file_name=f"invoice_split_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                    mime="application/zip",
                    type="primary"
                )
                
                # Statistics
                st.markdown("### 📈 Processing Statistics")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Postal Codes", len(result['matched']))
                with col2:
                    st.metric("Matched Pages", sum(len(pages) for pages in result['matched'].values()))
                with col3:
                    st.metric("Unmatched Pages", len(result['unmatched']))
                with col4:
                    st.metric("Total Pages", result['total_pages'])
                
                # Detailed breakdown
                if st.expander("📋 Detailed Breakdown"):
                    breakdown_data = []
                    for postal_code, pages in result['matched'].items():
                        page_numbers = [str(p[0] + 1) for p in pages]  # Convert to 1-based indexing
                        breakdown_data.append({
                            'Postal Code': postal_code,
                            'Page Count': len(pages),
                            'Page Numbers': ', '.join(page_numbers)
                        })
                    
                    df = pd.DataFrame(breakdown_data)
                    st.dataframe(df, use_container_width=True)
            else:
                st.warning("No postal codes were found in the uploaded PDF. Please check if the document contains valid UK postal codes.")
        else:
            st.info("👆 Upload and process a PDF file in the **Upload & Process** tab to see results here.")
    
    with tab3:
        st.markdown("""
        <div class="feedback-section">
            <h2>💬 Feedback</h2>
            <p>We'd love to hear from you! Share your thoughts, suggestions, or report any issues.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Feedback form
        with st.form("feedback_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Name *", placeholder="Enter your full name")
            
            with col2:
                email = st.text_input("Email *", placeholder="Enter your email address")
            
            description = st.text_area(
                "Description *",
                placeholder="Share your feedback, suggestions, or report any issues. We appreciate your input!",
                height=150
            )
            
            submitted = st.form_submit_button("📤 Send Feedback", type="primary", use_container_width=True)
            
            if submitted:
                if name and email and description:
                    if feedback_manager.save_feedback(name, email, description):
                        st.markdown("""
                        <div class="success-message">
                            ✅ Thank you! Your feedback has been submitted successfully.
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown("""
                        <div class="error-message">
                            ❌ Sorry, there was an error submitting your feedback. Please try again.
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.error("Please fill in all required fields.")
        
        # Usage statistics (optional)
        if st.expander("📊 Usage Statistics"):
            st.info("This section could show application usage statistics if needed.")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 1rem;">
        © 2025 Invoice Splitter Pro. Built with ❤️ using Streamlit for efficient document processing.
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()