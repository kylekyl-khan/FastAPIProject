# 安装自签名证书到受信任的根证书颁发机构存储
Write-Host "正在安装自签名证书到受信任的根证书颁发机构..."
try {
    # 导入CA证书到受信任的根证书颁发机构存储
    Import-Certificate -FilePath "ssl/ca.pem" -CertStoreLocation Cert:\LocalMachine\Root -ErrorAction Stop
    Write-Host "证书安装成功！" -ForegroundColor Green
    Write-Host "现在您可以重新尝试安装OWA插件。" -ForegroundColor Yellow
} catch {
    Write-Host "证书安装失败: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "请以管理员身份运行此脚本。" -ForegroundColor Yellow
}