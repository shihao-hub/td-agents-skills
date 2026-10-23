### 5. JDTLS 自动更新踩坑与本地回滚 SOP

若已被静默拉取了 1.63.0 等高版本，执行以下抢救与锁定：
1. **删除有毒的高版本目录**：
   删除 `%LOCALAPPDATA%\Zed\extensions\work\java\jdtls\1.63.0\`；
2. **重置检查记录**：
   将 `%LOCALAPPDATA%\Zed\extensions\work\java\jdtls\.update_checked` 中的版本修改回 `1.61.0`（或保留经实测兼容 Java 21 的本地最高版本）；
3. **配置锁死**：
   在 `.zed/settings.json` 及 `%APPDATA%\Zed\settings.json` 的 `lsp.jdtls.settings` 中配置 `"check_updates": "never"`。

---

---
name: kb-windows-java-maven-zed-setup
description: Windows 下 Java 21 与 Maven 零污染便携子目录配置、C 盘本地仓重定向防膨胀、Zed 编辑器动态 LSP 与 tasks.json JDWP 任务调试配置 SOP。
id: "008"
domain: dev
scope: zed
type: flow
slug: "Win下Java与Maven便携配置及Zed集成"
status: verified
created: "2026-09-22"
last_verified: "2026-10-24"
compatibility:
  os: ["windows"]
invocation:
  auto_trigger: true
### 5. JDTLS 自动更新踩坑与本地回滚 SOP

若已被静默拉取了 1.63.0 等高版本，执行以下抢救与锁定：
1. **删除有毒的高版本目录**：
   删除 `%LOCALAPPDATA%\Zed\extensions\work\java\jdtls\1.63.0\`；
2. **重置检查记录**：
   将 `%LOCALAPPDATA%\Zed\extensions\work\java\jdtls\.update_checked` 中的版本修改回 `1.61.0`（或保留经实测兼容 Java 21 的本地最高版本）；
3. **配置锁死**：
   在 `.zed/settings.json` 及 `%APPDATA%\Zed\settings.json` 的 `lsp.jdtls.settings` 中配置 `"check_updates": "never"`。

---

---

# Windows 下 Java 21 与 Maven 便携子目录配置及 Zed 任务调试集成指南

## 一、 现象与报错直击

1. **C 盘无感知持续膨胀与空间报警**：
   在 Windows 上使用官方 MSI/EXE 安装 JDK 或使用默认 Maven 编译大型 Spring Boot 项目数月后，C 盘空间骤降数十 GB。排查发现 `C:\Users\<Username>\.m2\repository` 堆积了大量 snapshot/release jar 包，且 Oracle 安装器在注册表和 `C:\Program Files\Java` 留存顽固残留。
2. **编辑器硬编码路径破坏可移植性**：
   在 `.zed/settings.json` 或 VS Code 中写死类似 `"java_home": "D:/Users/java/jdk-21"`，导致换一台开发机或变更安装目录后，编辑器 LSP (`jdtls`) 无法启动或报找不到指定运行时。
3. **轻量编辑器（如 Zed）调试 Java 体验缺失**：
   开发者希望在极速编辑器 Zed 中写 Java，但发现缺少类似 IDEA 的“一键图形断点调试”体系，不知道如何利用 tasks 与 JDWP 协议建立可控的开发-调试闭环。
4. **PowerShell 生成配置文件引入 UTF-8 BOM 乱码**：
   使用 PowerShell `Out-File` 保存 Java 源文件或 XML 配置时默认附加 `\xef\xbb\xbf` (BOM)，导致 `javac` 编译抛出：
   ```text
   [ERROR] 非法字符: '\ufeff'
   ```
5. **Zed 启动 jdtls 报 `Server reset the connection` 与 Exit code 13**：
   在 Zed 状态栏或语言服务器面板报 `Failed to run jdtls`，详细信息显示：
   ```text
   Error
   initializing server jdtls, id 4: Server reset the connection
   -- stderr --
   WARNING: Using incubator modules: jdk.incubator.vector
   ```

---

## 二、 底层根因剖析

1. **Maven 本地仓寻址机制与注释陷阱**：
   Maven 默认按 `${user.home}/.m2/repository` 解析本地仓库。在 `conf/settings.xml` 模板中，官方提供的 `<localRepository>` 样例默认包裹在 XML 块注释 `<!-- ... -->` 内部。如果误在注释内修改，或者在外部追加时被格式化工具覆盖，Maven 仍会静默回退到 C 盘。
2. **Amazon Corretto（AWS OpenJDK）的企业级定位与开源授权**：
   - **开源属性**：Amazon Corretto 是 100% 开源且完全免费商用的 OpenJDK 发行版，遵循 **GPLv2 with Classpath Exception (CPE)** 协议，源代码完全托管于 GitHub。
   - **企业级本质**：通过官方 Java SE TCK 兼容性认证，针对高吞吐生产云环境打了大量性能补丁，拥有 AWS 官方长期支持（LTS）。纯绿色 ZIP 解压即用，无商业授权条款（如 Oracle OTN 协议）暴雷风险。
3. **Zed 与 jdtls 的动态探测机制**：
   Eclipse JDT.LS（Java 语言服务器）具有原生的环境嗅探机制：当配置文件中省略显式的 `java_home` 与硬编码 `runtimes` 时，jdtls 会自动回退读取系统的 `JAVA_HOME` 环境变量及 `PATH`。过度在 IDE 项目级配置文件中硬编码绝对路径，反而破坏了项目的团队共享与跨机协同性。
5. **Zed Java 扩展自动拉取上游 JDTLS milestone 导致与 JDK 21 冲突**：
   Zed 的 Java 扩展（`zed-extensions/java`）默认开启 `check_updates: "always"`（每 24 小时向 Eclipse 官方 milestones 检查更新）。当上游发布高版本（如 1.63.0+）时，其 OSGi bundle（`org.eclipse.core.filesystem_1.12.0` 等）声明了 `Bundle-RequiredExecutionEnvironment: JavaSE-25`。若本地运行时为 Java 21 LTS，Equinox 运行时因缺少 JavaSE-25 能力而无法解析核心 bundle，抛出 `Unresolved requirement: Require-Capability: osgi.ee; filter:="(&(osgi.ee=JavaSE)(version=25))"` 并以 Exit Code 13 退出。前置代理 `java-lsp-proxy.exe` 捕获子进程退出，向 Zed 客户端上报 `Server reset the connection`。

4. **JDWP（Java Debug Wire Protocol）的底层通用性**：
   Java 自诞生起就将调试协议与具体 IDE 解耦。无论是 IDEA、VS Code 还是 Zed，底层均基于 JDWP。轻量编辑器只需通过 JVM 参数 `-agentlib:jdwp=...` 监听特定端口（如 5005），即可无缝支持本地或远程调试器挂载。

---

## 三、 标准解决与抢救 SOP

### 1. 便携式子目录环境装配（全量收敛至目标磁盘）

建议将 Java 基础软件统一收敛至非系统盘（如 `D:\Users\java\`）：
```text
D:\Users\java\
├── jdk-21/          # Amazon Corretto 21.x 解压目录
├── maven/           # Apache Maven 3.9.x 解压目录
└── maven-repo/      # 独立的本地私有依赖仓库
```

在 PowerShell 中执行以下免安装与配置脚本：

```powershell
# 1. 永久持久化写入用户环境变量（无需管理员权限）
[Environment]::SetEnvironmentVariable("JAVA_HOME", "D:\Users\java\jdk-21", "User")
[Environment]::SetEnvironmentVariable("MAVEN_HOME", "D:\Users\java\maven", "User")
[Environment]::SetEnvironmentVariable("M2_HOME", "D:\Users\java\maven", "User")

# 2. 安全追加 Path（自动去重）
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
$append = "D:\Users\java\jdk-21\bin;D:\Users\java\maven\bin"
if ($currentPath -notmatch [regex]::Escape("D:\Users\java\jdk-21\bin")) {
    $newPath = "$append;$currentPath"
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
}
```

### 2. Maven `settings.xml` 关键配置（防 C 盘膨胀 + 国内加速）

编辑 `D:\Users\java\maven\conf\settings.xml`，**务必确保 `<localRepository>` 在注释块外部**：

```xml
<settings xmlns="http://maven.apache.org/SETTINGS/1.2.0" ...>
  <!-- 显式绑定本地仓库至 D 盘 -->
  <localRepository>D:/Users/java/maven-repo</localRepository>

  <mirrors>
    <!-- 阿里云公共镜像，加速中央仓库下载 -->
    <mirror>
      <id>aliyunmaven</id>
      <mirrorOf>central</mirrorOf>
      <name>阿里云公共仓库</name>
      <url>https://maven.aliyun.com/repository/public</url>
    </mirror>
  </mirrors>
</settings>
```

### 3. Zed 编辑器无硬编码动态集成（`.zed/settings.json`）

在根工作区 `.zed/settings.json` 中配置，启用 `jdtls` 但**完全移除硬编码物理路径**，使其自动继承系统环境变量：

```json
{
  "languages": {
    "Java": {
      "enable_language_server": true,
      "language_servers": ["jdtls"],
      "formatter": "language_server"
    }
  },
  "lsp": {
    "jdtls": {
      "settings": {
        "lombok_support": true,
        "check_updates": "never"
      },
      "initialization_options": {
        "settings": {
          "java": {
            "errors": {
              "incompleteClasspath": {
                "severity": "warning"
              }
            }
          }
        }
      }
    }
  }
}
```

### 4. Zed 任务化启动与 JDWP 调试配置（`.zed/tasks.json`）

在 `.zed/tasks.json` 中定义标准命令，按 `Ctrl+Shift+T`（或 Command Palette）即可调出执行：

```json
[
  {
    "label": "Java: Run Spring Boot (career-starter-basics)",
    "command": "mvn spring-boot:run",
    "cwd": "$ZED_WORKTREE_ROOT/java_projects/career-starter-basics",
    "reveal": "always",
    "use_new_terminal": false
  },
  {
    "label": "Java: Debug Spring Boot (JDWP 5005)",
    "command": "mvn spring-boot:run -Dspring-boot.run.jvmArguments=\"-agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=*:5005\"",
    "cwd": "$ZED_WORKTREE_ROOT/java_projects/career-starter-basics",
    "reveal": "always",
    "use_new_terminal": false
  },
  {
    "label": "Java: Run Tests (Current Subproject)",
    "command": "mvn test",
    "cwd": "$ZED_DIRNAME",
    "reveal": "always",
    "use_new_terminal": false
  }
]
```

---

## 四、 验证与防复发建议

1. **精准验证仓库是否脱离 C 盘**：
   在任意子工程目录执行：
   ```powershell
   mvn help:evaluate -Dexpression=settings.localRepository -q -DforceStdout
   ```
   输出必须为 `D:\Users\java\maven-repo`（绝对不能显示 `C:\Users\...`）。
2. **清理已有 C 盘残留**：
   如果此前已经运行过构建，可将 `C:\Users\<Username>\.m2\repository` 内容移动至 `D:\Users\java\maven-repo` 后删除原目录。
3. **IDE 选型权衡原则**：
   - **轻量编写 / 日常快读 / 命令行自动化**：使用 **Zed + jdtls + tasks**，启动极快，内存占用低至百兆级。
   - **大型重构 / Spring 容器透视 / 复杂条件断点图形调试**：推荐配合 **IntelliJ IDEA** 打开同一工程目录（IDEA 直接识别标准 `pom.xml`，环境自动继承系统 `JAVA_HOME` 与 Maven 配置，互不干扰）。
4. **禁止 PowerShell 产生 UTF-8 BOM**：
   保存代码或配置脚本时，使用 `[System.IO.File]::WriteAllText($path, $content, [System.Text.UTF8Encoding]::new($false))`，绝不使用 `Out-File -Encoding utf8`。5. **锁定 LSP 自动更新（防静默破坏）**：
   轻量级 IDE 的扩展常常默认开启后台检查更新，针对 Java 这类与 JVM 运行时主版本强绑定的语言服务，一律配置 `"check_updates": "never"`，保持本地环境确定性。
