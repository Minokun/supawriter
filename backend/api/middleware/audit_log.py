"""Audit log middleware for API endpoints."""
from typing import Optional, List, Dict, Any, Callable, Awaitable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import json
import logging
from backend.api.services.audit import AuditService

logger = logging.getLogger(__name__)


class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    Audit log middleware for FastAPI.

    Logs all API calls and user actions for security, compliance,
    and debugging purposes. Captures request details, response status,
    and optional headers/body information.
    """

    # Default sensitive fields that should be redacted
    DEFAULT_SENSITIVE_FIELDS = [
        "password", "passwd", "secret", "token", "api_key", "apikey",
        "authorization", "session", "cookie", "credit_card", "ssn"
    ]

    # Default excluded paths (health checks, metrics, etc.)
    DEFAULT_EXCLUDE_PATHS = ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]

    def __init__(
        self,
        app: ASGIApp,
        audit_service: Optional[AuditService] = None,
        audit_service_factory: Optional[Callable[[], Awaitable[AuditService]]] = None,
        exclude_paths: Optional[List[str]] = None,
        log_headers: bool = False,
        log_body: bool = False,
        log_request_body: Optional[bool] = None,
        log_response_body: Optional[bool] = None,
        max_body_size: int = 10000,
        sensitive_fields: Optional[List[str]] = None,
        log_ip_address: bool = True
    ):
        """
        Initialize audit log middleware.

        Args:
            app: ASGI application
            audit_service: Audit service instance (for static usage)
            audit_service_factory: Async factory to create AuditService per request
            exclude_paths: Paths to exclude from logging
            log_headers: Whether to log request headers
            log_body: Whether to log request body
            log_request_body: Alias for log_body (from settings)
            log_response_body: Whether to log response body (reserved)
            max_body_size: Maximum body size to log (in bytes)
            sensitive_fields: List of sensitive field names to redact
            log_ip_address: Whether to log IP addresses
        """
        super().__init__(app)
        self.audit_service = audit_service
        self.audit_service_factory = audit_service_factory
        if audit_service is None and audit_service_factory is None:
            logger.warning("AuditLogMiddleware: no audit_service or factory provided, logging disabled")
        self.exclude_paths = set(exclude_paths or self.DEFAULT_EXCLUDE_PATHS)
        self.log_headers = log_headers
        self.log_body = log_body if log_request_body is None else log_request_body
        self.log_response_body = log_response_body or False
        self.max_body_size = max_body_size
        self.sensitive_fields = set(sensitive_fields or self.DEFAULT_SENSITIVE_FIELDS)
        self.log_ip_address = log_ip_address

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request through audit log middleware.

        Args:
            request: Incoming request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response
        """
        # Skip excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # No audit service configured
        if self.audit_service is None and self.audit_service_factory is None:
            return await call_next(request)

        # If we have a static audit_service, use it directly
        if self.audit_service is not None:
            return await self._dispatch_with_service(request, call_next, self.audit_service)

        # Use factory as async context manager to keep session alive during dispatch
        try:
            async with self.audit_service_factory() as audit_service:
                return await self._dispatch_with_service(request, call_next, audit_service)
        except Exception as e:
            logger.error(f"Failed to create audit service: {e}")
            return await call_next(request)

    async def _dispatch_with_service(self, request: Request, call_next, audit_service: AuditService) -> Response:
        """Dispatch request with a given audit service instance."""
        # Get user_id from request state (may be None for anonymous requests)
        user_id = getattr(request.state, 'user_id', None)

        # Get IP address
        ip_address = None
        if self.log_ip_address and request.client:
            ip_address = request.client.host

        # Get request headers if logging is enabled
        request_headers = None
        if self.log_headers:
            request_headers = self._sanitize_headers(dict(request.headers))

        # Get request body if logging is enabled
        request_body = None
        if self.log_body:
            request_body = await self._get_request_body(request)

        # Get custom action from request state (set by endpoints)
        custom_action = getattr(request.state, 'audit_action', None)
        resource_id = getattr(request.state, 'audit_resource_id', None)

        # Filter out Mock objects (from testing) or None values
        # Mock objects have a _mock_name attribute
        if custom_action is not None and hasattr(custom_action, '_mock_name'):
            custom_action = None
        if resource_id is not None and hasattr(resource_id, '_mock_name'):
            resource_id = None

        # Process the request
        response = await call_next(request)

        # Determine action (use custom action if provided, otherwise HTTP method)
        action = custom_action if custom_action else request.method

        # Determine resource (use resource_id if provided, otherwise path)
        resource = resource_id if resource_id else request.url.path

        # Create metadata dict for additional info
        metadata = self._build_metadata(request, response)

        # Log the request/response (never let audit failure crash the request)
        try:
            await audit_service.log_action(
                user_id=user_id,
                action=action,
                resource=resource,
                status_code=response.status_code,
                ip_address=ip_address,
                request_headers=request_headers,
                request_body=request_body,
                metadata=metadata
            )
        except Exception as e:
            logger.error(f"Audit logging failed for {request.method} {request.url.path}: {e}")

        return response

    async def _get_request_body(self, request: Request) -> Optional[str]:
        """
        Get request body, respecting size limits and filtering sensitive data.

        Args:
            request: Incoming request

        Returns:
            Request body as string, or None if too large or not available
        """
        try:
            # Try to get body from state (might be set by other middleware)
            if hasattr(request.state, 'raw_body'):
                body = request.state.raw_body
                if isinstance(body, bytes):
                    body = body.decode('utf-8', errors='ignore')
                return self._sanitize_body(body)

            # For streaming requests, we can't easily get the body
            # without consuming it, so we skip it
            return None
        except Exception:
            # If reading body fails, return None rather than breaking
            return None

    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """
        Sanitize headers by redacting sensitive values.

        Args:
            headers: Raw headers dictionary

        Returns:
            Sanitized headers dictionary
        """
        sanitized = {}
        for key, value in headers.items():
            key_lower = key.lower()
            # Check if this is a sensitive header
            if any(field in key_lower for field in self.sensitive_fields):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        return sanitized

    def _sanitize_body(self, body: str) -> Optional[str]:
        """
        Sanitize body by redacting sensitive field values.

        Args:
            body: Request body as string

        Returns:
            Sanitized body string, or None if too large
        """
        if not body:
            return None

        # Truncate if too large
        if len(body) > self.max_body_size:
            body = body[:self.max_body_size] + "... [TRUNCATED]"

        # Try to parse as JSON and sanitize sensitive fields
        try:
            data = json.loads(body)
            return self._sanitize_json(data)
        except (json.JSONDecodeError, TypeError):
            # Not JSON, return as-is (but truncated)
            return body

    def _sanitize_json(self, data: Any, parent_key: str = "") -> Any:
        """
        Recursively sanitize JSON data by redacting sensitive fields.

        Args:
            data: JSON data (dict, list, or primitive)
            parent_key: Parent key for nested structures

        Returns:
            Sanitized JSON data
        """
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                key_lower = key.lower()
                # Check if this is a sensitive field
                if any(field in key_lower for field in self.sensitive_fields):
                    sanitized[key] = "[REDACTED]"
                elif isinstance(value, (dict, list)):
                    sanitized[key] = self._sanitize_json(value, key)
                else:
                    sanitized[key] = value
            return sanitized
        elif isinstance(data, list):
            return [self._sanitize_json(item, parent_key) for item in data]
        else:
            return data

    def _build_metadata(self, request: Request, response: Response) -> Dict[str, Any]:
        """
        Build metadata dictionary with additional request/response info.

        Args:
            request: Incoming request
            response: HTTP response

        Returns:
            Metadata dictionary
        """
        metadata = {}

        # Safely convert query_params and path_params to dict
        try:
            metadata["query_params"] = dict(request.query_params)
        except (TypeError, AttributeError):
            metadata["query_params"] = {}

        try:
            metadata["path_params"] = dict(request.path_params)
        except (TypeError, AttributeError):
            metadata["path_params"] = {}

        # Add user agent if available
        if "user-agent" in request.headers:
            metadata["user_agent"] = request.headers["user-agent"]

        # Add request ID if available
        if "x-request-id" in request.headers:
            metadata["request_id"] = request.headers["x-request-id"]

        # Add content type
        if "content-type" in request.headers:
            metadata["content_type"] = request.headers["content-type"]

        return metadata

    async def get_user_audit_logs(
        self,
        user_id: int,
        limit: int = 100
    ) -> List:
        """
        Get audit logs for a specific user.

        Args:
            user_id: User ID
            limit: Maximum number of logs to return

        Returns:
            List of audit log entries
        """
        return await self.audit_service.get_user_logs(user_id, limit)

    async def get_resource_audit_logs(
        self,
        resource: str,
        limit: int = 100
    ) -> List:
        """
        Get audit logs for a specific resource.

        Args:
            resource: Resource path or ID
            limit: Maximum number of logs to return

        Returns:
            List of audit log entries
        """
        return await self.audit_service.get_resource_logs(resource, limit)
