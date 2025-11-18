"""啟動啟用 HTTPS 的 FastAPI 伺服器。

功能：
- 檢查專案根目錄是否有 server.pem / server.key
- 如果沒有，會用 trustme 自動產生一組自簽憑證
- 使用 uvicorn 以 HTTPS 方式監聽在 https://127.0.0.1:8443
"""

from pathlib import Path

import uvicorn
import trustme

from main import app


def ensure_certificates(base_dir: Path) -> tuple[Path, Path]:
    """
    確認憑證檔案存在，若不存在則自動產生：
    - ca.pem
    - server.pem
    - server.key
    """
    ca_path = base_dir / "ca.pem"
    cert_path = base_dir / "server.pem"
    key_path = base_dir / "server.key"

    if cert_path.exists() and key_path.exists():
        # 憑證已存在，直接使用
        return cert_path, key_path

    # 沒有就產生新的自簽憑證
    ca = trustme.CA()
    server_cert = ca.issue_cert("localhost", "127.0.0.1")

    ca.cert_pem.write_to_path(ca_path)
    server_cert.cert_chain_pems[0].write_to_path(cert_path)
    server_cert.private_key_pem.write_to_path(key_path)

    print("已自動產生 HTTPS 憑證：")
    print(f"  CA 憑證：{ca_path}")
    print(f"  伺服器憑證：{cert_path}")
    print(f"  私鑰：{key_path}")
    print("如需讓瀏覽器完全信任，請將 ca.pem 匯入系統的『受信任的根憑證授權單位』。")

    return cert_path, key_path


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    cert_path, key_path = ensure_certificates(base_dir)

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8443,
        ssl_certfile=str(cert_path),
        ssl_keyfile=str(key_path),
    )


if __name__ == "__main__":
    main()
