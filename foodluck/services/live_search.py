"""Asynchronous, fallback-capable client for real OpenStreetMap searches."""

from __future__ import annotations

import json
import urllib.parse
from typing import Optional

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from foodluck.data.nominatim import NominatimProvider
from foodluck.data.overpass import (
    MAX_RESPONSE_BYTES,
    USER_AGENT,
    OverpassProvider,
)
from foodluck.data.provider import RestaurantProviderError
from foodluck.models import RestaurantQuery


class LiveRestaurantSearch(QObject):
    """Search Overpass first, then automatically fall back to Nominatim.

    Both requests are asynchronous via QNetworkAccessManager. The GUI is never
    blocked, and the total wait is bounded to roughly 12 seconds.
    """

    started = Signal()
    succeeded = Signal(object)  # list[Restaurant]
    failed = Signal(str)

    OVERPASS_TIMEOUT_MS = 4000
    NOMINATIM_TIMEOUT_MS = 8000

    def __init__(
        self,
        provider: Optional[OverpassProvider] = None,
        nominatim_provider: Optional[NominatimProvider] = None,
        parent=None,
        timeout_ms: Optional[int] = None,
    ):
        super().__init__(parent)
        self.provider = provider or OverpassProvider()
        self.nominatim_provider = nominatim_provider or NominatimProvider()
        self._manager = QNetworkAccessManager(self)
        self._reply: Optional[QNetworkReply] = None
        self._query: Optional[RestaurantQuery] = None
        self._attempt: Optional[str] = None
        self._timed_out = False
        self._last_failure: Optional[str] = None
        self._overpass_timeout_ms = timeout_ms or self.OVERPASS_TIMEOUT_MS
        self._nominatim_timeout_ms = self.NOMINATIM_TIMEOUT_MS
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)

    @property
    def busy(self) -> bool:
        return self._reply is not None

    def start(self, query: RestaurantQuery) -> None:
        self.cancel()
        if query.latitude is None or query.longitude is None:
            self.failed.emit("真实搜索缺少地点坐标，请重新选择地点。")
            return
        self._query = query
        self._last_failure = None
        self.started.emit()
        self._start_overpass()

    def cancel(self) -> None:
        self._timer.stop()
        reply = self._reply
        self._reply = None
        self._query = None
        self._attempt = None
        self._timed_out = False
        if reply is not None:
            reply.abort()
            reply.deleteLater()

    # ------------------------------------------------------------------
    # Requests
    # ------------------------------------------------------------------
    def _start_overpass(self) -> None:
        query = self._query
        if query is None:
            return
        try:
            query_text = self.provider.build_query(query)
        except RestaurantProviderError as exc:
            self._start_nominatim(str(exc))
            return
        data = urllib.parse.urlencode({"data": query_text}).encode("utf-8")
        request = self._request(self.provider.endpoint)
        request.setHeader(
            QNetworkRequest.ContentTypeHeader,
            "application/x-www-form-urlencoded; charset=utf-8",
        )
        self._dispatch(request, "overpass", data, self._overpass_timeout_ms)

    def _start_nominatim(self, reason: str) -> None:
        self._last_failure = reason
        query = self._query
        if query is None:
            return
        try:
            url = self.nominatim_provider.build_url(query)
        except RestaurantProviderError as exc:
            self._finish_failure(str(exc))
            return
        request = self._request(url)
        self._dispatch(
            request, "nominatim", None, self._nominatim_timeout_ms
        )

    @staticmethod
    def _request(url: str) -> QNetworkRequest:
        request = QNetworkRequest(QUrl(url))
        request.setHeader(QNetworkRequest.UserAgentHeader, USER_AGENT)
        request.setRawHeader(b"Accept", b"application/json")
        return request

    def _dispatch(self, request, attempt: str, data, timeout_ms: int) -> None:
        self._attempt = attempt
        self._timed_out = False
        if data is None:
            reply = self._manager.get(request)
        else:
            reply = self._manager.post(request, data)
        self._reply = reply
        reply.finished.connect(lambda reply=reply: self._on_finished(reply))
        self._timer.start(timeout_ms)

    def _on_timeout(self) -> None:
        if self._reply is None:
            return
        self._timed_out = True
        self._reply.abort()

    # ------------------------------------------------------------------
    # Responses
    # ------------------------------------------------------------------
    def _on_finished(self, reply: QNetworkReply) -> None:
        if reply is not self._reply:
            return
        attempt = self._attempt or "overpass"
        self._reply = None
        self._timer.stop()
        query = self._query
        timed_out = self._timed_out

        try:
            if timed_out:
                seconds = (
                    self._overpass_timeout_ms
                    if attempt == "overpass"
                    else self._nominatim_timeout_ms
                ) // 1000
                self._attempt_failed(
                    attempt,
                    "真实搜索超时（{} 秒）。请检查网络或缩小搜索范围。".format(seconds),
                )
                return

            status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
            status_code = int(status) if status is not None else None
            if status_code is not None and status_code >= 500:
                self._attempt_failed(
                    attempt,
                    "OpenStreetMap 公共服务器繁忙（HTTP {}）。".format(status_code),
                )
                return
            if status_code == 429:
                self._attempt_failed(attempt, "OpenStreetMap 请求过于频繁，请稍等片刻。")
                return
            if reply.error() != QNetworkReply.NoError:
                message = reply.errorString()
                connection_errors = (
                    QNetworkReply.HostNotFoundError,
                    QNetworkReply.ConnectionRefusedError,
                )
                if hasattr(QNetworkReply, "NetworkSessionFailedError"):
                    connection_errors += (QNetworkReply.NetworkSessionFailedError,)
                if reply.error() in connection_errors:
                    message = "无法连接 OpenStreetMap，请检查网络连接。"
                self._attempt_failed(attempt, "真实搜索失败：{}".format(message))
                return
            if status_code is not None and status_code >= 400:
                self._attempt_failed(
                    attempt,
                    "OpenStreetMap 服务暂时不可用（HTTP {}）。".format(status_code),
                )
                return

            raw = bytes(reply.readAll())
            if len(raw) > MAX_RESPONSE_BYTES:
                self._attempt_failed(attempt, "返回数据过大，请缩小搜索范围。")
                return
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._attempt_failed(attempt, "返回了无法解析的数据。")
                return
            if query is None:
                return

            if attempt == "overpass":
                if (
                    isinstance(payload, dict)
                    and payload.get("remark")
                    and not payload.get("elements")
                ):
                    self._attempt_failed(attempt, "Overpass 服务繁忙。")
                    return
                results = self.provider.parse_payload(
                    payload,
                    origin_lat=query.latitude,
                    origin_lon=query.longitude,
                )
            else:
                results = self.nominatim_provider.parse_payload(
                    payload,
                    origin_lat=query.latitude,
                    origin_lon=query.longitude,
                    radius_km=query.radius_km,
                )
            self._query = None
            self._attempt = None
            self.succeeded.emit(results)
        except RestaurantProviderError as exc:
            self._attempt_failed(attempt, str(exc))
        except Exception:
            self._attempt_failed(attempt, "真实搜索失败，请稍后重试。")
        finally:
            reply.deleteLater()

    def _attempt_failed(self, attempt: str, message: str) -> None:
        if attempt == "overpass":
            self._start_nominatim(message)
        else:
            self._finish_failure(message)

    def _finish_failure(self, message: str) -> None:
        self._query = None
        self._attempt = None
        if self._last_failure and "Overpass" not in message:
            message = "{}（备用数据源 Nominatim 也未能完成查询）".format(message)
        self.failed.emit(message)
