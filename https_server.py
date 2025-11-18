from __future__ import annotations

"""啟動本地 HTTPS 反向代理，方便 Outlook Add-in 指向安全端點。"""

import ssl

import uvicorn

from main import app


def run_https_server() -> None:
    """使用既有憑證啟動 uvicorn HTTPS 服務。"""

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8443,
        ssl_certfile="ssl/cert.pem",
        ssl_keyfile="ssl/key.pem",
        timeout_keep_alive=30,
    )


if __name__ == "__main__":
    run_https_server()
