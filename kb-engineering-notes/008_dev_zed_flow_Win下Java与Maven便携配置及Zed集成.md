---
name: kb-windows-java-maven-zed-setup
description: Windows 下 Java 21 与 Maven 零污染便携子目录配置、C 盘本地仓重定向防膨胀、Zed 编辑器动态 LSP 与 tasks.json JDWP 任务调试配置 SOP。
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

---

## 二、 底层根因剖析

1. **Maven 本地仓寻址机制与注释陷阱**：
   Maven 默认按 `${user.home}/.m2/repository` 解析本地仓库。在 `conf/settings.xml` 模板中，官方提供的 `<localRepository>` 样例默认包裹在 XML 块注释 `<!-- ... -->` 内部。如果误在注释内修改，或者在外部追加时被格式化工具覆盖，Maven 仍会静默回退到 C 盘。
2. **Amazon Corretto（AWS OpenJDK）的企业级定位与开源授权**：
   - **开源属性**：Amazon Corretto 是 100% 开源且完全免费商用的 OpenJDK 发行版，遵循 **GPLv2 with Classpath Exception (CPE)** 协议，源代码完全托管于 GitHub。
   - **企业级本质**：通过官方 Java SE TCK 兼容性认证，针对高吞吐生产云环境打了大量性能补丁，拥有 AWS 官方长期支持（LTS）。纯绿色 ZIP 解压即用，无商业授权条款（如 Oracle OTN 协议）暴雷风险。
3. **Zed 与 jdtls 的动态探测机制**：
   Eclipse JDT.LS（Java 语言服务器）具有原生的环境嗅探机制：当配置文件中省略显式的 `java_home` 与硬编码 `runtimes` 时，jdtls 会自动回退读取系统的 `JAVA_HOME` 环境变量及 `PATH`。过度在 IDE 项目级配置文件中硬编码绝对路径，反而破坏了项目的团队共享与跨机协同性。
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
        "lombok_support": true
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
   保存代码或配置脚本时，使用 `[System.IO.File]::WriteAllText($path, $content, [System.Text.UTF8Encoding]::new($false))`，绝不使用 `Out-File -Encoding utf8`。