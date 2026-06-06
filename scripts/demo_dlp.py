import sys
import os

# Add the project root to the python path so we can import the app module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.security.dlp_scanner import PIIScanner

def run_demo():
    print("\n" + "="*50)
    print("🛡️ SECURE RAG MVP - DLP SCANNER DEMONSTRATION")
    print("="*50 + "\n")
    
    scanner = PIIScanner()
    
    mock_document = (
        "EMPLOYEE PERFORMANCE REVIEW\n"
        "Name: John Doe\n"
        "Email: john.doe@example.com\n"
        "Phone: 555-019-8273\n"
        "SSN: ***-**-6789\n"
        "\n"
        "Performance Summary:\n"
        "John has been a great asset to the team. Due to his performance, "
        "his base salary will be increased to $115,000.00 effective next month. "
        "Please keep this STRICTLY CONFIDENTIAL.\n"
    )
    
    print("📄 ORIGINAL DOCUMENT (Before Ingestion):")
    print("-" * 40)
    print(mock_document)
    print("-" * 40 + "\n")
    
    print("🔍 RUNNING DLP SCANNER...\n")
    result = scanner.redact(mock_document)
    
    print("✅ REDACTED DOCUMENT (Stored in Vector DB):")
    print("-" * 40)
    print(result.redacted_text)
    print("-" * 40 + "\n")
    
    print("📊 METADATA EXTRACTED:")
    print(f"- Contains Sensitive Data: {result.is_sensitive}")
    print(f"- Flags Triggered: {', '.join(result.flags)}")
    print("\n" + "="*50)

if __name__ == "__main__":
    run_demo()
