# Template Library

This directory stores all available dashboard template files.

## Directory Structure

```
template_library/
├── template_base.html          # Base template (default)
├── template_with_table.html   # Table template (for multiple highlights and many charts)
└── ...                        # Other custom templates
```

## Template Mapping Configuration

Template selection rules are configured in the `template_mapping.json` file. This file defines:

1. **Template library path** (`template_library_path`): Directory where template files are stored
2. **Default template** (`default_template`): Template used when no rule matches
3. **Selection rules** (`rules`): Rules for selecting templates based on the number of `highlight` and `view` blocks in the configuration
4. **Template metadata** (`templates`): Metadata and path information for each template

## Adding a New Template

1. Put the template file into the `template_library/` directory.
2. Add template metadata in `template_mapping.json`:
   ```json
   "templates": {
     "your_template.html": {
       "display_name": "Your template name",
       "description": "Template description",
       "source_path": "template_library/your_template.html"
     }
   }
   ```
3. (Optional) Add selection rules:
   ```json
   "rules": [
     {
       "name": "rule_name",
       "description": "Rule description",
       "conditions": {
         "highlight_count": {"min": 1},
         "view_count": {"min": 5}
       },
       "template": "your_template.html"
     }
   ]
   ```

## Template Selection Flow

1. Read the configuration file and count the number of `highlight` and `view` blocks.
2. Match rules in the order listed in `rules`.
3. If a rule matches, use the corresponding template.
4. If no rule matches, use the default template.
5. Copy the chosen template from the template library to `va_app/public/templates/`.
6. Perform variable replacement (dashboard name, description, chart titles, etc.).
7. Save the result as `page_customized.html`.

