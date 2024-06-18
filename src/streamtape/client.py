from typing import Any, Dict, List, Optional
from datetime import datetime
import hashlib

import httpx

from .exceptions import StreamtapeError

class StreamtapeAPI:
    """
    Interacts with the Streamtape's API.
    """
    
    BASE_URL: str = "https://api.streamtape.com"
    TIMEOUT: int = 30
    DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"
    CHUNK_SIZE: int = 4096
    
    def __init__(
        self: "StreamTape",
        login: Optional[str] = None,
        key: Optional[str] = None,
        timeout: int = TIMEOUT,
        datetime_format: str = DATETIME_FORMAT,
        chunk_size: int = CHUNK_SIZE
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
            raise StreamtapeError(status, response_dict["msg"])
        
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
        
        Parameters:
            login (str, optional): API-login.
            key (str, optional): API-key.
        
        Raises:
            StreamtapeError: If anything is wrong with the request.
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
        result["api_id"] = result.pop("apiid")
        result["signup_at"] = self._str_to_datetime(result["signup_at"])
        
        return result
    
    async def get_download_ticket(self: "StreamTape", file: str, login: Optional[str] = None, key: Optional[str] = None) -> Dict[str, Any]:
        """
        Prepare a download ticket.
        
        Parameters:
            file (str): The File-ID of the file.
            login (str, optional): API login. Defaults to None.
            key (str, optional): API key. Defaults to None.
        
        Raises:
            StreamtapeError: If anything is wrong with the request.
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
        
        Parameters:
            file (str): The File-ID of the file.
            ticket (str): Previously generated download ticket.
        
        Raises:
            StreamtapeError: If anything is wrong with the request.
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
        
        Parameters:
            file (str): The File-ID of the file.
            login (str, optional): API login. Defaults to None.
            key (str, optional): API key. Defaults to None.
        
        Raises:
            StreamtapeError: If anything is wrong with the request.
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
        
        Parameters:
            file_path (str): The path of the file to upload.
            folder (str): The Folder-ID to upload to. Defaults to None.
            httponly (bool, optional): If true, use only HTTP upload link. Defaults to None.
            login (str, optional): API login. Defaults to None.
            key (str, optional): API key. Defaults to None.
        
        Raises:
            StreamtapeError: If anything is wrong with the request.
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
        
        Parameters:
            url (str): The remote url.
            folder (str): The Folder-ID to upload to. Defaults to None.
            headers (bool, optional): Additional headers for the HTTP request. Defaults to None.
            name (str, optional): Custom name for the file. Defaults to None.
            login (str, optional): API login. Defaults to None.
            key (str, optional): API key. Defaults to None.
        
        Raises:
            StreamtapeError: If anything is wrong with the request.
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
        
        Parameters:
            upload_id (str): The Remote Upload-ID to remove (use "all" to remove all remote uploads).
            login (str, optional): API login. Defaults to None.
            key (str, optional): API key. Defaults to None.
        
        Raises:
            StreamtapeError: If anything is wrong with the request.
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
        
        Parameters:
            upload_id (str): The Remote Upload-ID.
            login (str, optional): API login. Defaults to None.
            key (str, optional): API key. Defaults to None.
        
        Raises:
            StreamtapeError: If anything is wrong with the request.
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
    
    async def get_files_and_folders(self: "StreamTape", folder: Optional[str] = None, login: Optional[str] = None, key: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the content of your folders.
        
        Parameters:
            folder (str, optional): The Folder-ID. Defaults to None.
            login (str, optional): API login. Defaults to None.
            key (str, optional): API key. Defaults to None.
        
        Raises:
            StreamtapeError: If anything is wrong with the request.
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
        
        Parameters:
            name (str, optional): The name of the folder.
            parent_folder (str, optional): The Folder-ID of the parent folder. Defaults to None.
            login (str, optional): API login. Defaults to None.
            key (str, optional): API key. Defaults to None.
        
        Raises:
            StreamtapeError: If anything is wrong with the request.
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
        
        Parameters:
            folder (str): The Folder-ID of folder to rename.
            name (str): The new name for the folder.
            login (str, optional): API login. Defaults to None.
            key (str, optional): API key. Defaults to None.
        
        Raises:
            StreamtapeError: If anything is wrong with the request.
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
        
        Parameters:
            folder (str): The Folder-ID of folder to delete.
            login (str, optional): API login. Defaults to None.
            key (str, optional): API key. Defaults to None.
        
        Raises:
            StreamtapeError: If anything is wrong with the request.
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
        
        Parameters:
            file (str): The File-ID of file to rename.
            login (str, optional): API login. Defaults to None.
            key (str, optional): API key. Defaults to None.
        
        Raises:
            StreamtapeError: If anything is wrong with the request.
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
        
        Parameters:
            file (str): The File-ID of file to move to.
            folder (str): The Folder-ID of folder to move the file to.
            login (str, optional): API login. Defaults to None.
            key (str, optional): API key. Defaults to None.
        
        Raises:
            StreamtapeError: If anything is wrong with the request.
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
        
        Parameters:
            file (str): The File-ID of file to delete.
            login (str, optional): API login. Defaults to None.
            key (str, optional): API key. Defaults to None.
        
        Raises:
            StreamtapeError: If anything is wrong with the request.
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
        
        Parameters:
            login (str, optional): API login. Defaults to None.
            key (str, optional): API key. Defaults to None.
        
        Raises:
            StreamtapeError: If anything is wrong with the request.
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
        
        Parameters:
            login (str, optional): API login. Defaults to None.
            key (str, optional): API key. Defaults to None.
        
        Raises:
            StreamtapeError: If anything is wrong with the request.
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
        
        Parameters:
            file (str): The File-ID of file.
            login (str, optional): API login. Defaults to None.
            key (str, optional): API key. Defaults to None.
        
        Raises:
            StreamtapeError: If anything is wrong with the request.
        Returns:
            str: The URL of the thumbnail of the file.
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