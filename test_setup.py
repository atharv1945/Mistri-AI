"""
Quick test script to verify the RAG pipeline setup.
Run this after installing dependencies and configuring .env
"""
import sys
from pathlib import Path

def test_imports():
    """Test that all required packages are installed."""
    print("🔍 Testing imports...")
    try:
        import boto3
        import faiss
        import pandas
        import numpy
        from fastapi import FastAPI
        from dotenv import load_dotenv
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_config():
    """Test AWS configuration."""
    print("\n🔍 Testing AWS configuration...")
    try:
        from backend.config import config
        print(f"✅ Config loaded: {config}")
        return True
    except Exception as e:
        print(f"❌ Config failed: {e}")
        print("💡 Make sure you've created a .env file with AWS credentials")
        return False

def test_data_files():
    """Test that required data files exist."""
    print("\n🔍 Testing data files...")
    csv_path = Path("data/error_codes/lg_error.csv")
    if csv_path.exists():
        print(f"✅ Found error codes CSV: {csv_path}")
        return True
    else:
        print(f"❌ Missing CSV file: {csv_path}")
        return False

def test_vector_store():
    """Test if vector store has been created."""
    print("\n🔍 Testing vector store...")
    index_path = Path("data/vector_store/faiss_index.bin")
    metadata_path = Path("data/vector_store/metadata.json")
    
    if index_path.exists() and metadata_path.exists():
        print(f"✅ Vector store exists")
        return True
    else:
        print(f"⚠️  Vector store not found")
        print(f"💡 Run: python backend/rag_ingest.py")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Mistri.AI RAG Pipeline - Setup Verification")
    print("=" * 60)
    
    results = []
    results.append(("Imports", test_imports()))
    results.append(("Configuration", test_config()))
    results.append(("Data Files", test_data_files()))
    results.append(("Vector Store", test_vector_store()))
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"{status} {name}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n🎉 All checks passed! Ready to run the API.")
        print("\n📝 Next steps:")
        print("   1. python backend/rag_ingest.py  (if not done)")
        print("   2. uvicorn backend.main:app --reload")
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
