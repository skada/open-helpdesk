# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from django.contrib import messages
from django.contrib.admin.templatetags.admin_urls import admin_urlname
from django.core.urlresolvers import reverse
from django.views.generic import RedirectView

from braces.views import GroupRequiredMixin

from mezzanine.conf import settings

from .models import Ticket

settings.use_editable()


class OpenTicketView(GroupRequiredMixin, RedirectView):
    group_required = [settings.HELPDESK_OPERATORS,
                      settings.HELPDESK_ADMINS]
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        ticket_pk = kwargs.get('pk')
        ticket_changelist_url = reverse(admin_urlname(Ticket._meta,
                                                      'changelist'))
        try:
            ticket = Ticket.objects.get(pk=ticket_pk)
            ticket.open(self.request.user)
            messages.success(self.request, 'Profile details updated.')
        except Ticket.DoesNotExist:
            # TODO: messaggio di errore per ticket non trovato
            return ticket_changelist_url
        except ValueError:
            # TODO: messaggio di errore per open che ha lanciato un'eccezione
            return ticket_changelist_url
        return reverse(admin_urlname(Ticket._meta, 'change'),
                       args=(ticket_pk,))
