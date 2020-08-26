from django.http.response import HttpResponseRedirectBase


class SlackRedirect(HttpResponseRedirectBase):
    allowed_schemes = ['slack']

