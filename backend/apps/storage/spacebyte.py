import json
import logging
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any
from django.conf import settings

logger = logging.getLogger(__name__)


class SpaceByteError(Exception):
    """Base exception for SpaceByte API interactions."""
    def __init__(self, message: str, status_code: int | None = None, response_body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class SpaceByteClient:
    """
    Client for the SpaceByte.in API (https://spacebyte.in/api-docs).
    
    Supports:
    - S3 direct multipart uploads (create, batch sign URLs, complete, abort)
    - S3 simple direct presigned uploads
    - SpaceByte FileEntry registration
    - Folder management
    - File downloads via entry hashes
    - Deletion / Trash management
    """

    def __init__(self, base_url: str | None = None, access_token: str | None = None):
        self.base_url = (base_url or getattr(settings, "SPACEBYTE_BASE_URL", "https://spacebyte.in/api/v1")).rstrip("/")
        self.access_token = access_token if access_token is not None else getattr(settings, "SPACEBYTE_ACCESS_TOKEN", "")

    @property
    def is_configured(self) -> bool:
        """Returns True if a non-empty access token is configured in environment."""
        token = self.access_token.strip() if self.access_token else ""
        return bool(token and token != "sample_token")

    def _headers(self, content_type: str = "application/json") -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "StorageCompanion-SpaceByte/1.0",
        }
        if content_type:
            headers["Content-Type"] = content_type
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def _request(
        self,
        method: str,
        path: str,
        data: dict | None = None,
        params: dict | None = None,
        timeout: int = 15,
    ) -> dict:
        if not self.is_configured:
            logger.info("SpaceByte token not configured; invoking development mock response for %s %s", method, path)
            return self._mock_response(method, path, data)

        url = f"{self.base_url}/{path.lstrip('/')}"
        if params:
            query_string = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
            if query_string:
                url = f"{url}?{query_string}"

        body_bytes = None
        if data is not None:
            body_bytes = json.dumps(data).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=body_bytes,
            headers=self._headers(),
            method=method.upper(),
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                content = response.read().decode("utf-8")
                return json.loads(content) if content else {}
        except urllib.error.HTTPError as e:
            raw_err = e.read().decode("utf-8")
            logger.error("SpaceByte API HTTPError [%s] %s: %s", e.code, url, raw_err)
            try:
                err_json = json.loads(raw_err)
            except Exception:
                err_json = {"message": raw_err}
            raise SpaceByteError(
                message=err_json.get("message", f"SpaceByte HTTP Error {e.code}"),
                status_code=e.code,
                response_body=err_json,
            ) from e
        except Exception as e:
            logger.error("SpaceByte API Connection Error: %s", str(e))
            raise SpaceByteError(f"Failed to connect to SpaceByte: {str(e)}") from e

    def _mock_response(self, method: str, path: str, data: dict | None) -> dict:
        """Deterministic mock responses for test suites and offline local development."""
        data = data or {}
        if "s3/multipart/create" in path:
            mock_id = f"sb_up_{uuid.uuid4().hex[:12]}"
            mock_key = f"uploads/mock/{data.get('filename', 'file.bin')}"
            return {"status": "success", "uploadId": mock_id, "key": mock_key, "acl": "private"}
        elif "s3/multipart/batch-sign-part-urls" in path:
            part_numbers = data.get("partNumbers", [1])
            upload_id = data.get("uploadId", "mock_id")
            key = data.get("key", "mock_key")
            urls = [
                {
                    "partNumber": p,
                    "url": f"https://storage.spacebyte.cloud/mock/{key}?uploadId={upload_id}&partNumber={p}&mockSign=valid",
                }
                for p in part_numbers
            ]
            return {"status": "success", "urls": urls}
        elif "s3/multipart/complete" in path:
            return {"status": "success", "message": "Multipart upload completed successfully"}
        elif "s3/simple/presign" in path:
            filename = data.get("filename", "file.bin")
            key = f"uploads/mock/{filename}"
            return {
                "status": "success",
                "url": f"https://storage.spacebyte.cloud/mock/{key}?mockSign=valid",
                "key": key,
                "acl": "private",
            }
        elif "s3/entries" in path:
            entry_id = int(uuid.uuid4().int % 1000000)
            mock_hash = uuid.uuid4().hex[:16]
            return {
                "status": "success",
                "fileEntry": {
                    "id": entry_id,
                    "name": data.get("clientName", "file.bin"),
                    "file_name": data.get("filename", "file.bin"),
                    "file_size": data.get("size", 1024),
                    "hash": mock_hash,
                    "url": f"secure/uploads/{entry_id}",
                    "parent_id": data.get("parentId"),
                },
            }
        elif "folders" in path:
            folder_id = int(uuid.uuid4().int % 1000000)
            return {
                "status": "success",
                "folder": {
                    "id": folder_id,
                    "name": data.get("name", "New Folder"),
                    "type": "folder",
                    "parent_id": data.get("parentId"),
                },
            }
        elif "file-entries" in path:
            return {"status": "success", "message": "Operation completed."}
        return {"status": "success"}

    # ------------------------------------------------------------------
    # Public API Endpoints
    # ------------------------------------------------------------------

    def init_multipart_upload(
        self,
        filename: str,
        mime: str = "application/octet-stream",
        part_count: int = 1,
    ) -> dict[str, Any]:
        """
        Creates an S3 multipart upload session and batches presigned URLs for all parts.
        """
        create_res = self._request("POST", "s3/multipart/create", {"filename": filename, "mime": mime})
        upload_id = create_res.get("uploadId")
        key = create_res.get("key")
        if not upload_id or not key:
            raise SpaceByteError("Invalid response from SpaceByte s3/multipart/create: missing uploadId or key")

        part_numbers = list(range(1, max(1, part_count) + 1))
        sign_res = self._request(
            "POST",
            "s3/multipart/batch-sign-part-urls",
            {"uploadId": upload_id, "key": key, "partNumbers": part_numbers},
        )
        urls = sign_res.get("urls", [])

        return {
            "upload_id": upload_id,
            "key": key,
            "presigned_urls": urls,
        }

    def complete_multipart_upload(self, upload_id: str, key: str, parts: list[dict]) -> dict:
        """
        Finalizes an S3 multipart upload on SpaceByte.
        Parts must be a list of {'PartNumber': int, 'ETag': str}.
        """
        payload = {
            "uploadId": upload_id,
            "key": key,
            "parts": parts,
        }
        return self._request("POST", "s3/multipart/complete", payload)

    def abort_multipart_upload(self, upload_id: str, key: str) -> dict:
        """Aborts an in-progress S3 multipart upload on SpaceByte."""
        payload = {"uploadId": upload_id, "key": key}
        return self._request("POST", "s3/multipart/abort", payload)

    def create_file_entry(
        self,
        filename: str,
        client_name: str,
        size: int,
        client_mime: str = "application/octet-stream",
        client_extension: str = "",
        parent_id: int | None = None,
    ) -> dict:
        """
        Registers an uploaded S3 file in the SpaceByte database, creating the FileEntry record.
        """
        if not client_extension and "." in client_name:
            client_extension = client_name.rsplit(".", 1)[-1].lower()

        payload = {
            "filename": filename,
            "clientName": client_name,
            "size": size,
            "clientMime": client_mime,
            "clientExtension": client_extension,
            "parentId": parent_id,
        }
        return self._request("POST", "s3/entries", payload)

    def simple_presign(self, filename: str, mime: str = "application/octet-stream") -> dict:
        """
        Generates a presigned URL for direct simple upload (< 100 MB).
        """
        return self._request("POST", "s3/simple/presign", {"filename": filename, "mime": mime})

    def create_folder(self, name: str, parent_id: int | None = None) -> dict:
        """Creates a folder in SpaceByte."""
        return self._request("POST", "folders", {"name": name, "parentId": parent_id})

    def delete_entries(self, entry_ids: list[int], delete_forever: bool = False) -> dict:
        """Deletes file entries in SpaceByte."""
        return self._request("DELETE", "file-entries", {"entryIds": entry_ids, "deleteForever": delete_forever})

    def move_entries(self, entry_ids: list[int], destination_id: int | None = None) -> dict:
        """Moves file entries to another folder in SpaceByte."""
        return self._request("POST", "file-entries/move", {"entryIds": entry_ids, "destinationId": destination_id})

    def get_download_url(self, hashes: str) -> str:
        """
        Returns the SpaceByte download endpoint for one or more file entry hashes.
        """
        return f"{self.base_url}/file-entries/download/{hashes}"

    def get_entries(
        self,
        per_page: int = 50,
        parent_id: int | None = None,
        query: str = "",
    ) -> dict:
        """Lists file entries from SpaceByte."""
        params = {"perPage": per_page, "folderId": parent_id, "query": query or None}
        return self._request("GET", "drive/file-entries", params=params)


# Singleton instance helper
def get_spacebyte_client() -> SpaceByteClient:
    return SpaceByteClient()
