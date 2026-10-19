# 本机额度用完时运行：把本机最新进度推到 GitHub，再开一个云端会话接着做。
# 用法：在本文件夹打开终端，运行
#   .\上云.ps1                    # 默认：接着做 进度.md 里写的下一步
#   .\上云.ps1 "具体任务说明"      # 指定任务
param([string]$Task = "")

Set-Location $PSScriptRoot
if (-not $Task) { $Task = "先读 CLAUDE.md 和 进度.md，接着做 进度.md 里写的下一步；遇到要我拍板的地方停下来问。" }

Write-Host "1/3 提交本机改动..."
git add -A
git commit -q -m ("本机进度快照 " + (Get-Date -Format 'yyyy-MM-dd HH:mm')) | Out-Null

Write-Host "2/3 推送到 GitHub..."
git push -q origin HEAD:main
if ($LASTEXITCODE -ne 0) {
    # GitHub 上有本机没有的新提交：本机进度另推一个分支，交给云端合并
    $snap = "local-" + (Get-Date -Format 'yyyyMMdd-HHmm')
    git push -q origin "HEAD:refs/heads/$snap"
    if ($LASTEXITCODE -ne 0) { Write-Host "推送失败：检查网络/代理后重试。" -ForegroundColor Red; exit 1 }
    $Task = "先把分支 $snap（本机最新进度）合并进 main 并推送，有冲突时两边内容都保留并告诉我。然后：" + $Task
    Write-Host "main 上有本机没有的提交，本机进度已推到分支 $snap，云端会先合并。" -ForegroundColor Yellow
}

Write-Host "3/3 开云端会话..."
Set-Clipboard -Value $Task
$cmd = Get-Command claude -ErrorAction SilentlyContinue
$exe = if ($cmd) { $cmd.Source } else {
    Get-ChildItem "$env:USERPROFILE\.vscode\extensions\anthropic.claude-code-*\resources\native-binary\claude.exe" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName
}
if ($exe) { & $exe --cloud $Task }
if (-not $exe -or $LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "命令行没开成。改用网页：打开 https://claude.ai/code ，选本仓库，粘贴任务（已复制到剪贴板）发送。" -ForegroundColor Yellow
    Start-Process "https://claude.ai/code"
}
