"""產生本機開發用的自簽憑證 (server.pem/server.key + ca.pem)。"""

import trustme

def main():
    # 建立一個假的 CA（信任來源）
    ca = trustme.CA()

    # 簽發給 localhost / 127.0.0.1 用的伺服器憑證
    server_cert = ca.issue_cert("localhost", "127.0.0.1")

    # 檔案名稱
    ca_cert_path = "ca.pem"
    cert_path = "server.pem"
    key_path = "server.key"

    # 寫出檔案
    ca.cert_pem.write_to_path(ca_cert_path)
    server_cert.cert_chain_pems[0].write_to_path(cert_path)
    server_cert.private_key_pem.write_to_path(key_path)

    print("已產生憑證檔案：")
    print(f"  CA 憑證：{ca_cert_path}")
    print(f"  伺服器憑證：{cert_path}")
    print(f"  私鑰：{key_path}")
    print("請將 ca.pem 匯入 Windows 信任的根憑證機構。")

if __name__ == "__main__":
    main()
