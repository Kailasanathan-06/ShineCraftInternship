from django import template
from django.utils.safestring import mark_safe
import html

register = template.Library()


def render_nested(value):
    if isinstance(value, dict):
        items = []
        for key, subvalue in value.items():
            humanized_key = html.escape(str(key)).replace('_', ' ').title()
            items.append(
                '<div class="prop-item">'
                f'<div class="prop-label">{humanized_key}</div>'
                f'<div class="prop-value">{render_nested(subvalue)}</div>'
                '</div>'
            )
        return '<div class="prop-list">' + ''.join(items) + '</div>'

    if isinstance(value, list):
        if all(not isinstance(item, (dict, list)) for item in value):
            items = ''.join(f'<li>{html.escape(str(item))}</li>' for item in value)
            return '<ul class="nested-list">' + items + '</ul>'

        items = []
        for index, item in enumerate(value, start=1):
            items.append(
                '<div class="nested-list-item">'
                f'<div class="nested-list-title">Item {index}</div>'
                f'{render_nested(item)}'
                '</div>'
            )
        return '<div class="nested-list">' + ''.join(items) + '</div>'

    if value is None:
        return '<span class="text-muted">None</span>'

    return html.escape(str(value))


@register.filter(is_safe=True)
def render_nested_html(value):
    return mark_safe(render_nested(value))


@register.filter
def humanize_key(value):
    if value is None:
        return ''
    return str(value).replace('_', ' ').title()
