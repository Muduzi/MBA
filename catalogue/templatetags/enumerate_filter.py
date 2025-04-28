from django import template


register = template.Library()


@register.filter()
def enumerate_list(iterable):
    return enumerate(iterable)
