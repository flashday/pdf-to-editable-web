# 表格型字段提取功能设计

> 创建日期：2026-01-28
> 状态：待实现
> 优先级：中

---

## 一、需求背景

当前系统的单据类型字段配置只支持**简单键值对**形式（如 `合同编号: xxx`）。

但实际业务中，很多单据包含**表格型数据**，例如：
- 合同中的"付款计划表"
- 发票中的"商品明细表"
- 出差报告中的"费用明细表"

需要扩展系统支持表格型字段的配置、提取和显示。

---

## 二、场景举例

### 2.1 合同付款计划表

| 付款阶段 | 付款比例 | 付款金额 | 付款条件 |
|---------|---------|---------|---------|
| 首付款 | 30% | 30万 | 合同签订后7日内 |
| 进度款 | 50% | 50万 | 验收合格后 |
| 尾款 | 20% | 20万 | 质保期满后 |

### 2.2 发票商品明细表

| 序号 | 商品名称 | 规格型号 | 数量 | 单价 | 金额 |
|-----|---------|---------|-----|-----|-----|
| 1 | 办公电脑 | i7/16G/512G | 10 | 5000 | 50000 |
| 2 | 显示器 | 27寸 4K | 10 | 2000 | 20000 |

### 2.3 出差费用明细表

| 费用类型 | 金额 | 备注 |
|---------|-----|-----|
| 高铁票 | 500 | 北京-上海 |
| 出租车 | 200 | 机场接送 |
| 住宿费 | 800 | 2晚 |

---

## 三、设计方案

### 3.1 扩展字段配置结构

**当前结构：**
```json
{
  "id": "contract",
  "name": "合同",
  "fields": ["合同编号", "甲方", "乙方", "合同金额"]
}
```

**扩展后结构：**
```json
{
  "id": "contract",
  "name": "合同",
  "fields": [
    { "name": "合同编号", "type": "text" },
    { "name": "甲方", "type": "text" },
    { "name": "乙方", "type": "text" },
    { "name": "合同金额", "type": "number" },
    { "name": "签订日期", "type": "date" },
    {
      "name": "付款计划",
      "type": "table",
      "columns": ["付款阶段", "付款比例", "付款金额", "付款条件"]
    },
    {
      "name": "商品明细",
      "type": "table",
      "columns": ["序号", "商品名称", "规格", "数量", "单价", "金额"]
    }
  ]
}
```

**字段类型说明：**
| type | 说明 | 示例 |
|------|------|------|
| `text` | 普通文本（默认） | 合同编号、甲方名称 |
| `number` | 数字 | 金额、数量 |
| `date` | 日期 | 签订日期、生效日期 |
| `table` | 表格 | 付款计划、商品明细 |

### 3.2 后端 LLM 提取逻辑

对于 `type: "table"` 的字段，需要生成特殊的提取 prompt：

```python
def build_table_extraction_prompt(field_name, columns, text):
    return f"""
从以下文本中提取"{field_name}"表格数据。

表格列定义：{', '.join(columns)}

请以 JSON 数组格式返回，每行数据为一个对象。如果某列数据缺失，使用空字符串。

示例输出格式：
[
  {{"付款阶段": "首付款", "付款比例": "30%", "付款金额": "30万", "付款条件": "合同签订后7日内"}},
  {{"付款阶段": "进度款", "付款比例": "50%", "付款金额": "50万", "付款条件": "验收合格后"}}
]

文本内容：
{text}

请提取表格数据（仅返回 JSON 数组，不要其他内容）：
"""
```

### 3.3 前端显示调整

#### Step5 数据提取结果显示

```javascript
function renderExtractedData(fieldConfig, value) {
    if (fieldConfig.type === 'table') {
        // 渲染为 HTML 表格
        return renderTableField(fieldConfig.name, fieldConfig.columns, value);
    } else {
        // 渲染为键值对
        return `<div class="field-item">
            <span class="field-label">${fieldConfig.name}:</span>
            <span class="field-value">${value}</span>
        </div>`;
    }
}

function renderTableField(name, columns, rows) {
    if (!Array.isArray(rows) || rows.length === 0) {
        return `<div class="field-item">
            <span class="field-label">${name}:</span>
            <span class="field-value">(无数据)</span>
        </div>`;
    }
    
    let html = `<div class="table-field">
        <div class="table-field-label">${name}:</div>
        <table class="extracted-table">
            <thead><tr>`;
    
    columns.forEach(col => {
        html += `<th>${col}</th>`;
    });
    
    html += `</tr></thead><tbody>`;
    
    rows.forEach(row => {
        html += '<tr>';
        columns.forEach(col => {
            html += `<td>${row[col] || ''}</td>`;
        });
        html += '</tr>';
    });
    
    html += '</tbody></table></div>';
    return html;
}
```

#### Step6 财务确认显示

表格字段在 Step6 中应该：
1. 以表格形式显示
2. 支持单元格编辑
3. 支持添加/删除行

---

## 四、实现步骤

### 阶段1：配置结构扩展
- [ ] 修改 `config/document_types.json` 支持新的字段结构
- [ ] 后端 API 兼容新旧两种格式（向后兼容）
- [ ] 前端单据类型配置界面支持表格字段配置

### 阶段2：后端提取逻辑
- [ ] 修改 `backend/services/llm_service.py` 支持表格字段提取
- [ ] 为表格字段生成专用的 LLM prompt
- [ ] 解析 LLM 返回的 JSON 数组格式

### 阶段3：前端显示
- [ ] 修改 `Step5DataExtract.js` 支持表格字段渲染
- [ ] 修改 `Step6Confirmation.js` 支持表格字段显示和编辑
- [ ] 添加表格相关的 CSS 样式

### 阶段4：测试验证
- [ ] 测试合同付款计划表提取
- [ ] 测试发票商品明细表提取
- [ ] 测试表格编辑功能

---

## 五、相关文件

| 文件 | 说明 |
|------|------|
| `config/document_types.json` | 单据类型配置 |
| `backend/services/llm_service.py` | LLM 提取服务 |
| `backend/api/v3_routes.py` | API 路由 |
| `frontend/src/components/steps/Step5DataExtract.js` | 步骤5组件 |
| `frontend/src/components/steps/Step6Confirmation.js` | 步骤6组件 |
| `frontend/src/components/DocumentTypeConfig.js` | 单据类型配置界面 |

---

## 六、注意事项

1. **向后兼容**：新结构需要兼容旧的简单字符串数组格式
2. **LLM 输出稳定性**：表格提取的 JSON 格式需要做好错误处理
3. **性能考虑**：大表格可能需要分页显示
4. **编辑体验**：表格编辑需要考虑用户体验（添加行、删除行、Tab 切换等）
