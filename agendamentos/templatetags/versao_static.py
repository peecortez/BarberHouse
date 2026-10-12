import os

from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def static_v(caminho):
    """Como {% static %}, mas acrescenta ?v=<data de modificação do arquivo>."""
    url = static(caminho)
    arquivo = finders.find(caminho)
    if isinstance(arquivo, str) and os.path.exists(arquivo):
        return f"{url}?v={int(os.path.getmtime(arquivo))}"
    return url