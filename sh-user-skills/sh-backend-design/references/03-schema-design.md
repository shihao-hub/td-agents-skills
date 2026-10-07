# 阶段⑤：表结构设计（物理 DDL）

> 主入口见 SKILL.md。输入是冻结的概念模型 + 阶段④的「数据需求清单」。表结构是概念模型的「存储投影」。

## 设计流程

```
概念模型 → 每实体一张表 + 关系落地（1:N加外键 / M:N建关联表）
        → 选类型、定约束（把规则清单翻译成约束）
        → 设计索引（对着接口的查询路径）
        → 反模式自查
```

## 一、命名规范

- 表名/字段名：小写+下划线；表用单数（团队统一即可）
- 主键统一 `id`；外键 `xxx_id`；布尔 `is_xxx`；时间 `xxx_at`；计数 `xxx_count`
- 索引：唯一 `uk_字段`、普通 `idx_字段`、复合 `idx_字段1_字段2`
- **避开保留字**：`order`→`order_info`、`desc`→`description`、`type`→`xxx_type`

## 二、字段类型速查（错一次痛一年）

| 业务 | 正确 | 绝对禁止/说明 |
|------|------|--------------|
| 主键/外键 | `BIGINT UNSIGNED` | 外键与主键同类型（JOIN 性能） |
| 状态 | `TINYINT UNSIGNED` + 注释 | 不用 ENUM（加值要改表） |
| 金额 | `DECIMAL(12,2)` 或整数存分 | **绝不用 FLOAT/DOUBLE**（浮点误差，财务对账灾难） |
| 手机号 | `VARCHAR(20)` | 不用数字类型（国际号码/前导零） |
| 时间 | `DATETIME` | 不用字符串存时间（无法排序/函数计算）；应用层统一 UTC |
| 短文本 | `VARCHAR(n)`，n 够用就好 | 不无脑 9999（影响性能） |
| 长文本 | `TEXT`/`MEDIUMTEXT` | 不能有默认值，少做索引 |
| 布尔 | `TINYINT(1)` | — |
| 动态扩展 | `JSON` | 只存「不查询」的属性，要查询的字段必须独立成列 |

## 三、约束设计（把规则清单翻译成约束）

**原则：能用数据库约束解决的，绝不靠应用代码。**

- 每条唯一性规则 → `UNIQUE KEY`（业务组合唯一用复合唯一，如 `(user_id, article_id)` 防重复点赞）
- 能 `NOT NULL` 就 `NOT NULL`（NULL 的比较/COUNT/索引都是坑），没有值用默认值代替
- 合理默认值：`status DEFAULT 0`、计数 `DEFAULT 0`、`created_at DEFAULT CURRENT_TIMESTAMP`
- 外键：互联网实践常不加物理外键（性能+分库+迁移成本），**但必须在注释里写明关联关系 + 应用层保证**，并定期做一致性巡检

**标准元字段（每张表）**：

```sql
`created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
`updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
```

## 四、主键策略

| 场景 | 选择 |
|------|------|
| 单库应用 | 自增 `BIGINT`（InnoDB 聚簇索引顺序写，快） |
| 分库分表 | 雪花 ID / UUID v7（全局唯一+趋势递增） |
| 对外暴露 | 不用连续自增（防枚举），订单号单独生成（日期+雪花+校验位） |

**不用业务字段做主键**（会变、会重复、可能过长）。

## 五、索引设计（对着接口的查询路径）

**索引不是事后装饰，阶段④的每个列表接口的「过滤+排序」条件就是索引清单。**

1. WHERE 等值字段 + JOIN 字段 + ORDER BY 字段建索引
2. 复合索引遵循**最左前缀**：等值列在前、区分度高的在前、范围/排序列在后
   - `GET /orders?user_id=&status=&sort=created_at` → `idx_user_status_created(user_id, status, created_at)`
3. 覆盖索引避免回表（响应字段都在索引里时极快，所以列表接口返回摘要字段还有性能红利）
4. 前缀索引用于长字符串：`KEY idx_url(url(20))`
5. 单表索引 ≤5 个（含主键）；写多读少的表更要克制
6. 避免索引失效：函数操作列、前导 `%` 通配、隐式类型转换

## 六、常见业务模式（按需套用）

### 快照（凭证类业务的铁律）
订单/合同/发票等**不可变历史事实**，引用的可变主数据的关键字段必须下单时冻结：
- 订单明细：`product_name_snapshot`、`price_snapshot`
- 订单主表：收货人/电话/地址快照（不能 JOIN 地址表——用户会改地址）
- 判断口诀：**「主数据改了，这条历史该不该变？不该变 → 存快照」**

### 事件与状态分离
- **状态表**（当前归属，如 `influencer_campaign`）vs **事件表**（append-only 留痕，如 `import_batch` + 明细）
- 状态变迁记日志：`order_status_log(order_id, from_status, to_status, operator)`

### 软删除
```sql
`is_deleted` TINYINT(1) NOT NULL DEFAULT 0,
`deleted_at` DATETIME NULL
```
核心业务表用软删（可恢复+审计）；软删与唯一约束冲突时用 `(field, is_deleted)` 复合唯一。用户要求删除（GDPR）→ 硬删。

### 树形结构
90% 用邻接表（`parent_id`，MySQL 8 用 CTE 递归）；层级深且频繁查子树 → 路径枚举/闭包表；静态树 → 嵌套集。

### 多租户（SaaS）
所有表带 `tenant_id`，所有索引以 `tenant_id` 为前导列。

### 用户私有 vs 全局共享（作用域落地）
- 全局：`entity_tag(entity_id, tag_id)`
- 私有：`entity_user_tag(entity_id, user_id, tag_id)`
- 混合场景（如「拉黑」共享、「特别关注」私有）拆两张表，语义清晰优先

## 七、反模式自查清单（写完 DDL 后过一遍）

- [ ] 金额没用浮点？手机号没用整数？
- [ ] 没有 ENUM 类型字段？
- [ ] 时间没用字符串存？
- [ ] 一个字段没塞多个值（"A,B,C"）？多值都拆表了？
- [ ] 没用保留字做表名/字段名？
- [ ] 每个表、每个字段都有 COMMENT？
- [ ] 该唯一的都有唯一约束？
- [ ] 字符集 utf8mb4？
- [ ] 快照场景冗余了快照字段？
- [ ] 每个列表接口的查询路径都有对应索引？
- [ ] 软删除和唯一约束不冲突？

## 八、标准建表模板

```sql
CREATE TABLE `order_info` (
  `id`             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '订单ID',
  `order_no`       VARCHAR(32) NOT NULL COMMENT '订单号',
  `user_id`        BIGINT UNSIGNED NOT NULL COMMENT '用户ID，关联 user.id',
  `status`         TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '状态 0待付款 1已付款 2已发货 3已完成 4已取消',
  `pay_amount`     DECIMAL(12,2) NOT NULL COMMENT '实付金额',
  `receiver_name`  VARCHAR(50) NOT NULL COMMENT '收货人（快照）',
  `created_at`     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_order_no` (`order_no`),
  KEY `idx_user_status_created` (`user_id`, `status`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='订单表';
```

## 九、与接口的迭代校验（铁律二后半环）

每张表写完，**回头扫一遍 API 契约**：
- 每个响应字段：表里有吗？来自哪列？（JOIN 还是快照？）
- 每个请求校验规则：约束能兜底吗？（如「一人一券」→ 唯一约束）
- 每个错误码：触发条件在表结构里成立吗？

发现接口要的字段表里没有 → 加字段或改接口；发现表里的约束接口没处理 → 补错误码。**④⑤来回两轮，设计基本收敛。**

## 阶段⑤产出

ER 关系图（文字版即可）+ 完整 DDL（含注释/约束/索引）+ 反模式自查记录。
