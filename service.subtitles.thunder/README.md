# Kodi 迅雷字幕（Thunder）

Kodi 中文字幕下载插件。播放影片时，合并视频 CID 匹配和名称搜索结果，下载后加载到播放器。

支持 UTF-8 编码转换、简繁转换和 ZIP 字幕包。

## 兼容性

- Kodi 19 及以上版本（Python 3）。
- 0.2.1 已在 Windows 版 Kodi 19 实测，字幕搜索、下载和加载正常。
- Android TV 尚未实测。

## 安装和使用

1. 下载插件安装包 `service.subtitles.thunder-0.3.1.zip`。
2. 在 Kodi 中打开 **设置 → 插件 → 从 ZIP 文件安装**，选择安装包。首次安装可能需要开启“未知来源”。
3. 播放影片，打开 **字幕 → 下载字幕 → Thunder**。
4. 选择字幕。ZIP 包含多个字幕时，可选择其中一个文件。

依赖 `script.module.requests` 和 `script.module.chardet`，由 Kodi 安装。

在插件设置中开启“文本字幕保存为 UTF-8”后，可选择简体或繁体转换。默认保留原编码。

## 使用说明

- 同时使用旧版 CID 接口和 HTTPS 名称接口，按下载地址合并去重。名称查询使用视频文件名及 Kodi 媒体标题；手动搜索可以输入英文片名和年份，例如 `Spider-Man.2.2004`。
- 支持本地文件和可读取、可定位的网络文件，如 SMB、NFS。无法计算 CID 时仍尝试名称搜索；单个接口失败时保留其他接口的结果。
- 查询仅发送 CID 和文件名或媒体标题，不发送本地目录、网络共享账号密码或视频内容。
- 列表中的文件匹配标记只表示候选在 CID 结果中出现，不代表时间轴已经验证。名称结果可能包含其他剪辑版，需要自行选择。
- 支持 SRT、ASS、SSA、SMI、VTT、SUB、TXT 及 ZIP 包。暂不支持 RAR、7z 和需要配套 IDX 文件的 VobSub 字幕。
- 下载及 ZIP 解压总大小上限为 20 MiB。
- 字幕库不一定包含当前视频版本的字幕。部分旧字幕名称已在源站损坏，列表会清理乱码并保留可读部分。
- 下载文件保存在 Kodi 插件数据目录 `addon_data/service.subtitles.thunder/`，停止播放后可手动清理。

## 更新记录

### 0.3.1

- 补齐 GPL v2 许可证、代码及素材来源说明。
- 更新插件元数据、依赖版本及原创图标和背景。
- 移除简繁转换库中未使用的旧命令行入口和 psyco 导入。

### 0.3.0

- 加入 HTTPS 名称搜索，与 CID 结果合并去重。
- 支持 Kodi 手动片名补搜；文件无法读取时仍可按名称查询。
- 单个接口故障时保留其他查询结果，名称候选不显示文件匹配标记。

### 0.2.1

- 修复字幕列表名称乱码，兼容旧中文编码、URL 转义名称和部分可恢复的乱码。

### 0.2.0

- 修复 Kodi 20 及以上版本的路径接口兼容问题。
- 修复含特殊字符的下载链接、字幕保存、UTF-8 编码及简繁转换。
- 增加网络超时、错误提示、ZIP 多字幕选择和下载大小限制。

## 开发

安装依赖并运行测试：

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

构建安装包：

```sh
python tools/build.py
```

安装包输出到 `dist/`，顶层目录为 `service.subtitles.thunder/`。GitHub Actions 在 Python 3.8、3.11、3.13 下运行测试并构建安装包。

## 官方仓库检查

```sh
python -m pip install kodi-addon-checker==0.0.36
python tools/build.py --stage build/official
python tools/check_official.py build/official/service.subtitles.thunder
```

每次检查使用新的暂存目录，避免混入旧文件。检查目标为 `matrix`，启用 PR 和依赖检查。
官方检查器 0.0.36 的仓库列表地址使用 HTTP，检查脚本改用 Kodi 官方镜像 `ftp.fau.de` 的 HTTPS 索引，未跳过检查项。
检查通过不等于官方收录；提交仍须由 Team Kodi 审核。0.3.1 尚未完成播放器实测。

图标与背景可用 `python tools/artwork.py` 重新生成，需要 Pillow 9.1 及以上版本。

## 来源与许可

许可证为 [GPL v2](LICENSE.txt)。代码来源、上游版本和素材说明见 [notice.txt](notice.txt)。
原插件结构参考 Shooter；简繁转换代码来自 skydark/nstools；CID 算法参考 weaming/thunder-subtitle。
图标与背景为本项目原创几何图形。插件与迅雷、Kodi 官方没有隶属关系。
