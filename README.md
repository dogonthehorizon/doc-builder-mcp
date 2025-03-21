# Document Builder MCP

A Model Context Protocol (MCP) server for building and querying document collections with ChromaDB.

## Features

- Ingest documents to collections with automatic chunking

## Installation

```bash
uv pip install -e .
```

## Usage

Run the MCP server:

```bash
# Run with persistent storage (required)
uv run main.py --chroma-path /path/to/storage/directory
```

### Available Tools

#### File Ingestion

- `ingest_file(file_path, collection_name, content_type)`: Read a file, chunk it, and store in ChromaDB
  - Automatically handles text files with recursive chunking
  - Supports binary and image files
  - Returns truncated content preview (100 chars), content type, file size, and chunk count

### Integration with Claude

Add this server to your Claude configuration:

```json
{
  "mcpServers": {
    "doc-builder": {
      "command": "uv run /path/to/doc_builder_mcp/main.py --chroma-path /path/to/storage/directory"
    }
  }
}
```

## Development

Run the server in development mode with MCP Inspector:

```bash
uv run mcp dev main.py --chroma-path /path/to/dev/storage
```
