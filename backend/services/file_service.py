"""File management service"""
import os
from pathlib import Path

class FileService:
    @staticmethod
    def list_files(path: str = "/"):
        """List files in directory"""
        try:
            files = []
            for item in Path(path).iterdir():
                files.append({
                    "name": item.name,
                    "path": str(item),
                    "is_dir": item.is_dir(),
                    "size": item.stat().st_size if item.is_file() else 0
                })
            return files
        except PermissionError:
            return []
    
    @staticmethod
    def search_files(pattern: str, path: str = "/"):
        """Search files by pattern"""
        files = []
        try:
            for root, dirs, filenames in os.walk(path):
                for filename in filenames:
                    if pattern.lower() in filename.lower():
                        files.append(os.path.join(root, filename))
                        if len(files) >= 100:
                            return files
        except PermissionError:
            pass
        return files

file_service = FileService()
