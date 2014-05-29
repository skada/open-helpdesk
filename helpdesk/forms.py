# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from mezzanine.conf import settings


class TicketAdminForm(forms.ModelForm):
    def clean_tipologies(self):
        """
        Additional validation for 'tipologies' field. If the number of
        tipologies selected is greater than 'HELPDESK_TICKET_MAX_TIPOLOGIES'
        setting, raise an ValidationError
        """
        settings.use_editable()
        max_tipologies = settings.HELPDESK_TICKET_MAX_TIPOLOGIES
        tipologies = self.cleaned_data['tipologies']
        if len(tipologies) > max_tipologies:
            msg = _('Too many tipologies selected. You can select a maximum'
                    ' of %(max)s.') % {'max': max_tipologies}
            raise ValidationError(msg, code='too_many_tipologies')
        return self.cleaned_data['tipologies']