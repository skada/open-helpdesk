# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from copy import deepcopy

from django.conf.urls import patterns, url
from django.contrib import admin
from django.contrib import messages
from django.contrib.admin.templatetags.admin_urls import admin_urlname
from django.contrib.contenttypes.generic import GenericTabularInline
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _, ugettext

from mezzanine.core.admin import TabularDynamicInlineAdmin

from .forms import TicketAdminAutocompleteForm
from .models import (
    Category, Tipology, Attachment, Ticket, HelpdeskUser, Message,
    Report, StatusChangesLog)
from .views import OpenTicketView, ObjectToolsView


class TipologyInline(TabularDynamicInlineAdmin):
    extra = 3
    model = Tipology


class MessageInline(TabularDynamicInlineAdmin):
    model = Message
    fields = ('content', 'recipient',)


class ReportTicketInline(TabularDynamicInlineAdmin):
    model = Report
    fields = ('content', 'action_on_ticket', 'visible_from_requester')

    def get_queryset(self, request):
        """If request.user is operator return queryset filterd by sender."""
        user = HelpdeskUser.get_from_request(request)
        qs = super(ReportTicketInline, self).get_queryset(request)
        if user.is_admin():
            return qs
        return qs.filter(sender=user)


class AttachmentInline(TabularDynamicInlineAdmin, GenericTabularInline):
    model = Attachment


class CategoryAdmin(admin.ModelAdmin):
    inlines = [TipologyInline]
    list_display = ['title', 'admin_tipologies']
    search_fields = ['title']


class TipologyAdmin(admin.ModelAdmin):
    list_display = ['title', 'admin_category', 'admin_sites']
    list_filter = ['category']
    search_fields = ['title', 'category__title']


class TicketAdmin(admin.ModelAdmin):
    actions = ['open_tickets']
    fieldsets = (
        (None, {
            'fields': ['tipologies', 'priority', 'content', 'related_tickets'],
        }),
    )
    filter_horizontal = ('tipologies',)
    form = TicketAdminAutocompleteForm
    inlines = [AttachmentInline, MessageInline]
    list_display = ['pk', 'admin_content', 'status', ]
    list_filter = ['priority', 'status', 'tipologies']
    list_per_page = 25
    list_select_related = True
    radio_fields = {'priority': admin.HORIZONTAL}
    readonly_fields = ['status']
    search_fields = ['content', 'user__username', 'user__first_name',
                     'user__last_name', 'requester__username',
                     'requester__first_name', 'requester__last_name',
                     'tipologies__title']

    operator_read_only_fields = ['content', 'tipologies', 'priority', 'status']
    operator_list_display = ['requester', 'created']
    operator_list_filter = ['requester', 'assignee']
    operator_actions = ['requester', 'assignee']

    # class Media:
    #     js = ('helpdesk/js/ticket.js',)

    def get_request_helpdeskuser(self, request):
        return HelpdeskUser.get_from_request(request)

    @staticmethod
    def get_object_tools(request, view_name, obj=None):
        user = HelpdeskUser.get_from_request(request)
        object_tools = {'change': []}
        admin_prefix_url = 'admin:'
        if obj:
            admin_prefix_url += '%s_%s' % (obj._meta.app_label,
                                           getattr(obj._meta, 'model_name',
                                                   obj._meta.module_name))
        if user.is_operator() or user.is_admin():
            if view_name == 'change' and obj:
                if obj.is_new():
                    object_tools[view_name].append(
                        {'url': reverse('{}_open'.format(admin_prefix_url),
                                        kwargs={'pk': obj.pk}),
                         'text': ugettext('Open and assign to me')})
                elif obj.is_open():
                    url = reverse(admin_urlname(Report._meta, 'add'))
                    object_tools[view_name].append(
                        {'url': '{}?ticket={}'.format(url, obj.pk),
                         'text': ugettext('Add report')})
        try:
            return object_tools[view_name]
        except KeyError:
            return list()

    # ModelsAdmin methods customized ##########################################
    def get_list_display(self, request):
        """
        Return default list_display if request.user is a requester. Otherwise
        if request.user is a operator or an admin return default list_display
        with operator_list_display.
        """
        user = self.get_request_helpdeskuser(request)
        list_display = list(super(TicketAdmin, self).get_list_display(request))
        if user.is_operator() or user.is_admin():
            list_display += self.operator_list_display
        return list_display

    def get_list_filter(self, request):
        """
        Return default list_filter if request.user is a requester. Otherwise
        if request.user is a operator, an admin or return default
        list_filter with append more fields.
        """
        user = self.get_request_helpdeskuser(request)
        list_filter = list(super(TicketAdmin, self).get_list_filter(request))
        if user.is_operator() or user.is_admin():
            list_filter += self.operator_list_filter
        return list_filter

    def get_fieldsets(self, request, obj=None):
        """
        Return default fieldsets if request.user is a requester.
        Otherwise request.user is a operator, an admin or superuser, append
        'requester' field to fieldsets.
        """
        user = self.get_request_helpdeskuser(request)
        fieldset = deepcopy(super(TicketAdmin, self).get_fieldsets(
            request, obj=obj))
        if user.is_operator() or user.is_admin():
            for field in ['requester', 'source']:
                fieldset[0][1]['fields'].append(field)
        if user.is_requester() and obj:
            # add custom fields so that they are in form. Otherwise are
            # ignored into "readonly_fields". Custom fields are methods of
            # Ticket model calleds 'admin_readonly_FIELD' where FIELD match
            # with a Ticket field.
            for field in ['content']:
                try:
                    index = fieldset[0][1]['fields'].index(field)
                    fieldset[0][1]['fields'][index] = (
                        'admin_readonly_{}'.format(field))
                except ValueError:  # pragma: no cover
                    pass
        if obj:
            fieldset[0][1]['fields'].append('status')
        return fieldset

    def get_formsets(self, request, obj=None):
        user = self.get_request_helpdeskuser(request)
        for inline in self.get_inline_instances(request, obj):
            if isinstance(inline, MessageInline):
                # hide MessageInline in the add view or user not is
                # a requester
                if obj is None or not user.is_requester():
                    continue  # pragma: no cover
            yield inline.get_formset(request, obj)

    def get_queryset(self, request):
        """
        Return a filtered queryset by user that match with request.user if
        request.user is a requester. Otherwise if request.user is a operator,
        an admin or superuser, queryset returned is not filtered.
        """
        user = self.get_request_helpdeskuser(request)
        # compatibility for django 1.5 where "get_queryset" method is
        # called "queryset" instead
        f_get_queryset = getattr(
            super(TicketAdmin, self), 'get_queryset', None)
        if not f_get_queryset:  # pragma: no cover
            f_get_queryset = getattr(super(TicketAdmin, self), 'queryset')
        qs = f_get_queryset(request)
        if user.is_superuser or user.is_operator() or user.is_admin():
            return qs
        return qs.filter(requester=user)

    def get_readonly_fields(self, request, obj=None):
        """
        Return a tuple with all fields if request.user is a requester.
        Otherwise return default empty readonly_fields.
        """
        if obj:
            user = self.get_request_helpdeskuser(request)
            if user.is_requester():
                fields = set()
                for e in self.get_fieldsets(request, obj=obj):
                    fields = fields.union(list(e[1]['fields']))
                return list(fields)
            elif user.is_operator() or user.is_admin():
                return list(TicketAdmin.operator_read_only_fields)
        return list(
            super(TicketAdmin, self).get_readonly_fields(request, obj=obj))

    def get_urls(self):
        # getattr is for re-compatibility django 1.5
        admin_prefix_url = '%s_%s' % (self.opts.app_label,
                                      getattr(self.opts, 'model_name',
                                              self.opts.module_name))
        urls = super(TicketAdmin, self).get_urls()
        my_urls = patterns(
            '',
            url(r'^open/(?P<pk>\d+)$',
                self.admin_site.admin_view(OpenTicketView.as_view()),
                name='{}_open'.format(admin_prefix_url)),
            url(r'^object_tools/$',
                self.admin_site.admin_view(ObjectToolsView.as_view()),
                name='{}_object_tools'.format(admin_prefix_url)),
        )
        return my_urls + urls

    def queryset(self, request):
        """
        Compatibility for django 1.5 where "get_queryset" method is
        called "queryset" instead
        """
        return self.get_queryset(request)  # pragma: no cover

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, Message):
                instance.sender = request.user
            instance.save()
        formset.save_m2m()

    def save_model(self, request, obj, form, change):
        if obj.requester_id is None:
            obj.requester = request.user
        super(TicketAdmin, self).save_model(request, obj, form, change)
        if not change:
            obj.initialize()

    # ModelsAdmin views methods customized ####################################
    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        # get the ticket's messages only if is change form
        user = self.get_request_helpdeskuser(request)
        if object_id:
            messages = user.get_messages_by_ticket(object_id)
            changelogs = StatusChangesLog.objects.filter(
                ticket_id=object_id).order_by('created')
            extra_context.update({'ticket_messages': messages,
                                  'ticket_changelogs': changelogs})
        return super(TicketAdmin, self).change_view(
            request, object_id, form_url=form_url, extra_context=extra_context)

    # ModelsAdmin actions #####################################################
    def open_tickets(self, request, queryset):
        success_msg = _('Tickets %(ticket_ids)s successfully opened'
                        ' and assigned.')
        error_msg = _('Errors occours: \n%(errors)s.')
        success_ids = []
        error_data = []
        user = self.get_request_helpdeskuser(request)
        print(type(queryset))
        if user.is_operator() or user.is_admin():
            for ticket in queryset.filter(status=Ticket.STATUS.new):
                try:
                    ticket.opening(user)
                    success_ids.append(str(ticket.pk))
                except Exception as e:
                    error_data.append((ticket.pk, str(e)))
            if success_ids:
                self.message_user(
                    request,
                    success_msg % {'ticket_ids': ','.join(success_ids)},
                    level=messages.SUCCESS)
            if error_data:
                self.message_user(
                    request,
                    error_msg % {'errors': ', '.join(
                        ['ticket {} [{}]'.format(id, exc)
                         for id, exc in error_data])},
                    level=messages.ERROR)
    open_tickets.short_description = _('Open e assign selected Tickets')

    def get_actions(self, request):
        user = self.get_request_helpdeskuser(request)
        actions = super(TicketAdmin, self).get_actions(request)
        if user.is_requester() and 'open_tickets' in actions:
            del actions['open_tickets']
        return actions


class ReportAdmin(admin.ModelAdmin):
    fields = ('ticket', 'content', 'visible_from_requester',
              'action_on_ticket')
    list_display = ['id', 'ticket', 'content', 'visible_from_requester',
                    'action_on_ticket', 'sender', 'recipient']
    search_fields = ['ticket__pk', 'ticket__content', 'content']


admin.site.register(Category, CategoryAdmin)
admin.site.register(Tipology, TipologyAdmin)
admin.site.register(Report, ReportAdmin)
admin.site.register(Ticket, TicketAdmin)
