import trustme
import os

# 创建证书颁发机构
ca = trustme.CA()

# 为localhost创建证书
server_cert = ca.issue_cert("localhost", "127.0.0.1", "::1")

# 保存证书和私钥
os.makedirs("ssl", exist_ok=True)

# 保存CA证书
ca.cert_pem.write_to_path("ssl/ca.pem")

# 保存服务器证书和私钥
server_cert.private_key_pem.write_to_path("ssl/key.pem")
server_cert.cert_chain_pems[0].write_to_path("ssl/cert.pem")

print("证书已生成:")
print("- CA证书: ssl/ca.pem")
print("- 服务器私钥: ssl/key.pem")
print("- 服务器证书: ssl/cert.pem")