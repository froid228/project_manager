from django import template


register = template.Library()


@register.filter
def ru_plural(value, forms):
    try:
        number = abs(int(value))
    except (TypeError, ValueError):
        return value

    choices = [item.strip() for item in forms.split(",")]
    if len(choices) != 3:
        return value

    last_two = number % 100
    last_one = number % 10

    if 11 <= last_two <= 14:
        form = choices[2]
    elif last_one == 1:
        form = choices[0]
    elif 2 <= last_one <= 4:
        form = choices[1]
    else:
        form = choices[2]

    return f"{value} {form}"
