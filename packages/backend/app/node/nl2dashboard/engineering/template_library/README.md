# 模板库 (Template Library)

这个目录用于存储所有可用的 Dashboard 模板文件。

## 目录结构

```
template_library/
├── template_base.html          # 基础模板（默认）
├── template_with_table.html   # 表格模板（适用于多个highlight和大量图表）
└── ...                        # 其他自定义模板
```

## 模板映射配置

模板选择规则在 `template_mapping.json` 文件中配置。该文件定义了：

1. **模板库路径** (`template_library_path`): 模板文件存储的目录
2. **默认模板** (`default_template`): 当没有规则匹配时使用的模板
3. **选择规则** (`rules`): 根据配置中的 highlight 和 view 块数量选择模板的规则
4. **模板信息** (`templates`): 每个模板的元数据和路径信息

## 添加新模板

1. 将模板文件放入 `template_library/` 目录
2. 在 `template_mapping.json` 中添加模板信息：
   ```json
   "templates": {
     "your_template.html": {
       "display_name": "你的模板名称",
       "description": "模板描述",
       "source_path": "template_library/your_template.html"
     }
   }
   ```
3. 添加选择规则（可选）：
   ```json
   "rules": [
     {
       "name": "rule_name",
       "description": "规则描述",
       "conditions": {
         "highlight_count": {"min": 1},
         "view_count": {"min": 5}
       },
       "template": "your_template.html"
     }
   ]
   ```

## 模板选择流程

1. 读取配置文件，统计 highlight 和 view 块的数量
2. 按照 `rules` 中的顺序匹配规则
3. 如果匹配成功，使用对应的模板
4. 如果没有匹配，使用默认模板
5. 从模板库复制模板到 `va_app/public/templates/`
6. 进行变量替换（Dashboard名称、描述、图表标题等）
7. 保存为 `page_customized.html`

