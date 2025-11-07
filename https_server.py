import uvicorn
import ssl
from main import app

if __name__ == "__main__":
    # 配置SSL上下文
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain('ssl/cert.pem', 'ssl/key.pem')
    
    # 启动HTTPS服务器
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8443,
        ssl_keyfile="ssl/key.pem",
        ssl_certfile="ssl/cert.pem"
    )