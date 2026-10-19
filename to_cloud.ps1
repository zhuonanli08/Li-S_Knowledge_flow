# 不用打命令：双击同一文件夹里的「双击上云.bat」即可。
# 作用：把本机最新进度推到 GitHub，然后打开 claude.ai/code，任务文字已复制好。
param([string]$Task = "", [switch]$DryRun)

Set-Location $PSScriptRoot
$repo = ((git remote get-url origin) -replace '.*/', '') -replace '\.git$', ''
if (-not $Task) { $Task = "先读 CLAUDE.md 和 进度.md，接着做 进度.md 里写的下一步；遇到要我拍板的地方停下来问。" }

Write-Host "1/3 保存本机改动..."
git add -A
git commit -q -m ("本机进度快照 " + (Get-Date -Format 'yyyy-MM-dd HH:mm')) | Out-Null

Write-Host "2/3 上传到 GitHub..."
git push -q origin HEAD:main
if ($LASTEXITCODE -ne 0) {
    # GitHub 上有本机没有的新提交：本机进度另传一个分支，交给云端合并
    $snap = "local-" + (Get-Date -Format 'yyyyMMdd-HHmm')
    git push -q origin "HEAD:refs/heads/$snap"
    if ($LASTEXITCODE -ne 0) { Write-Host "上传失败：确认 Clash 开着、网络正常，再双击一次。" -ForegroundColor Red; exit 1 }
    $Task = "先把分支 $snap（本机最新进度）合并进 main 并推送，有冲突时两边内容都保留并告诉我。然后：" + $Task
}

Write-Host "3/3 打开云端..."
if ($DryRun) { Write-Host "（测试模式：不打开网页）任务：$Task"; exit 0 }
Set-Clipboard -Value $Task
Start-Process "https://claude.ai/code"
Write-Host ""
Write-Host "已上传。浏览器里的 claude.ai/code 接着这样做：" -ForegroundColor Green
Write-Host "  1. 仓库选 $repo"
Write-Host "  2. 点输入框，按 Ctrl+V（任务已复制好）"
Write-Host "  3. 发送"
Write-Host "之后在网页或手机 Claude App 的 Code 里看进度、回答它的问题。这个窗口可以关掉。"
