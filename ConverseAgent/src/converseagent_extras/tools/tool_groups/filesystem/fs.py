import csv
import fnmatch
import io
import json
import os
import re
import shutil
import time
from typing import Any, Dict, List, Optional

from pdf2image import convert_from_path, pdfinfo_from_path
from pydantic import Field, model_validator

from converseagent.content import ImageContentBlock, TextContentBlock
from converseagent.logging_utils.logger_config import setup_logger
from converseagent.tools.base import BaseTool, BaseToolGroup
from converseagent.tools.tool_response import (
    BaseToolResponse,
    DocumentToolResponse,
    ImageToolResponse,
    ResponseStatus,
    ResponseType,
    TextToolResponse,
)

logger = setup_logger(__name__)


class FileSystemToolGroup(BaseToolGroup):
    """A group of tools for performing file system operations.

    This class contains various tools for file system operations such as
    listening directories, reading and writing files, and manipulating PDFs.
    """

    base_dir: str | None = Field(default=None)

    name: str = "fs_tools"
    description: str = "Tools for performing file system operations"
    instructions: str = """
    Use these tools to perform filesystem operations. 
    Be cautious when writing to or deleting files, as these actions 
    can't be undone.
    
    When renaming files or creating directories, ensure the paths are valid
    and you have the required permissions.
    
    When copying files or directories, make sure the destination path is 
    valid and you have write permissions.
    
    If you are reading PDF files, make sure to read the info first using 
    read_pdf_info tool before using read_pdf_file tool read the PDF. 
    If you have already read the PDF file and its pages before, and you 
    still have access to the previous results of read_pdf_file, try not 
    to read the PDF file again unless you absolutely need to.
    """

    @model_validator(mode="after")
    def validate_tools(self):
        """Check if tools are passed, otherwise add tools"""

        if not self.tools:
            self.tools = [
                ListDirectoryTool(base_dir=self.base_dir),
                ReadTextFilesTool(base_dir=self.base_dir),
                WriteTextFileTool(base_dir=self.base_dir),
                RenameFileTool(base_dir=self.base_dir),
                CreateDirectoriesTool(base_dir=self.base_dir),
                FileInfoTool(base_dir=self.base_dir),
                SearchFilesTool(base_dir=self.base_dir),
                CopyFileTool(base_dir=self.base_dir),
                CopyDirectoryTool(base_dir=self.base_dir),
                ReadPdfInfoTool(base_dir=self.base_dir),
                ReadPdfFileTool(base_dir=self.base_dir),
                EditTextFileTool(base_dir=self.base_dir),
                GetDirectoryTreeTool(base_dir=self.base_dir),
            ]
        return self

    @classmethod
    def get_tool_group_spec(cls):
        """Returns the tool group spec"""

        return {
            "toolGroupSpec": {
                "name": cls.model_fields["name"].default,
                "description": cls.model_fields["description"].default,
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "base_dir": {
                                "type": "string",
                                "description": "The base directory to limit the tools to",
                            }
                        },
                    }
                },
            }
        }


def check_file_path_within_base(base_dir, path):
    """Validates whether the given path  is within the base_dir.
    If the path is not within the base_dir, raises an error.

    Args:
        base_dir (str): The base dir
        path (str): The path to check

    Raises:
        ValueError
    """

    # Check if path in base dir, raise error if not
    if not os.path.abspath(path).startswith(os.path.abspath(base_dir)):
        raise PermissionError(
            f"Permission Denied: Path {path} is not within base directory {base_dir}"
        )


class BaseFileTool(BaseTool):
    """Base class for file system tools."""

    base_dir: str | None = Field(
        default=None, description="The base directory to limit the tools to"
    )


class ListDirectoryTool(BaseFileTool):
    """Lists the contents of a directory"""

    name: str = "list_directory"
    description: str = "Use this tool to list directories and files in a specified path"

    def invoke(self, *args, **kwargs) -> TextToolResponse:
        """Invokes the tool logic"""

        return self.list_directory(*args, **kwargs)

    def list_directory(self, path: str) -> TextToolResponse:
        """Lists the contents of a directory

        Args:
            path (str): The directory path to list.

        Returns:
            BaseToolResponse: The response from the tool containing the directory contents
        """

        # Get absolute path
        path = os.path.abspath(path)

        # Check path
        if self.base_dir:
            check_file_path_within_base(self.base_dir, path)

        try:
            # List the contents of the path
            contents = os.listdir(path)

            # Format the output to CSV
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Name", "Type"])
            for item in contents:
                item_path = os.path.join(path, item)
                item_type = "Directory" if os.path.isdir(item_path) else "File"
                writer.writerow([item, item_type])

            return TextToolResponse(ResponseStatus.SUCCESS, output.getvalue())

        except Exception as e:
            return TextToolResponse(
                ResponseStatus.ERROR, f"Listing directory encountered an error: {e}"
            )

    def get_tool_spec(self) -> Dict:
        """Returns the tool spec

        Returns:
            dict: The tool spec for the ListDirectoryTool
        """
        return {
            "toolSpec": {
                "name": self.name,
                "description": self.description,
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "The directory path to list. \
                                Defaults to current directory if not specified.",
                            }
                        },
                    }
                },
            }
        }


# Deprecated: See ReadTextFilesTool
class ReadTextFileTool(BaseFileTool):
    """Reads a text file"""

    name: str = "read_file"
    description: str = (
        "Use this tool to read the contents of "
        "plaintext file, optionally specifying start and end lines,"
        "and with an option to return line numbers"
    )

    def invoke(self, *args, **kwargs) -> TextToolResponse:
        """Invokes the tool logic"""

        return self.read_file(*args, **kwargs)

    def read_file(
        self,
        file_path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        return_line_numbers: Optional[bool] = False,
    ) -> TextToolResponse:
        """Reads the file and returns the the text.

        Args:
            file_path (str): The path to the file to be read
            start_line (int, optional): The line number to start reading from
                (1-based index, optional)
            end_line (int, optional): The line number to end reading at
                (inclusive, optional)
            return_line_numbers (bool, optional): Whether to include line
                numbers in the output (optional, default: false)

        Returns:
            TextToolResponse: The response from the tool containing the file
                contents
        """

        # Get absolute path
        file_path = os.path.abspath(file_path)

        # Check path
        if self.base_dir:
            check_file_path_within_base(self.base_dir, file_path)

        try:
            if not os.path.exists(file_path):
                return TextToolResponse(
                    ResponseStatus.ERROR, f"Error: File not found at {file_path}"
                )

            with open(file_path, "r", encoding="utf-8") as file:
                lines = file.readlines()
                start = max(0, start_line - 1) if start_line is not None else 0
                end = min(len(lines), end_line) if end_line is not None else len(lines)

                if return_line_numbers:
                    tool_response = TextToolResponse(
                        ResponseStatus.SUCCESS,
                        "".join(
                            f"{i + 1}: {line}"
                            for i, line in enumerate(lines[start:end], start=start)
                        ),
                    )
                    return tool_response

                else:
                    return TextToolResponse(
                        ResponseStatus.SUCCESS, "".join(lines[start:end])
                    )

        except UnicodeDecodeError:
            return TextToolResponse(
                ResponseStatus.ERROR,
                "Error: File is not encoded in UTF-8 or not a plaintext file",
            )

        except Exception as e:
            return TextToolResponse(
                ResponseStatus.ERROR, f"Reading file encountered an error: {e}"
            )

    def get_tool_spec(self) -> Dict:
        return {
            "toolSpec": {
                "name": self.name,
                "description": self.description,
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "The path to the file to be read",
                            },
                            "start_line": {
                                "type": "integer",
                                "description": "The line number to start reading \
                                    from (1-based index, optional)",
                            },
                            "end_line": {
                                "type": "integer",
                                "description": "The line number to end reading \
                                    at (inclusive, optional)",
                            },
                            "return_line_numbers": {
                                "type": "boolean",
                                "description": "Whether to include line numbers \
                                    in the output (optional, default: false)",
                            },
                        },
                        "required": ["file_path"],
                    }
                },
            }
        }


class ReadTextFilesTool(BaseFileTool):
    """Reads one or more text files"""

    name: str = "read_files"
    description: str = (
        "Use this tool to read the contents of "
        "plaintext files, optionally specifying start and end lines,"
        "and with an option to return line numbers"
    )

    def invoke(self, *args, **kwargs) -> BaseToolResponse:
        """Invokes the tool logic"""

        return self.read_files(*args, **kwargs)

    def read_files(self, files: List[Dict]) -> BaseToolResponse:
        """Reads each of the files and returns each of the text

        Args:
            files (List[Dict]): A list containing dicts of files to read
                - file_path (str): The path to the file to be read
                - start_line (int, optional): The line number to start reading from
                    (1-based index, optional)
                - end_line (int, optional): The line number to end reading at
                    (inclusive, optional)
                - return_line_numbers (bool, optional): Whether to include line
                    numbers in the output (optional, default: false)

        Returns:
            BaseContentBlock: Contains one or more Text content
        """

        # Final tool response
        tool_response = BaseToolResponse(
            status=ResponseStatus.SUCCESS, type=ResponseType.CONTENT
        )

        for file in files:
            read_response = {"file_path": file["file_path"]}

            # Get absolute path
            file_path = os.path.abspath(file["file_path"])
            start_line = file["start_line"] if "start_line" in file else None
            end_line = file["end_line"] if "end_line" in file else None
            return_line_numbers = (
                file["return_line_numbers"] if "return_line_numbers" in file else None
            )

            # Check path
            if self.base_dir:
                check_file_path_within_base(self.base_dir, file_path)

            try:
                if not os.path.exists(file_path):
                    read_response["content"] = f"Error: File not found at {file_path}"

                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    start = max(0, start_line - 1) if start_line is not None else 0
                    end = (
                        min(len(lines), end_line)
                        if end_line is not None
                        else len(lines)
                    )

                    if return_line_numbers:
                        read_response["content"] = "".join(
                            f"{i + 1}: {line}"
                            for i, line in enumerate(lines[start:end], start=start)
                        )

                    else:
                        read_response["content"] = "".join(lines[start:end])

            except UnicodeDecodeError:
                read_response["content"] = (
                    "Error: File is not encoded in UTF-8 or not a plaintext file",
                )

            except Exception as e:
                read_response["content"] = f"Reading file encountered an error: {e}"

            # Append result to tool_response
            tool_response.append_content(TextContentBlock(text=str(read_response)))

        return tool_response

    def get_tool_spec(self) -> Dict:
        return {
            "toolSpec": {
                "name": self.name,
                "description": self.description,
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "files": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "file_path": {
                                            "type": "string",
                                            "description": "The path to the file to be read",
                                        },
                                        "start_line": {
                                            "type": "integer",
                                            "description": "The line number to start reading \
                                                from (1-based index, optional)",
                                        },
                                        "end_line": {
                                            "type": "integer",
                                            "description": "The line number to end reading \
                                                at (inclusive, optional)",
                                        },
                                        "return_line_numbers": {
                                            "type": "boolean",
                                            "description": "Whether to include line numbers \
                                                in the output (optional, default: false)",
                                        },
                                    },
                                    "required": ["file_path"],
                                },
                            }
                        },
                        "required": ["files"],
                    }
                },
            }
        }


class ReadPdfInfoTool(BaseFileTool):
    """Reads the PDF metadata"""

    name: str = "read_pdf_info"
    description: str = "Use this tool to read the metadata information \
        of a PDF file."

    def invoke(self, *args, **kwargs) -> TextToolResponse:
        """Invokes the tool logic"""
        return self.read_pdf_info(*args, **kwargs)

    def read_pdf_info(self, file_path: str) -> TextToolResponse:
        """Reads the PDF file and returns the metadata.

        Args:
            file_path (str): The path to the PDF file to be read

        Returns:
            TextToolResponse: The response from the tool containing the PDF
                metadata
        """

        # Get absolute path
        file_path = os.path.abspath(file_path)

        # Check path
        if self.base_dir:
            check_file_path_within_base(self.base_dir, file_path)

        try:
            if not os.path.exists(file_path):
                return TextToolResponse(
                    ResponseStatus.ERROR, f"Error: File not found at {file_path}"
                )

            info = pdfinfo_from_path(file_path)

            return TextToolResponse(ResponseStatus.SUCCESS, json.dumps(info))

        except Exception as e:
            return TextToolResponse(
                ResponseStatus.ERROR, f"Reading PDF file encountered an error: {e}"
            )

    def get_tool_spec(self) -> Dict:
        return {
            "toolSpec": {
                "name": self.name,
                "description": self.description,
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "The path to the PDF file to be read",
                            }
                        },
                        "required": ["file_path"],
                    }
                },
            }
        }


class ReadPdfFileTool(BaseFileTool):
    """Reads the PDF file"""

    name: str = "read_pdf_file"
    description: str = (
        "Use this tool to read the contents of a PDF file."
        "A maximum of 20 pages can be read at one time."
    )

    as_images: bool = Field(default=True)

    def invoke(self, *args, **kwargs) -> TextToolResponse:
        """Invokes the tool logic"""
        return self.read_pdf_file(*args, **kwargs)

    def read_pdf_file(
        self,
        file_path: str,
        first_page: Optional[int] = None,
        last_page: Optional[int] = None,
    ) -> TextToolResponse:
        """Reads the PDF file and returns the text.

        Args:
            file_path (str): The path to the PDF file to be read
            first_page (int, optional): The page number to start reading from
                (1-based index, optional)
            last_page (int, optional): The page number to end reading at
                (inclusive, optional)

        Returns:
            TextToolResponse: The response from the tool containing the PDF
                contents
        """

        # Get absolute path
        file_path = os.path.abspath(file_path)

        # Uses an image-based approach to reading PDFs
        if self.as_images:
            # Check if last page is not less than first page
            if (
                last_page is not None
                and first_page is not None
                and last_page < first_page
            ):
                return TextToolResponse(
                    ResponseStatus.ERROR,
                    "Error: Last page cannot be less than the first page",
                )

            # Limit the number of pages to read
            if (
                last_page is not None
                and first_page is not None
                and (last_page - first_page + 1) > 20
            ):
                response = TextToolResponse(
                    ResponseStatus.ERROR,
                    text=(
                        f"Error: Cannot read more than 20 pages at once. "
                        f"You requested {last_page - first_page + 1} pages."
                    ),
                )

                return response

            content_list = []

            try:
                if not os.path.exists(file_path):
                    return TextToolResponse(
                        ResponseStatus.ERROR, f"Error: File not found at {file_path}"
                    )

                else:
                    # Read metadata
                    info = pdfinfo_from_path(file_path)

                    if info["Pages"] > 20 and last_page - first_page + 1 > 20:
                        return TextToolResponse(
                            ResponseStatus.ERROR,
                            text=(
                                f"Error: PDF file has more than 20 pages. "
                                f"Cannot read {info['Pages']} pages at once. "
                                "Specify first and last pages."
                            ),
                        )

                    # Convert PDF to images
                    images = convert_from_path(
                        file_path, first_page=first_page, last_page=last_page
                    )

                    content_list.append(
                        TextContentBlock(text=f"Contents of : {file_path}")
                    )

                    start_page = first_page if first_page is not None else 1
                    for i, img in enumerate(images, start=start_page):
                        img_byte_arr = io.BytesIO()
                        img.save(img_byte_arr, format="jpeg")

                        content_list.append(TextContentBlock(text=f"Page {i}"))

                        content_list.append(
                            ImageContentBlock(
                                extension="jpeg",
                                name=f"pg_{first_page}",
                                content_bytes=img_byte_arr.getvalue(),
                            )
                        )

                return BaseToolResponse(
                    status=ResponseStatus.SUCCESS,
                    type=ResponseType.CONTENT,
                    content=content_list,
                )

            except Exception as e:
                return TextToolResponse(
                    ResponseStatus.ERROR, f"Reading PDF file encountered an error: {e}"
                )

        # Uses Converse document block
        else:
            try:
                return DocumentToolResponse(
                    ResponseStatus.SUCCESS, uri=f"file://{file_path}"
                )

            except Exception as e:
                return TextToolResponse(
                    ResponseStatus.ERROR, f"Reading PDF file encountered an error: {e}"
                )

    def get_tool_spec(self) -> Dict:
        return {
            "toolSpec": {
                "name": self.name,
                "description": self.description,
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "The path to the PDF file to be read",
                            },
                            "first_page": {
                                "type": "integer",
                                "description": "The first page to read",
                            },
                            "last_page": {
                                "type": "integer",
                                "description": "The last page to read",
                            },
                        },
                        "required": ["file_path", "first_page", "last_page"],
                    }
                },
            }
        }


class ReadDocumentFileTool(BaseFileTool):
    """
    General purpose tool for reading pdf, csv, doc,
    docx, xls, xlsx, html, txt, and md.
    """

    name: str = "read_document_file"
    description: str = (
        "This tool can read pdf, csv, doc, docx, xls, xlsx,html, txt, and md."
    )

    def invoke(self, *args, **kwargs) -> DocumentToolResponse:
        """Invokes the tool logic"""
        return self.read_document_file(*args, **kwargs)

    def read_document_file(self, file_path: str) -> DocumentToolResponse:
        """Reads the document and returns a DocumentToolResponse"""

        # Get absolute filepath
        file_path = os.path.abspath(file_path)

        # Check path
        if self.base_dir:
            check_file_path_within_base(self.base_dir, file_path)

        try:
            return DocumentToolResponse(uri=f"file://{file_path}")

        except Exception as e:
            return TextToolResponse(
                ResponseStatus.ERROR, f"Reading PDF file encountered an error: {e}"
            )

    def get_tool_spec(self) -> Dict:
        return {
            "toolSpec": {
                "name": self.name,
                "description": self.description,
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "The filepath of the file",
                            }
                        },
                        "required": ["file_path"],
                    }
                },
            }
        }


class ReadImageFileTool(BaseFileTool):
    """
    Tool for reading image files
    """

    name: str = "read_image_file"
    description: str = "This tool can read png, jpeg, gif, webp"

    def invoke(self, *args, **kwargs) -> ImageToolResponse:
        """Invokes the tool logic"""
        return self.read_image_file(*args, **kwargs)

    def read_image_file(self, file_path: str) -> ImageToolResponse:
        """Reads the image and returns a ImageToolResponse"""

        # Get absolute filepath
        file_path = os.path.abspath(file_path)

        # Check path
        if self.base_dir:
            check_file_path_within_base(self.base_dir, file_path)

        try:
            return ImageToolResponse(uri=f"file://{file_path}")

        except Exception as e:
            return TextToolResponse(
                ResponseStatus.ERROR, f"Reading PDF file encountered an error: {e}"
            )

    def get_tool_spec(self) -> Dict:
        return {
            "toolSpec": {
                "name": self.name,
                "description": self.description,
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Filepath of the file",
                            }
                        },
                        "required": ["file_path"],
                    }
                },
            }
        }


class WriteTextFileTool(BaseFileTool):
    """Writes contents to a text file"""

    name: str = "write_text_file"
    description: str = """Use this tool to create a new file or write to an existing file.
    When using this tool, you must absolutely write the entire contents even
    if only a portion of it changes as the entire file will be overriden with the content you specify.
    """

    def invoke(self, *args, **kwargs) -> BaseToolResponse:
        """Invokes the tool logic"""
        return self.write_file(*args, **kwargs)

    def write_file(self, file_path: str, content: str) -> TextToolResponse:
        """Writes to a file.

        Args:
            file_path (str): The path to the file to be written
            content (str): The content to write to the file

        Returns:
            TextToolResponse: The response from the tool containing the status of
                the write operation
        """

        # Get absolute path
        file_path = os.path.abspath(file_path)

        # Check path
        if self.base_dir:
            check_file_path_within_base(self.base_dir, file_path)

        try:
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(content)
            return TextToolResponse(
                ResponseStatus.SUCCESS, f"Successfully wrote to {file_path}"
            )
        except Exception as e:
            return TextToolResponse(
                ResponseStatus.ERROR, f"Writing to file encountered an error: {e}"
            )

    def get_tool_spec(self) -> Dict:
        return {
            "toolSpec": {
                "name": self.name,
                "description": self.description,
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "The path to the file to be written",
                            },
                            "content": {
                                "type": "string",
                                "description": "The content to write to the file",
                            },
                        },
                        "required": ["file_path", "content"],
                    }
                },
            }
        }


class RenameFileTool(BaseFileTool):
    """Renames a file"""

    name: str = "rename_file"
    description: str = "Use this tool to rename a file or directory"

    def invoke(self, *args, **kwargs) -> TextToolResponse:
        """Invokes the tool logic"""
        return self.rename_file(*args, **kwargs)

    def rename_file(self, old_path: str, new_path: str) -> TextToolResponse:
        """Renames a file or directory.

        Args:
            old_path (str): The current path of the file or directory
            new_path (str): The new path for the file or directory

        Returns:
            TextToolResponse: The response from the tool containing the status of
                the rename operation
        """

        # Get absolute paths
        old_path = os.path.abspath(old_path)
        new_path = os.path.abspath(new_path)

        # Check path
        if self.base_dir:
            check_file_path_within_base(self.base_dir, old_path)
            check_file_path_within_base(self.base_dir, new_path)

        try:
            os.rename(old_path, new_path)
            return TextToolResponse(
                ResponseStatus.SUCCESS, f"Successfully renamed {old_path} to {new_path}"
            )
        except Exception as e:
            return TextToolResponse(
                ResponseStatus.ERROR, f"Renaming file encountered an error: {e}"
            )

    def get_tool_spec(self) -> Dict:
        return {
            "toolSpec": {
                "name": self.name,
                "description": self.description,
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "old_path": {
                                "type": "string",
                                "description": "The current path of the file or directory",
                            },
                            "new_path": {
                                "type": "string",
                                "description": "The new path for the file or directory",
                            },
                        },
                        "required": ["old_path", "new_path"],
                    }
                },
            }
        }


class CreateDirectoriesTool(BaseFileTool):
    """Creates directories"""

    name: str = "create_directories"
    description: str = "Use this tool to create multiple new directories"

    def invoke(self, *args, **kwargs) -> TextToolResponse:
        """Invokes the tool logic"""
        return self.create_directories(*args, **kwargs)

    def create_directories(self, directory_paths: List[str]) -> TextToolResponse:
        """Creates the directories

        Args:
            directory_paths (List[str]): The list of directory paths to be created

        """

        results = []
        for directory_path in directory_paths:
            # Get the absolute path to create
            directory_path = os.path.abspath(directory_path)

            # Check path
            if self.base_dir:
                check_file_path_within_base(self.base_dir, directory_path)

            try:
                os.makedirs(directory_path, exist_ok=True)
                results.append(f"Successfully created directory {directory_path}")
            except Exception as e:
                results.append(f"Error creating directory {directory_path}: {e}")

        return TextToolResponse(ResponseStatus.SUCCESS, "\n".join(results))

    def get_tool_spec(self) -> Dict:
        return {
            "toolSpec": {
                "name": self.name,
                "description": self.description,
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "directory_paths": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "The list of directory paths to be created",
                            }
                        },
                        "required": ["directory_paths"],
                    }
                },
            }
        }


class FileInfoTool(BaseFileTool):
    """Gets the file metadata"""

    name: str = "file_info"
    description: str = "Use this tool to get detailed information about a file"

    def invoke(self, *args, **kwargs) -> TextToolResponse:
        """Invokes the tool logic"""
        return self.file_info(*args, **kwargs)

    def file_info(self, file_path: str) -> TextToolResponse:
        """Returns the file metadata

        Args:
            file_path (str): The path to the file

        Returns:
            TextToolResponse: The response from the tool containing the file
                metadata
        """

        # Get the absolute path
        file_path = os.path.abspath(file_path)

        # Check path
        if self.base_dir:
            check_file_path_within_base(self.base_dir, file_path)

        try:
            if not os.path.exists(file_path):
                return TextToolResponse(
                    ResponseStatus.ERROR, f"Error: File not found at {file_path}"
                )

            stat_info = os.stat(file_path)
            info = {
                "name": os.path.basename(file_path),
                "size": stat_info.st_size,
                "created": time.ctime(stat_info.st_ctime),
                "last_modified": time.ctime(stat_info.st_mtime),
                "last_accessed": time.ctime(stat_info.st_atime),
                "is_directory": os.path.isdir(file_path),
            }
            return TextToolResponse(ResponseStatus.SUCCESS, json.dumps(info, indent=2))
        except Exception as e:
            return TextToolResponse(
                ResponseStatus.ERROR, f"Getting file info encountered an error: {e}"
            )

    def get_tool_spec(self) -> Dict:
        return {
            "toolSpec": {
                "name": self.name,
                "description": self.description,
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "The path to the file",
                            }
                        },
                        "required": ["file_path"],
                    }
                },
            }
        }


class SearchFilesTool(BaseFileTool):
    """Searches for files that matchas a pattern"""

    name: str = "search_files"
    description: str = "Use this tool to search for files matching a pattern in \
        a directory"

    def invoke(self, *args, **kwargs) -> TextToolResponse:
        """Invokes the tool logic"""

        return self.search_files(*args, **kwargs)

    def search_files(self, directory: str, pattern: str) -> TextToolResponse:
        """
        Searches for a pattern within the directory and returns the list of files

        Args:
            directory (str): The directory to search in
            pattern (str): The pattern to match against file names

        Returns:
            TextToolResponse: The response from the tool containing the list of
                matching files
        """

        # Get the absolute path
        directory = os.path.abspath(directory)

        # Check path
        if self.base_dir:
            check_file_path_within_base(self.base_dir, directory)

        try:
            # Convert the fnmatch pattern to a regular expression pattern
            regex_pattern = fnmatch.translate(pattern)
            # Compile the regular expression with IGNORECASE flag
            regex = re.compile(regex_pattern, re.IGNORECASE)

            matches = []
            for root, dirnames, filenames in os.walk(directory):
                # Use a list comprehension with regex.match for case-insensitive matching
                matches.extend(
                    os.path.join(root, filename)
                    for filename in filenames
                    if regex.match(filename)
                )
            return TextToolResponse(
                ResponseStatus.SUCCESS, json.dumps(matches, indent=2)
            )
        except Exception as e:
            return TextToolResponse(
                ResponseStatus.ERROR, f"Searching files encountered an error: {e}"
            )

    def get_tool_spec(self) -> TextToolResponse:
        return {
            "toolSpec": {
                "name": self.name,
                "description": self.description,
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "directory": {
                                "type": "string",
                                "description": "The directory to search in",
                            },
                            "pattern": {
                                "type": "string",
                                "description": "The pattern to match against file names",
                            },
                        },
                        "required": ["directory", "pattern"],
                    }
                },
            }
        }


class CopyFileTool(BaseFileTool):
    """Copies a file from one location to another"""

    name: str = "copy_file"
    description: str = "Use this tool to copy a file from one location to another"

    def invoke(self, *args, **kwargs) -> TextToolResponse:
        """Invokes the tool logic"""
        return self.copy_file(*args, **kwargs)

    def copy_file(self, source_path: str, destination_path: str) -> TextToolResponse:
        """Copies the file from the source to destination

        Args:
            source_path (str): The source filepath
            destination_path (str): The destination filepath

        Returns:
            TextToolResponse: The response from the tool containing the status of
                the copy operation
        """

        # Get absolute paths
        source_path = os.path.abspath(source_path)
        destination_path = os.path.abspath(destination_path)

        # Check path
        if self.base_dir:
            check_file_path_within_base(self.base_dir, source_path)
            check_file_path_within_base(self.base_dir, destination_path)

        try:
            shutil.copy2(source_path, destination_path)
            return TextToolResponse(
                ResponseStatus.SUCCESS,
                f"Successfully copied {source_path} to {destination_path}",
            )

        except Exception as e:
            return TextToolResponse(
                ResponseStatus.ERROR, f"Copying file encountered an error: {e}"
            )

    def get_tool_spec(self) -> TextToolResponse:
        return {
            "toolSpec": {
                "name": self.name,
                "description": self.description,
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "source_path": {
                                "type": "string",
                                "description": "The path of the file to be copied",
                            },
                            "destination_path": {
                                "type": "string",
                                "description": "The path where the file should be copied to",
                            },
                        },
                        "required": ["source_path", "destination_path"],
                    }
                },
            }
        }


class CopyDirectoryTool(BaseFileTool):
    """Copies an entire directory and its content from one location to another"""

    name: str = "copy_directory"
    description: str = (
        "Use this tool to copy an entire directory from one location to another"
    )

    def invoke(self, *args, **kwargs) -> TextToolResponse:
        """Invokes the tool logic"""
        return self.copy_directory(*args, **kwargs)

    def copy_directory(
        self, source_path: str, destination_path: str
    ) -> TextToolResponse:
        """Copies the directory from the source to destination

        Args:
            source_path (str): The source directory path
            destination_path (str): The destination directory path

        Returns:
            TextToolResponse: The response from the tool containing the status of
                the copy operation
        """

        # Get absolute paths
        source_path = os.path.abspath(source_path)
        destination_path = os.path.abspath(destination_path)

        # Check path
        if self.base_dir:
            check_file_path_within_base(self.base_dir, source_path)
            check_file_path_within_base(self.base_dir, destination_path)

        try:
            shutil.copytree(source_path, destination_path)
            return TextToolResponse(
                ResponseStatus.SUCCESS,
                f"Successfully copied directory {source_path} to {destination_path}",
            )
        except Exception as e:
            return TextToolResponse(
                ResponseStatus.ERROR, f"Copying directory encountered an error: {e}"
            )

    def get_tool_spec(self) -> Dict:
        return {
            "toolSpec": {
                "name": self.name,
                "description": self.description,
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "source_path": {
                                "type": "string",
                                "description": "The path of the directory to be copied",
                            },
                            "destination_path": {
                                "type": "string",
                                "description": "The path where the directory should be copied to",
                            },
                        },
                        "required": ["source_path", "destination_path"],
                    }
                },
            }
        }


class EditTextFileTool(BaseTool):
    """Tool for efficiently editing text files by manipulating specific lines

    This tool provides functionality to:
    - Delete specific lines by line number
    - Insert new content at specific line numbers
    - Preserve proper spacing and line endings
    """

    name: str = "edit_text_file"
    description: str = "Use this tool to delete specific lines or insert content at particular line numbers"
    base_dir: str | None = Field(
        default=None, description="The base directory to limit the tool to"
    )

    def invoke(self, *args, **kwargs) -> TextToolResponse:
        """Invokes the tool logic"""
        return self.edit_file(*args, **kwargs)

    def edit_file(
        self,
        file_path: str,
        delete_lines: Optional[List[int]] = None,
        insertions: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> TextToolResponse:
        """Edits a text file by deleting and/or inserting lines with proper spacing control."""
        file_path = os.path.abspath(file_path)

        if self.base_dir and not os.path.abspath(file_path).startswith(
            os.path.abspath(self.base_dir)
        ):
            return TextToolResponse(
                ResponseStatus.ERROR,
                f"Permission Denied: Path {file_path} is not within base directory {self.base_dir}",
            )

        try:
            # Read existing content and detect line ending
            with open(file_path, "r", encoding="utf-8") as file:
                lines = file.readlines()
                default_line_ending = (
                    "\r\n" if lines and lines[0].endswith("\r\n") else "\n"
                )

            # Convert to 0-based indexing and sort
            delete_lines = sorted([i - 1 for i in (delete_lines or [])])

            # Process insertions with enhanced spacing control
            processed_insertions = {}
            if insertions:
                # Sort insertions by line number to process them in order
                sorted_insertions = sorted(
                    [(int(k) - 1, v) for k, v in insertions.items()], key=lambda x: x[0]
                )

                # Track how many lines have been deleted before each insertion point
                deletion_offset = 0
                next_delete_idx = 0

                for line_num, v in sorted_insertions:
                    # Calculate how many deletions occur before this insertion
                    while (
                        next_delete_idx < len(delete_lines)
                        and delete_lines[next_delete_idx] < line_num
                    ):
                        deletion_offset += 1
                        next_delete_idx += 1

                    # Adjust insertion point based on previous deletions
                    adjusted_line_num = line_num - deletion_offset

                    content = v.get("content", "")
                    indent = v.get("indent", 0)
                    preserve_spacing = v.get("preserve_spacing", False)
                    line_ending = v.get("line_ending", default_line_ending)

                    final_content = (
                        content if preserve_spacing else " " * indent + content.lstrip()
                    )
                    if not final_content.endswith(("\n", "\r\n")):
                        final_content += line_ending

                    processed_insertions[adjusted_line_num] = final_content

            # Create new content with proper ordering
            new_lines = []
            current_line = 0

            while current_line < len(lines):
                # Handle insertions that come before this line
                if current_line in processed_insertions:
                    new_lines.append(processed_insertions[current_line])

                # Include existing line if not marked for deletion
                if current_line not in delete_lines:
                    new_lines.append(lines[current_line])

                current_line += 1

            # Handle remaining insertions past end of file
            max_line = len(lines) - len(delete_lines)
            for line_num in sorted(k for k in processed_insertions if k >= max_line):
                new_lines.append(processed_insertions[line_num])

            # Write back to file
            with open(file_path, "w", encoding="utf-8") as file:
                file.writelines(new_lines)

            return TextToolResponse(
                ResponseStatus.SUCCESS, f"Successfully edited {file_path}"
            )

        except ValueError as ve:
            return TextToolResponse(
                ResponseStatus.ERROR, f"Error processing line numbers: {str(ve)}"
            )
        except Exception as e:
            return TextToolResponse(
                ResponseStatus.ERROR, f"Editing file encountered an error: {str(e)}"
            )

    def get_tool_spec(self) -> Dict:
        """Returns the tool specification for the EditTextFileTool"""
        return {
            "toolSpec": {
                "name": self.name,
                "description": self.description,
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "The path to the file to be edited",
                            },
                            "delete_lines": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "List of line numbers to delete (1-based indexing)",
                            },
                            "insertions": {
                                "type": "object",
                                "propertyNames": {
                                    "pattern": "^[0-9]+$",
                                    "description": "Line numbers (1-based indexing)",
                                },
                                "additionalProperties": {
                                    "type": "object",
                                    "properties": {
                                        "content": {
                                            "type": "string",
                                            "description": "Content to insert",
                                        },
                                        "indent": {
                                            "type": "integer",
                                            "description": "Number of spaces for indentation",
                                        },
                                        "preserve_spacing": {
                                            "type": "boolean",
                                            "description": "Whether to preserve exact spacing",
                                        },
                                        "line_ending": {
                                            "type": "string",
                                            "description": "Line ending to use",
                                        },
                                    },
                                    "required": ["content"],
                                },
                                "description": "Enhanced insertion configuration",
                            },
                        },
                        "required": ["file_path"],
                    }
                },
            }
        }


class GetDirectoryTreeTool(BaseFileTool):
    """Creates a tree view of a directory structure"""

    name: str = "get_directory_tree"
    description: str = "Use this tool to generate a tree view of a directory structure."

    def invoke(self, *args, **kwargs) -> TextToolResponse:
        """Invokes the tool logic"""
        return self.get_directory_tree(*args, **kwargs)

    def get_directory_tree(self, path: str, max_depth: int = -1) -> TextToolResponse:
        """Creates a tree view of the directory structure.

        Args:
            path (str): The root directory path to start from
            max_depth (int, optional): Maximum depth to traverse (-1 for unlimited).
                Defaults to 1.

        Returns:
            TextToolResponse: The response containing the tree structure
        """
        # Get absolute path
        path = os.path.abspath(path)

        # Check path
        if self.base_dir:
            check_file_path_within_base(self.base_dir, path)

        try:
            if not os.path.exists(path):
                return TextToolResponse(
                    ResponseStatus.ERROR, f"Error: Path not found at {path}"
                )

            def generate_tree(
                start_path: str, prefix: str = "", current_depth: int = 0
            ) -> List[str]:
                if max_depth != -1 and current_depth > max_depth:
                    return []

                tree_lines = []
                dir_contents = sorted(os.listdir(start_path))

                for i, item in enumerate(dir_contents):
                    item_path = os.path.join(start_path, item)
                    is_last = i == len(dir_contents) - 1

                    # Create the proper prefix for current item
                    current_prefix = "└── " if is_last else "├── "
                    tree_lines.append(prefix + current_prefix + item)

                    if os.path.isdir(item_path):
                        # Create the proper prefix for items inside this directory
                        next_prefix = prefix + ("    " if is_last else "│   ")
                        tree_lines.extend(
                            generate_tree(item_path, next_prefix, current_depth + 1)
                        )

                return tree_lines

            tree_content = [os.path.basename(path)]
            tree_content.extend(generate_tree(path))

            return TextToolResponse(ResponseStatus.SUCCESS, "\n".join(tree_content))

        except Exception as e:
            return TextToolResponse(
                ResponseStatus.ERROR,
                f"Creating directory tree encountered an error: {e}",
            )

    def get_tool_spec(self) -> Dict:
        return {
            "toolSpec": {
                "name": self.name,
                "description": self.description,
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "The root directory path to create tree from",
                            },
                            "max_depth": {
                                "type": "integer",
                                "description": "Maximum depth to traverse (default: 1)",
                                "default": 1,
                            },
                        },
                        "required": ["path"],
                    }
                },
            }
        }
