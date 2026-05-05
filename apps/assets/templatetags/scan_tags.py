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
                '<tr>'
                f'<th style="width: 30%; background-color: #f8fafc; border: 1px solid #e2e8f0; padding: 12px 16px; text-align: left; font-weight: 600; color: #475569;">{humanized_key}</th>'
                f'<td style="border: 1px solid #e2e8f0; padding: 12px 16px; color: #1e293b;">{render_nested(subvalue)}</td>'
                '</tr>'
            )
        return '<table style="width: 100%; border-collapse: collapse; margin-bottom: 1rem; border: 1px solid #e2e8f0;"><tbody>' + ''.join(items) + '</tbody></table>'

    if isinstance(value, list):
        if all(not isinstance(item, (dict, list)) for item in value):
            items = ''.join(f'<li style="margin-bottom: 4px;">{html.escape(str(item))}</li>' for item in value)
            return '<ul style="margin: 0; padding-left: 20px; list-style-type: disc;">' + items + '</ul>'

        items = []
        for index, item in enumerate(value, start=1):
            items.append(
                '<div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-bottom: 10px;">'
                f'<div style="font-weight: 700; color: #475569; margin-bottom: 8px; font-size: 0.85rem;">🔹 Item {index}</div>'
                f'{render_nested(item)}'
                '</div>'
            )
        return '<div style="list-style: none; padding: 0; margin: 0; width: 100%;">' + ''.join(items) + '</div>'

    if value is None:
        return '<span style="color: #94a3b8; font-style: italic;">None</span>'

    return html.escape(str(value))


@register.filter(is_safe=True)
def render_nested_html(value):
    return mark_safe(render_nested(value))


@register.filter
def humanize_key(value):
    if value is None:
        return ''
    return str(value).replace('_', ' ').title()
