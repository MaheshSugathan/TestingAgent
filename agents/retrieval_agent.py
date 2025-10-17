"""Retrieval agent for loading test datasets from S3."""

import json
import time
from typing import List, Dict, Any, Optional
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from langchain.schema import Document
from langchain.document_loaders import TextLoader

from .base import RetrievalAgent, AgentState


class S3RetrievalAgent(RetrievalAgent):
    """Retrieval agent that loads datasets from S3 bucket."""
    
    def __init__(
        self,
        config: Dict[str, Any],
        bucket_name: str,
        key_prefix: str = "test-data/",
        aws_region: str = "us-east-1",
        **kwargs
    ):
        """Initialize S3 retrieval agent.
        
        Args:
            config: Agent configuration
            bucket_name: S3 bucket name
            key_prefix: Key prefix for files
            aws_region: AWS region
            **kwargs: Additional configuration
        """
        super().__init__(config, **kwargs)
        self.bucket_name = bucket_name
        self.key_prefix = key_prefix
        self.aws_region = aws_region
        
        # Initialize S3 client
        try:
            self.s3_client = boto3.client('s3', region_name=aws_region)
            self.logger.info(f"Initialized S3 client for bucket: {bucket_name}")
        except NoCredentialsError:
            self.logger.error("AWS credentials not found")
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize S3 client: {e}")
            raise
    
    async def execute(self, state: AgentState) -> AgentState:
        """Execute retrieval operation.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated agent state with retrieved documents
        """
        start_time = time.time()
        session_id = state.session_id
        
        try:
            self.log_with_context(
                "info",
                "Starting document retrieval from S3",
                session_id=session_id,
                bucket=self.bucket_name,
                prefix=self.key_prefix
            )
            
            # List objects in S3
            objects = await self._list_s3_objects()
            if not objects:
                self.log_with_context(
                    "warning",
                    "No objects found in S3 bucket",
                    session_id=session_id
                )
                return state
            
            # Retrieve documents
            documents = await self._retrieve_documents(objects, session_id)
            
            # Update state
            state.data['documents'] = documents
            state.data['retrieval_metadata'] = {
                'bucket': self.bucket_name,
                'prefix': self.key_prefix,
                'object_count': len(objects),
                'document_count': len(documents),
                'retrieval_time': time.time() - start_time
            }
            
            # Record metrics
            duration = time.time() - start_time
            self._record_execution_time("retrieval", duration, session_id)
            self._record_success("retrieval", session_id)
            self.record_agent_metric(
                metric_name="documents_retrieved",
                value=len(documents),
                unit="Count",
                session_id=session_id
            )
            
            self.log_with_context(
                "info",
                f"Successfully retrieved {len(documents)} documents",
                session_id=session_id,
                duration=duration
            )
            
            return state
            
        except Exception as e:
            self.log_with_context(
                "error",
                f"Failed to retrieve documents: {e}",
                session_id=session_id,
                error=str(e)
            )
            self._record_failure("retrieval", session_id, e)
            raise
    
    async def _list_s3_objects(self) -> List[Dict[str, Any]]:
        """List objects in S3 bucket with the specified prefix.
        
        Returns:
            List of S3 object information
        """
        objects = []
        
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=self.key_prefix
            ):
                if 'Contents' in page:
                    objects.extend(page['Contents'])
            
            # Filter by supported formats
            supported_extensions = {'.json', '.txt', '.md'}
            filtered_objects = [
                obj for obj in objects
                if Path(obj['Key']).suffix.lower() in supported_extensions
            ]
            
            self.logger.info(f"Found {len(filtered_objects)} supported files in S3")
            return filtered_objects
            
        except ClientError as e:
            self.logger.error(f"Failed to list S3 objects: {e}")
            raise
    
    async def _retrieve_documents(
        self,
        objects: List[Dict[str, Any]],
        session_id: str
    ) -> List[Document]:
        """Retrieve and parse documents from S3 objects.
        
        Args:
            objects: List of S3 object information
            session_id: Session ID for logging
            
        Returns:
            List of LangChain documents
        """
        documents = []
        
        for obj in objects:
            try:
                # Download object content
                response = self.s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key=obj['Key']
                )
                
                content = response['Body'].read().decode('utf-8')
                file_path = Path(obj['Key'])
                file_extension = file_path.suffix.lower()
                
                # Parse based on file type
                if file_extension == '.json':
                    doc = await self._parse_json_content(content, obj['Key'])
                elif file_extension in ['.txt', '.md']:
                    doc = await self._parse_text_content(content, obj['Key'])
                else:
                    self.log_with_context(
                        "warning",
                        f"Unsupported file format: {file_extension}",
                        session_id=session_id,
                        file_key=obj['Key']
                    )
                    continue
                
                if doc:
                    documents.append(doc)
                    
            except Exception as e:
                self.log_with_context(
                    "error",
                    f"Failed to process file {obj['Key']}: {e}",
                    session_id=session_id,
                    file_key=obj['Key'],
                    error=str(e)
                )
                continue
        
        return documents
    
    async def _parse_json_content(self, content: str, file_key: str) -> Optional[Document]:
        """Parse JSON content into a Document.
        
        Args:
            content: File content as string
            file_key: S3 object key
            
        Returns:
            LangChain Document or None
        """
        try:
            data = json.loads(content)
            
            # Handle different JSON structures
            if isinstance(data, list):
                # Multiple documents
                texts = []
                for item in data:
                    if isinstance(item, dict):
                        if 'text' in item:
                            texts.append(item['text'])
                        elif 'content' in item:
                            texts.append(item['content'])
                        else:
                            texts.append(str(item))
                    else:
                        texts.append(str(item))
                text_content = '\n\n'.join(texts)
            elif isinstance(data, dict):
                if 'text' in data:
                    text_content = data['text']
                elif 'content' in data:
                    text_content = data['content']
                else:
                    text_content = json.dumps(data, indent=2)
            else:
                text_content = str(data)
            
            return Document(
                page_content=text_content,
                metadata={
                    'source': file_key,
                    'file_type': 'json',
                    's3_bucket': self.bucket_name
                }
            )
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON from {file_key}: {e}")
            return None
    
    async def _parse_text_content(self, content: str, file_key: str) -> Document:
        """Parse text content into a Document.
        
        Args:
            content: File content as string
            file_key: S3 object key
            
        Returns:
            LangChain Document
        """
        return Document(
            page_content=content,
            metadata={
                'source': file_key,
                'file_type': 'text',
                's3_bucket': self.bucket_name
            }
        )
    
    async def get_single_document(self, key: str) -> Optional[Document]:
        """Retrieve a single document by S3 key.
        
        Args:
            key: S3 object key
            
        Returns:
            LangChain Document or None
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            content = response['Body'].read().decode('utf-8')
            file_path = Path(key)
            file_extension = file_path.suffix.lower()
            
            if file_extension == '.json':
                return await self._parse_json_content(content, key)
            else:
                return await self._parse_text_content(content, key)
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve single document {key}: {e}")
            return None
