"""
RAG Ingestion Pipeline for Mistri.AI
Reads error codes from CSV, generates embeddings using AWS Bedrock, and stores in FAISS.
"""
import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

import boto3
import pandas as pd
import numpy as np
import faiss

from backend.config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RAGIngestor:
    """
    Handles ingestion of error codes into the vector database.
    
    This class reads error codes from CSV, generates embeddings using
    Amazon Bedrock Titan, and stores them in a local FAISS index.
    
    TODO: Replace FAISS with Amazon Aurora pgvector for production deployment.
    """
    
    def __init__(self):
        """Initialize the RAG ingestor with Bedrock client."""
        try:
            # Initialize Bedrock Runtime client
            self.bedrock_runtime = boto3.client(
                service_name='bedrock-runtime',
                **config.get_boto3_session_kwargs()
            )
            logger.info(f"Initialized Bedrock client in region: {config.aws_region}")
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {e}")
            raise
        
        # Vector store configuration
        self.vector_store_path = Path(config.vector_store_path)
        self.index_file = self.vector_store_path / "faiss_index.bin"
        self.metadata_file = self.vector_store_path / "metadata.json"
        self.category_index_file = self.vector_store_path / "category_index.json"
        
        # Ensure vector store directory exists
        self.vector_store_path.mkdir(parents=True, exist_ok=True)
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for text using Amazon Bedrock Titan.
        
        Args:
            text: Input text to embed
            
        Returns:
            numpy array of embedding vector (1536 dimensions for Titan)
            
        Raises:
            Exception: If Bedrock API call fails
        """
        try:
            # Prepare request body for Titan embeddings
            request_body = json.dumps({
                "inputText": text
            })
            
            # Invoke Bedrock model
            response = self.bedrock_runtime.invoke_model(
                modelId=config.bedrock_embed_model,
                contentType='application/json',
                accept='application/json',
                body=request_body
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            embedding = np.array(response_body['embedding'], dtype=np.float32)
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding for text: {text[:50]}... Error: {e}")
            raise
    
    def load_error_codes(self, csv_path: str) -> List[Dict[str, str]]:
        """
        Load error codes from CSV file.
        
        Args:
            csv_path: Path to the error codes CSV file
            
        Returns:
            List of dictionaries containing error code data
        """
        try:
            df = pd.read_csv(csv_path)
            logger.info(f"Loaded {len(df)} error codes from {csv_path}")
            
            # Convert to list of dicts
            error_codes = []
            for _, row in df.iterrows():
                error_codes.append({
                    'code': str(row['Error_Code']),
                    'name': str(row['Error_Name']),
                    'description': str(row['Description_Cause'])
                })
            
            return error_codes
            
        except Exception as e:
            logger.error(f"Failed to load error codes from {csv_path}: {e}")
            raise
    
    def format_error_text(self, error: Dict[str, str]) -> str:
        """
        Format error code data into searchable text.
        
        Args:
            error: Dictionary with 'code', 'name', 'description' keys
            
        Returns:
            Formatted text string
        """
        return f"Error {error['code']}: {error['name']} - {error['description']}"
    
    def ingest_error_codes(self, csv_path: str, batch_size: int = 10):
        """
        Main ingestion pipeline: Load CSV, generate embeddings, store in FAISS.
        
        **THE TREE BUILDER**: Attaches metadata for category-based filtering.
        
        Args:
            csv_path: Path to error codes CSV
            batch_size: Number of embeddings to generate before saving checkpoint
        """
        logger.info("Starting error code ingestion pipeline...")
        
        # Load error codes
        error_codes = self.load_error_codes(csv_path)
        
        # Generate embeddings
        embeddings = []
        metadata = []
        category_index = {
            config.CATEGORY_ERROR_CODES: [],
            config.CATEGORY_SCHEMATICS: [],
            config.CATEGORY_GENERAL: []
        }
        
        for i, error in enumerate(error_codes):
            try:
                # Format text
                text = self.format_error_text(error)
                
                # Generate embedding
                logger.info(f"Processing {i+1}/{len(error_codes)}: {error['code']}")
                embedding = self.generate_embedding(text)
                
                embeddings.append(embedding)
                
                # CRITICAL: Attach metadata for tree-based filtering
                # Source is CSV -> category='ERROR_CODES', type='text'
                metadata.append({
                    'id': i,
                    'category': config.CATEGORY_ERROR_CODES,  # Tree category
                    'type': 'text',  # Content type
                    'code': error['code'],
                    'name': error['name'],
                    'description': error['description'],
                    'text': text
                })
                
                # Add to category index
                category_index[config.CATEGORY_ERROR_CODES].append(i)
                
            except Exception as e:
                logger.error(f"Failed to process error code {error['code']}: {e}")
                continue
        
        if not embeddings:
            raise ValueError("No embeddings were generated successfully")
        
        # Convert to numpy array
        embeddings_array = np.vstack(embeddings)
        logger.info(f"Generated {len(embeddings)} embeddings with shape {embeddings_array.shape}")
        
        # Create FAISS index
        # TODO: Replace with Amazon Aurora pgvector connection
        # Example Aurora setup:
        # import psycopg2
        # conn = psycopg2.connect(
        #     host=config.aurora_host,
        #     database=config.aurora_db,
        #     user=config.aurora_user,
        #     password=config.aurora_password
        # )
        # cursor = conn.cursor()
        # cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        # cursor.execute("""
        #     CREATE TABLE IF NOT EXISTS error_embeddings (
        #         id SERIAL PRIMARY KEY,
        #         code TEXT,
        #         category TEXT,
        #         embedding vector(1536)
        #     );
        # """)
        
        dimension = embeddings_array.shape[1]
        index = faiss.IndexFlatL2(dimension)  # L2 distance for similarity
        index.add(embeddings_array)
        
        # Save FAISS index
        faiss.write_index(index, str(self.index_file))
        logger.info(f"Saved FAISS index to {self.index_file}")
        
        # Save metadata
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Saved metadata to {self.metadata_file}")
        
        # Save category index (THE TREE STRUCTURE)
        with open(self.category_index_file, 'w') as f:
            json.dump(category_index, f, indent=2)
        logger.info(f"Saved category index to {self.category_index_file}")
        logger.info(f"Category breakdown: {[(k, len(v)) for k, v in category_index.items()]}")
        
        logger.info(f"✅ Ingestion complete! Indexed {len(embeddings)} error codes.")


def main():
    """Main entry point for ingestion script."""
    # Path to error codes CSV
    csv_path = "data/error_codes/lg_error.csv"
    
    if not os.path.exists(csv_path):
        logger.error(f"Error codes CSV not found at {csv_path}")
        return
    
    try:
        ingestor = RAGIngestor()
        ingestor.ingest_error_codes(csv_path)
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise


if __name__ == "__main__":
    main()
