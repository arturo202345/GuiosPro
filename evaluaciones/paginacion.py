from django.core.paginator import Paginator


def paginar(request, queryset, por_pagina=20):
    """Devuelve (página, querystring sin 'page') para conservar los filtros al paginar."""
    pagina = Paginator(queryset, por_pagina).get_page(request.GET.get('page'))
    params = request.GET.copy()
    params.pop('page', None)
    return pagina, params.urlencode()
