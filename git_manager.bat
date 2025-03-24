@echo off
chcp 65001 > nul
mode con cols=100 lines=30
title Git项目管理工具

:menu
cls
echo ====================================
echo        Git项目管理工具
echo ====================================
echo.
echo "[1] 初始化Git仓库 (git init)"
echo "[2] 查看当前状态 (git status)"
echo "[3] 添加所有更改 (git add .)"
echo "[4] 提交更改 (git commit)"
echo "[5] 推送到远程 (git push)"
echo "[6] 拉取更新 (git pull)"
echo "[7] 查看分支 (git branch)"
echo "[8] 切换分支"
echo "[9] 创建新分支"
echo "[10] 使用帮助"
echo "[11] 合并分支"
echo "[12] 查看提交历史"
echo "[13] 撤销未提交的更改"
echo "[14] 代码恢复选项"
echo "[0] 退出"
echo.
echo ====================================

set /p choice="请输入选项编号: "

if "%choice%"=="1" goto init
if "%choice%"=="2" goto status
if "%choice%"=="3" goto add
if "%choice%"=="4" goto commit
if "%choice%"=="5" goto push
if "%choice%"=="6" goto pull
if "%choice%"=="7" goto branch
if "%choice%"=="8" goto checkout
if "%choice%"=="9" goto newbranch
if "%choice%"=="10" goto help
if "%choice%"=="11" goto merge
if "%choice%"=="12" goto log
if "%choice%"=="13" goto reset
if "%choice%"=="14" goto recovery
if "%choice%"=="0" goto end

:init
cls
echo 正在初始化Git仓库...
git init
echo.
set /p remote="是否要添加远程仓库？(Y/N): "
if /i "%remote%"=="Y" (
    set /p url="请输入远程仓库URL: "
    git remote add origin %url%
    echo 已添加远程仓库
)
pause
goto menu

:status
cls
echo 当前Git状态：
git status
pause
goto menu

:add
cls
git add .
echo 已添加所有更改到暂存区
pause
goto menu

:commit
cls
set /p msg="请输入提交信息: "
git commit -m "%msg%"
pause
goto menu

:push
cls
git push
pause
goto menu

:pull
cls
git pull
pause
goto menu

:branch
cls
echo 当前分支列表：
git branch
pause
goto menu

:checkout
cls
echo 当前分支列表：
git branch
set /p branch="请输入要切换的分支名: "
git checkout %branch%
pause
goto menu

:newbranch
cls
set /p newbranch="请输入新分支名: "
git checkout -b %newbranch%
echo 已创建并切换到新分支: %newbranch%
pause
goto menu

:help
cls
echo ====================================
echo          Git管理工具使用帮助
echo ====================================
echo.
echo  日常开发流程：
echo  1. 查看当前状态
echo    - 用于查看哪些文件被修改了
echo    - 可以看到哪些文件还未提交
echo    - 建议每次操作前都先查看状态
echo.
echo  2. 添加所有更改
echo    - 当您完成一个功能或修复后使用
echo    - 会将所有修改的文件添加到暂存区
echo.
echo  3. 提交更改
echo    - 在添加文件后使用
echo    - 会要求您输入提交信息
echo    - 建议写清楚这次提交做了什么改动
echo.
echo  4. 推送到远程
echo    - 将您的提交推送到GitHub仓库
echo    - 建议经常推送，避免代码丢失
echo.
echo 分支管理：
echo  6. 查看分支
echo    - 显示所有本地分支
echo    - 当前分支会用 * 标记
echo.
echo  7. 切换分支
echo    - 在不同分支间切换
echo    - 切换前确保当前分支的修改已提交
echo.
echo  8. 创建新分支
echo    - 开发新功能时使用
echo    - 会创建并自动切换到新分支
echo.
echo  10. 合并分支
echo    - 将其他分支的改动合并到当前分支
echo.
echo 同步和撤销：
echo  5. 拉取更新
echo    - 从GitHub获取最新代码
echo    - 如果多人协作，建议经常拉取
echo.
echo  11. 查看提交历史
echo    - 查看最近的提交记录
echo    - 可以看到每次提交的内容
echo.
echo  12. 撤销未提交的更改
echo    - 放弃所有未提交的修改
echo    - 警告：请谨慎使用，无法恢复
echo.
echo 典型工作流程：
echo  1. 开始工作前：
echo     1 -^> 5（查看状态 -^> 拉取更新）
echo.
echo  2. 开发新功能：
echo     8 -^> 写代码 -^> 1 -^> 2 -^> 3 -^> 4
echo     (新建分支 -^> 开发 -^> 查看状态 -^> 添加 -^> 提交 -^> 推送)
echo.
echo  3. 完成功能合并：
echo     7 -^> 10 -^> 4
echo     (切换到主分支 -^> 合并功能分支 -^> 推送)
echo.
echo 使用建议：
echo  - 经常使用 [1] 查看状态，了解当前工作区情况
echo  - 每完成一个小功能就提交一次（[2] -^> [3]）
echo  - 定期推送到远程（[4]），避免代码丢失
echo  - 在进行重要操作前先备份或提交当前更改
echo.
pause
goto menu

:merge
cls
echo 当前分支列表：
git branch
set /p mergefrom="请输入要合并的源分支名: "
git merge %mergefrom%
pause
goto menu

:log
cls
git log --oneline --graph --decorate -n 10
pause
goto menu

:reset
cls
echo 警告：这将撤销所有未提交的更改！
set /p confirm="确定要继续吗？(Y/N): "
if /i "%confirm%"=="Y" (
    git reset --hard HEAD
    echo 已撤销所有未提交的更改
) else (
    echo 操作已取消
)
pause
goto menu

:recovery
cls
echo ====================================
echo        代码恢复选项
echo ====================================
echo.
echo "[1] 撤销工作区更改（未git add）"
echo "[2] 撤销暂存区更改（已git add）"
echo "[3] 撤销最近一次提交（已commit）"
echo "[4] 恢复到指定的历史版本"
echo "[5] 查看最近的提交记录"
echo "[0] 返回主菜单"
echo.
set /p rchoice="请选择恢复方式: "

if "%rchoice%"=="1" goto recovery_working
if "%rchoice%"=="2" goto recovery_staged
if "%rchoice%"=="3" goto recovery_commit
if "%rchoice%"=="4" goto recovery_version
if "%rchoice%"=="5" goto recovery_log
if "%rchoice%"=="0" goto menu

:recovery_working
cls
echo 警告：这将丢失所有未提交的修改！
set /p confirm="确定要继续吗？(Y/N): "
if /i "%confirm%"=="Y" (
    git checkout -- .
    echo 已撤销所有工作区的修改
) else (
    echo 操作已取消
)
pause
goto recovery

:recovery_staged
cls
echo 警告：这将撤销暂存区的修改（已git add的文件）！
set /p confirm="确定要继续吗？(Y/N): "
if /i "%confirm%"=="Y" (
    git reset HEAD .
    echo 已撤销暂存区的修改（文件仍保留在工作区）
) else (
    echo 操作已取消
)
pause
goto recovery

:recovery_commit
cls
echo 警告：这将撤销最近一次提交！
set /p confirm="确定要继续吗？(Y/N): "
if /i "%confirm%"=="Y" (
    git reset --soft HEAD^
    echo 已撤销最近一次提交（改动保留在暂存区）
) else (
    echo 操作已取消
)
pause
goto recovery

:recovery_version
cls
echo 当前提交历史：
git log --oneline -n 10
echo.
set /p commit="请输入要恢复到的提交ID（输入q返回）: "
if "%commit%"=="q" goto recovery
git reset --hard %commit%
echo 已恢复到指定版本
pause
goto recovery

:recovery_log
cls
git log --oneline --graph --decorate -n 10
pause
goto recovery

:end
cls
echo ====================================
echo          确认退出
echo ====================================
echo.
set /p confirm="确定要退出吗？(Y/N): "
if /i "%confirm%"=="Y" (
    cls
    echo ====================================
    echo    感谢使用Git项目管理工具
    echo ====================================
    ping -n 2 127.0.0.1 > nul
    exit
) else (
    goto menu
) 