@echo off
chcp 65001 > nul
setlocal EnableDelayedExpansion
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
echo "[15] 删除分支"
echo "[16] 标签管理"
echo "[17] 储藏更改(Stash)"
echo "[18] 远程仓库管理"
echo "[19] 查看差异(Diff)"
echo "[20] 冲突解决助手"
echo "[21] 子模块管理"
echo "[22] Git配置管理"
echo "[23] Git钩子管理"
echo "[24] 仓库统计信息"
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
if "%choice%"=="15" goto deletebranch
if "%choice%"=="16" goto tag_management
if "%choice%"=="17" goto stash_management
if "%choice%"=="18" goto remote_management
if "%choice%"=="19" goto diff
if "%choice%"=="20" goto conflict_helper
if "%choice%"=="21" goto submodule_management
if "%choice%"=="22" goto git_config
if "%choice%"=="23" goto hooks_management
if "%choice%"=="24" goto repo_stats
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

:deletebranch
cls
echo 当前分支列表：
git branch
set /p branch="请输入要删除的分支名(当前分支无法删除): "
set /p confirm="确定要删除分支 %branch% 吗？(Y/N): "
if /i "%confirm%"=="Y" (
    git branch -d %branch%
    if errorlevel 1 (
        echo.
        echo 分支可能未完全合并，是否强制删除？(Y/N): 
        set /p force=""
        if /i "!force!"=="Y" (
            git branch -D %branch%
            echo 分支已强制删除
        ) else (
            echo 操作已取消
        )
    ) else (
        echo 分支已删除
    )
) else (
    echo 操作已取消
)
pause
goto menu

:tag_management
cls
echo ====================================
echo        标签管理
echo ====================================
echo.
echo "[1] 列出所有标签"
echo "[2] 创建新标签"
echo "[3] 删除标签"
echo "[4] 推送标签到远程"
echo "[0] 返回主菜单"
echo.
set /p tchoice="请选择操作: "

if "%tchoice%"=="1" goto list_tags
if "%tchoice%"=="2" goto create_tag
if "%tchoice%"=="3" goto delete_tag
if "%tchoice%"=="4" goto push_tag
if "%tchoice%"=="0" goto menu

:list_tags
cls
echo 所有标签：
git tag
pause
goto tag_management

:create_tag
cls
set /p tagname="请输入标签名(如v1.0.0): "
set /p tagmsg="请输入标签说明: "
git tag -a %tagname% -m "%tagmsg%"
echo 标签已创建
pause
goto tag_management

:delete_tag
cls
echo 当前标签列表：
git tag
set /p tagname="请输入要删除的标签名: "
git tag -d %tagname%
echo 标签已删除
pause
goto tag_management

:push_tag
cls
echo 当前标签列表：
git tag
set /p tagname="请输入要推送的标签名(输入all推送所有标签): "
if "%tagname%"=="all" (
    git push origin --tags
    echo 所有标签已推送到远程
) else (
    git push origin %tagname%
    echo 标签已推送到远程
)
pause
goto tag_management

:stash_management
cls
echo ====================================
echo        储藏管理(Stash)
echo ====================================
echo.
echo "[1] 查看所有储藏"
echo "[2] 创建新储藏"
echo "[3] 应用储藏"
echo "[4] 删除储藏"
echo "[0] 返回主菜单"
echo.
set /p schoice="请选择操作: "

if "%schoice%"=="1" goto list_stash
if "%schoice%"=="2" goto create_stash
if "%schoice%"=="3" goto apply_stash
if "%schoice%"=="4" goto delete_stash
if "%schoice%"=="0" goto menu

:list_stash
cls
echo 所有储藏：
git stash list
pause
goto stash_management

:create_stash
cls
set /p stashmsg="请输入储藏说明(直接回车使用默认): "
if "%stashmsg%"=="" (
    git stash
) else (
    git stash push -m "%stashmsg%"
)
echo 更改已储藏
pause
goto stash_management

:apply_stash
cls
echo 所有储藏：
git stash list
set /p stashindex="请输入要应用的储藏索引(如stash@{0}直接输入0): "
set /p keepstash="应用后保留储藏？(Y/N): "
if /i "%keepstash%"=="Y" (
    git stash apply stash@{%stashindex%}
    echo 储藏已应用(并保留)
) else (
    git stash pop stash@{%stashindex%}
    echo 储藏已应用并删除
)
pause
goto stash_management

:delete_stash
cls
echo 所有储藏：
git stash list
set /p stashindex="请输入要删除的储藏索引(如stash@{0}直接输入0,输入all删除所有): "
if "%stashindex%"=="all" (
    git stash clear
    echo 所有储藏已清除
) else (
    git stash drop stash@{%stashindex%}
    echo 储藏已删除
)
pause
goto stash_management

:remote_management
cls
echo ====================================
echo        远程仓库管理
echo ====================================
echo.
echo "[1] 查看远程仓库"
echo "[2] 添加远程仓库"
echo "[3] 删除远程仓库"
echo "[4] 修改远程仓库URL"
echo "[0] 返回主菜单"
echo.
set /p rchoice="请选择操作: "

if "%rchoice%"=="1" goto list_remote
if "%rchoice%"=="2" goto add_remote
if "%rchoice%"=="3" goto remove_remote
if "%rchoice%"=="4" goto change_remote_url
if "%rchoice%"=="0" goto menu

:list_remote
cls
echo 远程仓库信息：
git remote -v
pause
goto remote_management

:add_remote
cls
set /p remotename="请输入远程仓库名称(如origin): "
set /p remoteurl="请输入远程仓库URL: "
git remote add %remotename% %remoteurl%
echo 远程仓库已添加
pause
goto remote_management

:remove_remote
cls
echo 当前远程仓库：
git remote -v
set /p remotename="请输入要删除的远程仓库名称: "
git remote remove %remotename%
echo 远程仓库已删除
pause
goto remote_management

:change_remote_url
cls
echo 当前远程仓库：
git remote -v
set /p remotename="请输入要修改的远程仓库名称: "
set /p remoteurl="请输入新的远程仓库URL: "
git remote set-url %remotename% %remoteurl%
echo 远程仓库URL已修改
pause
goto remote_management

:diff
cls
echo ====================================
echo        查看差异(Diff)
echo ====================================
echo.
echo "[1] 查看工作区与暂存区的差异"
echo "[2] 查看暂存区与最近提交的差异"
echo "[3] 查看两个提交之间的差异"
echo "[4] 查看两个分支之间的差异"
echo "[0] 返回主菜单"
echo.
set /p dchoice="请选择操作: "

if "%dchoice%"=="1" goto diff_working_staged
if "%dchoice%"=="2" goto diff_staged_commit
if "%dchoice%"=="3" goto diff_commits
if "%dchoice%"=="4" goto diff_branches
if "%dchoice%"=="0" goto menu

:diff_working_staged
cls
git diff
pause
goto diff

:diff_staged_commit
cls
git diff --staged
pause
goto diff

:diff_commits
cls
echo 提交历史：
git log --oneline -n 10
echo.
set /p commit1="请输入较旧的提交ID: "
set /p commit2="请输入较新的提交ID(不填则与当前HEAD比较): "
if "%commit2%"=="" (
    git diff %commit1% HEAD
) else (
    git diff %commit1% %commit2%
)
pause
goto diff

:diff_branches
cls
echo 分支列表：
git branch
echo.
set /p branch1="请输入第一个分支名: "
set /p branch2="请输入第二个分支名: "
git diff %branch1% %branch2%
pause
goto diff

:conflict_helper
cls
echo ====================================
echo        冲突解决助手
echo ====================================
echo.
echo "[1] 列出有冲突的文件"
echo "[2] 使用mergetool解决冲突"
echo "[3] 标记冲突为已解决"
echo "[4] 中止合并操作"
echo "[5] 拉取远程时自动使用策略(rebase/merge)"
echo "[0] 返回主菜单"
echo.
set /p cchoice="请选择操作: "

if "%cchoice%"=="1" goto list_conflicts
if "%cchoice%"=="2" goto resolve_with_tool
if "%cchoice%"=="3" goto mark_resolved
if "%cchoice%"=="4" goto abort_merge
if "%cchoice%"=="5" goto pull_strategy
if "%cchoice%"=="0" goto menu

:list_conflicts
cls
echo 查找冲突文件...
git diff --name-only --diff-filter=U
echo.
echo 注意：如果没有显示文件，则当前没有冲突需要解决。
pause
goto conflict_helper

:resolve_with_tool
cls
set /p usevscode="是否使用VS Code作为合并工具？(Y/N): "
if /i "%usevscode%"=="Y" (
    git config --local merge.tool vscode
    git config --local mergetool.vscode.cmd "code --wait $MERGED"
    echo 已设置VS Code为合并工具
)
git mergetool
echo 合并工具已关闭，请检查冲突是否解决
pause
goto conflict_helper

:mark_resolved
cls
echo 当前冲突文件：
git diff --name-only --diff-filter=U
set /p file="请输入要标记为已解决的文件路径(输入all标记所有): "
if "%file%"=="all" (
    git add .
    echo 所有冲突已标记为解决
) else (
    git add %file%
    echo 文件 %file% 已标记为解决
)
pause
goto conflict_helper

:abort_merge
cls
set /p confirm="确定要中止当前的合并操作吗？(Y/N): "
if /i "%confirm%"=="Y" (
    git merge --abort
    echo 合并操作已中止
) else (
    echo 操作已取消
)
pause
goto conflict_helper

:pull_strategy
cls
echo ====================================
echo        拉取策略设置
echo ====================================
echo.
echo 当前拉取策略：
git config pull.rebase || echo "未设置(默认merge)"
echo.
echo "[1] 设置为rebase策略(推荐)"
echo "[2] 设置为merge策略"
echo "[3] 恢复默认"
echo "[0] 返回上级菜单"
echo.
set /p pschoice="请选择策略: "

if "%pschoice%"=="1" (
    git config pull.rebase true
    echo 已设置为rebase策略
) else if "%pschoice%"=="2" (
    git config pull.rebase false
    echo 已设置为merge策略
) else if "%pschoice%"=="3" (
    git config --unset pull.rebase
    echo 已恢复默认设置
)
pause
goto conflict_helper

:submodule_management
cls
echo ====================================
echo        子模块管理
echo ====================================
echo.
echo "[1] 列出子模块"
echo "[2] 添加子模块"
echo "[3] 更新所有子模块"
echo "[4] 删除子模块"
echo "[0] 返回主菜单"
echo.
set /p smchoice="请选择操作: "

if "%smchoice%"=="1" goto list_submodules
if "%smchoice%"=="2" goto add_submodule
if "%smchoice%"=="3" goto update_submodules
if "%smchoice%"=="4" goto remove_submodule
if "%smchoice%"=="0" goto menu

:list_submodules
cls
echo 当前子模块：
git submodule status
pause
goto submodule_management

:add_submodule
cls
set /p repo="请输入子模块仓库URL: "
set /p path="请输入子模块本地路径: "
git submodule add %repo% %path%
echo 子模块已添加
pause
goto submodule_management

:update_submodules
cls
set /p init="是否初始化新的子模块？(Y/N): "
if /i "%init%"=="Y" (
    git submodule update --init --recursive
    echo 已初始化并更新所有子模块
) else (
    git submodule update --recursive
    echo 已更新所有子模块
)
pause
goto submodule_management

:remove_submodule
cls
echo 当前子模块：
git submodule status
set /p submodule="请输入要删除的子模块路径: "
set /p confirm="确定要删除子模块 %submodule% 吗？(Y/N): "
if /i "%confirm%"=="Y" (
    git submodule deinit -f %submodule%
    git rm -f %submodule%
    echo 删除子模块配置...
    rmdir /s /q .git\modules\%submodule%
    echo 子模块已删除
) else (
    echo 操作已取消
)
pause
goto submodule_management

:git_config
cls
echo ====================================
echo        Git配置管理
echo ====================================
echo.
echo "[1] 查看所有配置"
echo "[2] 设置用户信息"
echo "[3] 配置别名(alias)"
echo "[4] 配置编辑器"
echo "[5] 配置自动换行(CRLF)"
echo "[0] 返回主菜单"
echo.
set /p gchoice="请选择操作: "

if "%gchoice%"=="1" goto list_config
if "%gchoice%"=="2" goto set_user
if "%gchoice%"=="3" goto set_alias
if "%gchoice%"=="4" goto set_editor
if "%gchoice%"=="5" goto set_crlf
if "%gchoice%"=="0" goto menu

:list_config
cls
echo 当前Git配置：
git config --list
pause
goto git_config

:set_user
cls
echo 当前用户信息：
git config user.name
git config user.email
echo.
set /p username="请输入用户名: "
set /p email="请输入邮箱: "
set /p scope="设置范围(global/local): "
git config --%scope% user.name "%username%"
git config --%scope% user.email "%email%"
echo 用户信息已设置
pause
goto git_config

:set_alias
cls
echo 当前别名配置：
git config --get-regexp alias
echo.
set /p alias="请输入别名(如st): "
set /p command="请输入对应的Git命令(如status): "
set /p scope="设置范围(global/local): "
git config --%scope% alias.%alias% %command%
echo 别名已设置
pause
goto git_config

:set_editor
cls
echo 当前编辑器：
git config core.editor
echo.
echo 常用编辑器选项:
echo [1] VS Code (code --wait)
echo [2] Notepad (notepad)
echo [3] Notepad++ (notepad++ -multiInst -notabbar -nosession)
echo [4] 自定义
echo.
set /p echoice="请选择编辑器: "
set scope=global
if "%echoice%"=="1" (
    git config --%scope% core.editor "code --wait"
) else if "%echoice%"=="2" (
    git config --%scope% core.editor "notepad"
) else if "%echoice%"=="3" (
    git config --%scope% core.editor "notepad++ -multiInst -notabbar -nosession"
) else if "%echoice%"=="4" (
    set /p editor="请输入编辑器命令: "
    git config --%scope% core.editor "%editor%"
)
echo 编辑器已设置
pause
goto git_config

:set_crlf
cls
echo 当前换行符配置：
git config core.autocrlf
echo.
echo 换行符处理选项:
echo [1] true (提交时转换为LF，检出时转换为CRLF，推荐Windows用户)
echo [2] input (提交时转换为LF，检出时不转换，推荐Linux/Mac用户)
echo [3] false (不自动转换，保持原样)
echo.
set /p crlf="请选择换行符处理方式: "
set scope=global
if "%crlf%"=="1" (
    git config --%scope% core.autocrlf true
    echo 已设置为true (Windows推荐)
) else if "%crlf%"=="2" (
    git config --%scope% core.autocrlf input
    echo 已设置为input (Linux/Mac推荐)
) else if "%crlf%"=="3" (
    git config --%scope% core.autocrlf false
    echo 已设置为false (不自动转换)
)
pause
goto git_config

:hooks_management
cls
echo ====================================
echo        Git钩子管理
echo ====================================
echo.
echo "[1] 查看可用钩子"
echo "[2] 编辑钩子脚本"
echo "[3] 启用/禁用钩子"
echo "[0] 返回主菜单"
echo.
set /p hchoice="请选择操作: "

if "%hchoice%"=="1" goto list_hooks
if "%hchoice%"=="2" goto edit_hook
if "%hchoice%"=="3" goto toggle_hook
if "%hchoice%"=="0" goto menu

:list_hooks
cls
echo Git钩子位置：.git/hooks/
echo.
echo 常用的Git钩子：
echo - pre-commit：提交前执行，常用于代码风格检查、单元测试等
echo - prepare-commit-msg：准备提交消息时执行
echo - commit-msg：提交消息验证
echo - post-commit：提交后执行，常用于通知或日志
echo - pre-push：推送前执行，常用于验证代码
echo - post-checkout：切换分支后执行
echo.
echo 当前启用的钩子：
dir .git\hooks /b | findstr /v "\.sample$"
pause
goto hooks_management

:edit_hook
cls
echo 可用钩子：
dir .git\hooks /b
echo.
set /p hookname="请输入要编辑的钩子名称(如pre-commit): "
if not exist ".git\hooks\%hookname%" (
    echo 创建新钩子文件...
    if "%hookname:~-3%" neq ".sh" (
        copy nul .git\hooks\%hookname%
    ) else (
        copy nul ".git\hooks\%hookname%"
    )
    echo @echo off > .git\hooks\%hookname%
    echo echo 执行钩子: %hookname% >> .git\hooks\%hookname%
    echo exit 0 >> .git\hooks\%hookname%
    attrib -r .git\hooks\%hookname%
)
notepad .git\hooks\%hookname%
pause
goto hooks_management

:toggle_hook
cls
echo 当前可用钩子：
dir .git\hooks /b
echo.
set /p hookname="请输入要启用/禁用的钩子名称: "
if exist ".git\hooks\%hookname%" (
    ren ".git\hooks\%hookname%" "%hookname%.disabled"
    echo 钩子已禁用
) else if exist ".git\hooks\%hookname%.disabled" (
    ren ".git\hooks\%hookname%.disabled" "%hookname%"
    echo 钩子已启用
) else if exist ".git\hooks\%hookname%.sample" (
    copy ".git\hooks\%hookname%.sample" ".git\hooks\%hookname%"
    echo 已从示例创建并启用钩子
) else (
    echo 找不到指定的钩子
)
pause
goto hooks_management

:repo_stats
cls
echo ====================================
echo        仓库统计信息
echo ====================================
echo.
echo "[1] 查看代码行数统计"
echo "[2] 查看提交者贡献统计"
echo "[3] 查看文件修改频率"
echo "[4] 查看分支图表"
echo "[0] 返回主菜单"
echo.
set /p rchoice="请选择操作: "

if "%rchoice%"=="1" goto code_stats
if "%rchoice%"=="2" goto author_stats
if "%rchoice%"=="3" goto file_stats
if "%rchoice%"=="4" goto branch_graph
if "%rchoice%"=="0" goto menu

:code_stats
cls
echo 代码行数统计（可能需要一些时间）...
git ls-files | findstr /v "\.png$ \.jpg$ \.gif$ \.ico$" | xargs wc -l 2>nul
if errorlevel 1 (
    echo 无法使用wc命令，尝试使用其他方式...
    echo 请安装Git Bash或WSL以获取更好的统计功能
)
pause
goto repo_stats

:author_stats
cls
echo 提交者贡献统计...
git shortlog -sn --all
echo.
echo 详细贡献统计...
git log --pretty=format:"%%an - %%ar : %%s" | head -n 20
pause
goto repo_stats

:file_stats
cls
echo 文件修改频率（最常修改的文件）...
git log --pretty=format: --name-only | sort | uniq -c | sort -rg | head -10
pause
goto repo_stats

:branch_graph
cls
echo 分支图表...
git log --graph --oneline --all --decorate -n 20
pause
goto repo_stats

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