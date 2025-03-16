{% macro generate_alias_name(custom_alias_name=none, node=none) -%}
    {% set prefixes = ["raw_", "semantic_", "stg_"] %}
    {% set ns = namespace(alias=node.name) %}
    
    {% for prefix in prefixes %}
        {% if ns.alias.startswith(prefix) %}
            {% set ns.alias = ns.alias[(prefix | length):] %}
        {% endif %}
    {% endfor %}
    
    {%- if custom_alias_name -%}
        {{ custom_alias_name | trim }}
    {%- elif node.version -%}
        {{ ns.alias ~ "_v" ~ (node.version | replace(".", "_")) }}
    {%- else -%}
        {{ ns.alias }}
    {%- endif %}
{%- endmacro %}
