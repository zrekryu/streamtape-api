from typing import Any, Dict, List, Optional
from datetime import datetime
import hashlib

import httpx

from .exceptions import StreamTapeError

class StreamTape:
    """
    API Class.
    """
    
    BASE_URL: str = "https://api.streamtape.com"
    
    def __init__(
        self: "StreamTape",
        login: Optional[str] = None,
        key: Optional[str] = None,
        timeout: Optional[int] = 30,
        datetime_format: Optional[str] = "%Y-%m-%d %H:%M:%S",
        chunk_size: Optional[int] = 4096
        ) -> None:
        self.base_url = self.BASE_URL
        
        self.login = login
        self.key = key
        self.timeout = timeout
        self.datetime_format = datetime_format
        self.chunk_size = chunk_size
        
        self._client: AsyncClient = httpx.AsyncClient(timeout=self.timeout)
    
    async def _request(
        self: "StreamTape",
        method: str,
        base_url: Optional[str] = None,
        endpoint: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None
        ) -> Dict[str, Any]:
        url = base_url if base_url else self.base_url
        if endpoint:
            url += endpoint
        
        response: httpx.Response = await self._client.request(
            method=method,
            url=url,
            params=params,
            files=files
            )
        response.raise_for_status()
        
        response_dict: Dict[str, Any] = response.json()
        status: int = response_dict["status"]
        if not 200 <= status < 300:
            raise StreamTapeError(status, response_dict["msg"])
        
        return response_dict["result"]
    
    def _str_to_datetime(self: "StreamTape", datetime_string: str) -> datetime:
        return datetime.strptime(datetime_string, self.datetime_format)
    
    def _calculate_sha256(self: "StreamTape", file_path: str) -> str:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(self.chunk_size)
                if not chunk:
                    break
                
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
    async def get_account_info(self: "StreamTape", login: Optional[str] = None, key: Optional[str] = None) -> Dict[str, Any]:
        """
        Get information about the account (total used storage, reward, etc.)
        
        Raises:
            StreamTapeError: If anything is wrong with the request.
        Returns:
            Dict[str, Any]: result of the request.
        """
        method: str = "GET"
        endpoint: str = "/account/info"
        params: Dict[str, Any] = {
            "login": login or self.login,
            "key": key or self.key
        }
        
        result: Dict[str, Any] = await self._request(method, endpoint=endpoint, params=params)
        result["apiid"] = result.pop("apiid")
        result["signup_at"] = self._str_to_datetime(result["signup_at"])
        
        return result
    
    async def get_download_ticket(self: "StreamTape", file: str, login: Optional[str] = None, key: Optional[str] = None) -> Dict[str, Any]:
        """
        Prepare a download ticket.
        
        Raises:
            StreamTapeError: If anything is wrong with the request.
        Returns:
            Dict[str, Any]: result of the request.
        """
        method: str = "GET"
        endpoint: str = "/file/dlticket"
        params: Dict[str, Any] = {
            "login": login or self.login,
            "key": key or self.key,
            "file": file
        }
        
        result: Dict[str, Any] = await self._request(method, endpoint=endpoint, params=params)
        return result
    
    async def get_download_link(self: "StreamTape", file: str, ticket: str) -> Dict[str, Any]:
        """
        Get a download link by using download ticket.
        
        Raises:
            StreamTapeError: If anything is wrong with the request.
        Returns:
            Dict[str, Any]: result of the request.
        """
        method: str = "GET"
        endpoint: str = "/file/dl"
        params: Dict[str, Any] = {
            "file": file,
            "ticket": ticket
        }
        
        result: Dict[str, Any] = await self._request(method, endpoint=endpoint, params=params)
        return result
    
    async def get_file_info(self: "StreamTape", file: List[str], login: Optional[str] = None, key: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the status of a file, e.g. if the file exists.
        
        Raises:
            StreamTapeError: If anything is wrong with the request.
        Returns:
            Dict[str, Any]: result of the request.
        """
        method: str = "GET"
        endpoint: str = "/file/info"
        params: Dict[str, Any] = {
            "login": login or self.login,
            "key": key or self.key,
            "file": ",".join(file)
        }
        
        result: Dict[str, Any] = await self._request(method, endpoint=endpoint, params=params)
        return result
    
    async def upload_file(
        self: "StreamTape",
        file_path: str,
        folder: Optional[str] = None,
        httponly: Optional[bool] = None,
        login: Optional[str] = None,
        key: Optional[str] = None
        ) -> Dict[str, Any]:
        """
        Upload a file.
        
        Raises:
            StreamTapeError: If anything is wrong with the request.
        Returns:
            Dict[str, Any]: result of the request.
        """
        endpoint: str = "/file/ul"
        params: Dict[str, Any] = {
            "login": login or self.login,
            "key": key or self.key,
            "folder": folder,
            "sha256": self._calculate_sha256(file_path),
            "httponly": httponly
        }
        
        result: Dict[str, Any] = await self._request("GET", endpoint=endpoint, params=params)
        return await self._request("POST", base_url=result["url"], files={"file1": open(file_path, "rb")})
    
    async def remote_upload(
        self: "StreamTape",
        url: str,
        folder: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
        login: Optional[str] = None,
        key: Optional[str] = None
        ) -> Dict[str, Any]:
        """
        Remote Upload a file.
        
        Raises:
            StreamTapeError: If anything is wrong with the request.
        Returns:
            Dict[str, Any]: result of the request.
        """
        method: str = "GET"
        endpoint: str = "/remotedl"
        params: Dict[str, Any] = {
            "login": login or self.login,
            "key": key or self.key,
            "url": url,
            "folder": folder,
            "headers": headers,
            "name": name
        }
        
        result: Dict[str, Any] = await self._request(method, endpoint=endpoint, params=params)
        return result
    
    async def remove_remote_upload(self: "StreamTape", upload_id: str, login: Optional[str] = None, key: Optional[str] = None) -> bool:
        """
        Removing/Cancelling a remote upload.
        
        Raises:
            StreamTapeError: If anything is wrong with the request.
        Returns:
            Dict[str, Any]: result of the request.
        """
        method: str = "GET"
        endpoint: str = "/file/info"
        params: Dict[str, Any] = {
            "login": login or self.login,
            "key": key or self.key,
            "id": upload_id
        }
        
        result: bool = await self._request(method, endpoint=endpoint, params=params)
        return result
    
    async def get_remote_upload_status(self: "StreamTape", upload_id: str, login: Optional[str] = None, key: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the status of a Remote Upload.
        
        Raises:
            StreamTapeError: If anything is wrong with the request.
        Returns:
            Dict[str, Any]: result of the request.
        """
        method: str = "GET"
        endpoint: str = "/remotedl/status"
        params: Dict[str, Any] = {
            "login": login or self.login,
            "key": key or self.key,
            "id": upload_id
        }
        
        result: Dict[str, Any] = await self._request(method, endpoint=endpoint, params=params)
        result["added"] = self._str_to_datetime(result["added"])
        result["last_update"] = self._str_to_datetime(result["last_update"])
        return result
    
    async def get_files_and_folders(self: "StreamTape", folder: Optional[str], login: Optional[str] = None, key: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the content of your folders.
        
        Raises:
            StreamTapeError: If anything is wrong with the request.
        Returns:
            Dict[str, Any]: result of the request.
        """
        method: str = "GET"
        endpoint: str = "/file/listfolder"
        params: Dict[str, Any] = {
            "login": login or self.login,
            "key": key or self.key,
            "folder": folder
        }
        
        result: Dict[str, Any] = await self._request(method, endpoint=endpoint, params=params)
        return result
    
    async def create_folder(self: "StreamTape", name: str, parent_folder: Optional[str] = None, login: Optional[str] = None, key: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new folder.
        
        Raises:
            StreamTapeError: If anything is wrong with the request.
        Returns:
            Dict[str, Any]: result of the request.
        """
        method: str = "GET"
        endpoint: str = "/file/createfolder"
        params: Dict[str, Any] = {
            "login": login or self.login,
            "key": key or self.key,
            "name": name,
            "pid": parent_folder
        }
        
        result: Dict[str, Any] = await self._request(method, endpoint=endpoint, params=params)
        return result
    
    async def rename_folder(self: "StreamTape", folder: str, name: str, login: Optional[str] = None, key: Optional[str] = None) -> bool:
        """
        Rename a folder.
        
        Raises:
            StreamTapeError: If anything is wrong with the request.
        Returns:
            bool: True if the folder was successfully renamed, False otherwise.
        """
        method: str = "GET"
        endpoint: str = "/file/renamefolder"
        params: Dict[str, Any] = {
            "login": login or self.login,
            "key": key or self.key,
            "folder": folder,
            "name": name
        }
        
        result: bool = await self._request(method, endpoint=endpoint, params=params)
        return result
    
    async def delete_folder(self: "StreamTape", folder: str, login: Optional[str] = None, key: Optional[str] = None) -> bool:
        """
        Delete a folder along with all its subfolders and files.
        
        Raises:
            StreamTapeError: If anything is wrong with the request.
        Results:
            bool: True if the folder was successfully renamed, False otherwise.
        """
        method: str = "GET"
        endpoint: str = "/file/deletefolder"
        params: Dict[str, Any] = {
            "login": login or self.login,
            "key": key or self.key,
            "folder": folder
        }
        
        result: bool = await self._request(method, endpoint=endpoint, params=params)
        return result
    
    async def rename_file(self: "StreamTape", file: str, name: str, login: Optional[str] = None, key: Optional[str] = None) -> bool:
        """
        Rename a file.
        
        Raises:
            StreamTapeError: If anything is wrong with the request.
        Returns:
            bool: True if the folder was successfully renamed, False otherwise.
        """
        method: str = "GET"
        endpoint: str = "/file/rename"
        params: Dict[str, Any] = {
            "login": login or self.login,
            "key": key or self.key,
            "file": file,
            "name": name
        }
        
        result: bool = await self._request(method, endpoint=endpoint, params=params)
        return result
    
    async def move_file(self: "StreamTape", file: str, folder: str, login: Optional[str] = None, key: Optional[str] = None) -> bool:
        """
        Move a file.
        
        Raises:
            StreamTapeError: If anything is wrong with the request.
        Returns:
            bool: True if the folder was successfully renamed, False otherwise.
        """
        method: str = "GET"
        endpoint: str = "/file/move"
        params: Dict[str, Any] = {
            "login": login or self.login,
            "key": key or self.key,
            "file": file,
            "folder": folder
        }
        
        result: bool = await self._request(method, endpoint=endpoint, params=params)
        return result
    
    async def delete_file(self: "StreamTape", file: str, login: Optional[str] = None, key: Optional[str] = None) -> bool:
        """
        Delete a file.
        
        Raises:
            StreamTapeError: If anything is wrong with the request.
        Returns:
            bool: True if the folder was successfully renamed, False otherwise.
        """
        method: str = "GET"
        endpoint: str = "/file/delete"
        params: Dict[str, Any] = {
            "login": login or self.login,
            "key": key or self.key,
            "file": file
        }
        
        result: bool = await self._request(method, endpoint=endpoint, params=params)
        return result
    
    async def get_running_converts(self: "StreamTape", login: Optional[str] = None, key: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the list of all running conversions with their details.
        
        Raises:
            StreamTapeError: If anything is wrong with the request.
        Returns:
            Dict[str, Any]: result of the request.
        """
        method: str = "GET"
        endpoint: str = "/file/runningconverts"
        params: Dict[str, Any] = {
            "login": login or self.login,
            "key": key or self.key,
        }
        
        result: Dict[str, Any] = await self._request(method, endpoint=endpoint, params=params)
        return result
    
    async def get_failed_converts(self: "StreamTape", login: Optional[str] = None, key: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a list of all failed conversions.
        
        Raises:
            StreamTapeError: If anything is wrong with the request.
        Returns:
            Dict[str, Any]: result of the request.
        """
        method: str = "GET"
        endpoint: str = "/file/failedconverts"
        params: Dict[str, Any] = {
            "login": login or self.login,
            "key": key or self.key,
        }
        
        result: Dict[str, Any] = await self._request(method, endpoint=endpoint, params=params)
        return result
    
    async def get_thumbnail_image(self: "StreamTape", file: str, login: Optional[str] = None, key: Optional[str] = None) -> str:
        """
        Get the thumbnail of a file.
        
        Raises:
            StreamTapeError: If anything is wrong with the request.
        Returns:
            Dict[str, Any]: result of the request.
        """
        method: str = "GET"
        endpoint: str = "/file/getsplash"
        params: Dict[str, Any] = {
            "login": login or self.login,
            "key": key or self.key,
            "file": file
        }
        
        result: str = await self._request(method, endpoint=endpoint, params=params)
        return result