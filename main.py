import argparse
import mimetypes
import uuid
from pathlib import Path
from typing import Optional

import chromadb
from chonkie.chunker import RecursiveChunker
from mcp.server.fastmcp import FastMCP, Image

# Create an MCP server for document building
mcp = FastMCP("DocBuilder")

# Initialize the Chroma client at module level
chroma_client = None


@mcp.tool()
def ingest_file(
    file_path: str, collection_name: str, content_type: Optional[str] = None
) -> dict:
    """
    Read a file from the local filesystem, chunk its contents using RecursiveChunker,
    and store the chunks in the specified Chroma collection.

    Args:
        file_path: Path to the file (absolute or relative)
        collection_name: Name of the Chroma collection to store chunks in
        content_type: Optional MIME type override

    Returns:
        Dictionary containing content, content_type, size, and number of chunks created
    """
    # Verify the collection exists
    global chroma_client
    if not chroma_client:
        return {"error": "Chroma client not initialized"}

    try:
        chroma_client.get_collection(collection_name)
    except ValueError:
        return {
            "error": f"Collection '{collection_name}' does not exist. Please create it first."
        }

    try:
        # Resolve file path
        path = Path(file_path).expanduser().resolve()

        # Check if file exists
        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        # Determine content type if not provided
        if not content_type:
            content_type, _ = mimetypes.guess_type(str(path))
            content_type = content_type or "application/octet-stream"

        # Handle image files
        if content_type and content_type.startswith("image/"):
            # Return image as an MCP Image
            with open(path, "rb") as f:
                binary_data = f.read()
                img_format = content_type.split("/")[-1]
                return {
                    "content": Image(data=binary_data, format=img_format),
                    "content_type": content_type,
                    "size": len(binary_data),
                }

        chunker = RecursiveChunker(chunk_size=1024)
        # Handle text files
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                size = len(content)

                # Create chunks using RecursiveChunker
                chunks = chunker.chunk(content)

                # Prepare documents and metadata for Chroma
                documents = []
                metadatas = []
                ids = []

                # Process each chunk
                for i, chunk in enumerate(chunks):
                    chunk_id = str(uuid.uuid4())
                    documents.append(chunk.text)
                    metadatas.append(
                        {
                            "source_file": str(path),
                            "content_type": content_type,
                            "chunk_index": i,
                            "total_chunks": len(chunks),
                        }
                    )
                    ids.append(chunk_id)

                # Add chunks to the Chroma collection
                collection = chroma_client.get_collection(collection_name)
                collection.add(documents=documents, metadatas=metadatas, ids=ids)

        except UnicodeDecodeError:
            # Handle binary files
            with open(path, "rb") as f:
                binary_data = f.read()
                content = f"<Binary data of type {content_type}, size {len(binary_data)} bytes>"
                size = len(binary_data)

                # For binary files, just add a single entry with metadata
                collection = chroma_client.get_collection(collection_name)
                collection.add(
                    documents=[content],
                    metadatas=[
                        {
                            "source_file": str(path),
                            "content_type": content_type,
                            "is_binary": True,
                        }
                    ],
                    ids=[str(uuid.uuid4())],
                )

        # Truncate content to 100 characters for the response to prevent large outputs
        truncated_content = content[:100] + "..." if len(content) > 100 else content
        return {
            "content": truncated_content,
            "content_type": content_type,
            "size": size,
            "chunks_created": len(chunks) if "chunks" in locals() else 1,  # pyright:ignore
        }

    except Exception as e:
        return {"error": f"Error reading file: {str(e)}"}


def init_chroma(persistent_path):
    """Initialize the Chroma client with a persistent storage path"""
    global chroma_client

    if not persistent_path:
        raise ValueError("A persistent path for Chroma storage is required")

    # Use persistent client with the provided path
    path = Path(persistent_path)
    print(f"Initializing Chroma in persistent mode with path: {path.absolute()}")
    chroma_client = chromadb.PersistentClient(path=str(path.absolute()))


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="DocBuilder MCP Server")
    parser.add_argument(
        "--chroma-path",
        type=str,
        required=True,
        help="Path for Chroma persistent storage. Required for running the DocBuilder MCP server.",
    )

    args = parser.parse_args()

    # Initialize Chroma client
    init_chroma(args.chroma_path)

    # Run the MCP server
    mcp.run()


if __name__ == "__main__":
    main()
